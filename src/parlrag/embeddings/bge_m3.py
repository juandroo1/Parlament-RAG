"""bge-m3 über sentence-transformers, CPU (plan.md, Abschnitt 2; Entscheidungsprotokoll, Task 2.2).

Modell und Tokenizer werden getrennt und erst bei Bedarf geladen. `torch`,
`sentence_transformers` und `transformers` werden erst dann importiert, damit CLI und
API schnell starten und `/health` nicht vom Modell abhängt.
"""

import threading
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np

from parlrag.db.models import EMBEDDING_DIMENSIONS
from parlrag.embeddings.base import EmbeddingError, Vectors

ModelLoader = Callable[[], Any]
TokenCounterLoader = Callable[[], Callable[[str], int]]


def load_sentence_transformer(model_name: str, device: str, max_seq_length: int) -> Any:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, device=device)
    model.max_seq_length = max_seq_length
    return model


def load_token_counter(model_name: str) -> Callable[[str], int]:
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.model_max_length = 10**9  # nur zählen; keine Warnung bei langen Dokumenten

    def count(text: str) -> int:
        return len(tokenizer(text, add_special_tokens=False)["input_ids"])

    return count


class BgeM3Embedder:
    """Lokales Embedding-Modell; standardmässig BAAI/bge-m3 mit 1024 Dimensionen."""

    def __init__(
        self,
        *,
        model_name: str = "BAAI/bge-m3",
        device: str = "cpu",
        batch_size: int = 16,
        max_seq_length: int = 1024,
        dimensions: int = EMBEDDING_DIMENSIONS,
        model_loader: ModelLoader | None = None,
        token_counter_loader: TokenCounterLoader | None = None,
    ) -> None:
        self._model_name = model_name
        self._dimensions = dimensions
        self.batch_size = batch_size
        self._model_loader = model_loader or (
            lambda: load_sentence_transformer(model_name, device, max_seq_length)
        )
        self._token_counter_loader = token_counter_loader or (
            lambda: load_token_counter(model_name)
        )
        self._model: Any = None
        self._token_counter: Callable[[str], int] | None = None
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_loaded(self) -> bool:
        return self._model is not None

    def _get_model(self) -> Any:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = self._model_loader()
        return self._model

    def _get_token_counter(self) -> Callable[[str], int]:
        if self._token_counter is None:
            with self._lock:
                if self._token_counter is None:
                    self._token_counter = self._token_counter_loader()
        return self._token_counter

    def embed_documents(self, texts: Sequence[str]) -> Vectors:
        if not texts:
            return np.empty((0, self._dimensions), dtype=np.float32)
        raw = self._get_model().encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        vectors = np.asarray(raw, dtype=np.float32)
        if vectors.shape != (len(texts), self._dimensions):
            raise EmbeddingError(
                f"{self._model_name} lieferte Form {vectors.shape}, "
                f"erwartet ({len(texts)}, {self._dimensions})"
            )
        return vectors

    def embed_query(self, text: str) -> Vectors:
        vector: Vectors = self.embed_documents([text])[0]
        return vector

    def count_tokens(self, text: str) -> int:
        return self._get_token_counter()(text)
