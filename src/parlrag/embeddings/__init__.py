"""Embeddings: Interface und Implementierungen. Auswahl nur über `get_embedder()`."""

from parlrag.config import Settings
from parlrag.embeddings.base import Embedder, EmbeddingError, Vectors
from parlrag.embeddings.bge_m3 import BgeM3Embedder

__all__ = ["BgeM3Embedder", "Embedder", "EmbeddingError", "Vectors", "get_embedder"]


def get_embedder(settings: Settings) -> Embedder:
    """Die einzige Stelle, die die Implementierung wählt (später z. B. ein API-Modell)."""
    return BgeM3Embedder(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        max_seq_length=settings.embedding_max_seq_length,
    )
