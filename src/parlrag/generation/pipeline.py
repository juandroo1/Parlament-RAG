"""Frage → Retrieval → Antwort mit Quellen (Task 4.4).

Dieselbe Pipeline nutzen `parlrag ask`, später `POST /ask` (Task 5.1) und die Antwort-Evals
(Task 4.5), wie es plan.md (Abschnitt 1) verlangt.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass

from parlrag.config import Settings
from parlrag.db.session import get_engine
from parlrag.embeddings import get_embedder
from parlrag.generation.answer import AnswerGenerator, GeneratedAnswer
from parlrag.llm import get_llm
from parlrag.retrieval import (
    RetrievalConfig,
    Retriever,
    SearchFilters,
    SearchHit,
    SearchMode,
    SupportsSearch,
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
        if (mode or self.default_mode) == "fulltext" or embedder is None:
            return None
        start = self.clock()
        embedder.embed_query("Modell laden")
        return (self.clock() - start) * 1000

    def ask(
        self, question: str, filters: SearchFilters | None = None, *, mode: SearchMode | None = None
    ) -> AskResult:
        filters = filters or SearchFilters()
        mode = mode or self.default_mode
        start = self.clock()
        hits = self.retriever.search(question, filters, mode=mode)
        retrieved = self.clock()
        answer = self.generator.generate(question, hits)
        done = self.clock()
        return AskResult(
            question=question,
            filters=filters,
            mode=mode,
            answer=answer,
            hits=hits,
            min_similarity=self.generator.min_similarity,
            retrieval_ms=(retrieved - start) * 1000,
            generation_ms=(done - retrieved) * 1000,
        )


def build_pipeline(settings: Settings | None = None) -> AskPipeline:
    """Aus den Einstellungen; das LLM zuerst, damit ein fehlender Key oder eine fehlende
    Claude-CLI gemeldet wird, bevor das Embedding-Modell lädt."""
    settings = settings or Settings()
    llm = get_llm(settings)
    retriever = Retriever(
        get_engine(), get_embedder(settings), RetrievalConfig.from_settings(settings)
    )
    generator = AnswerGenerator(
        llm,
        context_chunks=settings.answer_context_chunks,
        min_similarity=settings.answer_min_similarity,
    )
    return AskPipeline(retriever, generator, default_mode=settings.retrieval_mode)
