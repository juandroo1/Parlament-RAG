"""Retrieval: Volltext, Vektor, Reciprocal Rank Fusion und Filter (plan.md, Abschnitt 6)."""

from parlrag.retrieval.filters import SearchFilters
from parlrag.retrieval.retriever import (
    RetrievalConfig,
    Retriever,
    SearchHit,
    SearchMode,
    SupportsSearch,
    best_similarity,
)

__all__ = [
    "RetrievalConfig",
    "Retriever",
    "SearchFilters",
    "SearchHit",
    "SearchMode",
    "SupportsSearch",
    "best_similarity",
]
