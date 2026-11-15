"""Reranker für die Suchtreffer (plan.md, Abschnitt 6, Schritt 4; Experiment Task 6.1a).

Ein Cross-Encoder (Standard: BAAI/bge-reranker-v2-m3, lokal auf der CPU) bewertet Frage und
Abschnitt gemeinsam und sortiert die besten Treffer der Vektorsuche neu. Das Modell wird erst
beim ersten Aufruf geladen; mit `RETRIEVAL_RERANK=false` (Standard) entsteht kein Reranker.
"""

from collections.abc import Callable, Sequence
from typing import Any, Protocol

from parlrag.config import Settings


class Reranker(Protocol):
    @property
    def model_name(self) -> str: ...

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        """Relevanz je Abschnitt, höher ist besser (Reihenfolge wie `passages`)."""
        ...


def load_cross_encoder(model_name: str, device: str, max_length: int) -> Any:
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, device=device, max_length=max_length)


class CrossEncoderReranker:
    def __init__(
        self,
        model_name: str,
        *,
        device: str = "cpu",
        max_length: int = 512,
        batch_size: int = 16,
        loader: Callable[[str, str, int], Any] = load_cross_encoder,
    ) -> None:
        self._model_name = model_name
        self.device = device
        self.max_length = max_length
        self.batch_size = batch_size
        self.loader = loader
        self._model: Any = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_loaded(self) -> bool:
        return self._model is not None

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        if not passages:
            return []
        if self._model is None:
            self._model = self.loader(self._model_name, self.device, self.max_length)
        scores = self._model.predict(
            [(query, passage) for passage in passages],
            batch_size=self.batch_size,
            show_progress_bar=False,
        )
        return [float(score) for score in scores]


def get_reranker(settings: Settings) -> Reranker | None:
    """Reranker gemäss `RETRIEVAL_RERANK` und `RERANKER_MODEL`; None, wenn ausgeschaltet."""
    if not settings.retrieval_rerank:
        return None
    return CrossEncoderReranker(settings.reranker_model, device=settings.embedding_device)
