"""Antwort-Evals (Task 4.5a; plan.md, Abschnitt 9; spec.md, Abschnitt 6).

Jede Frage läuft durch dieselbe `AskPipeline` wie `parlrag ask`; beantwortete Fragen bewertet
danach der Judge. Metriken:

- Zitiergenauigkeit: Anteil der Paare (Aussage, zitierte Quelle), bei denen die Quelle stützt.
- Faithfulness: mittlere Stützung der Aussagen (gestützt 1, teilweise 0.5, nicht gestützt 0).
- Ablehnungsquote: unbeantwortbare Fragen mit «keine ausreichende Grundlage» (AK-3.2).
- Falsche Ablehnungen: beantwortbare Fragen mit diesem Hinweis, ohne wertende (AK-3.3).
- Neutralität: wertende Fragen ohne eigene Wertung; eine Ablehnung gilt als neutral (AK-7.1).
- Antwortsprache: erkannte Sprache der Antwort = Sprache der Frage (AK-1.1).
- Latenz p50/p95 der ganzen Frage und Kosten pro Frage, Antwort und Judge getrennt.

Ein Fehler bei einer Frage (z. B. Abo-Limit) wird erfasst; der Lauf geht weiter.
"""

import dataclasses
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel

from parlrag.evals.dataset import GoldenItem
from parlrag.evals.judge import Judge, JudgeOutput, citation_accuracy, faithfulness
from parlrag.evals.metrics import mean, percentile
from parlrag.generation.pipeline import AskResult
from parlrag.llm import LLMError, Usage
from parlrag.retrieval import SearchFilters, SearchMode
from parlrag.retrieval.fulltext import detect_query_language

ANSWER_METRICS = (
    "citation_accuracy",
    "faithfulness",
    "refusal_rate",
    "false_refusal_rate",
    "neutrality",
    "language_accuracy",
    "answer_p50_ms",
    "answer_p95_ms",
    "answer_cost_usd",
    "judge_cost_usd",
)


class SupportsAsk(Protocol):
    def ask(
        self, question: str, filters: SearchFilters | None = None, *, mode: SearchMode | None = None
    ) -> AskResult: ...


class AnswerResult(BaseModel):
    """Antwort und Bewertung einer Frage; Felder sind leer, wenn ein Schritt fehlschlug."""

    id: str
    language: str
    tags: tuple[str, ...]
    answerable: bool
    answer: str | None = None
    insufficient_context: bool | None = None
    insufficient_reason: str | None = None
    best_similarity: float | None = None
    sources: list[str] = []  # «[n] <source_type>:<source_id>»
    cited_expected: list[str] = []  # erwartete Dokumente, die zitiert wurden
    answer_language: str | None = None
    total_ms: float | None = None
    attempts: int | None = None
    answer_usage: dict[str, Any] | None = None
    judge: JudgeOutput | None = None
    judge_usage: dict[str, Any] | None = None
    citation_accuracy: float | None = None
    faithfulness: float | None = None
    neutral: bool | None = None
    error: str | None = None
    judge_error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def refused(self) -> bool:
        return bool(self.insufficient_context)

    @property
    def language_ok(self) -> bool | None:
        return None if self.answer_language is None else self.answer_language == self.language


@dataclass(frozen=True)
class AnswerReport:
    answers: list[AnswerResult]
    metrics: dict[str, float]
    counts: dict[str, int]


def _usage_dict(usage: Usage | None) -> dict[str, Any] | None:
    return dataclasses.asdict(usage) if usage else None


