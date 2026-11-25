"""Prüft die Leitplanken der Entwicklungsskripte für das Claude-Abo (Spec 001, AK-6.3).

Die Skripte sind PowerShell und laufen nur lokal unter Windows; die CI prüft deshalb ihren Inhalt:
Das Abo bleibt lokal, nichts wird ausserhalb von 127.0.0.1 erreichbar, und `dev-up.ps1` stoppt
nur die Container, die einen API-Key brauchen.
"""

import re
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _read(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8-sig")


def _commands(script: str, verbs: str) -> list[str]:
    """`docker compose`-Aufrufe, die das Skript ausführt (nicht Erwähnungen in Meldungen)."""
    pattern = rf"^\s*(docker compose (?:{verbs})\b.*?)\s*$"
    return re.findall(pattern, script, flags=re.MULTILINE)


@pytest.fixture(scope="module")
def dev_up() -> str:
    return _read("dev-up.ps1")


@pytest.fixture(scope="module")
def dev_api() -> str:
    return _read("dev-api.ps1")


@pytest.mark.parametrize("name", ["dev-api.ps1", "dev-up.ps1"])
def test_scripts_are_utf8_with_bom(name: str) -> None:
    # Windows PowerShell 5.1 liest UTF-8 ohne BOM als ANSI; dann sind die Umlaute kaputt.
    assert (SCRIPTS / name).read_bytes().startswith(b"\xef\xbb\xbf")


def test_dev_api_uses_the_subscription_on_localhost(dev_api: str) -> None:
    assert '$env:LLM_BACKEND = "claude-code"' in dev_api
    assert "--host 127.0.0.1" in dev_api


def test_dev_up_starts_the_api_through_dev_api(dev_up: str) -> None:
    assert '"dev-api.ps1"' in dev_up
    assert "-Port $Port -Model $Model -Effort $Effort" in dev_up


def test_dev_up_starts_only_the_database_container(dev_up: str) -> None:
    assert _commands(dev_up, "up|start") == ["docker compose up -d --wait db"]


def test_dev_up_stops_only_app_and_web(dev_up: str) -> None:
    assert _commands(dev_up, "stop|down|rm") == ["docker compose stop app web"]


def test_dev_up_web_ui_uses_the_local_api(dev_up: str) -> None:
    assert '$env:API_TARGET = "http://127.0.0.1:$Port"' in dev_up
    assert '"--strictPort"' in dev_up


def test_dev_up_checks_before_changing_anything(dev_up: str) -> None:
    # Fehlende Werkzeuge oder ein belegter Port brechen ab, bevor Container gestoppt werden.
    stop = dev_up.index("docker compose stop app web")
    for check in ('"claude"', "npm install", "uv sync", "Get-NetTCPConnection -LocalPort $WebPort"):
        assert dev_up.index(check) < stop, check


def test_dev_up_cleans_up_the_web_ui(dev_up: str) -> None:
    assert re.search(r"finally\s*\{[^}]*taskkill /PID \$webProcess\.Id /T /F", dev_up)
