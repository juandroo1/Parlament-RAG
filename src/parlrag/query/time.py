"""Zeitraum in der Frage erkennen (Spec 003, AK-17.1; plan.md Abschnitt 4, Protokoll).

Muster auf Deutsch und Französisch, verglichen in normalisierter Form (ohne Akzente):

- Session: «Herbstsession 2025», «session d'automne 2025» → Daten der Session aus dem Katalog;
  fehlt sie dort (vor oder nach den Daten), ihr Kalendermonat. «letzte Session»/«dernière session».
- Monat und Jahr: «im März 2025», «en mars 2025».
- Bereiche: «seit/ab/nach 2024», «vor/bis 2025», «zwischen 2024 und 2025», «von 2024 bis 2025»,
  «depuis/dès/après/avant/jusqu'en …», «entre … et …», «de … à …».
- Jahr: nach einer Präposition («im Jahr 2025», «en 2024»), nach einer Person oder Funktion
  («Funiciello 2022», «der Bundesrat 2024») oder auf Deutsch nach einem kleingeschriebenen Wort
  («Was wurde 2024 …»). Nach einem deutschen Nomen oder französischen Wort ohne Signal ist sie
  Teil eines Titels («Voranschlag 2025», «budget 2022») und zählt nicht.

Jahreszahlen nach dem laufenden Jahr zählen nur in Session oder Monat («Frühjahrssession 2027»),
sonst sind sie ein Ziel («bis 2050»). Die erste Angabe in der Frage gilt; widersprüchliche
Bereiche ergeben keinen Zeitraum.
"""

import calendar
import datetime as dt
from dataclasses import dataclass
from typing import Literal

from parlrag.query.catalog import CALENDAR_MONTH, Catalog, SessionKind
from parlrag.query.tokens import FUNCTION_WORDS, Token

PeriodKind = Literal["year", "month", "session", "range", "last_session"]

MONTHS = {
    "januar": 1,
    "janner": 1,
    "februar": 2,
    "marz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
    "janvier": 1,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "decembre": 12,
}

GERMAN_SESSIONS: dict[str, SessionKind] = {
    "fruhjahrssession": "spring",
    "fruhlingssession": "spring",
    "sondersession": "special",
    "sommersession": "summer",
    "herbstsession": "autumn",
    "wintersession": "winter",
}
# «session de printemps», «session d'été», «session d'automne», «session d'hiver»,
# «session spéciale»
FRENCH_SESSIONS: dict[str, SessionKind] = {
    "printemps": "spring",
    "speciale": "special",
    "ete": "summer",
    "automne": "autumn",
    "hiver": "winter",
}

# Präpositionen, nach denen eine Jahreszahl ein Zeitraum ist.
YEAR_PREPOSITIONS = frozenset(
    {
        "im",
        "in",
        "jahr",
        "wahrend",
        "anno",
        "en",
        "durant",
        "pendant",
        "an",
        "annee",
        "cours",
    }
)
FROM_WORDS = frozenset({"seit", "ab", "depuis", "des"})
AFTER_WORDS = frozenset({"nach", "apres"})
BEFORE_WORDS = frozenset({"vor", "avant"})
UNTIL_WORDS = frozenset({"bis", "jusqu"})
RANGE_START = frozenset({"zwischen", "von", "entre", "de"})
RANGE_JOIN = frozenset({"und", "bis", "et", "a"})


@dataclass(frozen=True)
class Period:
    date_from: dt.date | None
    date_to: dt.date | None
    kind: PeriodKind
    start: int  # Wortindex der Angabe
    end: int


def _year(token: Token) -> int | None:
    if token.is_number and len(token.text) == 4 and token.text[:2] in ("19", "20"):
        return int(token.text)
    return None


def _month_range(year: int, month: int) -> tuple[dt.date, dt.date]:
    return dt.date(year, month, 1), dt.date(year, month, calendar.monthrange(year, month)[1])


def _session_period(kind: SessionKind, year: int, catalog: Catalog, start: int, end: int) -> Period:
    session = catalog.session(kind, year)
    if session is not None:
        return Period(session.first, session.last, "session", start, end)
    first, last = _month_range(year, CALENDAR_MONTH[kind])
    return Period(first, last, "session", start, end)


