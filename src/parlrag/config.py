"""Konfiguration über Umgebungsvariablen (bzw. `.env`).

Jedes Feld hier muss auch in `.env.example` stehen; ein Test prüft das.
"""

from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Effort = Literal["low", "medium", "high", "xhigh", "max"]
SearchMode = Literal["hybrid", "fulltext", "vector"]
# api: Anthropic-API mit API-Key; claude-code: Claude-Abo über die Claude-Code-CLI (AK-6.3).
LLMBackend = Literal["api", "claude-code"]


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

    # LLM-Backend: `api` (Standard, API-Key) oder `claude-code` (Claude-Abo, nur lokal mit uv).
    llm_backend: LLMBackend = "api"
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-opus-5-5"
    anthropic_effort: Effort = "high"

    # Judge der Antwort-Evals (Task 4.5a): bewertet Zitate, Faithfulness und Neutralität.
    judge_model: str = "claude-sonnet-5-5"
    judge_effort: Effort = "medium"

    # Generierung (plan.md, Abschnitt 7): so viele Chunks gehen als nummerierte Quellen ans LLM.
    answer_context_chunks: int = Field(default=8, ge=1, le=50)
    # Unter dieser Cosine-Similarity des besten Vektortreffers: «keine ausreichende Grundlage»
    # ohne LLM-Aufruf (Task 4.3, auf dem Goldset kalibriert).
    answer_min_similarity: float = Field(default=0.55, ge=0.0, le=1.0)

    # OData-Dienst der Parlamentsdienste (plan.md, Abschnitt 3); schonend abfragen.
    odata_base_url: str = "https://ws.parlament.ch/odata.svc/"
    odata_min_interval_seconds: float = Field(default=1.0, ge=0)
    odata_max_retries: int = Field(default=5, ge=0)
    odata_timeout_seconds: float = Field(default=60.0, gt=0)
    raw_cache_dir: Path = Path("data/raw")

    # Chunking (plan.md, Abschnitt 5); Höchstgrösse = 1,2-mal Ziel. Experimente: 300/500/800.
    chunk_target_tokens: int = Field(default=500, ge=50)
    chunk_overlap_ratio: float = Field(default=0.15, ge=0, lt=0.5)

    # Embeddings (plan.md, Abschnitt 2); das Modell wird erst bei Bedarf geladen.
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cpu"
    embedding_batch_size: int = Field(default=16, ge=1)
    embedding_max_seq_length: int = Field(default=1024, ge=32, le=8192)

    # Index: Kontext-Header beim Einbetten (Experiment «mit/ohne Header», plan.md Abschnitt 10).
    index_context_header: bool = True

    # Retrieval (plan.md, Abschnitt 6): Standard-Suchart (Baseline Task 3.3: vector), Kandidaten
    # je Suchart, RRF-Konstante, Anzahl Treffer.
    retrieval_mode: SearchMode = "vector"
    retrieval_candidates: int = Field(default=50, ge=1, le=1000)
    retrieval_rrf_k: int = Field(default=60, ge=1)
    retrieval_top_n: int = Field(default=20, ge=1)

    @property
    def database_url(self) -> str:
        """Verbindungs-URL; nicht Teil von `repr()`, damit das Passwort nicht in Logs landet."""
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password.get_secret_value(), safe="")
        return (
            f"postgresql+psycopg://{user}:{password}@{self.postgres_host}:{self.postgres_port}"
            f"/{self.postgres_db}"
        )
