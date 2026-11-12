"""Gemeinsame Fixtures. Datenbank-Tests laufen in einer eigenen Datenbank `parlrag_test`."""

from collections.abc import Iterator

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from parlrag.config import Settings
from parlrag.db.session import create_db_engine

TEST_DATABASE = "parlrag_test"


@pytest.fixture(scope="session")
def test_database_url() -> Iterator[str]:
    """Legt `parlrag_test` frisch an und entfernt sie am Ende; ohne erreichbares Postgres: skip."""
    try:
        settings = Settings()
    except ValidationError:
        pytest.skip("Keine Datenbank-Konfiguration (.env bzw. POSTGRES_*) vorhanden")

    admin = create_db_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS {TEST_DATABASE} WITH (FORCE)"))
            connection.execute(text(f"CREATE DATABASE {TEST_DATABASE}"))
    except OperationalError:
        admin.dispose()
        pytest.skip("Postgres nicht erreichbar (docker compose up -d db)")

    yield settings.model_copy(update={"postgres_db": TEST_DATABASE}).database_url

    with admin.connect() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {TEST_DATABASE} WITH (FORCE)"))
    admin.dispose()