def _sessions(tokens: list[Token], catalog: Catalog) -> list[Period]:
    found = []
    norms = [t.norm for t in tokens]
    for i, word in enumerate(norms):
        year = _year(tokens[i + 1]) if i + 1 < len(tokens) else None
        if word in GERMAN_SESSIONS and year:
            found.append(_session_period(GERMAN_SESSIONS[word], year, catalog, i, i + 2))
        if word == "session":
            # «session d'automne 2025» (session, d, automne, 2025) oder «session spéciale 2025»
            rest = norms[i + 1 : i + 4]
            for offset, part in enumerate(rest[:2], start=1):
                if part in FRENCH_SESSIONS and i + offset + 1 < len(tokens):
                    year = _year(tokens[i + offset + 1])
                    if year:
                        kind = FRENCH_SESSIONS[part]
                        found.append(_session_period(kind, year, catalog, i, i + offset + 2))
                    break
        last = catalog.last_session
        if last is not None:
            if word in ("letzte", "letzten") and i + 1 < len(norms) and norms[i + 1] == "session":
                found.append(Period(last.first, last.last, "last_session", i, i + 2))
            if word in ("derniere",) and i + 1 < len(norms) and norms[i + 1] == "session":
                found.append(Period(last.first, last.last, "last_session", i, i + 2))
    return found


def _months(tokens: list[Token]) -> list[Period]:
    found = []
    for i, token in enumerate(tokens[:-1]):
        month = MONTHS.get(token.norm)
        year = _year(tokens[i + 1])
        if month and year:
            first, last = _month_range(year, month)
            found.append(Period(first, last, "month", i, i + 2))
    return found


def _ranges(tokens: list[Token], today: dt.date) -> list[Period | None]:
    """Bereiche; `None` steht für einen widersprüchlichen Bereich (dann kein Zeitraum)."""
    found: list[Period | None] = []
    norms = [t.norm for t in tokens]

    def past_year(k: int) -> int | None:
        year = _year(tokens[k]) if 0 <= k < len(tokens) else None
        return year if year is not None and year <= today.year else None

    i = 0
    while i < len(tokens):
        word = norms[i]
        # «à partir de 2024», «jusqu'en 2024», «jusqu'à 2024»
        offset = 1
        if word == "a" and norms[i + 1 : i + 3] == ["partir", "de"]:
            word, offset = "des", 3
        if word == "jusqu" and i + 1 < len(norms) and norms[i + 1] in ("en", "a"):
            offset = 2
        first_year = past_year(i + offset)
        if first_year is None:
            i += 1
            continue
        after = i + offset + 1
        joined = after + 1 < len(tokens) and norms[after] in RANGE_JOIN
        second = past_year(after + 1) if joined else None
        if second is not None and (word in RANGE_START or word in FROM_WORDS):
            if second < first_year:
                found.append(None)
            else:
                period = Period(
                    dt.date(first_year, 1, 1), dt.date(second, 12, 31), "range", i, after + 2
                )
                found.append(period)
            i = after + 2
            continue
        if word in FROM_WORDS:
            found.append(Period(dt.date(first_year, 1, 1), None, "range", i, after))
        elif word in AFTER_WORDS:
            found.append(Period(dt.date(first_year + 1, 1, 1), None, "range", i, after))
        elif word in BEFORE_WORDS:
            found.append(Period(None, dt.date(first_year - 1, 12, 31), "range", i, after))
        elif word in UNTIL_WORDS:
            found.append(Period(None, dt.date(first_year, 12, 31), "range", i, after))
        i += 1
    return found


def _years(
    tokens: list[Token], today: dt.date, person_ends: set[int], german: bool
) -> list[Period]:
    found = []
    for i, token in enumerate(tokens):
        year = _year(token)
        if year is None or year > today.year:
            continue
        before = tokens[i - 1] if i > 0 else None
        counts = (
            before is None
            or before.norm in YEAR_PREPOSITIONS
            or before.norm in FUNCTION_WORDS
            or i in person_ends
            or (german and not before.capitalized and not before.is_number)
        )
        if counts:
            found.append(Period(dt.date(year, 1, 1), dt.date(year, 12, 31), "year", i, i + 1))
    return found


def detect_period(
    tokens: list[Token],
    catalog: Catalog,
    today: dt.date,
    *,
    person_ends: frozenset[int] = frozenset(),
    german: bool = True,
) -> Period | None:
    """Erste Zeitangabe der Frage; None ohne Angabe oder bei widersprüchlichem Bereich.

    `person_ends`: Wortindizes direkt nach einem erkannten Namen («Funiciello 2022»)."""
    candidates: list[Period | None] = [
        *_sessions(tokens, catalog),
        *_months(tokens),
        *_ranges(tokens, today),
        *_years(tokens, today, set(person_ends), german),
    ]
    if any(candidate is None for candidate in candidates):
        return None
    periods = [candidate for candidate in candidates if candidate is not None]
    if not periods:
        return None
    first_start = min(period.start for period in periods)
    # Bei gleichem Anfang die längste Angabe («zwischen 2024 und 2025» vor «2024»).
    return max(
        (period for period in periods if period.start == first_start),
        key=lambda period: period.end,
    )
