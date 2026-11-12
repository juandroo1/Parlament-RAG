"""Konfiguration über Umgebungsvariablen (bzw. `.env`).

Jedes Feld hier muss auch in `.env.example` stehen; ein Test prüft das.
"""

from typing import Literal
from urllib.parse import quote

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Effort = Literal["low", "medium", "high", "xhigh", "max"]


class Settings(BaseSettings):
    """Laufzeitkonfiguration der Anwendung."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_user: str = "parlrag"
    postgres_password: SecretStr
    postgres_db: str = "parlrag"
    # 127.0.0.1 statt localhost: Unter Windows löst localhost zuerst zu ::1 auf,
    # Docker bindet den Port aber nur an 127.0.0.1.
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432

    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-opus-5-5"
    anthropic_effort: Effort = "high"

    @property
    def database_url(self) -> str:
        """Verbindungs-URL; nicht Teil von `repr()`, damit das Passwort nicht in Logs landet."""
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password.get_secret_value(), safe="")
        return (
            f"postgresql+psycopg://{user}:{password}@{self.postgres_host}:{self.postgres_port}"
            f"/{self.postgres_db}"
        )
