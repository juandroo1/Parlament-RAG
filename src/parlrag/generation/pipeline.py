"""Frage → Erkennung → Retrieval → Antwort mit Quellen (Task 4.4, Spec 003 Task 8.4).

Dieselbe Pipeline nutzen `parlrag ask`, `POST /ask` (Task 5.1) und die Antwort-Evals
(Task 4.5), wie es plan.md (Abschnitt 1) verlangt. Person und Zeitraum aus der Frage erkennt
der `DetectingRetriever` (Spec 003, plan.md Abschnitt 7); liegt der Zeitraum ausserhalb der
Daten, antwortet die Pipeline ohne Suche und ohne LLM (AK-16.1).
"""

import time
from collections.abc import Callable
from dataclasses import dataclass

from parlrag.config import Settings
from parlrag.db.session import get_engine
from parlrag.embeddings import get_embedder
from parlrag.generation.answer import AnswerGenerator, GeneratedAnswer
from parlrag.llm import get_llm
from parlrag.query.resolve import CatalogCache, Coverage, Resolution
from parlrag.query.search import DetectingRetriever, SearchOutcome
from parlrag.query.speakers import Speaker
from parlrag.retrieval import (
    RetrievalConfig,
    Retriever,
    SearchFilters,
    SearchHit,
    SearchMode,
    SupportsSearch,
    get_reranker,
)


@dataclass(frozen=True)
class AskResult:
    question: str
    filters: SearchFilters
    mode: SearchMode
    answer: GeneratedAnswer
    hits: list[SearchHit]
    min_similarity: float
    retrieval_ms: float
    generation_ms: float
    detected: tuple[str, ...] = ()  # erkannte Filter in `filters` (AK-17.5)
    speaker_candidates: tuple[Speaker, ...] = ()
    coverage: Coverage | None = None
    retried_without: tuple[str, ...] = ()

    @property
    def total_ms(self) -> float:
        return self.retrieval_ms + self.generation_ms


class AskPipeline:
    def __init__(
        self,
        retriever: SupportsSearch,
        generator: AnswerGenerator,
        *,
        default_mode: SearchMode = "vector",
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.retriever = retriever
        self.generator = generator
        self.default_mode = default_mode
        self.clock = clock

    def warm_up(self, mode: SearchMode | None = None) -> float | None:
        """Lädt das Embedding-Modell vorab (Dauer in ms), damit die gemessene Suchzeit den
        einmaligen Start nicht enthält; None ohne Vektorsuche."""
        embedder = getattr(self.retriever, "embedder", None)
        if (mode or self.default_mode) == "fulltext":
            embedder = None
        reranker = getattr(self.retriever, "reranker", None)
        if embedder is None and reranker is None:
            return None
        start = self.clock()
        if embedder is not None:
            embedder.embed_query("Modell laden")
        if reranker is not None:
            reranker.score("Modell laden", ["Modell laden"])
        return (self.clock() - start) * 1000

    def ask(
        self,
        question: str,
        filters: SearchFilters | None = None,
        *,
        mode: SearchMode | None = None,
        detect: bool = True,
    ) -> AskResult:
        filters = filters or SearchFilters()
        mode = mode or self.default_mode
        start = self.clock()
        if isinstance(self.retriever, DetectingRetriever):
            outcome = self.retriever.run(question, filters, mode=mode, detect=detect)
        else:
            hits = self.retriever.search(question, filters, mode=mode)
            outcome = SearchOutcome(hits=hits, resolution=Resolution(filters=filters))
        retrieved = self.clock()
        resolution = outcome.resolution
        if resolution.out_of_range and resolution.coverage is not None:
            coverage = resolution.coverage
            answer = self.generator.out_of_range(question, coverage.first, coverage.last)
        else:
            answer = self.generator.generate(question, outcome.hits)
        done = self.clock()
        return AskResult(
            question=question,
            filters=resolution.filters,
            mode=mode,
            answer=answer,
            hits=outcome.hits,
            min_similarity=self.generator.min_similarity,
            retrieval_ms=(retrieved - start) * 1000,
            generation_ms=(done - retrieved) * 1000,
            detected=resolution.detected,
            speaker_candidates=resolution.speaker_candidates,
            coverage=resolution.coverage,
            retried_without=outcome.retried_without,
        )


def build_pipeline(
    settings: Settings | None = None, *, retriever: SupportsSearch | None = None
) -> AskPipeline:
    """Aus den Einstellungen; das LLM zuerst, damit ein fehlender Key oder eine fehlende
    Claude-CLI gemeldet wird, bevor das Embedding-Modell lädt. Ein übergebener Retriever
    wird geteilt (Eval-Runner: das Embedding-Modell nur einmal laden)."""
    settings = settings or Settings()
    llm = get_llm(settings)
    if retriever is None:
        retriever = with_detection(
            Retriever(
                get_engine(),
                get_embedder(settings),
                RetrievalConfig.from_settings(settings),
                get_reranker(settings),
            ),
            settings,
        )
    generator = AnswerGenerator(
        llm,
        context_chunks=settings.answer_context_chunks,
        min_similarity=settings.answer_min_similarity,
    )
    return AskPipeline(retriever, generator, default_mode=settings.retrieval_mode)


def with_detection(retriever: Retriever, settings: Settings) -> DetectingRetriever:
    """Retriever mit Erkennung von Person und Zeitraum; der Katalog kommt aus derselben
    Datenbank und wird höchstens alle 10 Minuten neu geladen (plan.md, Abschnitt 3)."""
    return DetectingRetriever(
        retriever,
        CatalogCache(retriever.engine).get,
        min_similarity=settings.answer_min_similarity,
        enabled=settings.query_detection,
    )
