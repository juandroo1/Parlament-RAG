"""Prüft die Alembic-Migration gegen echtes Postgres mit pgvector (plan.md, Abschnitt 4)."""

import datetime as dt
from collections.abc import Iterator
from typing import Any

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, func, inspect, select, text
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from conftest import truncate_documents
from parlrag.db.migrate import downgrade_base, upgrade_head
from parlrag.db.models import EMBEDDING_DIMENSIONS, Base, Chunk, Document
from parlrag.db.session import create_db_engine

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def engine(test_database_url: str) -> Iterator[Engine]:
    upgrade_head(test_database_url)
    db_engine = create_db_engine(test_database_url)
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Session auf leeren Tabellen, deren Änderungen am Ende zurückgerollt werden."""
    truncate_documents(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db_session:
            yield db_session
        transaction.rollback()


def make_document(**overrides: Any) -> Document:
    values: dict[str, Any] = {
        "source_type": "transcript",
        "source_id": "418982",
        "language": "de",
        "title": "Einführung einer Deklarationspflicht für PFAS",
        "text": "Die Problematik der PFAS-Substanzen ist bekannt.",
        "speaker_name": "Michel Matthias",
        "parl_group": "RL",
        "council": "SR",
        "date": dt.date(2026, 9, 15),
        "business_numbers": ["25.3866", "25.3902", "25.3906"],
        "subject_id": 82315,
        "sort_order": 6,
        "url": "https://www.parlament.ch/de/ratsbetrieb/amtliches-bulletin/"
        "amtliches-bulletin-die-verhandlungen?SubjectId=82315#votum6",
        "raw_hash": "abc123",
    }
    values.update(overrides)
    return Document(**values)


def make_chunk(document: Document, **overrides: Any) -> Chunk:
    values: dict[str, Any] = {
        "chunk_index": 0,
        "language": document.language,
        "text": document.text,
        "token_count": 12,
    }
    values.update(overrides)
    return Chunk(document=document, **values)


def test_pgvector_extension_is_installed(engine: Engine) -> None:
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one_or_none()
    assert version is not None


def test_tables_and_indexes_exist(engine: Engine) -> None:
    inspector = inspect(engine)
    assert {"documents", "chunks"} <= set(inspector.get_table_names())

    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public'")
        ).all()
    indexes: dict[str, str] = {name: definition for name, definition in rows}
    assert "USING gin (tsv)" in indexes["ix_chunks_tsv"]
    assert "USING hnsw (embedding vector_cosine_ops)" in indexes["ix_chunks_embedding_hnsw"]
    assert "USING gin (business_numbers)" in indexes["ix_documents_business_numbers"]
    assert "(date, council, parl_group)" in indexes["ix_documents_date_council_parl_group"]


def test_migration_matches_models(engine: Engine) -> None:
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert differences == []


def test_document_with_chunk_roundtrip(session: Session) -> None:
    document = make_document()
    make_chunk(document, embedding=[0.1] * EMBEDDING_DIMENSIONS)
    session.add(document)
    session.flush()

    stored = session.get(Document, document.id)
    assert stored is not None
    assert stored.business_numbers == ["25.3866", "25.3902", "25.3906"]
    assert stored.debate_dates == []
    assert stored.chunks[0].metadata_ == {}
    embedding = stored.chunks[0].embedding
    assert embedding is not None
    assert len(embedding) == EMBEDDING_DIMENSIONS


def test_tsv_uses_language_specific_stemming(session: Session) -> None:
    german = make_document(text="Die Kantone fordern Massnahmen.")
    french = make_document(
        source_id="418885", language="fr", text="Les cantons demandent des mesures."
    )
    make_chunk(german)
    make_chunk(french)
    session.add_all([german, french])
    session.flush()

    def matches(document: Document, config: str, query: str) -> bool:
        return bool(
            session.scalar(
                select(Chunk.tsv.op("@@")(func.to_tsquery(config, query))).where(
                    Chunk.document_id == document.id
                )
            )
        )

    # «Kantone» wird mit der deutschen Konfiguration auf «kanton» reduziert,
    # «cantons» mit der französischen auf «canton».
    assert matches(german, "german", "Kanton")
    assert matches(french, "french", "canton")
    assert not matches(german, "german", "canton")


@pytest.mark.parametrize(
    "overrides",
    [
        {"language": "it"},
        {"source_type": "vote"},
        {"council": "VB"},
        {"debate_councils": ["NR", "XX"]},
    ],
)
def test_check_constraints_reject_invalid_values(
    session: Session, overrides: dict[str, Any]
) -> None:
    session.add(make_document(**overrides))
    with pytest.raises(IntegrityError):
        session.flush()


def test_source_is_unique_per_language(session: Session) -> None:
    session.add(make_document())
    session.flush()
    session.add(make_document())
    with pytest.raises(IntegrityError):
        session.flush()


def test_embedding_dimension_is_enforced(session: Session) -> None:
    document = make_document()
    make_chunk(document, embedding=[0.1, 0.2, 0.3])
    session.add(document)
    with pytest.raises(DataError):
        session.flush()


def test_deleting_a_document_deletes_its_chunks(session: Session) -> None:
    document = make_document()
    make_chunk(document, chunk_index=0)
    make_chunk(document, chunk_index=1)
    session.add(document)
    session.flush()

    session.execute(text("DELETE FROM documents WHERE id = :id"), {"id": document.id})
    remaining = session.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == document.id)
    )
    assert remaining == 0


def test_downgrade_and_upgrade_again(test_database_url: str, engine: Engine) -> None:
    downgrade_base(test_database_url)
    assert not {"documents", "chunks"} & set(inspect(engine).get_table_names())

    upgrade_head(test_database_url)
    assert {"documents", "chunks"} <= set(inspect(engine).get_table_names())
