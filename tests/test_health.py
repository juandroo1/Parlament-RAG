from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine

from parlrag import __version__
from parlrag.api.main import app
from parlrag.db.session import get_engine


@pytest.fixture
def client_with_engine() -> Iterator[tuple[TestClient, list[Engine]]]:
    """TestClient, dessen Datenbank-Engine pro Test gesetzt werden kann."""
    engines: list[Engine] = []
    app.dependency_overrides[get_engine] = lambda: engines[0]
    try:
        yield TestClient(app), engines
    finally:
        app.dependency_overrides.clear()


def test_health_returns_ok_when_database_answers(
    client_with_engine: tuple[TestClient, list[Engine]],
) -> None:
    client, engines = client_with_engine
    engines.append(create_engine("sqlite://"))  # beantwortet SELECT 1 ohne Server

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_unreachable(
    client_with_engine: tuple[TestClient, list[Engine]],
) -> None:
    client, engines = client_with_engine
    # Port 1 auf localhost: Verbindung wird sofort abgelehnt.
    engines.append(
        create_engine(
            "postgresql+psycopg://user:pw@127.0.0.1:1/none", connect_args={"connect_timeout": 1}
        )
    )

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unreachable"}


def test_app_reports_package_version() -> None:
    assert app.version == __version__
