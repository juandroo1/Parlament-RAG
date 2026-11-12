"""Statistik über den Bestand in `documents` (Task 1.4).

Mit `session_id` wird eingeschränkt auf die Voten dieser Session und auf Geschäfte, die
im Zeitraum dieser Voten debattiert wurden (`debate_dates`).
"""

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Connection, Engine, text

CHARS_PER_TOKEN_ESTIMATE = 4  # grobe Faustregel; echte Zahlen mit dem Tokenizer in Task 2.1

# Reste von Markup oder Platzhaltern des Amtlichen Bulletins (Textbereinigung, Task 1.2).
RESIDUAL_MARKUP_PATTERN = r"<[a-zA-Z/]|\[(GZ|VS|NB|NAM|PAGE)"

_SCOPE = """
WITH session_days AS (
    SELECT min(date) AS first_day, max(date) AS last_day
    FROM documents
    WHERE source_type = 'transcript' AND session_id = CAST(:session_id AS integer)
),
scope AS (
    SELECT d.* FROM documents d
    WHERE CAST(:session_id AS integer) IS NULL
       OR (d.source_type = 'transcript' AND d.session_id = CAST(:session_id AS integer))
       OR (d.source_type = 'business' AND EXISTS (
            SELECT 1 FROM unnest(d.debate_dates) AS debate(day), session_days s
            WHERE debate.day BETWEEN s.first_day AND s.last_day))
)
"""


@dataclass(frozen=True)
class LengthStats:
    documents: int
    total_chars: int
    mean_chars: float
    median_chars: float
    p90_chars: float
    max_chars: int

    @property
    def estimated_tokens(self) -> int:
        return self.total_chars // CHARS_PER_TOKEN_ESTIMATE


@dataclass
class CorpusStats:
    by_type_language: dict[tuple[str, str], int] = field(default_factory=dict)
    lengths: dict[str, LengthStats] = field(default_factory=dict)
    transcripts_by_council: dict[str, int] = field(default_factory=dict)
    transcripts_by_parl_group: dict[str, int] = field(default_factory=dict)
    first_date: dt.date | None = None
    last_date: dt.date | None = None
    quality: dict[str, int] = field(default_factory=dict)

    @property
    def total_documents(self) -> int:
        return sum(self.by_type_language.values())


def _rows(connection: Connection, query: str, session_id: int | None, **params: Any) -> list[Any]:
    return list(connection.execute(text(_SCOPE + query), {"session_id": session_id, **params}))


def compute_stats(engine: Engine, session_id: int | None = None) -> CorpusStats:
    stats = CorpusStats()
    with engine.connect() as connection:
        for source_type, language, count in _rows(
            connection,
            "SELECT source_type, language, count(*) FROM scope GROUP BY 1, 2 ORDER BY 1, 2",
            session_id,
        ):
            stats.by_type_language[(source_type, language)] = count

        for row in _rows(
            connection,
            """
            SELECT source_type, count(*), sum(length(text)), avg(length(text)),
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY length(text)),
                   percentile_cont(0.9) WITHIN GROUP (ORDER BY length(text)),
                   max(length(text))
            FROM scope GROUP BY 1 ORDER BY 1
            """,
            session_id,
        ):
            stats.lengths[row[0]] = LengthStats(
                documents=row[1],
                total_chars=int(row[2]),
                mean_chars=float(row[3]),
                median_chars=float(row[4]),
                p90_chars=float(row[5]),
                max_chars=int(row[6]),
            )

        for council, count in _rows(
            connection,
            "SELECT coalesce(council, '-'), count(*) FROM scope "
            "WHERE source_type = 'transcript' GROUP BY 1 ORDER BY 2 DESC, 1",
            session_id,
        ):
            stats.transcripts_by_council[council] = count

        for group, count in _rows(
            connection,
            "SELECT coalesce(parl_group, 'ohne Fraktion'), count(*) FROM scope "
            "WHERE source_type = 'transcript' GROUP BY 1 ORDER BY 2 DESC, 1",
            session_id,
        ):
            stats.transcripts_by_parl_group[group] = count

        ((first, last),) = _rows(
            connection,
            "SELECT min(date), max(date) FROM scope WHERE source_type = 'transcript'",
            session_id,
        )
        stats.first_date, stats.last_date = first, last

        ((markup, empty_title, no_speaker, no_chunks),) = _rows(
            connection,
            """
            SELECT
                count(*) FILTER (WHERE text ~ :markup),
                count(*) FILTER (WHERE btrim(title) = ''),
                count(*) FILTER (WHERE source_type = 'transcript' AND speaker_name IS NULL),
                count(*) FILTER (WHERE NOT EXISTS (
                    SELECT 1 FROM chunks c WHERE c.document_id = scope.id))
            FROM scope
            """,
            session_id,
            markup=RESIDUAL_MARKUP_PATTERN,
        )
        stats.quality = {
            "Restmarkup": markup,
            "leerer Titel": empty_title,
            "Votum ohne Redner": no_speaker,
            "ohne Chunks": no_chunks,
        }
    return stats
