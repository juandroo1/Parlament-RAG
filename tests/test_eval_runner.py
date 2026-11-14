"""Eval-Runner (Task 3.2): Messung, Ergebnisdateien, Vergleich mit dem Vorlauf und CLI.

Ohne Datenbank und ohne Modell: Ein Fake-Retriever liefert pro Frage feste Treffer.
"""

import datetime as dt
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from fakes import FakeEmbedder
from parlrag import cli
from parlrag.evals import GoldenItem
from parlrag.evals import results as results_module
from parlrag.evals.results import (
    EvalError,
    EvalRun,
    comparison_warning,
    find_previous,
    git_state,
    load_run,
    metric_rows,
    misses,
    render_markdown,
    write_run,
)
from parlrag.evals.runner import CHUNKS_PER_QUERY, evaluate_retrieval, select_suite
from parlrag.retrieval import SearchFilters, SearchHit

ITEMS = [
    {
        "id": "q01",
        "question": "Was sagte Bundesrat Rösti zum Kühlwasser?",
        "language": "de",
        "expected_source_ids": ["transcript:1", "business:2"],
        "answerable": True,
        "tags": ["teilkorpus", "smoke"],
    },
    {
        "id": "q02",
        "question": "Qu'a dit le Conseil fédéral sur la grêle ?",
        "language": "fr",
        "filters": {"council": "SR"},
        "expected_source_ids": ["transcript:3"],
        "answerable": True,
        "tags": ["fr", "crosslingual", "filter", "smoke"],
    },
    {
        "id": "q03",
        "question": "Was beschloss der Bieler Stadtrat zur Fusion?",
        "language": "de",
        "expected_source_ids": [],
        "answerable": False,
        "tags": ["unanswerable", "smoke"],
    },
    {
        "id": "q04",
        "question": "Ist die Inklusions-Initiative eine gute Vorlage?",
        "language": "de",
        "expected_source_ids": ["transcript:4"],
        "answerable": True,
        "tags": ["wertend"],
    },
]
GOLDEN = [GoldenItem.model_validate(item) for item in ITEMS]

# Treffer als Chunks (mit Wiederholungen desselben Dokuments).
HITS = {
    "q01": ["transcript:1", "transcript:1", "transcript:5", "business:2", "business:2"],
    "q02": [f"transcript:{n}" for n in range(10, 21)] + ["transcript:3"],  # Dokument-Rang 12
    "q04": ["transcript:9", "transcript:4"],
}


def _hit(key: str, rank: int) -> SearchHit:
    source_type, source_id = key.split(":")
    return SearchHit(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        text="…",
        section=None,
        score=1 / (60 + rank),
        rank=rank,
        fulltext_rank=None,
        fulltext_score=None,
        vector_rank=rank,
        vector_similarity=0.5,
        source_type=source_type,
        source_id=source_id,
        language="de",
        title="Titel",
        speaker_name=None,
        parl_group=None,
        canton=None,
        council="NR",
        date=dt.date(2026, 9, 15),
        debate_dates=(),
        debate_councils=(),
        business_numbers=(),
        url="https://www.parlament.ch/",
    )


class FakeRetriever:
    def __init__(self, hits: dict[str, list[str]] = HITS) -> None:
        self.by_question = {item.question: hits.get(item.id, []) for item in GOLDEN}
        self.calls: list[dict[str, Any]] = []
        self.embedder = FakeEmbedder()

    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        *,
        mode: str = "hybrid",
        top_n: int | None = None,
    ) -> list[SearchHit]:
        self.calls.append({"query": query, "filters": filters, "mode": mode, "top_n": top_n})
        return [_hit(key, rank) for rank, key in enumerate(self.by_question[query], start=1)]


def _clock(step: float = 0.1) -> Any:
    ticks = iter(n * step for n in range(10_000))
    return lambda: next(ticks)


def test_select_suite() -> None:
    assert [item.id for item in select_suite(GOLDEN, "smoke")] == ["q01", "q02", "q03"]
    assert [item.id for item in select_suite(GOLDEN, "full")] == ["q01", "q02", "q03", "q04"]


