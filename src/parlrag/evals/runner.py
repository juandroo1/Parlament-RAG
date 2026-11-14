"""Eval-Runner für Retrieval-Metriken (Task 3.2, plan.md Abschnitt 9).

Nutzt denselben Retriever wie `parlrag search` und `POST /ask`. Gemessen werden nur
beantwortbare Fragen; unbeantwortbare haben keine erwarteten Quellen und zählen erst bei den
Antwort-Metriken (Task 4.5) mit.
"""

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, text

from parlrag.evals.dataset import GoldenItem
from parlrag.evals.metrics import (
    dedupe_documents,
    mean,
    percentile,
    recall_at_k,
    reciprocal_rank,
)
from parlrag.ingest.mapping import Language
from parlrag.retrieval import SearchFilters, SearchHit, SearchMode

Suite = Literal["smoke", "full"]

RECALL_K = (5, 10, 20)
MRR_K = 10
# Chunks pro Frage: Nach dem Deduplizieren auf Dokumente bleiben genug für Recall@20.
CHUNKS_PER_QUERY = 100
TOP_DOCUMENTS_SHOWN = 10

QUALITY_METRICS = (*(f"recall@{k}" for k in RECALL_K), f"mrr@{MRR_K}")
LATENCY_METRICS = ("search_p50_ms", "search_p95_ms")

# Teilsets für die Auswertung; leere Teilsets werden weggelassen.
SUBSETS: dict[str, Callable[[GoldenItem], bool]] = {
    "de": lambda item: item.language == "de",
    "fr": lambda item: item.language == "fr",
    "crosslingual": lambda item: item.has("crosslingual"),
    "filter": lambda item: item.has("filter"),
    "teilkorpus": lambda item: item.has("teilkorpus"),
    "wertend": lambda item: item.has("wertend"),
}


class SupportsSearch(Protocol):
    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        *,
        mode: SearchMode = "hybrid",
        top_n: int | None = None,
    ) -> list[SearchHit]: ...


class QuestionResult(BaseModel):
    """Ergebnis einer Frage; `ranks` ist der Dokument-Rang jeder erwarteten Quelle."""

    model_config = ConfigDict(frozen=True)

    id: str
    language: Language
    tags: tuple[str, ...]
    expected_source_ids: tuple[str, ...]
    ranks: dict[str, int | None]
    top_documents: tuple[str, ...]
    metrics: dict[str, float]
    search_ms: float


class SubsetResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    n: int
    metrics: dict[str, float]


@dataclass(frozen=True)
class RetrievalReport:
    questions: list[QuestionResult]
    skipped_unanswerable: int
    metrics: dict[str, float]
    subsets: dict[str, SubsetResult]


def select_suite(items: Sequence[GoldenItem], suite: Suite) -> list[GoldenItem]:
    """`smoke`: Fragen mit Tag `smoke`; `full`: alle Fragen."""
    return [item for item in items if suite == "full" or item.has("smoke")]


def evaluate_question(
    item: GoldenItem,
    retriever: SupportsSearch,
    mode: SearchMode,
    clock: Callable[[], float] = time.perf_counter,
) -> QuestionResult:
    start = clock()
    hits = retriever.search(item.question, item.filters, mode=mode, top_n=CHUNKS_PER_QUERY)
    search_ms = (clock() - start) * 1000
    ranked = dedupe_documents(hit.source_key for hit in hits)
    positions = {key: rank for rank, key in enumerate(ranked, start=1)}
    expected = item.expected_source_ids
    metrics = {f"recall@{k}": recall_at_k(ranked, expected, k) for k in RECALL_K}
    metrics[f"mrr@{MRR_K}"] = reciprocal_rank(ranked, expected, MRR_K)
    return QuestionResult(
        id=item.id,
        language=item.language,
        tags=item.tags,
        expected_source_ids=expected,
        ranks={key: positions.get(key) for key in expected},
        top_documents=tuple(ranked[:TOP_DOCUMENTS_SHOWN]),
        metrics=metrics,
        search_ms=search_ms,
    )


def summarize(results: Sequence[QuestionResult]) -> dict[str, float]:
    """Mittel der Qualitätsmetriken über die Fragen, dazu p50/p95 der Suchdauer."""
    summary = {name: mean([r.metrics[name] for r in results]) for name in QUALITY_METRICS}
    durations = [r.search_ms for r in results]
    summary["search_p50_ms"] = percentile(durations, 50)
    summary["search_p95_ms"] = percentile(durations, 95)
    return summary


def evaluate_retrieval(
    items: Sequence[GoldenItem],
    retriever: SupportsSearch,
    mode: SearchMode,
    *,
    clock: Callable[[], float] = time.perf_counter,
    progress: Callable[[QuestionResult], None] | None = None,
) -> RetrievalReport:
    answerable = [item for item in items if item.answerable]
    if not answerable:
        raise ValueError("Keine beantwortbaren Fragen in der Auswahl")
    results: list[QuestionResult] = []
    for item in answerable:
        result = evaluate_question(item, retriever, mode, clock)
        results.append(result)
        if progress:
            progress(result)
    by_id = {r.id: r for r in results}
    subsets = {}
    for name, belongs in SUBSETS.items():
        members = [by_id[item.id] for item in answerable if belongs(item)]
        if members:
            subsets[name] = SubsetResult(n=len(members), metrics=summarize(members))
    return RetrievalReport(
        questions=results,
        skipped_unanswerable=len(items) - len(answerable),
        metrics=summarize(results),
        subsets=subsets,
    )


def corpus_snapshot(engine: Engine) -> dict[str, Any]:
    """Stand des Korpus zum Lauf: Dokumente, Chunks und Index-Signaturen."""
    with engine.connect() as connection:
        documents = connection.scalar(text("SELECT count(*) FROM documents"))
        signatures = {
            str(signature): int(count)
            for signature, count in connection.execute(
                text("SELECT metadata ->> 'index', count(*) FROM chunks GROUP BY 1 ORDER BY 1")
            )
        }
    return {
        "documents": int(documents or 0),
        "chunks": sum(signatures.values()),
        "chunks_by_signature": signatures,
    }
