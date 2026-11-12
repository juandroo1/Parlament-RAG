"""Alembic-Umgebung. Die Datenbank-URL kommt aus `config.attributes["url"]` oder den Settings."""

from alembic import context
from sqlalchemy import pool

from parlrag.config import Settings
from parlrag.db.models import Base
from parlrag.db.session import create_db_engine

config = context.config
target_metadata = Base.metadata


def _database_url() -> str:
    url = config.attributes.get("url")
    return url if isinstance(url, str) else Settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_db_engine(_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