def test_evaluate_retrieval_measures_documents_not_chunks() -> None:
    retriever = FakeRetriever()
    report = evaluate_retrieval(GOLDEN, retriever, "vector", clock=_clock())

    assert [q.id for q in report.questions] == ["q01", "q02", "q04"]
    assert report.skipped_unanswerable == 1
    q01, q02, q04 = report.questions
    assert q01.top_documents == ("transcript:1", "transcript:5", "business:2")
    assert q01.ranks == {"transcript:1": 1, "business:2": 3}
    assert q01.metrics == {"recall@5": 1.0, "recall@10": 1.0, "recall@20": 1.0, "mrr@10": 1.0}
    assert q02.ranks == {"transcript:3": 12}
    assert q02.metrics == {"recall@5": 0.0, "recall@10": 0.0, "recall@20": 1.0, "mrr@10": 0.0}
    assert q04.metrics["mrr@10"] == 0.5
    assert len(q02.top_documents) == 10

    assert report.metrics["recall@10"] == pytest.approx(2 / 3)
    assert report.metrics["mrr@10"] == pytest.approx(0.5)
    assert report.metrics["search_p95_ms"] == pytest.approx(100.0)


def test_evaluate_retrieval_passes_filters_mode_and_depth() -> None:
    retriever = FakeRetriever()
    evaluate_retrieval(GOLDEN, retriever, "fulltext", clock=_clock())

    assert [call["filters"] for call in retriever.calls] == [
        None,
        SearchFilters(council="SR"),
        None,
    ]
    assert {call["mode"] for call in retriever.calls} == {"fulltext"}
    assert {call["top_n"] for call in retriever.calls} == {CHUNKS_PER_QUERY}


def test_subsets() -> None:
    report = evaluate_retrieval(GOLDEN, FakeRetriever(), "hybrid", clock=_clock())

    assert {name: subset.n for name, subset in report.subsets.items()} == {
        "de": 2,
        "fr": 1,
        "crosslingual": 1,
        "filter": 1,
        "teilkorpus": 1,
        "wertend": 1,
    }
    assert report.subsets["crosslingual"].metrics["recall@10"] == 0.0
    assert report.subsets["de"].metrics["mrr@10"] == 0.75


def test_only_unanswerable_questions_is_an_error() -> None:
    with pytest.raises(ValueError, match="beantwortbaren"):
        evaluate_retrieval([GOLDEN[2]], FakeRetriever(), "hybrid")


def _run(
    created_at: dt.datetime = dt.datetime(2026, 11, 14, 10, 0, tzinfo=dt.UTC),
    mode: str = "hybrid",
    hits: dict[str, list[str]] = HITS,
    items: list[GoldenItem] = GOLDEN,
) -> EvalRun:
    report = evaluate_retrieval(items, FakeRetriever(hits), mode, clock=_clock())  # type: ignore[arg-type]
    return EvalRun(
        created_at=created_at,
        git_sha="abc1234def5678",
        git_dirty=False,
        suite="full",
        mode=mode,  # type: ignore[arg-type]
        golden="evals/datasets/golden.jsonl",
        questions_total=len(items),
        skipped_unanswerable=report.skipped_unanswerable,
        config={"chunks_per_query": CHUNKS_PER_QUERY},
        corpus={"documents": 42515, "chunks": 102891},
        metrics=report.metrics,
        subsets=report.subsets,
        questions=report.questions,
    )


def test_write_run_creates_json_and_markdown_without_overwriting(tmp_path: Path) -> None:
    run = _run()
    first = write_run(run, None, tmp_path)
    second = write_run(run, None, tmp_path)

    assert first.name == "2026-11-14_abc1234_full-hybrid.json"
    assert second.name == "2026-11-14_abc1234_full-hybrid-2.json"
    assert first.with_suffix(".md").exists()
    assert load_run(first) == run


