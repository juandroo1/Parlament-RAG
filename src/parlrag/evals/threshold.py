"""Kalibrierung der Schwelle für «keine ausreichende Grundlage» (Task 4.3, AK-3.2/3.3).

Grundlage ist die beste Cosine-Similarity pro Frage. Unter der Schwelle wird ohne LLM-Aufruf
abgelehnt: richtig bei unbeantwortbaren Fragen, falsch bei beantwortbaren.
"""

from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict

from parlrag.evals.dataset import GoldenItem

CANDIDATES = tuple(round(0.50 + step / 100, 2) for step in range(16))  # 0.50 bis 0.65


class ThresholdRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    threshold: float
    unanswerable_refused: int
    answerable_refused: int


class ThresholdReport(BaseModel):
    """Wirkung der Schwelle auf die gemessenen Fragen (ohne Fragen ohne Similarity)."""

    model_config = ConfigDict(frozen=True)

    threshold: float
    unanswerable: int
    answerable: int
    unanswerable_refused: int
    answerable_refused: int
    candidates: list[ThresholdRow]


def _row(
    threshold: float, items: Sequence[GoldenItem], similarities: Mapping[str, float]
) -> ThresholdRow:
    refused = [item for item in items if similarities[item.id] < threshold]
    return ThresholdRow(
        threshold=threshold,
        unanswerable_refused=sum(not item.answerable for item in refused),
        answerable_refused=sum(item.answerable for item in refused),
    )


def threshold_report(
    items: Sequence[GoldenItem],
    similarities: Mapping[str, float | None],
    threshold: float,
    candidates: Sequence[float] = CANDIDATES,
) -> ThresholdReport | None:
    """None, wenn keine Frage eine Similarity hat (z. B. Suchart `fulltext`)."""
    measured = {key: value for key, value in similarities.items() if value is not None}
    scoped = [item for item in items if item.id in measured]
    if not scoped:
        return None
    current = _row(threshold, scoped, measured)
    return ThresholdReport(
        threshold=threshold,
        unanswerable=sum(not item.answerable for item in scoped),
        answerable=sum(item.answerable for item in scoped),
        unanswerable_refused=current.unanswerable_refused,
        answerable_refused=current.answerable_refused,
        candidates=[_row(value, scoped, measured) for value in candidates],
    )


def threshold_summary(report: ThresholdReport) -> str:
    return (
        f"Schwelle {report.threshold:.2f}: fängt {report.unanswerable_refused} von "
        f"{report.unanswerable} unbeantwortbaren Fragen ohne LLM ab, weist "
        f"{report.answerable_refused} von {report.answerable} beantwortbaren fälschlich ab."
    )
