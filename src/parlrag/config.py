"""Konfiguration über Umgebungsvariablen (bzw. `.env`).

Jedes Feld hier muss auch in `.env.example` stehen; ein Test prüft das.
"""

from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic import Field, SecretStr
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

    # OData-Dienst der Parlamentsdienste (plan.md, Abschnitt 3); schonend abfragen.
    odata_base_url: str = "https://ws.parlament.ch/odata.svc/"
    odata_min_interval_seconds: float = Field(default=1.0, ge=0)
    odata_max_retries: int = Field(default=5, ge=0)
    odata_timeout_seconds: float = Field(default=60.0, gt=0)
    raw_cache_dir: Path = Path("data/raw")

    @property
    def database_url(self) -> str:
        """Verbindungs-URL; nicht Teil von `repr()`, damit das Passwort nicht in Logs landet."""
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password.get_secret_value(), safe="")
        return (
            f"postgresql+psycopg://{user}:{password}@{self.postgres_host}:{self.postgres_port}"
            f"/{self.postgres_db}"
        )
