"""Ergebnisdateien der Eval-Läufe in `evals/results/` und Vergleich mit dem Vorlauf (AK-6.1/6.2).

Pro Lauf eine JSON-Datei `<datum>_<sha>_<suite>-<modus>.json` und eine Markdown-Zusammenfassung
mit demselben Namen; Läufe mit Antworten (`--answers`) enden auf `-answers`. Vorlauf ist der letzte
Lauf mit derselben Suite, demselben Modus und (bei Antworten) demselben Antwortmodell.
"""

import datetime as dt
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from parlrag.evals.answers import ANSWER_METRICS, AnswerResult
from parlrag.evals.runner import (
    LATENCY_METRICS,
    MRR_K,
    QUALITY_METRICS,
    QuestionResult,
    SubsetResult,
    Suite,
)
from parlrag.evals.threshold import ThresholdReport, threshold_summary
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
    "citation_accuracy": "Zitiergenauigkeit",
    "faithfulness": "Faithfulness",
    "refusal_rate": "Ablehnungsquote (unbeantwortbar)",
    "false_refusal_rate": "Falsche Ablehnungen",
    "neutrality": "Neutralität (wertend)",
    "language_accuracy": "Antwortsprache",
    "answer_p50_ms": "Antwortzeit p50",
    "answer_p95_ms": "Antwortzeit p95",
    "answer_cost_usd": "Kosten Antwort pro Frage",
    "judge_cost_usd": "Kosten Judge pro Frage",
}
MS_METRICS = (*LATENCY_METRICS, "answer_p50_ms", "answer_p95_ms")
COST_METRICS = ("answer_cost_usd", "judge_cost_usd")


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
    # Ab Task 4.3; fehlen in älteren Ergebnisdateien.
    similarities: dict[str, float | None] = {}
    threshold: ThresholdReport | None = None
    # Ab Task 4.5a, nur bei `--answers`.
    answer_config: dict[str, Any] | None = None
    answer_counts: dict[str, int] = {}
    answers: list[AnswerResult] = []

    @property
    def answer_model(self) -> str | None:
        return (self.answer_config or {}).get("answer_model")


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
    stem = f"{run.created_at:%Y-%m-%d}_{run.git_sha[:7]}_{run.suite}-{run.mode}"
    return stem + ("-answers" if run.answer_config else "")


def load_run(path: Path) -> EvalRun:
    try:
        return EvalRun.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise EvalError(f"Ergebnisdatei {path} ist nicht lesbar: {exc}") from exc