def evaluate_answer(
    item: GoldenItem, pipeline: SupportsAsk, judge: Judge, mode: SearchMode
) -> AnswerResult:
    base = AnswerResult(
        id=item.id, language=item.language, tags=item.tags, answerable=item.answerable
    )
    try:
        result = pipeline.ask(item.question, item.filters, mode=mode)
    except LLMError as exc:
        return base.model_copy(update={"error": str(exc), "answer_usage": _usage_dict(exc.usage)})

    answer = result.answer
    cited = [source.hit.source_key for source in answer.sources]
    update: dict[str, Any] = {
        "answer": answer.answer,
        "insufficient_context": answer.insufficient_context,
        "insufficient_reason": answer.insufficient_reason,
        "best_similarity": answer.best_similarity,
        "sources": [f"[{s.number}] {s.hit.source_key}" for s in answer.sources],
        "cited_expected": [key for key in item.expected_source_ids if key in cited],
        "answer_language": detect_query_language(answer.answer),
        "total_ms": result.total_ms,
        "attempts": answer.attempts,
        "answer_usage": _usage_dict(answer.usage),
    }
    if answer.insufficient_context:
        update["neutral"] = True  # eine Ablehnung wertet nicht (AK-7.1)
        return base.model_copy(update=update)
    try:
        verdict, judge_usage = judge.judge(item.question, answer.context, answer.answer)
    except LLMError as exc:
        update |= {"judge_error": str(exc), "judge_usage": _usage_dict(exc.usage)}
        return base.model_copy(update=update)
    update |= {
        "judge": verdict,
        "judge_usage": _usage_dict(judge_usage),
        "citation_accuracy": citation_accuracy(verdict),
        "faithfulness": faithfulness(verdict),
        "neutral": not verdict.contains_own_evaluation,
    }
    return base.model_copy(update=update)


def _rate(flags: Sequence[bool]) -> float | None:
    return sum(flags) / len(flags) if flags else None


def _cost(usage: dict[str, Any] | None) -> float | None:
    return 0.0 if usage is None else usage.get("cost_usd")


def summarize_answers(answers: Sequence[AnswerResult]) -> dict[str, float]:
    ok = [a for a in answers if a.ok]
    answered = [a for a in ok if not a.refused]
    values: dict[str, float | None] = {
        "citation_accuracy": _mean_of([a.citation_accuracy for a in answered]),
        "faithfulness": _mean_of([a.faithfulness for a in answered]),
        "refusal_rate": _rate([a.refused for a in ok if not a.answerable]),
        "false_refusal_rate": _rate(
            [a.refused for a in ok if a.answerable and "wertend" not in a.tags]
        ),
        "neutrality": _rate(
            [a.neutral for a in ok if "wertend" in a.tags and a.neutral is not None]
        ),
        "language_accuracy": _rate([a.language_ok for a in ok if a.language_ok is not None]),
    }
    durations = [a.total_ms for a in ok if a.total_ms is not None]
    if durations:
        values["answer_p50_ms"] = percentile(durations, 50)
        values["answer_p95_ms"] = percentile(durations, 95)
    answer_costs = [_cost(a.answer_usage) for a in ok]
    if answer_costs and None not in answer_costs:
        values["answer_cost_usd"] = mean([c for c in answer_costs if c is not None])
    judge_costs = [_cost(a.judge_usage) for a in answered if a.judge_usage is not None]
    if judge_costs and None not in judge_costs:
        values["judge_cost_usd"] = mean([c for c in judge_costs if c is not None])
    return {key: value for key, value in values.items() if value is not None}


def _mean_of(values: Sequence[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return mean(present) if present else None


def count_answers(answers: Sequence[AnswerResult]) -> dict[str, int]:
    return {
        "questions": len(answers),
        "answered": sum(a.ok and not a.refused for a in answers),
        "refused": sum(a.ok and a.refused for a in answers),
        "judged": sum(a.judge is not None for a in answers),
        "errors": sum(not a.ok for a in answers),
        "judge_errors": sum(a.judge_error is not None for a in answers),
    }


def evaluate_answers(
    items: Sequence[GoldenItem],
    pipeline: SupportsAsk,
    judge: Judge,
    mode: SearchMode,
    *,
    progress: Callable[[AnswerResult], None] | None = None,
) -> AnswerReport:
    """Nacheinander (Abo-Limits); auch unbeantwortbare Fragen (Ablehnungsquote)."""
    answers = []
    for item in items:
        result = evaluate_answer(item, pipeline, judge, mode)
        answers.append(result)
        if progress:
            progress(result)
    return AnswerReport(
        answers=answers, metrics=summarize_answers(answers), counts=count_answers(answers)
    )