def test_find_previous_uses_latest_run_of_same_suite_and_mode(tmp_path: Path) -> None:
    assert find_previous(tmp_path, "full", "hybrid") is None
    older = write_run(_run(dt.datetime(2026, 11, 13, tzinfo=dt.UTC)), None, tmp_path)
    newer = write_run(_run(dt.datetime(2026, 11, 14, tzinfo=dt.UTC)), None, tmp_path)
    write_run(_run(dt.datetime(2026, 11, 15, tzinfo=dt.UTC), mode="fulltext"), None, tmp_path)

    assert older != newer
    assert find_previous(tmp_path, "full", "hybrid") == newer
    assert find_previous(tmp_path, "smoke", "hybrid") is None


def test_unreadable_result_file_is_reported(tmp_path: Path) -> None:
    (tmp_path / "kaputt.json").write_text("{}", encoding="utf-8")
    with pytest.raises(EvalError, match=r"kaputt.json"):
        find_previous(tmp_path, "full", "hybrid")


def test_metric_rows_show_delta_to_previous_run() -> None:
    better = {**HITS, "q02": ["transcript:3"]}
    previous, current = _run(), _run(hits=better)
    rows = {row[0]: row[1:] for row in metric_rows(current.metrics, previous.metrics)}

    assert rows["Recall@10"] == ("1.000", "0.667", "+0.333")
    assert rows["Recall@20"] == ("1.000", "1.000", "±0.000")
    assert rows["Suchdauer p95"] == ("100 ms", "100 ms", "+0 ms")
    first = {row[0]: row[1:] for row in metric_rows(current.metrics, None)}
    assert first["MRR@10"] == ("0.833", "-", "-")


def test_comparison_warns_when_questions_differ() -> None:
    assert comparison_warning(_run(), _run()) is None
    assert comparison_warning(_run(), None) is None
    assert comparison_warning(_run(items=GOLDEN[:2]), _run()) is not None


def test_misses_list_expected_ranks() -> None:
    lines = misses(_run())
    assert lines == ["q02 (Recall@10 0.00): transcript:3 #12"]
    not_found = misses(_run(hits={**HITS, "q04": ["transcript:9"]}))
    assert "q04 (Recall@10 0.00): transcript:4 nicht gefunden" in not_found


def test_markdown_summary() -> None:
    previous = _run()
    current = _run().model_copy(update={"previous": "2026-11-13_abc1234_full-hybrid.json"})
    text = render_markdown(current, previous)

    assert text.startswith("# Eval-Lauf 2026-11-14 10:00 · full · hybrid")
    assert "42'515 Dokumente, 102'891 Chunks" in text
    assert "`2026-11-13_abc1234_full-hybrid.json`" in text
    assert "| Recall@10 | 0.667 | 0.667 | ±0.000 |" in text
    assert "| crosslingual | 1 |" in text
    assert "- q02 (Recall@10 0.00): transcript:3 #12" in text
    assert "kein Vorlauf" in render_markdown(_run(), None)


def test_git_state_outside_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_git(*args: Any, **kwargs: Any) -> None:
        raise FileNotFoundError("git")

    monkeypatch.setattr(results_module.subprocess, "run", no_git)
    with pytest.raises(EvalError, match="nur lokal mit uv"):
        git_state()


def test_git_state_reports_sha_and_dirty(monkeypatch: pytest.MonkeyPatch) -> None:
    outputs = {"rev-parse": "abc123\n", "status": " M src/parlrag/cli.py\n"}

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert ":(top,exclude)evals/results" in args or args[1] == "rev-parse"
        return subprocess.CompletedProcess(args, 0, stdout=outputs[args[1]])

    monkeypatch.setattr(results_module.subprocess, "run", fake_run)
    assert git_state() == ("abc123", True)


# --- CLI ---------------------------------------------------------------------------------

runner = CliRunner()


