"""Prüft den CI-Workflow gegen CLAUDE.md, Abschnitt CI, und plan.md (Entscheidungsprotokoll)."""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


@pytest.fixture(scope="module")
def workflow() -> dict[Any, Any]:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _triggers(workflow: dict[Any, Any]) -> dict[str, Any]:
    # PyYAML (YAML 1.1) liest den Schlüssel `on` als True.
    triggers = workflow.get("on", workflow.get(True))
    assert isinstance(triggers, dict)
    return triggers


def _run_commands(job: dict[str, Any]) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def test_runs_on_pull_requests_and_pushes_to_main(workflow: dict[Any, Any]) -> None:
    triggers = _triggers(workflow)
    assert "pull_request" in triggers
    assert triggers["push"]["branches"] == ["main"]


def test_has_read_only_permissions(workflow: dict[Any, Any]) -> None:
    assert workflow["permissions"] == {"contents": "read"}


def test_lint_test_job_runs_all_checks(workflow: dict[Any, Any]) -> None:
    commands = _run_commands(workflow["jobs"]["lint-test"])
    for expected in [
        "uv sync --frozen",
        "uv run ruff check .",
        "uv run ruff format --check .",
        "uv run mypy src tests",
        "uv run pytest",
    ]:
        assert expected in commands


def test_db_tests_are_mandatory_in_ci(workflow: dict[Any, Any]) -> None:
    job = workflow["jobs"]["lint-test"]
    assert job["env"]["PARLRAG_REQUIRE_DB"] == "1"
    assert job["services"]["postgres"]["image"] == "pgvector/pgvector:pg16"
    assert job["env"]["POSTGRES_HOST"] == "127.0.0.1"


def test_docker_smoke_test_builds_waits_checks_and_cleans_up(workflow: dict[Any, Any]) -> None:
    job = workflow["jobs"]["docker-smoke"]
    commands = _run_commands(job)
    joined = "\n".join(commands)
    assert "cp .env.example .env" in commands
    assert "docker compose build" in commands
    assert re.search(r"docker compose up -d --wait\b", joined)
    assert "http://127.0.0.1:8000/health" in joined
    teardown = next(step for step in job["steps"] if step.get("run") == "docker compose down -v")
    assert teardown["if"] == "always()"


def test_actions_are_pinned_to_commit_shas(workflow: dict[Any, Any]) -> None:
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", step["uses"]), step["uses"]


def test_no_evals_in_ci() -> None:
    assert "parlrag eval" not in WORKFLOW.read_text(encoding="utf-8")
