"""Statistik über den Bestand (Task 1.4)."""

import datetime as dt
import re

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from typer.testing import CliRunner

from fakes import FakeEmbedder
from ingest_fakes import PFAS_DAY, FixtureSource
from parlrag import cli
from parlrag.db.models import Chunk, Document
from parlrag.index.indexer import IndexConfig, index_documents
from parlrag.ingest.mapping import Language
from parlrag.ingest.pipeline import collect_session, run_ingest
from parlrag.stats import CorpusStats, IndexSummary, LengthStats, StorageSizes, compute_stats

BOTH: frozenset[Language] = frozenset({"de", "fr"})


@pytest.fixture
def ingested(empty_db: Engine) -> Engine:
    run_ingest(FixtureSource(), sessionmaker(empty_db), PFAS_DAY, PFAS_DAY, BOTH)
    return empty_db


def _expected_lengths() -> dict[str, list[int]]:
    source = FixtureSource()
    (session,) = source.sessions(PFAS_DAY, PFAS_DAY)
    batch = collect_session(source, session, PFAS_DAY, PFAS_DAY, BOTH)
    lengths: dict[str, list[int]] = {"transcript": [], "business": []}
    for document in batch.documents:
        lengths[document.source_type].append(len(document.text))
    return lengths


@pytest.mark.db
def test_volume_lengths_and_distribution(ingested: Engine) -> None:
    stats = compute_stats(ingested)

    assert stats.by_type_language == {
        ("business", "de"): 1,
        ("business", "fr"): 1,
        ("transcript", "de"): 4,
        ("transcript", "fr"): 2,
    }
    assert stats.total_documents == 8
    expected = _expected_lengths()
    speeches = stats.lengths["transcript"]
    assert speeches.documents == 6
    assert speeches.total_chars == sum(expected["transcript"])
    assert speeches.max_chars == max(expected["transcript"])
    assert speeches.estimated_tokens == sum(expected["transcript"]) // 4
    assert stats.lengths["business"].documents == 2
    assert stats.transcripts_by_council == {"SR": 6}
    assert stats.transcripts_by_parl_group == {
        "M-E": 2,
        "RL": 1,
        "S": 1,
        "V": 1,
        "ohne Fraktion": 1,
    }
    assert (stats.first_date, stats.last_date) == (PFAS_DAY, PFAS_DAY)
    assert stats.quality == {
        "Restmarkup": 0,
        "leerer Titel": 0,
        "Votum ohne Redner": 0,
        "ohne Chunks": 8,
    }


@pytest.mark.db
@pytest.mark.parametrize(
    "legitimate",
    [
        "Siehe <https://www.bj.admin.ch/bj/de/home.html> > Publikationen.",
        "Die Kantone können sog. <weitere Nutzungszonen> vorsehen.",
        "Gemäss Bundesgesetz über die Verrechnungssteuer [VStG] und [VSA; SR 513.11].",
        "Der Wert liegt bei <5 Prozent.",
    ],
)
def test_quality_check_ignores_legitimate_brackets(ingested: Engine, legitimate: str) -> None:
    """Fehlalarme aus dem vollen Ingest (Task 2.6) zählen nicht als Restmarkup."""
    with Session(ingested) as db, db.begin():
        michel = db.scalars(select(Document).where(Document.source_id == "418982")).one()
        michel.text += " " + legitimate

    assert compute_stats(ingested).quality["Restmarkup"] == 0


@pytest.mark.db
@pytest.mark.parametrize(
    "residue", ["<p>Rest</p>", '<span class="x">Rest', "Zeile<br/>", "[GZ]", "[PAGE 727]"]
)
def test_quality_check_detects_each_kind_of_residue(ingested: Engine, residue: str) -> None:
    with Session(ingested) as db, db.begin():
        michel = db.scalars(select(Document).where(Document.source_id == "418982")).one()
        michel.text += " " + residue

    assert compute_stats(ingested).quality["Restmarkup"] == 1


@pytest.mark.db
def test_quality_checks_detect_problems(ingested: Engine) -> None:
    with Session(ingested) as db, db.begin():
        michel = db.scalars(select(Document).where(Document.source_id == "418982")).one()
        michel.text += " [GZ] <p>Rest</p>"
        db.add(Chunk(document=michel, chunk_index=0, language="de", text="x", token_count=1))

    quality = compute_stats(ingested).quality

    assert quality["Restmarkup"] == 1
    assert quality["ohne Chunks"] == 7


@pytest.mark.db
def test_session_filter(ingested: Engine) -> None:
    assert compute_stats(ingested, session_id=5215).total_documents == 8
    other = compute_stats(ingested, session_id=9999)
    assert other.total_documents == 0
    assert other.lengths == {}
    assert other.first_date is None


def test_stats_command_prints_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = CorpusStats(
        by_type_language={("transcript", "de"): 4000, ("transcript", "fr"): 1200},
        lengths={"transcript": LengthStats(5200, 20_800_000, 4000.0, 3100.0, 8000.0, 41000)},
        transcripts_by_council={"NR": 3600, "SR": 1600},
        transcripts_by_parl_group={"V": 1300, "ohne Fraktion": 400},
        first_date=dt.date(2026, 9, 14),
        last_date=dt.date(2026, 10, 2),
        quality={"Restmarkup": 0, "ohne Chunks": 5200},
        index=IndexSummary(
            indexed_documents=4133,
            chunks=10978,
            mean_chunk_tokens=270.4,
            chunks_by_signature={"BAAI/bge-m3|target=500": 10978},
        ),
        storage=StorageSizes(
            database=900 * 1024 * 1024,
            documents_table=60 * 1024 * 1024,
            chunks_table=800 * 1024 * 1024,
            vector_index=500 * 1024 * 1024,
        ),
    )
    requested: list[int | None] = []

    def fake_load(session_id: int | None) -> CorpusStats:
        requested.append(session_id)
        return fake

    monkeypatch.setattr(cli, "load_stats", fake_load)

    result = CliRunner().invoke(cli.app, ["stats", "--session-id", "5215"])

    assert result.exit_code == 0, result.output
    assert requested == [5215]
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "Dokumente (Session 5215): 5'200" in plain
    assert "20'800'000" in plain  # Zeichen
    assert "5'200'000" in plain  # ≈ Tokens
    assert "Rat NR" in plain
    assert "Restmarkup" in plain
    assert "10'978" in plain  # Chunks
    assert "Signatur BAAI/bge-m3|target=500" in plain
    assert "800 MB" in plain and "500 MB" in plain


@pytest.mark.db
def test_index_summary_and_storage(ingested: Engine) -> None:
    before = compute_stats(ingested)
    assert before.index.indexed_documents == 0 and before.index.chunks == 0

    index_documents(ingested, FakeEmbedder(), IndexConfig(model_name="fake/model"))
    after = compute_stats(ingested)

    with Session(ingested) as db:
        chunk_count = db.scalar(select(func.count()).select_from(Chunk))
    assert after.index.indexed_documents == 8
    assert after.index.chunks == chunk_count
    assert after.index.mean_chunk_tokens > 0
    assert after.index.chunks_by_signature == {
        IndexConfig(model_name="fake/model").signature: chunk_count
    }
    assert after.quality["ohne Chunks"] == 0
    assert after.storage.database > after.storage.chunks_table > 0
    assert after.storage.vector_index > 0
    assert compute_stats(ingested, session_id=9999).index.chunks == 0
