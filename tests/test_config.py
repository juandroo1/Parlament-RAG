from pathlib import Path

import pytest
from pydantic import ValidationError

from parlrag.config import Settings

ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"
ENV_VARS = [name.upper() for name in Settings.model_fields]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests sehen keine echten Umgebungsvariablen; `.env` wird per `_env_file=None` ignoriert."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")


def _env_example_keys() -> set[str]:
    keys = set()
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            keys.add(stripped.split("=", 1)[0].strip())
    return keys


def test_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.anthropic_model == "claude-opus-5-5"
    assert settings.anthropic_effort == "high"
    assert settings.anthropic_api_key is None
    assert settings.postgres_host == "127.0.0.1"
    assert settings.postgres_port == 5432
    assert (
        settings.database_url == "postgresql+psycopg://parlrag:test-password@127.0.0.1:5432/parlrag"
    )


def test_postgres_password_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTGRES_PASSWORD")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_environment_overrides_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    monkeypatch.setenv("ANTHROPIC_EFFORT", "low")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "6543")

    settings = Settings(_env_file=None)

    assert settings.anthropic_model == "claude-sonnet-5-5"
    assert settings.anthropic_effort == "low"
    assert settings.database_url == "postgresql+psycopg://parlrag:test-password@db:6543/parlrag"


def test_database_url_escapes_special_characters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss:w/rd")

    settings = Settings(_env_file=None)

    assert (
        settings.database_url
        == "postgresql+psycopg://parlrag:p%40ss%3Aw%2Frd@127.0.0.1:5432/parlrag"
    )


def test_invalid_effort_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_EFFORT", "extreme")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_secrets_are_not_leaked_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-value")

    settings = Settings(_env_file=None)

    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-secret-value"
    for secret in ["sk-ant-secret-value", "test-password"]:
        assert secret not in repr(settings)
        assert secret not in str(settings.model_dump())


def test_env_example_lists_exactly_the_settings_fields() -> None:
    assert _env_example_keys() == set(ENV_VARS)


def test_env_example_contains_no_api_key() -> None:
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            assert line == "ANTHROPIC_API_KEY="
