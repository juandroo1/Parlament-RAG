"""Prüft die Leitplanken aus CLAUDE.md (Abschnitt Docker) an den Konfigurationsdateien."""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def compose() -> dict[str, Any]:
    data = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.fixture(scope="module")
def services(compose: dict[str, Any]) -> dict[str, Any]:
    result = compose["services"]
    assert isinstance(result, dict)
    return result


def test_expected_services_exist(services: dict[str, Any]) -> None:
    assert {"db", "app"} <= services.keys()
    assert services["db"]["image"].startswith("pgvector/pgvector:pg16")


def test_ports_are_bound_to_localhost(services: dict[str, Any]) -> None:
    for name, service in services.items():
        for port in service.get("ports", []):
            assert str(port).startswith("127.0.0.1:"), f"{name}: {port}"


def test_every_service_has_a_healthcheck(services: dict[str, Any]) -> None:
    for name, service in services.items():
        assert "healthcheck" in service, name


def test_app_waits_for_healthy_db(services: dict[str, Any]) -> None:
    assert services["app"]["depends_on"]["db"]["condition"] == "service_healthy"


def test_no_literal_secrets_in_compose(services: dict[str, Any]) -> None:
    secret_keys = re.compile(r"PASSWORD|API_KEY|SECRET|TOKEN", re.IGNORECASE)
    for name, service in services.items():
        environment = service.get("environment", {})
        assert isinstance(environment, dict), f"{name}: environment als Mapping schreiben"
        for key, value in environment.items():
            if secret_keys.search(key):
                assert str(value).startswith("${"), f"{name}.{key} enthält einen Klartextwert"


def test_db_does_not_receive_the_full_env_file(services: dict[str, Any]) -> None:
    assert "env_file" not in services["db"]


def test_pgdata_volume_is_declared(compose: dict[str, Any], services: dict[str, Any]) -> None:
    assert "pgdata" in compose["volumes"]
    assert any(v.startswith("pgdata:") for v in services["db"]["volumes"])


def test_raw_cache_is_bind_mounted_for_app(services: dict[str, Any]) -> None:
    app = services["app"]
    assert "./data/raw:/app/data/raw" in app["volumes"]
    assert app["environment"]["RAW_CACHE_DIR"] == "/app/data/raw"


def test_model_cache_is_a_volume_not_part_of_the_image(
    compose: dict[str, Any], services: dict[str, Any]
) -> None:
    assert "hf-cache" in compose["volumes"]
    assert "hf-cache:/home/app/.cache/huggingface" in services["app"]["volumes"]
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "HF_HOME=/home/app/.cache/huggingface" in dockerfile
    assert "chown -R app:app /home/app/.cache" in dockerfile


def test_torch_comes_from_the_cpu_index() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'torch = [{ index = "pytorch-cpu" }]' in pyproject
    assert 'url = "https://download.pytorch.org/whl/cpu"' in pyproject
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "nvidia-' not in lock
    assert 'name = "triton"' not in lock


def test_dockerfile_runs_as_non_root_without_uv() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    final_stage = dockerfile.rsplit("\nFROM ", 1)[1]
    users = re.findall(r"^USER\s+(\S+)", final_stage, flags=re.MULTILINE)
    assert users, "finale Stage ohne USER"
    assert users[-1] not in {"root", "0"}
    assert "uv" not in re.findall(r"^COPY --from=(\S+)", final_stage, flags=re.MULTILINE)
    assert "uv sync --frozen --no-dev" in dockerfile


def test_entrypoint_runs_migrations_before_command() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    final_stage = dockerfile.rsplit("\nFROM ", 1)[1]
    assert 'ENTRYPOINT ["docker-entrypoint.sh"]' in final_stage

    script = (ROOT / "docker-entrypoint.sh").read_bytes()
    assert b"\r" not in script, "CRLF bricht das Skript im Linux-Container"
    lines = script.decode("utf-8").splitlines()
    assert lines[0] == "#!/bin/sh"
    assert "set -e" in lines
    migrate = lines.index("python -m parlrag.db.migrate")
    assert lines.index('exec "$@"') > migrate


@pytest.mark.parametrize("entry", [".git", ".venv", "data/", "node_modules", "__pycache__", ".env"])
def test_dockerignore_contains_required_entries(entry: str) -> None:
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert entry in lines
