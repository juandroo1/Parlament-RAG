"""Ingest-Ablauf mit Fixture-Quelle (ohne Netz) und gegen die Testdatenbank (Task 1.3)."""

import datetime as dt
from urllib.parse import unquote

import httpx2
import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from ingest_fakes import PFAS_DAY, FixtureSource
from parlrag.db.models import Chunk, Document
from parlrag.ingest.mapping import Language
from parlrag.ingest.odata import ODataClient
from parlrag.ingest.pipeline import collect_session, run_ingest
from parlrag.ingest.source import ODataSource

BOTH: frozenset[Language] = frozenset({"de", "fr"})
FRENCH: frozenset[Language] = frozenset({"fr"})


# --- Ohne Datenbank -----------------------------------------------------------------


def test_collect_one_day_yields_speeches_and_businesses() -> None:
    source = FixtureSource()
    (session,) = source.sessions(PFAS_DAY, PFAS_DAY)

    batch = collect_session(source, session, PFAS_DAY, PFAS_DAY, BOTH)

    assert session.name == "Herbstsession 2026"
    assert batch.meetings == 2  # NR und SR am 15.09.2026
    transcripts = [d for d in batch.documents if d.source_type == "transcript"]
    businesses = [d for d in batch.documents if d.source_type == "business"]
    assert len(transcripts) == 6
    # 10 Einträge mit Type 1, davon 4 präsidiale Verfahrensvoten ohne Sprache
    assert batch.transcripts == 10
    assert batch.skipped_transcripts == 4
    assert {(d.source_id, d.language) for d in businesses} == {
        ("20253906", "de"),
        ("20253906", "fr"),
    }
    assert all(d.debate_dates == (PFAS_DAY,) and d.debate_councils == ("SR",) for d in businesses)


def test_only_meeting_days_in_range_are_requested() -> None:
    source = FixtureSource()
    (session,) = source.sessions(PFAS_DAY, PFAS_DAY)

    collect_session(source, session, PFAS_DAY, PFAS_DAY, BOTH)

    days = [args[1] for name, args in source.calls if name == "transcripts"]
    assert days == [PFAS_DAY]
    meetings = [args for name, args in source.calls if name == "subjects"]
    assert sorted(meetings) == [5262, 5263]


def test_language_filter_keeps_only_requested_languages() -> None:
    source = FixtureSource()
    (session,) = source.sessions(PFAS_DAY, PFAS_DAY)

    batch = collect_session(source, session, PFAS_DAY, PFAS_DAY, FRENCH)

    assert {d.language for d in batch.documents} == {"fr"}
    assert len([d for d in batch.documents if d.source_type == "transcript"]) == 2
    assert [args[1] for name, args in source.calls if name == "businesses"] == ["FR"]


def test_odata_source_builds_expected_queries() -> None:
    seen: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(unquote(str(request.url)))
        return httpx2.Response(200, content=b'{"d": []}')

    client = ODataClient(
        base_url="https://ws.parlament.ch/odata.svc/",
        cache=None,
        min_interval_seconds=0,
        transport=httpx2.MockTransport(handler),
    )
    source = ODataSource(client)
    source.sessions(dt.date(2026, 9, 1), dt.date(2026, 9, 30))
    source.transcripts(5215, PFAS_DAY)
    source.businesses([20253906, 20253902], "FR")
    assert source.businesses([], "DE") == []

    assert "StartDate le datetime'2026-09-30T23:59:59'" in seen[0]
    assert "EndDate ge datetime'2026-09-01T00:00:00'" in seen[0]
    assert "IdSession eq '5215' and MeetingDate eq '20260915'" in seen[1]
    assert "Language eq 'DE' and Type eq 1" in seen[1]
    assert "Language eq 'FR' and (ID eq 20253906 or ID eq 20253902)" in seen[2]
    assert len(seen) == 3  # leere ID-Liste ohne Request


# --- Mit Datenbank -------------------------------------------------------------------


@pytest.mark.db
def test_ingest_is_idempotent(empty_db: Engine) -> None:
    factory = sessionmaker(empty_db)

    first = run_ingest(FixtureSource(), factory, PFAS_DAY, PFAS_DAY, BOTH)
    second = run_ingest(FixtureSource(), factory, PFAS_DAY, PFAS_DAY, BOTH)

    assert (first.stored.inserted, first.stored.updated, first.stored.unchanged) == (8, 0, 0)
    assert (second.stored.inserted, second.stored.updated, second.stored.unchanged) == (0, 0, 8)
    with Session(empty_db) as db:
        assert db.scalar(select(func.count()).select_from(Document)) == 8


@pytest.mark.db
def test_changed_document_is_updated_and_its_chunks_removed(empty_db: Engine) -> None:
    factory = sessionmaker(empty_db)
    run_ingest(FixtureSource(), factory, PFAS_DAY, PFAS_DAY, BOTH)
    with Session(empty_db) as db, db.begin():
        michel = db.scalars(select(Document).where(Document.source_id == "418982")).one()
        db.add(Chunk(document=michel, chunk_index=0, language="de", text="alt", token_count=1))
        michel.raw_hash = "veraltet"  # simuliert eine inhaltliche Änderung im Dienst
        michel.text = "veralteter Text"

    result = run_ingest(FixtureSource(), factory, PFAS_DAY, PFAS_DAY, BOTH)

    assert (result.stored.updated, result.stored.unchanged) == (1, 7)
    with Session(empty_db) as db:
        michel = db.scalars(select(Document).where(Document.source_id == "418982")).one()
        assert michel.text.startswith("Die Problematik")
        assert michel.chunks == []


@pytest.mark.db
def test_business_debates_are_merged_across_runs(empty_db: Engine) -> None:
    factory = sessionmaker(empty_db)
    run_ingest(FixtureSource(), factory, PFAS_DAY, PFAS_DAY, BOTH)
    earlier = dt.date(2026, 3, 10)
    with Session(empty_db) as db, db.begin():
        for business in db.scalars(select(Document).where(Document.source_type == "business")):
            business.debate_dates = [earlier]
            business.debate_councils = ["NR"]
            business.raw_hash = "aus einem früheren Lauf"

    result = run_ingest(FixtureSource(), factory, PFAS_DAY, PFAS_DAY, BOTH)

    assert result.stored.updated == 2
    with Session(empty_db) as db:
        for business in db.scalars(select(Document).where(Document.source_type == "business")):
            assert business.debate_dates == [earlier, PFAS_DAY]
            assert business.debate_councils == ["NR", "SR"]
    again = run_ingest(FixtureSource(), factory, PFAS_DAY, PFAS_DAY, BOTH)
    assert again.stored.unchanged == 8  # zusammengeführter Stand ist stabil
