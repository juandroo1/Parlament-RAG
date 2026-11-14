"""Retrieval-Metriken auf Dokumentebene (Task 3.2)."""

import pytest

from parlrag.evals.metrics import (
    dedupe_documents,
    mean,
    percentile,
    recall_at_k,
    reciprocal_rank,
)


def test_dedupe_keeps_first_occurrence_in_rank_order() -> None:
    chunks = ["transcript:1", "business:9", "transcript:1", "transcript:2", "business:9"]
    assert dedupe_documents(chunks) == ["transcript:1", "business:9", "transcript:2"]


@pytest.mark.parametrize(
    ("k", "expected_recall"),
    [(1, 0.0), (2, 0.5), (3, 0.5), (4, 1.0), (10, 1.0)],
)
def test_recall_at_k_counts_expected_documents_in_top_k(k: int, expected_recall: float) -> None:
    ranked = ["transcript:7", "transcript:1", "business:3", "business:9"]
    assert recall_at_k(ranked, ["transcript:1", "business:9"], k) == expected_recall


def test_recall_without_expected_documents_is_an_error() -> None:
    with pytest.raises(ValueError):
        recall_at_k(["transcript:1"], [], 10)


def test_reciprocal_rank_uses_first_expected_document() -> None:
    ranked = ["transcript:7", "transcript:8", "business:3", "transcript:1"]
    assert reciprocal_rank(ranked, {"transcript:1", "business:3"}) == pytest.approx(1 / 3)
    assert reciprocal_rank(ranked, {"transcript:7"}) == 1.0


def test_reciprocal_rank_is_zero_beyond_k() -> None:
    ranked = [f"transcript:{n}" for n in range(1, 21)]
    assert reciprocal_rank(ranked, {"transcript:11"}, k=10) == 0.0
    assert reciprocal_rank(ranked, {"transcript:11"}, k=20) == pytest.approx(1 / 11)
    assert reciprocal_rank([], {"transcript:1"}) == 0.0


def test_percentile_nearest_rank() -> None:
    values = [float(n) for n in range(1, 21)]  # 1 … 20
    assert percentile(values, 50) == 10.0
    assert percentile(values, 95) == 19.0
    assert percentile(values, 100) == 20.0
    assert percentile([5.0], 95) == 5.0
    with pytest.raises(ValueError):
        percentile([], 50)


def test_mean() -> None:
    assert mean([1.0, 0.0, 0.5]) == 0.5
    with pytest.raises(ValueError):
        mean([])
