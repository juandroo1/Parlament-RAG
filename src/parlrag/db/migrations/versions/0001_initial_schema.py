"""initial schema: documents and chunks

Revision ID: 0001
Revises:
Create Date: 2026-11-12 18:55:30.017059
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Die Extension bleibt beim Downgrade bestehen, weil sie schon vorher existiert haben kann.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("speaker_name", sa.Text(), nullable=True),
        sa.Column("speaker_function", sa.Text(), nullable=True),
        sa.Column("parl_group", sa.Text(), nullable=True),
        sa.Column("canton", sa.Text(), nullable=True),
        sa.Column("council", sa.Text(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "debate_dates",
            postgresql.ARRAY(sa.Date()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "debate_councils",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "business_numbers",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("subject_id", sa.BigInteger(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("raw_hash", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "council IS NULL OR council IN ('NR', 'SR', 'V')", name=op.f("ck_documents_council")
        ),
        sa.CheckConstraint(
            "debate_councils <@ ARRAY['NR', 'SR', 'V']::text[]",
            name=op.f("ck_documents_debate_councils"),
        ),
        sa.CheckConstraint("language IN ('de', 'fr')", name=op.f("ck_documents_language")),
        sa.CheckConstraint(
            "source_type IN ('transcript', 'business')", name=op.f("ck_documents_source_type")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint(
            "source_type",
            "source_id",
            "language",
            name=op.f("uq_documents_source_type_source_id_language"),
        ),
    )
    op.create_index(
        op.f("ix_documents_business_numbers"),
        "documents",
        ["business_numbers"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        op.f("ix_documents_date_council_parl_group"),
        "documents",
        ["date", "council", "parl_group"],
        unique=False,
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector(CASE language WHEN 'de' THEN 'german'::regconfig "
                "ELSE 'french'::regconfig END, text)",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint("language IN ('de', 'fr')", name=op.f("ck_chunks_language")),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_chunks_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chunks")),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name=op.f("uq_chunks_document_id_chunk_index")
        ),
    )
    op.create_index(op.f("ix_chunks_document_id"), "chunks", ["document_id"], unique=False)
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(op.f("ix_chunks_tsv"), "chunks", ["tsv"], unique=False, postgresql_using="gin")


def downgrade() -> None:
    op.drop_index(op.f("ix_chunks_tsv"), table_name="chunks")
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
    op.drop_index(op.f("ix_chunks_document_id"), table_name="chunks")
    op.drop_table("chunks")
    op.drop_index(op.f("ix_documents_date_council_parl_group"), table_name="documents")
    op.drop_index(op.f("ix_documents_business_numbers"), table_name="documents")
    op.drop_table("documents")
