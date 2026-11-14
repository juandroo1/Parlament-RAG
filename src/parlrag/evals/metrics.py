"""Retrieval-Metriken auf Dokumentebene (plan.md, Abschnitt 9; spec.md, Abschnitt 6).

Treffer sind Chunks; gemessen wird auf Dokumenten im Format `<source_type>:<source_id>`.
Mehrere Chunks desselben Dokuments zählen einmal, am Rang ihres besten Chunks.
"""

import math
from collections.abc import Collection, Iterable, Sequence


def dedupe_documents(keys: Iterable[str]) -> list[str]:
    """Dokument-IDs in Rangfolge, jede nur beim ersten Vorkommen."""
    return list(dict.fromkeys(keys))


def recall_at_k(ranked: Sequence[str], expected: Collection[str], k: int) -> float:
    """Anteil der erwarteten Dokumente unter den Top k."""
    if not expected:
        raise ValueError("Recall ohne erwartete Dokumente ist nicht definiert")
    return len(set(ranked[:k]) & set(expected)) / len(set(expected))


def reciprocal_rank(ranked: Sequence[str], expected: Collection[str], k: int = 10) -> float:
    """1 / Rang des ersten erwarteten Dokuments in den Top k, sonst 0 (Mittel: MRR@k)."""
    for rank, key in enumerate(ranked[:k], start=1):
        if key in expected:
            return 1 / rank
    return 0.0


def percentile(values: Sequence[float], q: float) -> float:
    """Perzentil nach der Nearest-Rank-Methode (p95 = Wert, den 95 % nicht überschreiten)."""
    if not values:
        raise ValueError("Perzentil einer leeren Liste")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q / 100 * len(ordered)) - 1)]


def mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("Mittel einer leeren Liste")
    return sum(values) / len(values)
