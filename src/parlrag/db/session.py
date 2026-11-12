"""Engine-Erzeugung aus der Konfiguration."""

from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine

from parlrag.config import Settings

CONNECT_TIMEOUT_SECONDS = 5


def create_db_engine(url: str, **kwargs: Any) -> Engine:
    """Engine mit Verbindungs-Timeout, damit eine nicht erreichbare DB nie unbegrenzt blockiert."""
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
        **kwargs,
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Gemeinsame Engine der Anwendung; auch als FastAPI-Dependency nutzbar."""
    return create_db_engine(Settings().database_url)
