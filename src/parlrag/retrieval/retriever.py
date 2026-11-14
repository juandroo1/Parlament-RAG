"""Retriever: Volltext und Vektor, fusioniert mit RRF (plan.md, Abschnitt 6).

Modi: `vector` (Standard gemäss Baseline in Task 3.3, einstellbar über `RETRIEVAL_MODE`),
`fulltext` und `hybrid`. In den Einzelmodi ist der Score ebenfalls 1 / (k + Rang), damit alle
Modi vergleichbar sind. `fulltext` lädt kein Embedding-Modell.
"""

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine, bindparam, text

from parlrag.config import SearchMode, Settings
from parlrag.embeddings import Embedder
from parlrag.retrieval.filters import SearchFilters
from parlrag.retrieval.fulltext import search_fulltext
from parlrag.retrieval.fusion import reciprocal_rank_fusion
from parlrag.retrieval.vector import search_vector

__all__ = ["RetrievalConfig", "Retriever", "SearchHit", "SearchMode"]


@dataclass(frozen=True)
class RetrievalConfig:
    candidates: int = 50
    rrf_k: int = 60
    top_n: int = 20
    mode: SearchMode = "vector"

    @classmethod
    def from_settings(cls, settings: Settings) -> "RetrievalConfig":
        return cls(
            candidates=settings.retrieval_candidates,
            rrf_k=settings.retrieval_rrf_k,
            top_n=settings.retrieval_top_n,
            mode=settings.retrieval_mode,
        )


@dataclass(frozen=True)
class SearchHit:
    """Ein Treffer mit allem, was die Quellenangabe braucht (AK-2.1, AK-2.2)."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    text: str
    section: str | None
    score: float
    rank: int
    fulltext_rank: int | None
    fulltext_score: float | None
    vector_rank: int | None
    vector_similarity: float | None
    source_type: str
    source_id: str
    language: str
    title: str
    speaker_name: str | None
    parl_group: str | None
    canton: str | None
    council: str | None
    date: dt.date
    debate_dates: tuple[dt.date, ...]
    debate_councils: tuple[str, ...]
    business_numbers: tuple[str, ...]
    url: str
    speaker_function: str | None = None  # z. B. «BR-F» für Bundesratsmitglieder

    @property
    def source_key(self) -> str:
        """Dokument-ID im Goldset-Format `<source_type>:<source_id>` (plan.md, Abschnitt 9)."""
        return f"{self.source_type}:{self.source_id}"


_DETAILS_SQL = text("""
SELECT c.id, c.document_id, c.chunk_index, c.text, c.metadata ->> 'section',
       d.source_type, d.source_id, d.language, d.title, d.speaker_name, d.parl_group,
       d.canton, d.council, d.date, d.debate_dates, d.debate_councils, d.business_numbers, d.url,
       d.speaker_function
FROM chunks c JOIN documents d ON d.id = c.document_id
WHERE c.id IN :ids
""").bindparams(bindparam("ids", expanding=True))


class Retriever:
    def __init__(
        self, engine: Engine, embedder: Embedder, config: RetrievalConfig | None = None
    ) -> None:
        self.engine = engine
        self.embedder = embedder
        self.config = config or RetrievalConfig()

    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        *,
        mode: SearchMode | None = None,
        top_n: int | None = None,
    ) -> list[SearchHit]:
        """Sucht mit `mode`, ohne Angabe mit der Standard-Suchart der Konfiguration."""
        mode = mode or self.config.mode
        filters = filters or SearchFilters()
        limit = self.config.candidates
        fulltext: list[tuple[uuid.UUID, float]] = []
        vector: list[tuple[uuid.UUID, float]] = []
        query_vector = self.embedder.embed_query(query) if mode != "fulltext" else None

        with self.engine.begin() as connection:
            if mode in ("hybrid", "fulltext"):
                fulltext = search_fulltext(connection, query, filters, limit)
            if query_vector is not None:
                vector = search_vector(connection, query_vector, filters, limit)

            rankings = [[chunk_id for chunk_id, _ in ranking] for ranking in (fulltext, vector)]
            fused = reciprocal_rank_fusion(
                [ranking for ranking in rankings if ranking],
                k=self.config.rrf_k,
                top_n=top_n or self.config.top_n,
            )
            if not fused:
                return []
            details = {
                row[0]: row
                for row in connection.execute(_DETAILS_SQL, {"ids": [cid for cid, _ in fused]})
            }

        fulltext_info = {cid: (rank, score) for rank, (cid, score) in enumerate(fulltext, 1)}
        vector_info = {cid: (rank, sim) for rank, (cid, sim) in enumerate(vector, 1)}
        return [
            _hit(
                details[chunk_id],
                score,
                rank,
                fulltext_info.get(chunk_id),
                vector_info.get(chunk_id),
            )
            for rank, (chunk_id, score) in enumerate(fused, start=1)
        ]


def _hit(
    row: Any,
    score: float,
    rank: int,
    fulltext: tuple[int, float] | None,
    vector: tuple[int, float] | None,
) -> SearchHit:
    return SearchHit(
        chunk_id=row[0],
        document_id=row[1],
        chunk_index=row[2],
        text=row[3],
        section=row[4],
        score=score,
        rank=rank,
        fulltext_rank=fulltext[0] if fulltext else None,
        fulltext_score=fulltext[1] if fulltext else None,
        vector_rank=vector[0] if vector else None,
        vector_similarity=vector[1] if vector else None,
        source_type=row[5],
        source_id=row[6],
        language=row[7],
        title=row[8],
        speaker_name=row[9],
        parl_group=row[10],
        canton=row[11],
        council=row[12],
        date=row[13],
        debate_dates=tuple(row[14]),
        debate_councils=tuple(row[15]),
        business_numbers=tuple(row[16]),
        url=row[17],
        speaker_function=row[18],
    )
