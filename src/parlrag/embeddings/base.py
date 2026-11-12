"""Embedding-Interface. Alle Embedding-Aufrufe laufen über dieses Interface (CLAUDE.md)."""

from collections.abc import Sequence
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

Vectors = NDArray[np.float32]


class EmbeddingError(RuntimeError):
    """Das Modell lieferte keine verwertbaren Vektoren."""


class Embedder(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed_documents(self, texts: Sequence[str]) -> Vectors:
        """Normalisierte Vektoren, Form (len(texts), dimensions)."""
        ...

    def embed_query(self, text: str) -> Vectors:
        """Normalisierter Vektor einer Suchanfrage, Form (dimensions,)."""
        ...

    def count_tokens(self, text: str) -> int:
        """Anzahl Tokens ohne Spezialtokens, mit dem Tokenizer des Modells."""
        ...
