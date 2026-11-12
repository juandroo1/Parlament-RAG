"""Reciprocal Rank Fusion (plan.md, Abschnitt 6): score = Σ 1 / (k + Rang), Rang ab 1."""

from collections.abc import Hashable, Sequence


def reciprocal_rank_fusion[T: Hashable](
    rankings: Sequence[Sequence[T]], *, k: int = 60, top_n: int | None = None
) -> list[tuple[T, float]]:
    """Fusioniert Ranglisten; bei gleichem Score entscheidet der beste Einzelrang, dann die
    Reihenfolge des ersten Auftretens (deterministisch)."""
    scores: dict[T, float] = {}
    best_rank: dict[T, int] = {}
    first_seen: dict[T, int] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
            best_rank[item] = min(best_rank.get(item, rank), rank)
            first_seen.setdefault(item, len(first_seen))
    ordered = sorted(scores, key=lambda item: (-scores[item], best_rank[item], first_seen[item]))
    if top_n is not None:
        ordered = ordered[:top_n]
    return [(item, scores[item]) for item in ordered]
