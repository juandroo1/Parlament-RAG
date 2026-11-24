"""Person und Zeitraum aus einer Frage (Spec 003, US-17; plan.md Abschnitte 4 und 5).

Ein reines Modul: Frage, Katalog und heutiges Datum rein, Erkennung raus. Kein LLM, keine
Datenbank, kein Netz (AK-17.6). Die Person wird zuerst erkannt, weil die Regel für eine
allein stehende Jahreszahl sie braucht («Funiciello 2022»).
"""

import datetime as dt
from dataclasses import dataclass
from functools import lru_cache

from parlrag.query.catalog import Catalog
from parlrag.query.person import PersonMatch, SpeakerIndex, detect_person
from parlrag.query.speakers import Speaker
from parlrag.query.time import Period, detect_period
from parlrag.query.tokens import tokenize
from parlrag.retrieval.fulltext import detect_query_language


@dataclass(frozen=True)
class Detection:
    """Erkannte Angaben einer Frage; leer, wenn nichts erkannt wurde."""

    period: Period | None = None
    speaker: Speaker | None = None
    speaker_candidates: tuple[Speaker, ...] = ()
    title_mention: bool = False  # ein Name als Teil eines Geschäftstitels («Initiative X»)
    # Textstellen [start, end) von erkannter Person und Zeitraum in der Frage
    speaker_spans: tuple[tuple[int, int], ...] = ()
    period_span: tuple[int, int] | None = None

    @property
    def empty(self) -> bool:
        return self.period is None and self.speaker is None and not self.speaker_candidates


@lru_cache(maxsize=4)
def speaker_index(speakers: tuple[Speaker, ...]) -> SpeakerIndex:
    return SpeakerIndex.build(speakers)


def detect(question: str, catalog: Catalog, today: dt.date) -> Detection:
    tokens = tokenize(question)
    person: PersonMatch = detect_person(tokens, speaker_index(catalog.speakers))
    period = detect_period(
        tokens,
        catalog,
        today,
        person_ends=frozenset(end for _, end in person.spans),
        german=detect_query_language(question) != "fr",
    )
    speaker_spans = (
        tuple((tokens[start].start, tokens[end - 1].end) for start, end in person.spans)
        if person.speaker is not None
        else ()
    )
    period_span = (
        (tokens[period.start].start, tokens[period.end - 1].end) if period is not None else None
    )
    return Detection(
        period=period,
        speaker=person.speaker,
        speaker_candidates=person.candidates,
        title_mention=person.title,
        speaker_spans=speaker_spans,
        period_span=period_span,
    )
