"""Ergebnisdateien der Eval-Läufe in `evals/results/` und Vergleich mit dem Vorlauf (AK-6.1/6.2).

Pro Lauf eine JSON-Datei `<datum>_<sha>_<suite>-<modus>.json` und eine Markdown-Zusammenfassung
mit demselben Namen. Vorlauf ist der letzte Lauf mit derselben Suite und demselben Modus.
"""

import datetime as dt
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from parlrag.evals.runner import (
    LATENCY_METRICS,
    MRR_K,
    QUALITY_METRICS,
    QuestionResult,
    SubsetResult,
    Suite,
)
from parlrag.retrieval import SearchMode

DEFAULT_RESULTS_DIR = Path("evals/results")
SCHEMA_VERSION = 1

METRIC_LABELS = {
    "recall@5": "Recall@5",
    "recall@10": "Recall@10",
    "recall@20": "Recall@20",
    f"mrr@{MRR_K}": f"MRR@{MRR_K}",
    "search_p50_ms": "Suchdauer p50",
    "search_p95_ms": "Suchdauer p95",
}


class EvalError(RuntimeError):
    """Der Eval-Lauf kann nicht ausgeführt oder gespeichert werden."""


class EvalRun(BaseModel):
    """Ein Eval-Lauf mit Konfiguration, Korpus-Stand und Ergebnissen."""

    schema_version: int = SCHEMA_VERSION
    created_at: dt.datetime
    git_sha: str
    git_dirty: bool
    suite: Suite
    mode: SearchMode
    golden: str
    questions_total: int
    skipped_unanswerable: int
    config: dict[str, Any]
    corpus: dict[str, Any]
    metrics: dict[str, float]
    subsets: dict[str, SubsetResult]
    questions: list[QuestionResult]
    previous: str | None = None  # Dateiname des Vergleichslaufs


def git_state() -> tuple[str, bool]:
    """Git-SHA von HEAD und ob ungecommittete Änderungen vorliegen (ohne `evals/results/`)."""
    try:
        sha = _git("rev-parse", "HEAD").strip()
        status = _git("status", "--porcelain", "--", ":(top)", ":(top,exclude)evals/results")
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise EvalError(
            "Kein Git-Repository gefunden. Evals laufen nur lokal mit uv "
            "(`uv run parlrag eval`), nicht im Container."
        ) from exc
    return sha, bool(status.strip())


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True, encoding="utf-8"
    ).stdout


def run_stem(run: EvalRun) -> str:
    return f"{run.created_at:%Y-%m-%d}_{run.git_sha[:7]}_{run.suite}-{run.mode}"


def load_run(path: Path) -> EvalRun:
    try:
        return EvalRun.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise EvalError(f"Ergebnisdatei {path} ist nicht lesbar: {exc}") from exc


def find_previous(results_dir: Path, suite: Suite, mode: SearchMode) -> Path | None:
    """Letzter Lauf mit derselben Suite und demselben Modus, nach Zeitpunkt."""
    candidates = [
        (run.created_at, path)
        for path in sorted(results_dir.glob("*.json"))
        if (run := load_run(path)).suite == suite and run.mode == mode
    ]
    return max(candidates)[1] if candidates else None


def write_run(run: EvalRun, previous: EvalRun | None, results_dir: Path) -> Path:
    """Schreibt JSON und Markdown; ein bestehender Lauf wird nie überschrieben."""
    results_dir.mkdir(parents=True, exist_ok=True)
    stem = name = run_stem(run)
    number = 1
    while (results_dir / f"{name}.json").exists():
        number += 1
        name = f"{stem}-{number}"
    path = results_dir / f"{name}.json"
    path.write_text(run.model_dump_json(indent=2) + "\n", encoding="utf-8")
    path.with_suffix(".md").write_text(render_markdown(run, previous), encoding="utf-8")
    return path


def comparison_warning(run: EvalRun, previous: EvalRun | None) -> str | None:
    """Hinweis, wenn der Vorlauf andere Fragen gemessen hat (Δ dann nur bedingt aussagekräftig)."""
    if previous is None:
        return None
    if {q.id for q in run.questions} != {q.id for q in previous.questions}:
        return (
            "Der Vorlauf hat andere Fragen gemessen; die Differenzen sind nur bedingt vergleichbar."
        )
    return None


