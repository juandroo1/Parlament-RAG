"""Inkrementelle Indexierung: Dokumente → Chunks mit Embeddings (Task 2.3).

Jeder Chunk trägt in `metadata["index"]` die Index-Signatur (Modell, Chunk-Ziel, Overlap,
Header, Chunker-Version). Offen ist ein Dokument, wenn es keinen Chunk mit der aktuellen
Signatur hat: neu geladen, beim Ingest geändert (Chunks gelöscht) oder mit anderen
Einstellungen indexiert. Gearbeitet wird in Paketen mit einem Commit pro Paket.
"""

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import batched

from sqlalchemy import Engine, delete, select, text
from sqlalchemy.orm import Session

from parlrag.config import Settings
from parlrag.db.models import Chunk, Document
from parlrag.db.scope import SESSION_SCOPE_CTE
from parlrag.embeddings import Embedder
from parlrag.index.chunker import ChunkingConfig, chunk_document
from parlrag.index.header import embedding_text
from parlrag.ingest.mapping import DocumentData

logger = logging.getLogger(__name__)

# Erhöhen, wenn sich die Logik des Chunkers ändert: Alle Dokumente werden dann neu indexiert.
CHUNKER_VERSION = 1
DEFAULT_BATCH_DOCUMENTS = 32


@dataclass(frozen=True)
class IndexConfig:
    model_name: str
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    context_header: bool = True

    @property
    def signature(self) -> str:
        return (
            f"{self.model_name}|target={self.chunking.target_tokens}"
            f"|overlap={self.chunking.overlap_ratio}|header={int(self.context_header)}"
            f"|chunker=v{CHUNKER_VERSION}"
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "IndexConfig":
        return cls(
            model_name=settings.embedding_model,
            chunking=ChunkingConfig.from_settings(settings),
            context_header=settings.index_context_header,
        )


@dataclass
class IndexStats:
    pending: int = 0
    documents: int = 0
    chunks: int = 0
    seconds: float = 0.0

    @property
    def chunks_per_second(self) -> float:
        return self.chunks / self.seconds if self.seconds else 0.0


ProgressCallback = Callable[[IndexStats], None]


def pending_document_ids(
    engine: Engine,
    signature: str,
    *,
    session_id: int | None = None,
    limit: int | None = None,
    rebuild: bool = False,
) -> list[uuid.UUID]:
    """Dokumente ohne Chunk mit dieser Signatur (oder alle bei `rebuild`), älteste zuerst."""
    query = (
        SESSION_SCOPE_CTE
        + """
        SELECT s.id FROM scope s
        WHERE CAST(:rebuild AS boolean) OR NOT EXISTS (
            SELECT 1 FROM chunks c
            WHERE c.document_id = s.id AND c.metadata ->> 'index' = :signature)
        ORDER BY s.date, s.source_type, s.source_id, s.language
        LIMIT CAST(:limit AS integer)
    """
    )
    params = {"session_id": session_id, "signature": signature, "limit": limit, "rebuild": rebuild}
    with engine.connect() as connection:
        return [row[0] for row in connection.execute(text(query), params)]


def _index_batch(
    engine: Engine, embedder: Embedder, config: IndexConfig, ids: tuple[uuid.UUID, ...]
) -> tuple[int, int]:
    """Ein Paket in einer Transaktion: chunken, einbetten, alte Chunks ersetzen."""
    with Session(engine) as db, db.begin():
        records = db.scalars(
            select(Document).where(Document.id.in_(ids)).order_by(Document.date, Document.id)
        ).all()
        planned = []
        texts: list[str] = []
        for record in records:
            document = DocumentData.from_record(record)
            chunks = chunk_document(document, embedder.count_tokens, config.chunking)
            planned.append((record.id, document, chunks))
            texts.extend(
                embedding_text(document, chunk, with_header=config.context_header)
                for chunk in chunks
            )
        vectors = embedder.embed_documents(texts)

        db.execute(delete(Chunk).where(Chunk.document_id.in_(ids)))
        position = 0
        for document_id, document, chunks in planned:
            for chunk in chunks:
                db.add(
                    Chunk(
                        document_id=document_id,
                        chunk_index=chunk.chunk_index,
                        language=document.language,
                        text=chunk.text,
                        token_count=chunk.token_count,
                        embedding=vectors[position],
                        metadata_={**chunk.metadata, "index": config.signature},
                    )
                )
                position += 1
    return len(records), len(texts)


def index_documents(
    engine: Engine,
    embedder: Embedder,
    config: IndexConfig,
    *,
    session_id: int | None = None,
    limit: int | None = None,
    rebuild: bool = False,
    batch_documents: int = DEFAULT_BATCH_DOCUMENTS,
    progress: ProgressCallback | None = None,
) -> IndexStats:
    ids = pending_document_ids(
        engine, config.signature, session_id=session_id, limit=limit, rebuild=rebuild
    )
    stats = IndexStats(pending=len(ids))
    start = time.monotonic()
    for batch in batched(ids, batch_documents):
        documents, chunks = _index_batch(engine, embedder, config, batch)
        stats.documents += documents
        stats.chunks += chunks
        stats.seconds = time.monotonic() - start
        if progress is not None:
            progress(stats)
    stats.seconds = time.monotonic() - start
    return stats


def log_progress(stats: IndexStats) -> None:
    """Fortschritt mit Rate und geschätzter Restzeit (aus der Dokument-Rate)."""
    remaining = stats.pending - stats.documents
    eta = remaining * stats.seconds / stats.documents if stats.documents else 0.0
    logger.info(
        "%d/%d Dokumente, %d Chunks, %.1f Chunks/s, Rest ≈ %d min",
        stats.documents,
        stats.pending,
        stats.chunks,
        stats.chunks_per_second,
        round(eta / 60),
    )