def find_previous(
    results_dir: Path, suite: Suite, mode: SearchMode, answer_model: str | None = None
) -> Path | None:
    """Letzter Lauf mit derselben Suite, demselben Modus und demselben Antwortmodell (None:
    Lauf ohne Antworten), nach Zeitpunkt."""
    candidates = [
        (run.created_at, path)
        for path in sorted(results_dir.glob("*.json"))
        if (run := load_run(path)).suite == suite
        and run.mode == mode
        and run.answer_model == answer_model
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
    if {q.id for q in run.questions} != {q.id for q in previous.questions} or {
        a.id for a in run.answers
    } != {a.id for a in previous.answers}:
        return (
            "Der Vorlauf hat andere Fragen gemessen; die Differenzen sind nur bedingt vergleichbar."
        )
    return None


def format_value(name: str, value: float | None) -> str:
    if value is None:
        return "-"
    if name in MS_METRICS:
        return f"{value:.0f} ms"
    return f"{value:.4f} USD" if name in COST_METRICS else f"{value:.3f}"


def format_delta(name: str, value: float | None, previous: float | None) -> str:
    if value is None or previous is None:
        return "-"
    delta = value - previous
    if name in MS_METRICS:
        return f"{delta:+.0f} ms"
    if name in COST_METRICS:
        return f"{delta:+.4f} USD"
    return "±0.000" if abs(delta) < 0.0005 else f"{delta:+.3f}"


def metric_rows(
    metrics: dict[str, float], previous: dict[str, float] | None
) -> list[tuple[str, str, str, str]]:
    """Zeilen (Metrik, Wert, Vorlauf, Δ) für Terminal und Markdown."""
    previous = previous or {}
    answer_metrics = [name for name in ANSWER_METRICS if name in metrics or name in previous]
    return [
        (
            METRIC_LABELS[name],
            format_value(name, metrics.get(name)),
            format_value(name, previous.get(name)),
            format_delta(name, metrics.get(name), previous.get(name)),
        )
        for name in (*QUALITY_METRICS, *LATENCY_METRICS, *answer_metrics)
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


THRESHOLD_HEADER = ("Schwelle", "unbeantwortbar abgefangen", "beantwortbar fälschlich abgewiesen")


def threshold_rows(report: ThresholdReport) -> list[tuple[str, str, str]]:
    return [
        (
            f"{row.threshold:.2f}" + (" (aktuell)" if row.threshold == report.threshold else ""),
            f"{row.unanswerable_refused} / {report.unanswerable}",
            f"{row.answerable_refused} / {report.answerable}",
        )
        for row in report.candidates
    ]


ANSWER_HEADER = (
    "Frage",
    "Art",
    "Ergebnis",
    "erwartete zitiert",
    "Zitiergenauigkeit",
    "Faithfulness",
    "Sprache",
    "neutral",
    "Zeit",
)
REASON_LABELS = {"low_similarity": "Schwelle", "model": "Modell", "no_hits": "keine Treffer"}


def _kind(answer: AnswerResult) -> str:
    if not answer.answerable:
        return "unbeantwortbar"
    return "wertend" if "wertend" in answer.tags else answer.language


def _outcome(answer: AnswerResult) -> str:
    if answer.error:
        return "Fehler: " + answer.error[:60]
    if answer.refused:
        return f"abgelehnt ({REASON_LABELS.get(answer.insufficient_reason or '', '?')})"
    if answer.judge_error:
        return "beantwortet, Judge-Fehler"
    return "beantwortet" + (f", {answer.attempts} Versuche" if (answer.attempts or 0) > 1 else "")


def _flag(value: bool | None) -> str:
    return "-" if value is None else ("ja" if value else "nein")


def answer_rows(run: EvalRun) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    for answer in run.answers:
        expected = len(answer.cited_expected)
        rows.append(
            (
                answer.id,
                _kind(answer),
                _outcome(answer),
                str(expected) if answer.answerable and not answer.refused else "-",
                format_value("citation_accuracy", answer.citation_accuracy),
                format_value("faithfulness", answer.faithfulness),
                _flag(answer.language_ok),
                _flag(answer.neutral) if "wertend" in answer.tags else "-",
                format_value("answer_p50_ms", answer.total_ms),
            )
        )
    return rows


def answer_progress(answer: AnswerResult) -> str:
    """Eine Zeile pro Frage während des Laufs."""
    parts = [answer.id, _outcome(answer)]
    if answer.citation_accuracy is not None:
        parts.append(f"Zitate {answer.citation_accuracy:.2f}")
    if answer.faithfulness is not None:
        parts.append(f"Faithfulness {answer.faithfulness:.2f}")
    if answer.total_ms is not None:
        parts.append(f"{answer.total_ms / 1000:.1f} s")
    return "  ".join(parts)


def answer_summary(run: EvalRun) -> str:
    counts = run.answer_counts
    config = run.answer_config or {}
    line = (
        f"{counts.get('questions', 0)} Fragen: {counts.get('answered', 0)} beantwortet, "
        f"{counts.get('refused', 0)} abgelehnt, {counts.get('errors', 0)} Fehler; "
        f"{counts.get('judged', 0)} vom Judge bewertet. Antworten: {config.get('answer_model')} "
        f"(`{config.get('answer_effort')}`), Judge: {config.get('judge_model')} "
        f"(`{config.get('judge_effort')}`), Backend `{config.get('llm_backend')}`."
    )
    if config.get("llm_backend") == "claude-code":
        line += (
            " Über das Claude-Abo: Antwortzeiten enthalten den Start der CLI, Kosten sind "
            "Schätzungen von Claude Code."
        )
    return line


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
    if run.threshold:
        lines += ["", "## Schwelle für «keine ausreichende Grundlage»", ""]
        lines += [threshold_summary(run.threshold), ""]
        lines += _table(THRESHOLD_HEADER, threshold_rows(run.threshold))
    if run.answers:
        lines += ["", "## Antworten", "", answer_summary(run), ""]
        lines += _table(ANSWER_HEADER, answer_rows(run))
    lines += ["", "## Verfehlte Quellen (Recall@10 < 1)", ""]
    lines += [f"- {line}" for line in misses(run)] or ["Keine."]
    return "\n".join(lines) + "\n"
