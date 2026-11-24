"""Personen in der Frage erkennen (Spec 003, AK-17.1, AK-17.3; plan.md Abschnitt 5).

Abgleich über Wörter mit den Namen im Katalog («Nachname Vorname»; das letzte Wort gilt als
Vorname). Regeln:

- Eine Folge von Wörtern, die alle im Namen einer Person vorkommen, mit mindestens einem Wort,
  das nicht der Vorname ist («Funiciello», «Tamara Funiciello», «Michaud Gigon»).
- Nur ein Wort (der Nachname) zählt nur grossgeschrieben, ohne Artikel davor («der Fischer») und
  mit einem Signal: Funktion oder Zuschreibung direkt davor («Bundesrat Rösti», «laut Würth»,
  «selon Amaudruz») oder ein Verb des Sagens in der Frage («Was sagte Funiciello …»).
- Eine Funktion davor schränkt ein («Bundesrat Pfister», «Nationalrat Müller»).
- Passt der Treffer auf mehrere Personen, wird nicht gefiltert; die Personen sind Kandidaten.
- Steht ein Geschäftstyp davor («Initiative Funiciello», «Motion Aeschi»), ist das ein Titel,
  keine Person.
- Mehrere verschiedene Personen in einer Frage: kein Filter, alle sind Kandidaten.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from parlrag.query.speakers import Speaker
from parlrag.query.tokens import FUNCTION_WORDS, Token, normalize

# Namenspartikel: zählen nur innerhalb eines Namens, nie allein («de Quattro», «von Siebenthal»).
PARTICLES = frozenset({"de", "von", "van", "la", "le", "du", "di", "da", "dal", "del"})

# Geschäftstypen vor einem Namen: Titel eines Geschäfts, keine Rednerin.
TITLE_WORDS = frozenset(
    {
        "initiative",
        "motion",
        "postulat",
        "interpellation",
        "anfrage",
        "standesinitiative",
        "parlementaire",
        "volksinitiative",
        "pa",
        "iv",
        "mo",
        "po",
    }
)

# Artikel vor einem einzelnen Wort: ein Nomen, keine Person («zur Lage der Fischer»).
ARTICLES = frozenset(
    {
        "der",
        "die",
        "das",
        "den",
        "dem",
        "des",
        "ein",
        "eine",
        "einer",
        "einen",
        "einem",
        "le",
        "la",
        "les",
        "l",
        "un",
        "une",
        "aux",
        "au",
    }
)

# Zuschreibung direkt vor dem Namen.
ATTRIBUTION_WORDS = frozenset({"laut", "gemass", "gemaess", "von", "selon", "apres", "par"})

# Verben des Sagens und Argumentierens als Wortanfang (normalisiert), Deutsch und Französisch.
SPEECH_STEMS = (
    "sag",
    "gesagt",
    "meint",
    "gemeint",
    "betont",
    "erklart",
    "begrund",
    "argumentier",
    "entgegn",
    "forder",
    "gefordert",
    "kritisier",
    "antwort",
    "geantwortet",
    "hielt",
    "fand",
    "verlangt",
    "beantragt",
    "lehnt",
    "befurwort",
    "sprach",
    "gesprochen",
    "ausserte",
    "geaussert",
    "warnt",
    "gewarnt",
    "verwies",
    "reagiert",
    "bezeichnet",
    "empfahl",
    "stellte",
    "wollte",
    "dit",
    "dire",
    "declar",
    "affirm",
    "expliqu",
    "soulign",
    "repond",
    "defend",
    "present",
    "justifi",
    "estim",
    "critiqu",
    "insist",
    "rappel",
    "indiqu",
    "precis",
    "recommand",
    "plaid",
    "evoqu",
)


@dataclass(frozen=True)
class PersonMatch:
    """Ergebnis: eine eindeutige Person, Kandidaten (mehrdeutig) oder ein Titel."""

    speaker: Speaker | None = None
    candidates: tuple[Speaker, ...] = ()
    title: bool = False  # Name als Teil eines Geschäftstitels erkannt
    spans: tuple[tuple[int, int], ...] = field(default=())  # Wortindizes [start, end) der Namen


@dataclass(frozen=True)
class SpeakerIndex:
    """Wort → Personen; je Person die Namenswörter und das Wort des Vornamens."""

    speakers: tuple[Speaker, ...]
    by_word: dict[str, frozenset[int]]
    first_name: tuple[str, ...]

    @classmethod
    def build(cls, speakers: tuple[Speaker, ...]) -> "SpeakerIndex":
        by_word: dict[str, set[int]] = defaultdict(set)
        first_names = []
        for i, speaker in enumerate(speakers):
            words = [normalize(word) for word in speaker.name.split()]
            for word in words:
                by_word[word].add(i)
            first_names.append(words[-1] if len(words) > 1 else "")
        return cls(
            speakers=speakers,
            by_word={word: frozenset(ids) for word, ids in by_word.items()},
            first_name=tuple(first_names),
        )


@dataclass(frozen=True)
class _Run:
    start: int
    end: int
    ids: frozenset[int]


def _runs(tokens: list[Token], index: SpeakerIndex) -> list[_Run]:
    """Längste Wortfolgen, deren Wörter alle zu derselben Person passen."""
    runs: list[_Run] = []
    i = 0
    while i < len(tokens):
        ids = index.by_word.get(tokens[i].norm)
        if not ids or tokens[i].norm in PARTICLES:
            i += 1
            continue
        best = _Run(i, i + 1, ids)
        j = i + 1
        current = ids
        while j < len(tokens):
            more = index.by_word.get(tokens[j].norm)
            if not more or not (current & more):
                break
            current = current & more
            j += 1
            best = _Run(i, j, current)
        # Partikel vor dem Namen mitnehmen («de Quattro»).
        start = best.start
        while start > 0 and tokens[start - 1].norm in PARTICLES:
            ids_with = index.by_word.get(tokens[start - 1].norm, frozenset()) & best.ids
            if not ids_with:
                break
            start -= 1
            best = _Run(start, best.end, ids_with)
        runs.append(best)
        i = best.end
    return runs


def _has_speech_verb(tokens: list[Token]) -> bool:
    return any(token.norm.startswith(SPEECH_STEMS) for token in tokens)


def _candidates(run: _Run, tokens: list[Token], index: SpeakerIndex) -> frozenset[int]:
    """Personen, bei denen der Treffer mehr als nur den Vornamen umfasst."""
    words = {tokens[k].norm for k in range(run.start, run.end)} - PARTICLES
    return frozenset(i for i in run.ids if words - {index.first_name[i]})


# Funktion vor dem Namen → Bundesrat, Nationalrat oder Ständerat.
FEDERAL_COUNCIL_ROLE = frozenset(
    {
        "bundesrat",
        "bundesratin",
        "bundesprasident",
        "bundesprasidentin",
        "federal",
        "federale",
        "confederation",
    }
)
NATIONAL_COUNCIL_ROLE = frozenset({"nationalrat", "nationalratin", "national", "nationale"})
STATES_COUNCIL_ROLE = frozenset({"standerat", "standeratin", "etats"})


def _by_role(ids: frozenset[int], before: str, index: SpeakerIndex) -> frozenset[int]:
    """Kandidaten nach der Funktion davor einschränken; passt keiner, bleiben alle."""
    if before in FEDERAL_COUNCIL_ROLE:
        narrowed = {i for i in ids if index.speakers[i].federal_council}
    elif before in NATIONAL_COUNCIL_ROLE:
        narrowed = {
            i
            for i in ids
            if not index.speakers[i].federal_council and index.speakers[i].council == "NR"
        }
    elif before in STATES_COUNCIL_ROLE:
        narrowed = {
            i
            for i in ids
            if not index.speakers[i].federal_council and index.speakers[i].council == "SR"
        }
    else:
        return ids
    return frozenset(narrowed) or ids


def detect_person(tokens: list[Token], index: SpeakerIndex) -> PersonMatch:
    speech = _has_speech_verb(tokens)
    found: list[tuple[_Run, frozenset[int]]] = []
    title = False
    for run in _runs(tokens, index):
        ids = _candidates(run, tokens, index)
        if not ids:
            continue
        before = tokens[run.start - 1].norm if run.start > 0 else ""
        if before in TITLE_WORDS:
            title = True
            continue
        name_words = [t for t in tokens[run.start : run.end] if t.norm not in PARTICLES]
        if len(name_words) == 1:
            single = name_words[0]
            signal = before in FUNCTION_WORDS or before in ATTRIBUTION_WORDS or speech
            if not single.capitalized or not signal or before in ARTICLES:
                continue
        # Die Funktion davor schränkt ein («Bundesrat Pfister»: Martin, nicht Gerhard Pfister).
        found.append((run, _by_role(ids, before, index)))

    if not found:
        return PersonMatch(title=title)
    spans = tuple((run.start, run.end) for run, _ in found)
    distinct = {ids for _, ids in found}
    all_ids = sorted(frozenset().union(*distinct), key=lambda i: index.speakers[i].name)
    if len(distinct) == 1 and len(next(iter(distinct))) == 1:
        (only,) = next(iter(distinct))
        return PersonMatch(speaker=index.speakers[only], title=title, spans=spans)
    return PersonMatch(
        candidates=tuple(index.speakers[i] for i in all_ids), title=title, spans=spans
    )
