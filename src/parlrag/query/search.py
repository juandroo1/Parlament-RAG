"""Suche mit Erkennung von Person und Zeitraum (Spec 003, plan.md Abschnitt 7).

`DetectingRetriever` umschliesst einen Retriever mit derselben Schnittstelle: So nutzen
`parlrag search`, `ask`, die API und die Retrieval-Evals dieselbe Erkennung.

1. Filter auflösen (`resolve`): gesetzte Filter haben Vorrang.
2. Zeitraum ganz ausserhalb der Daten: keine Suche, keine Treffer (AK-16.1).
3. Suchen mit den angewandten Filtern.
4. Rückfall (AK-17.4): War die Person nur erkannt und gibt es keine Treffer oder liegt die beste
   Similarity unter `min_similarity`, noch einmal ohne Personenfilter. Beim Zeitraum gibt es
   keinen Rückfall: Ein ausdrücklich genanntes Jahr wird nicht stillschweigend aufgehoben.
"""

import datetime as dt
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from parlrag.query.catalog import Catalog
from parlrag.query.resolve import Resolution, resolve
from parlrag.retrieval import SearchFilters, SearchHit, SearchMode, SupportsSearch
from parlrag.retrieval.retriever import best_similarity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchOutcome:
    hits: list[SearchHit]
    resolution: Resolution
    retried_without: tuple[str, ...] = field(default=())


class DetectingRetriever:
    def __init__(
        self,
        retriever: SupportsSearch,
        catalog: Callable[[], Catalog],
        *,
        min_similarity: float,
        enabled: bool = True,
        today: Callable[[], dt.date] = dt.date.today,
    ) -> None:
        self.retriever = retriever
        self.catalog = catalog
        self.min_similarity = min_similarity
        self.enabled = enabled
        self.today = today

    def __getattr__(self, name: str) -> Any:
        # embedder, reranker, config, engine des umschlossenen Retrievers (Warm-up, Evals).
        return getattr(self.retriever, name)

    def run(
        self,
        query: str,
        filters: SearchFilters | None = None,
        *,
        mode: SearchMode = "hybrid",
        top_n: int | None = None,
        detect: bool = True,
    ) -> SearchOutcome:
        resolution = resolve(
            query, filters, self.catalog(), self.today(), detection=self.enabled and detect
        )
        if resolution.out_of_range:
            return SearchOutcome(hits=[], resolution=resolution)
        hits = self.retriever.search(query, resolution.filters, mode=mode, top_n=top_n)
        if resolution.speaker_detected and self._too_weak(hits):
            without = resolution.filters.model_copy(update={"speaker": None})
            logger.info(
                "Erkannte Person %s ohne passende Voten; Suche ohne Personenfilter",
                resolution.filters.speaker,
            )
            retried = self.retriever.search(query, without, mode=mode, top_n=top_n)
            detected = tuple(key for key in resolution.detected if key != "speaker")
            return SearchOutcome(
                hits=retried,
                resolution=Resolution(
                    filters=without,
                    detected=detected,
                    speaker_candidates=resolution.speaker_candidates,
                    coverage=resolution.coverage,
                    out_of_range=False,
                ),
                retried_without=("speaker",),
            )
        return SearchOutcome(hits=hits, resolution=resolution)

    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        *,
        mode: SearchMode = "hybrid",
        top_n: int | None = None,
    ) -> list[SearchHit]:
        return self.run(query, filters, mode=mode, top_n=top_n).hits

    def _too_weak(self, hits: list[SearchHit]) -> bool:
        if not hits:
            return True
        best = best_similarity(hits)
        return best is not None and best < self.min_similarity