@pytest.fixture
def eval_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    golden = tmp_path / "golden.jsonl"
    golden.write_text("\n".join(json.dumps(item) for item in ITEMS) + "\n", encoding="utf-8")
    retriever = FakeRetriever()
    state = {"dirty": False}
    monkeypatch.setattr(cli, "git_state", lambda: ("abc1234def5678", state["dirty"]))
    monkeypatch.setattr(cli, "build_retriever", lambda: retriever)
    monkeypatch.setattr(
        cli,
        "describe_eval",
        lambda r: ({"chunks_per_query": 100}, {"documents": 3, "chunks": 5}),
    )
    return {
        "args": ["--golden", str(golden), "--results-dir", str(tmp_path / "results")],
        "results": tmp_path / "results",
        "retriever": retriever,
        "state": state,
    }


def test_eval_cli_writes_results_and_compares_with_previous_run(eval_env: dict[str, Any]) -> None:
    first = runner.invoke(cli.app, ["eval", "--suite", "full", *eval_env["args"]])
    assert first.exit_code == 0, first.output
    assert "Kein Vorlauf" in first.output
    assert "Recall@10" in first.output and "crosslingual" in first.output
    assert "q02 (Recall@10 0.00): transcript:3 #12" in first.output

    second = runner.invoke(cli.app, ["eval", "--suite", "full", *eval_env["args"]])
    assert second.exit_code == 0, second.output
    assert "±0.000" in second.output

    files = sorted(eval_env["results"].glob("*.json"))
    assert [f.name[11:] for f in files] == [
        "abc1234_full-hybrid-2.json",
        "abc1234_full-hybrid.json",
    ]
    latest = load_run(files[0])
    assert latest.previous == files[1].name
    assert latest.questions_total == 4 and latest.skipped_unanswerable == 1
    assert latest.corpus == {"documents": 3, "chunks": 5}
    assert len(list(eval_env["results"].glob("*.md"))) == 2


def test_eval_cli_smoke_suite_and_mode(eval_env: dict[str, Any]) -> None:
    result = runner.invoke(cli.app, ["eval", "--mode", "fulltext", *eval_env["args"]])

    assert result.exit_code == 0, result.output
    retriever = eval_env["retriever"]
    assert len(retriever.calls) == 2  # smoke: q01, q02 (q03 unbeantwortbar)
    assert {call["mode"] for call in retriever.calls} == {"fulltext"}
    assert retriever.embedder.calls == 0  # Volltext lädt kein Modell
    run = load_run(next(eval_env["results"].glob("*.json")))
    assert (run.suite, run.mode) == ("smoke", "fulltext")


def test_eval_cli_compare_with_explicit_run(eval_env: dict[str, Any]) -> None:
    runner.invoke(cli.app, ["eval", "--mode", "fulltext", *eval_env["args"]])
    baseline = next(eval_env["results"].glob("*.json"))

    result = runner.invoke(cli.app, ["eval", "--compare", str(baseline), *eval_env["args"]])

    assert result.exit_code == 0, result.output
    assert f"Vergleich mit {baseline.name}" in result.output


def test_eval_cli_warns_about_uncommitted_changes(eval_env: dict[str, Any]) -> None:
    eval_env["state"]["dirty"] = True
    result = runner.invoke(cli.app, ["eval", *eval_env["args"]])

    assert result.exit_code == 0
    assert "ungecommittete" in result.output
    assert load_run(next(eval_env["results"].glob("*.json"))).git_dirty


def test_eval_cli_stops_without_git(
    eval_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_git() -> tuple[str, bool]:
        raise EvalError("Evals laufen nur lokal mit uv")

    monkeypatch.setattr(cli, "git_state", no_git)
    result = runner.invoke(cli.app, ["eval", *eval_env["args"]])

    assert result.exit_code == 1
    assert "nur lokal mit uv" in result.output
    assert eval_env["retriever"].calls == []


def test_eval_cli_reports_invalid_golden_set(eval_env: dict[str, Any], tmp_path: Path) -> None:
    broken = tmp_path / "broken.jsonl"
    broken.write_text("{kein json\n", encoding="utf-8")
    result = runner.invoke(
        cli.app, ["eval", "--golden", str(broken), "--results-dir", str(tmp_path / "r")]
    )

    assert result.exit_code == 1
    assert "Zeile 1" in result.output
