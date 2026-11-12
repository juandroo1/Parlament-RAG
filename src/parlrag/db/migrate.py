"""Migrationen programmatisch ausführen.

Aufruf im Container (Entrypoint) und lokal: `python -m parlrag.db.migrate`.
Kommt ohne `alembic.ini` aus, weil das Image kein Projektverzeichnis enthält.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def alembic_config(url: str | None = None) -> Config:
    """Alembic-Konfiguration; ohne `url` liest `env.py` die URL aus den Settings."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    if url is not None:
        # Über attributes statt set_main_option: URL-kodierte Passwörter enthalten «%».
        config.attributes["url"] = url
    return config


def upgrade_head(url: str | None = None) -> None:
    command.upgrade(alembic_config(url), "head")


def downgrade_base(url: str | None = None) -> None:
    command.downgrade(alembic_config(url), "base")


if __name__ == "__main__":
    # Ohne alembic.ini richtet Alembic kein Logging ein; so erscheinen die Schritte im Log.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    upgrade_head()
    logging.getLogger("parlrag.db.migrate").info("Datenbankschema ist aktuell.")
