"""Reciprocal Rank Fusion (plan.md, Abschnitt 6)."""

import pytest

from parlrag.retrieval.fusion import reciprocal_rank_fusion


def test_scores_follow_the_formula() -> None:
    fused = dict(reciprocal_rank_fusion([["a", "b"], ["b", "c"]], k=60))
    assert fused["a"] == pytest.approx(1 / 61)
    assert fused["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert fused["c"] == pytest.approx(1 / 62)


def test_items_in_both_lists_rank_above_single_list_items() -> None:
    fused = [item for item, _ in reciprocal_rank_fusion([["a", "x", "b"], ["y", "b", "z"]], k=60)]
    assert fused[0] == "b"


def test_ties_are_broken_by_best_rank_then_first_appearance() -> None:
    # a (Rang 1, Liste 1) und y (Rang 1, Liste 2) haben denselben Score.
    fused = [item for item, _ in reciprocal_rank_fusion([["a", "b"], ["y", "z"]], k=60)]
    assert fused == ["a", "y", "b", "z"]


def test_top_n_and_empty_input() -> None:
    assert len(reciprocal_rank_fusion([list("abcdef")], top_n=3)) == 3
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []
