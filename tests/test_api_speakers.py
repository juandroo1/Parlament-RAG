"""`GET /speakers` (Task 8.2, AK-18.1): Personen mit Voten für den Filter «Person»."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from ingest_fakes import PFAS_DAY, FixtureSource
from parlrag.api.main import app
from parlrag.db.session import get_engine
from parlrag.ingest.pipeline import run_ingest
from parlrag.query.speakers import sort_key


@pytest.fixture
def client_with_engine() -> Iterator[tuple[TestClient, list[Engine]]]:
    engines: list[Engine] = []
    app.dependency_overrides[get_engine] = lambda: engines[0]
    try:
        yield TestClient(app), engines
    finally:
        app.dependency_overrides.clear()


@pytest.mark.db
def test_speakers_lists_people_with_speeches(
    client_with_engine: tuple[TestClient, list[Engine]], empty_db: Engine
) -> None:
    client, engines = client_with_engine
    run_ingest(FixtureSource(), sessionmaker(empty_db), PFAS_DAY, PFAS_DAY, frozenset({"de", "fr"}))
    engines.append(empty_db)

    response = client.get("/speakers")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=600"
    speakers = response.json()
    names = [speaker["name"] for speaker in speakers]
    assert names == sorted(names, key=sort_key)
    assert len(names) == len(set(names))
    michel = next(speaker for speaker in speakers if speaker["name"] == "Michel Matthias")
    assert michel["parl_group"] == "RL" and michel["canton"] == "ZG" and michel["council"] == "SR"
    assert michel["federal_council"] is False and michel["votes"] >= 1
    federal = [speaker for speaker in speakers if speaker["federal_council"]]
    assert federal and all(speaker["parl_group"] is None for speaker in federal)


@pytest.mark.db
def test_speakers_is_empty_without_documents(
    client_with_engine: tuple[TestClient, list[Engine]], empty_db: Engine
) -> None:
    client, engines = client_with_engine
    engines.append(empty_db)
    assert client.get("/speakers").json() == []


def test_speakers_returns_503_without_database(
    client_with_engine: tuple[TestClient, list[Engine]],
) -> None:
    client, engines = client_with_engine
    engines.append(
        create_engine(
            "postgresql+psycopg://user:pw@127.0.0.1:1/none", connect_args={"connect_timeout": 1}
        )
    )

    response = client.get("/speakers")

    assert response.status_code == 503
    assert response.headers["x-error-code"] == "unavailable"


def test_sort_key_ignores_accents_and_case() -> None:
    names = ["Zybach Ursula", "Égerszegi Christine", "de Quattro Jacqueline", "Amaudruz Céline"]
    assert sorted(names, key=sort_key) == [
        "Amaudruz Céline",
        "de Quattro Jacqueline",
        "Égerszegi Christine",
        "Zybach Ursula",
    ]
