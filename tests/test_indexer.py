"""Inkrementelle Indexierung (Task 2.3), mit nachgebautem Embedder gegen `parlrag_test`."""

import hashlib
import re
from collections.abc import Sequence
from typing import Any

import numpy as np
import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from typer.testing import CliRunner

from ingest_fakes import PFAS_DAY, FixtureSource
from parlrag import cli
from parlrag.db.models import Chunk, Document
from parlrag.embeddings import EmbeddingError, Vectors
from parlrag.index.chunker import ChunkingConfig, approximate_token_count, chunk_document
from parlrag.index.indexer import IndexConfig, IndexStats, index_documents
from parlrag.ingest.mapping import DocumentData, Language
from parlrag.ingest.pipeline import run_ingest

BOTH: frozenset[Language] = frozenset({"de", "fr"})


class FakeEmbedder:
    """Deterministische Vektoren aus dem Text-Hash; merkt sich alle eingebetteten Texte."""

    model_name = "fake/model"
    dimensions = 1024

    def __init__(self, fail_after: int | None = None) -> None:
        self.texts: list[str] = []
        self.calls = 0
        self.fail_after = fail_after

    def embed_documents(self, texts: Sequence[str]) -> Vectors:
        self.calls += 1
        if self.fail_after is not None and self.calls > self.fail_after:
            raise EmbeddingError("simulierter Fehler")
        self.texts.extend(texts)
        vectors = np.empty((len(texts), self.dimensions), dtype=np.float32)
        for row, value in enumerate(texts):
            seed = int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big")
            vector = np.random.default_rng(seed).normal(size=self.dimensions)
            vectors[row] = vector / np.linalg.norm(vector)
        return vectors

    def embed_query(self, text: str) -> Vectors:
        vector: Vectors = self.embed_documents([text])[0]
        return vector

    def count_tokens(self, text: str) -> int:
        return approximate_token_count(text)


CONFIG = IndexConfig(model_name="fake/model")


@pytest.fixture
def ingested(empty_db: Engine) -> Engine:
    run_ingest(FixtureSource(), sessionmaker(empty_db), PFAS_DAY, PFAS_DAY, BOTH)
    return empty_db


def chunk_rows(engine: Engine) -> list[Chunk]:
    with Session(engine) as db:
        return list(db.scalars(select(Chunk).order_by(Chunk.document_id, Chunk.chunk_index)))


def expected_chunks(engine: Engine, config: IndexConfig = CONFIG) -> dict[str, list[str]]:
    with Session(engine) as db:
        result = {}
        for record in db.scalars(select(Document)):
            document = DocumentData.from_record(record)
            chunks = chunk_document(document, approximate_token_count, config.chunking)
            result[str(record.id)] = [chunk.text for chunk in chunks]
        return result


pytestmark = pytest.mark.db


def test_indexes_all_documents_with_embeddings_and_signature(ingested: Engine) -> None:
    embedder = FakeEmbedder()

    stats = index_documents(ingested, embedder, CONFIG)

    expected = expected_chunks(ingested)
    rows = chunk_rows(ingested)
    assert (stats.pending, stats.documents) == (8, 8)
    assert stats.chunks == len(rows) == sum(len(texts) for texts in expected.values())
    by_document: dict[str, list[str]] = {}
    for row in rows:
        by_document.setdefault(str(row.document_id), []).append(row.text)
        assert row.embedding is not None and len(row.embedding) == 1024
        assert row.metadata_["index"] == CONFIG.signature
        assert row.token_count == approximate_token_count(row.text)
    assert by_document == expected


def test_embedding_text_has_header_and_can_be_switched_off(ingested: Engine) -> None:
    with_header = FakeEmbedder()
    index_documents(ingested, with_header, CONFIG)
    assert any(
        t.startswith("Ständerat · 15.09.2026 · Michel Matthias (RL, ZG)") for t in with_header.texts
    )

    without_header = FakeEmbedder()
    index_documents(ingested, without_header, IndexConfig("fake/model", context_header=False))
    stored = {row.text for row in chunk_rows(ingested)}
    assert set(without_header.texts) == stored


