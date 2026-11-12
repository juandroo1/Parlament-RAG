from fastapi.testclient import TestClient

from parlrag import __version__
from parlrag.api.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_reports_package_version() -> None:
    assert app.version == __version__
