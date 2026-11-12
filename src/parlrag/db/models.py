"""SQLAlchemy-Modelle gemäss plan.md, Abschnitt 4.

Das Schema in der Datenbank entsteht ausschliesslich über Alembic-Migrationen
(`parlrag/db/migrations`). Ein Test stellt sicher, dass Modelle und Migrationen übereinstimmen.
"""

import datetime as dt
import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBEDDING_DIMENSIONS = 1024

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Volltext-Konfiguration je nach Sprache des Chunks (plan.md, Abschnitt 2).
TSV_EXPRESSION = (
    "to_tsvector(CASE language WHEN 'de' THEN 'german'::regconfig "
    "ELSE 'french'::regconfig END, text)"
)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Document(Base):
    """Ein Votum (Transcript) oder ein Geschäftstext (Business) in einer Sprache."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sql_text("gen_random_uuid()")
    )
    source_type: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    speaker_name: Mapped[str | None] = mapped_column(Text)
    speaker_function: Mapped[str | None] = mapped_column(Text)
    parl_group: Mapped[str | None] = mapped_column(Text)
    canton: Mapped[str | None] = mapped_column(Text)
    council: Mapped[str | None] = mapped_column(Text)
    date: Mapped[dt.date] = mapped_column(Date)
    debate_dates: Mapped[list[dt.date]] = mapped_column(
        ARRAY(Date), server_default=sql_text("'{}'")
    )
    debate_councils: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=sql_text("'{}'"))
    business_numbers: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=sql_text("'{}'")
    )
    session_id: Mapped[int | None] = mapped_column(Integer)
    subject_id: Mapped[int | None] = mapped_column(BigInteger)
    sort_order: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(Text)
    raw_hash: Mapped[str] = mapped_column(Text)

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint("source_type", "source_id", "language"),
        CheckConstraint("source_type IN ('transcript', 'business')", name="source_type"),
        CheckConstraint("language IN ('de', 'fr')", name="language"),
        CheckConstraint("council IS NULL OR council IN ('NR', 'SR', 'V')", name="council"),
        CheckConstraint(
            "debate_councils <@ ARRAY['NR', 'SR', 'V']::text[]", name="debate_councils"
        ),
        Index(None, "date", "council", "parl_group"),
        Index(None, "business_numbers", postgresql_using="gin"),
    )


class Chunk(Base):
    """Ein Abschnitt eines Dokuments mit Volltext- und Vektorindex."""

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sql_text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    tsv: Mapped[str] = mapped_column(TSVECTOR, Computed(TSV_EXPRESSION, persisted=True))
    embedding: Mapped[Any | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, server_default=sql_text("'{}'::jsonb")
    )

    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index"),
        CheckConstraint("language IN ('de', 'fr')", name="language"),
        Index(None, "document_id"),
        Index(None, "tsv", postgresql_using="gin"),
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