def test_second_run_has_nothing_to_do(ingested: Engine) -> None:
    index_documents(ingested, FakeEmbedder(), CONFIG)
    embedder = FakeEmbedder()

    stats = index_documents(ingested, embedder, CONFIG)

    assert (stats.pending, stats.documents, stats.chunks) == (0, 0, 0)
    assert embedder.calls == 0


def test_only_changed_documents_are_reindexed(ingested: Engine) -> None:
    index_documents(ingested, FakeEmbedder(), CONFIG)
    with Session(ingested) as db, db.begin():
        michel = db.scalars(select(Document).where(Document.source_id == "418982")).one()
        michel.raw_hash = "veraltet"
    # Der Ingest erkennt die Änderung und löscht die Chunks dieses Dokuments.
    run_ingest(FixtureSource(), sessionmaker(ingested), PFAS_DAY, PFAS_DAY, BOTH)

    stats = index_documents(ingested, FakeEmbedder(), CONFIG)

    assert (stats.pending, stats.documents) == (1, 1)


def test_changed_settings_trigger_full_reindex_without_duplicates(ingested: Engine) -> None:
    index_documents(ingested, FakeEmbedder(), CONFIG)
    smaller = IndexConfig("fake/model", chunking=ChunkingConfig(target_tokens=100))
    assert smaller.signature != CONFIG.signature

    stats = index_documents(ingested, FakeEmbedder(), smaller)

    rows = chunk_rows(ingested)
    assert stats.documents == 8
    assert {row.metadata_["index"] for row in rows} == {smaller.signature}
    assert len(rows) == sum(len(t) for t in expected_chunks(ingested, smaller).values())


def test_limit_session_scope_and_rebuild(ingested: Engine) -> None:
    assert index_documents(ingested, FakeEmbedder(), CONFIG, limit=3).documents == 3
    assert index_documents(ingested, FakeEmbedder(), CONFIG, session_id=9999).pending == 0
    assert index_documents(ingested, FakeEmbedder(), CONFIG, session_id=5215).documents == 5
    assert index_documents(ingested, FakeEmbedder(), CONFIG, rebuild=True).documents == 8


def test_failed_batch_is_rolled_back(ingested: Engine) -> None:
    progress: list[int] = []

    with pytest.raises(EmbeddingError):
        index_documents(
            ingested,
            FakeEmbedder(fail_after=1),
            CONFIG,
            batch_documents=3,
            progress=lambda stats: progress.append(stats.documents),
        )

    assert progress == [3]  # erstes Paket gespeichert, zweites abgebrochen
    with Session(ingested) as db:
        indexed = db.scalar(select(func.count(func.distinct(Chunk.document_id))))
    assert indexed == 3
    assert index_documents(ingested, FakeEmbedder(), CONFIG).documents == 5  # Fortsetzung


# --- CLI -----------------------------------------------------------------------------


def test_index_command_passes_options_and_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_execute(session_id: int | None, limit: int | None, rebuild: bool) -> IndexStats:
        calls.append({"session_id": session_id, "limit": limit, "rebuild": rebuild})
        return IndexStats(pending=40, documents=40, chunks=96, seconds=48.0)

    monkeypatch.setattr(cli, "execute_index", fake_execute)

    result = CliRunner().invoke(cli.app, ["index", "--session-id", "5215", "--limit", "40"])

    assert result.exit_code == 0, result.output
    assert calls == [{"session_id": 5215, "limit": 40, "rebuild": False}]
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "Indexiert: 40 Dokumente, 96 Chunks in 48 s (2.0 Chunks/s)" in plain


def test_index_command_reports_nothing_to_do(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "execute_index", lambda *args: IndexStats())
    result = CliRunner().invoke(cli.app, ["index"])
    assert result.exit_code == 0
    assert "Nichts zu tun" in result.output
    assert CliRunner().invoke(cli.app, ["index", "--limit", "0"]).exit_code == 2
