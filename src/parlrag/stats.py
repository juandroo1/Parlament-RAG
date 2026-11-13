"""Statistik über den Bestand in `documents` (Task 1.4).

Mit `session_id` wird eingeschränkt auf die Voten dieser Session und auf Geschäfte, die
im Zeitraum dieser Voten debattiert wurden (`debate_dates`).
"""

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Connection, Engine, text

from parlrag.db.scope import SESSION_SCOPE_CTE

CHARS_PER_TOKEN_ESTIMATE = 4  # grobe Faustregel; echte Zahlen mit dem Tokenizer in Task 2.1

# Reste von Markup oder Platzhaltern des Amtlichen Bulletins (Textbereinigung, Task 1.2).
# Nur die Tags und Platzhalter, die in den Quellen vorkommen; Links in spitzen Klammern
# (<https://…>) oder Abkürzungen wie [VStG] sind normaler Text (Fehlalarme in Task 2.6).
# Achtung: In Postgres-Regex ist `\b` ein Backspace, keine Wortgrenze.
RESIDUAL_MARKUP_PATTERN = (
    r"</?(pd_text|p|b|i|br|span|ul|ol|li|h[1-6]|strong|em|div|a|table|tr|td)([\s/][^>]*)?>"
    r"|\[(GZ|VS|NB|NAM|PAGE ?[0-9]*)\]"
)


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


@dataclass(frozen=True)
class IndexSummary:
    """Stand des Index im gewählten Umfang (Task 2.6)."""

    indexed_documents: int = 0
    chunks: int = 0
    mean_chunk_tokens: float = 0.0
    chunks_by_signature: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class StorageSizes:
    """Speicherbedarf in Bytes; immer für die ganze Datenbank, unabhängig vom Umfang."""

    database: int = 0
    documents_table: int = 0
    chunks_table: int = 0
    vector_index: int = 0


@dataclass
class CorpusStats:
    by_type_language: dict[tuple[str, str], int] = field(default_factory=dict)
    lengths: dict[str, LengthStats] = field(default_factory=dict)
    transcripts_by_council: dict[str, int] = field(default_factory=dict)
    transcripts_by_parl_group: dict[str, int] = field(default_factory=dict)
    first_date: dt.date | None = None
    last_date: dt.date | None = None
    quality: dict[str, int] = field(default_factory=dict)
    index: IndexSummary = field(default_factory=IndexSummary)
    storage: StorageSizes = field(default_factory=StorageSizes)

    @property
    def total_documents(self) -> int:
        return sum(self.by_type_language.values())


def _rows(connection: Connection, query: str, session_id: int | None, **params: Any) -> list[Any]:
    return list(
        connection.execute(text(SESSION_SCOPE_CTE + query), {"session_id": session_id, **params})
    )


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

        ((indexed, chunks, mean_tokens),) = _rows(
            connection,
            "SELECT count(DISTINCT c.document_id), count(*), coalesce(avg(c.token_count), 0) "
            "FROM chunks c JOIN scope s ON s.id = c.document_id",
            session_id,
        )
        signatures = _rows(
            connection,
            "SELECT coalesce(c.metadata ->> 'index', '-'), count(*) "
            "FROM chunks c JOIN scope s ON s.id = c.document_id GROUP BY 1 ORDER BY 2 DESC, 1",
            session_id,
        )
        stats.index = IndexSummary(
            indexed_documents=indexed,
            chunks=chunks,
            mean_chunk_tokens=float(mean_tokens),
            chunks_by_signature={signature: count for signature, count in signatures},
        )

        sizes = connection.execute(
            text(
                "SELECT pg_database_size(current_database()), "
                "pg_total_relation_size('documents'), pg_total_relation_size('chunks'), "
                "coalesce(pg_relation_size(to_regclass('ix_chunks_embedding_hnsw')), 0)"
            )
        ).one()
        stats.storage = StorageSizes(*(int(value) for value in sizes))
    return stats
