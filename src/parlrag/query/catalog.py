"""Katalog für die Erkennung (Spec 003, plan.md Abschnitt 3): abgedeckter Zeitraum, Sessionen und
Personen, alles aus `documents` abgeleitet. In Tests wird er direkt gebaut (AK-17.6)."""

import datetime as dt
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Connection, text

from parlrag.query.speakers import Speaker, list_speakers

SessionKind = Literal["spring", "special", "summer", "autumn", "winter"]

# Art der Session aus dem Monat ihrer Mitte (z. B. Herbstsession 15.9. bis 2.10.: September).
KIND_BY_MONTH: dict[int, SessionKind] = {
    2: "spring",
    3: "spring",
    4: "special",
    5: "special",
    6: "summer",
    9: "autumn",
    10: "autumn",
    11: "winter",
    12: "winter",
}

# Kalenderfenster einer Session, die nicht im Katalog ist (z. B. «Herbstsession 2022»): ganzer
# Monat, in dem diese Session üblicherweise stattfindet. Reicht für «ausserhalb» (AK-16.1).
CALENDAR_MONTH: dict[SessionKind, int] = {
    "spring": 3,
    "special": 5,
    "summer": 6,
    "autumn": 9,
    "winter": 12,
}

RANGE_SQL = text("SELECT min(date), max(date) FROM documents WHERE source_type = 'transcript'")
SESSIONS_SQL = text("""
SELECT session_id, min(date) AS first, max(date) AS last
FROM documents
WHERE source_type = 'transcript' AND session_id IS NOT NULL
GROUP BY session_id
ORDER BY min(date)
""")


@dataclass(frozen=True)
class Session:
    id: int
    kind: SessionKind
    year: int
    first: dt.date
    last: dt.date


@dataclass(frozen=True)
class Catalog:
    """Erstes und letztes Datum der Voten (None ohne Voten), Sessionen, Personen."""

    first: dt.date | None
    last: dt.date | None
    sessions: tuple[Session, ...]
    speakers: tuple[Speaker, ...]

    def session(self, kind: SessionKind, year: int) -> Session | None:
        return next((s for s in self.sessions if s.kind == kind and s.year == year), None)

    @property
    def last_session(self) -> Session | None:
        return max(self.sessions, key=lambda s: s.first, default=None)


def session_kind(first: dt.date, last: dt.date) -> SessionKind | None:
    middle = first + (last - first) / 2
    return KIND_BY_MONTH.get(middle.month)


def build_sessions(rows: list[tuple[int, dt.date, dt.date]]) -> tuple[Session, ...]:
    sessions = []
    for session_id, first, last in rows:
        kind = session_kind(first, last)
        if kind is not None:
            middle = first + (last - first) / 2
            sessions.append(Session(session_id, kind, middle.year, first, last))
    return tuple(sessions)


def load_catalog(connection: Connection) -> Catalog:
    first, last = connection.execute(RANGE_SQL).one()
    rows = [(row.session_id, row.first, row.last) for row in connection.execute(SESSIONS_SQL)]
    return Catalog(
        first=first,
        last=last,
        sessions=build_sessions(rows),
        speakers=tuple(list_speakers(connection)),
    )
