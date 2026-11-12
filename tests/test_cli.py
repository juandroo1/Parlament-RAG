"""CLI `parlrag ingest`: Optionen und Ausgabe (Pipeline ersetzt, kein Netz, keine DB)."""

import datetime as dt
import logging
import re
from typing import Any

import pytest
from typer.testing import CliRunner

from parlrag import cli
from parlrag.ingest.pipeline import IngestStats
from parlrag.ingest.store import UpsertResult

runner = CliRunner()


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    recorded: list[dict[str, Any]] = []

    def fake_execute(
        since: dt.date, until: dt.date, languages: frozenset[str], refresh: bool
    ) -> IngestStats:
        recorded.append(
            {"since": since, "until": until, "languages": languages, "refresh": refresh}
        )
        return IngestStats(
            sessions=1,
            meetings=2,
            subjects=12,
            transcripts=7,
            skipped_transcripts=1,
            businesses=1,
            documents=8,
            stored=UpsertResult(inserted=8),
        )

    monkeypatch.setattr(cli, "execute_ingest", fake_execute)
    return recorded


@pytest.mark.parametrize(
    ("flags", "level"), [([], logging.WARNING), (["--verbose"], logging.DEBUG)]
)
def test_http_request_logging_only_when_verbose(
    calls: list[dict[str, Any]], flags: list[str], level: int
) -> None:
    result = runner.invoke(cli.app, [*flags, "ingest", "--since", "2026-09-15"])

    assert result.exit_code == 0, result.output
    assert logging.getLogger("httpx2").level == level


def test_help_lists_ingest_options() -> None:
    result = runner.invoke(cli.app, ["ingest", "--help"])
    assert result.exit_code == 0
    # In der CI färbt Rich die Hilfe ein; ANSI-Codes entfernen, bevor verglichen wird.
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    for option in ["--since", "--until", "--lang", "--refresh"]:
        assert option in plain


def test_ingest_passes_parsed_options(calls: list[dict[str, Any]]) -> None:
    result = runner.invoke(
        cli.app,
        ["ingest", "--since", "2026-09-15", "--until", "2026-09-16", "--lang", "FR", "--refresh"],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "since": dt.date(2026, 9, 15),
            "until": dt.date(2026, 9, 16),
            "languages": frozenset({"fr"}),
            "refresh": True,
        }
    ]
    assert "Dokumente: 8 (neu 8, geändert 0, unverändert 0)" in result.output


def test_defaults_cover_spec_scope_until_today(calls: list[dict[str, Any]]) -> None:
    result = runner.invoke(cli.app, ["ingest"])

    assert result.exit_code == 0, result.output
    assert calls[0]["since"] == dt.date(2023, 12, 1)
    assert calls[0]["until"] == dt.date.today()
    assert calls[0]["languages"] == frozenset({"de", "fr"})
    assert calls[0]["refresh"] is False


@pytest.mark.parametrize(
    "args",
    [
        ["--since", "15.09.2026"],
        ["--since", "2026-09-16", "--until", "2026-09-15"],
        ["--lang", "it"],
        ["--lang", ","],
    ],
)
def test_invalid_options_are_rejected(calls: list[dict[str, Any]], args: list[str]) -> None:
    result = runner.invoke(cli.app, ["ingest", *args])

    assert result.exit_code == 2
    assert calls == []
