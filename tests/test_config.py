from pathlib import Path

import pytest
from pydantic import ValidationError

from parlrag.config import Settings

ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"
ENV_VARS = [name.upper() for name in Settings.model_fields]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests dürfen weder echte Umgebungsvariablen noch eine lokale `.env` sehen."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


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
    assert settings.database_url.startswith("postgresql://")


def test_environment_overrides_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    monkeypatch.setenv("ANTHROPIC_EFFORT", "low")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/x")

    settings = Settings(_env_file=None)

    assert settings.anthropic_model == "claude-sonnet-5-5"
    assert settings.anthropic_effort == "low"
    assert settings.database_url == "postgresql://u:p@db:5432/x"


def test_invalid_effort_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_EFFORT", "extreme")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_api_key_is_not_leaked_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-value")

    settings = Settings(_env_file=None)

    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-secret-value"
    assert "sk-ant-secret-value" not in repr(settings)
    assert "sk-ant-secret-value" not in str(settings.model_dump())


def test_env_example_lists_exactly_the_settings_fields() -> None:
    assert _env_example_keys() == set(ENV_VARS)


def test_env_example_contains_no_secret_values() -> None:
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            assert line == "ANTHROPIC_API_KEY="
