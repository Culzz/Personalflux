import pytest
from evaluate import recall_at_k, ndcg_at_k, reciprocal_rank


def test_recall():
    assert recall_at_k([1, 2, 3], {2, 9}, k=3) == 0.5


def test_perfect_ndcg():
    assert ndcg_at_k([1, 2], {1, 2}, k=2) == pytest.approx(1.0)


def test_ndcg_prefers_earlier_hit():
    early = ndcg_at_k([1, 5, 6], {1}, k=3)
    late = ndcg_at_k([5, 6, 1], {1}, k=3)
    assert early > late


def test_reciprocal_rank():
    assert reciprocal_rank([7, 8, 9], {9}, k=3) == pytest.approx(1 / 3)
    assert reciprocal_rank([7, 8, 9], {1}, k=3) == 0.0