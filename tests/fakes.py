"""Nachgebauter Embedder für Tests: deterministisch, ohne Modell-Download."""

import hashlib
from collections.abc import Sequence

import numpy as np

from parlrag.embeddings import EmbeddingError, Vectors
from parlrag.index.chunker import approximate_token_count


class FakeEmbedder:
    """Vektoren aus dem Text-Hash: gleicher Text, gleicher Vektor; verschiedene Texte sind
    praktisch orthogonal. Merkt sich alle eingebetteten Texte und die Anzahl Aufrufe."""

    model_name = "fake/model"
    dimensions = 1024

    def __init__(self, fail_after: int | None = None) -> None:
        self.texts: list[str] = []
        self.calls = 0
        self.fail_after = fail_after

    def embed_documents(self, texts: Sequence[str]) -> Vectors:
        self.calls += 1
        if self.fail_after is not None and self.calls > self.fail_after:
            raise EmbeddingError("simulierter Fehler")
        self.texts.extend(texts)
        vectors = np.empty((len(texts), self.dimensions), dtype=np.float32)
        for row, value in enumerate(texts):
            seed = int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big")
            vector = np.random.default_rng(seed).normal(size=self.dimensions)
            vectors[row] = vector / np.linalg.norm(vector)
        return vectors

    def embed_query(self, text: str) -> Vectors:
        vector: Vectors = self.embed_documents([text])[0]
        return vector

    def count_tokens(self, text: str) -> int:
        return approximate_token_count(text)
