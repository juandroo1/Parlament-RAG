"""Gemeinsame Fixtures. Datenbank-Tests laufen in einer eigenen Datenbank `parlrag_test`."""

import os
from collections.abc import Iterator
from typing import NoReturn

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

from parlrag.config import Settings
from parlrag.db.migrate import upgrade_head
from parlrag.db.session import create_db_engine

TEST_DATABASE = "parlrag_test"
REQUIRE_DB_ENV = "PARLRAG_REQUIRE_DB"


def skip_or_fail(reason: str) -> NoReturn:
    """Ohne Datenbank lokal überspringen; in der CI (`PARLRAG_REQUIRE_DB=1`) fehlschlagen."""
    if os.environ.get(REQUIRE_DB_ENV) == "1":
        pytest.fail(f"{reason} ({REQUIRE_DB_ENV}=1 verlangt eine Datenbank)")
    pytest.skip(reason)


@pytest.fixture(scope="session")
def test_database_url() -> Iterator[str]:
    """Legt `parlrag_test` frisch an und entfernt sie am Ende; ohne Postgres: skip bzw. fail."""
    try:
        settings = Settings()
    except ValidationError:
        skip_or_fail("Keine Datenbank-Konfiguration (.env bzw. POSTGRES_*) vorhanden")

    admin = create_db_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS {TEST_DATABASE} WITH (FORCE)"))
            connection.execute(text(f"CREATE DATABASE {TEST_DATABASE}"))
    except OperationalError:
        admin.dispose()
        skip_or_fail("Postgres nicht erreichbar (docker compose up -d db)")

    yield settings.model_copy(update={"postgres_db": TEST_DATABASE}).database_url

    with admin.connect() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {TEST_DATABASE} WITH (FORCE)"))
    admin.dispose()


@pytest.fixture(scope="session")
def migrated_engine(test_database_url: str) -> Iterator[Engine]:
    """Engine auf `parlrag_test` mit aktuellem Schema."""
    upgrade_head(test_database_url)
    engine = create_db_engine(test_database_url)
    yield engine
    engine.dispose()


def truncate_documents(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE documents CASCADE"))


@pytest.fixture
def empty_db(migrated_engine: Engine) -> Iterator[Engine]:
    """Migrierte Testdatenbank ohne Dokumente und Chunks; wird danach wieder geleert."""
    truncate_documents(migrated_engine)
    yield migrated_engine
    truncate_documents(migrated_engine)
