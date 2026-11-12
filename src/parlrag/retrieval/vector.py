"""Vektorsuche (Cosine) über den HNSW-Index (Entscheidungsprotokoll, Task 2.4).

pgvector liefert mit den Standardwerten höchstens `hnsw.ef_search` = 40 Treffer und filtert
nach dem Index-Scan. Deshalb pro Abfrage (nur in dieser Transaktion):
- `hnsw.ef_search` = max(100, 2 * limit),
- `hnsw.iterative_scan = relaxed_order` (pgvector ≥ 0.8): Der Scan läuft weiter, bis genug
  Treffer den Filter erfüllen; danach wird exakt nach Distanz sortiert.
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Connection, bindparam, text

from parlrag.db.models import EMBEDDING_DIMENSIONS
from parlrag.embeddings import Vectors
from parlrag.retrieval.filters import FILTER_SQL, SearchFilters

VECTOR_SQL = text(f"""
WITH candidates AS MATERIALIZED (
    SELECT c.id, c.embedding <=> :query_vector AS distance
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.embedding IS NOT NULL AND {FILTER_SQL}
    ORDER BY distance
    LIMIT :limit
)
SELECT id, 1 - distance AS similarity FROM candidates ORDER BY distance, id
""").bindparams(bindparam("query_vector", type_=Vector(EMBEDDING_DIMENSIONS)))


def search_vector(
    connection: Connection, query_vector: Vectors, filters: SearchFilters, limit: int
) -> list[tuple[uuid.UUID, float]]:
    """(Chunk-ID, Cosine-Ähnlichkeit) absteigend. Muss in einer Transaktion laufen."""
    connection.execute(
        text(
            "SELECT set_config('hnsw.ef_search', :ef_search, true), "
            "set_config('hnsw.iterative_scan', 'relaxed_order', true)"
        ),
        {"ef_search": str(max(100, 2 * limit))},
    )
    rows = connection.execute(
        VECTOR_SQL, {"query_vector": query_vector, "limit": limit, **filters.sql_params()}
    )
    return [(row[0], float(row[1])) for row in rows]