def format_value(name: str, value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.0f} ms" if name in LATENCY_METRICS else f"{value:.3f}"


def format_delta(name: str, value: float | None, previous: float | None) -> str:
    if value is None or previous is None:
        return "-"
    delta = value - previous
    if name in LATENCY_METRICS:
        return f"{delta:+.0f} ms"
    return "±0.000" if abs(delta) < 0.0005 else f"{delta:+.3f}"


def metric_rows(
    metrics: dict[str, float], previous: dict[str, float] | None
) -> list[tuple[str, str, str, str]]:
    """Zeilen (Metrik, Wert, Vorlauf, Δ) für Terminal und Markdown."""
    previous = previous or {}
    return [
        (
            METRIC_LABELS[name],
            format_value(name, metrics.get(name)),
            format_value(name, previous.get(name)),
            format_delta(name, metrics.get(name), previous.get(name)),
        )
        for name in (*QUALITY_METRICS, *LATENCY_METRICS)
    ]


def subset_rows(run: EvalRun, previous: EvalRun | None) -> list[tuple[str, ...]]:
    """Zeilen (Teilset, n, Recall@5/10/20, MRR@10, Δ Recall@10)."""
    rows = []
    for name, subset in run.subsets.items():
        before = previous.subsets.get(name) if previous else None
        rows.append(
            (
                name,
                str(subset.n),
                *(format_value(metric, subset.metrics[metric]) for metric in QUALITY_METRICS),
                format_delta(
                    "recall@10",
                    subset.metrics["recall@10"],
                    before.metrics["recall@10"] if before else None,
                ),
            )
        )
    return rows


SUBSET_HEADER = ("Teilset", "n", "Recall@5", "Recall@10", "Recall@20", "MRR@10", "Δ Recall@10")


def misses(run: EvalRun) -> list[str]:
    """Fragen mit Recall@10 < 1 und dem Dokument-Rang jeder erwarteten Quelle."""
    lines = []
    for question in run.questions:
        if question.metrics["recall@10"] < 1:
            ranks = ", ".join(
                f"{key} {'#' + str(rank) if rank else 'nicht gefunden'}"
                for key, rank in question.ranks.items()
            )
            lines.append(f"{question.id} (Recall@10 {question.metrics['recall@10']:.2f}): {ranks}")
    return lines


def _number(value: int) -> str:
    return f"{value:,}".replace(",", "'")


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return lines + ["| " + " | ".join(row) + " |" for row in rows]


def render_markdown(run: EvalRun, previous: EvalRun | None) -> str:
    measured = len(run.questions)
    lines = [
        f"# Eval-Lauf {run.created_at:%Y-%m-%d %H:%M} · {run.suite} · {run.mode}",
        "",
        f"- Commit: `{run.git_sha[:7]}`"
        + (" (mit ungecommitteten Änderungen)" if run.git_dirty else ""),
        f"- Goldset: `{run.golden}`, {run.questions_total} Fragen, davon {measured} gemessen"
        f" ({run.skipped_unanswerable} unbeantwortbare übersprungen)",
        "- Vergleich: "
        + (
            f"`{run.previous}` (Commit `{previous.git_sha[:7]}`)"
            if previous and run.previous
            else "kein Vorlauf mit derselben Suite und demselben Modus"
        ),
        "- Konfiguration: " + ", ".join(f"`{key}={value}`" for key, value in run.config.items()),
        f"- Korpus: {_number(run.corpus.get('documents', 0))} Dokumente, "
        f"{_number(run.corpus.get('chunks', 0))} Chunks",
    ]
    if warning := comparison_warning(run, previous):
        lines += ["", f"> {warning}"]
    lines += ["", "## Metriken", ""]
    lines += _table(
        ("Metrik", "Wert", "Vorlauf", "Δ"),
        metric_rows(run.metrics, previous.metrics if previous else None),
    )
    lines += ["", "## Teilsets", ""]
    lines += _table(SUBSET_HEADER, subset_rows(run, previous))
    lines += ["", "## Verfehlte Quellen (Recall@10 < 1)", ""]
    lines += [f"- {line}" for line in misses(run)] or ["Keine."]
    return "\n".join(lines) + "\n"
