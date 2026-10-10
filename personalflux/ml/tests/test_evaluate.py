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


import pandas as pd
from baselines import ItemKNNRecommender


def _tiny_train(with_purchase=False):
    rows = [
        (1, 10, "view", 1), (1, 20, "view", 1),
        (2, 10, "view", 1), (2, 20, "view", 1),
        (3, 10, "view", 1),
    ]
    if with_purchase:
        rows.append((3, 20, "transaction", 5))
    return pd.DataFrame(rows, columns=["user_id", "item_id", "event", "weight"])


def test_knn_recommends_co_occurring_item():
    model = ItemKNNRecommender(min_item_users=2).fit(_tiny_train())
    assert model.recommend(3, k=1) == [20]


def test_knn_excludes_purchased_items():
    model = ItemKNNRecommender(min_item_users=2).fit(_tiny_train(with_purchase=True))
    assert model.recommend(3, k=1) == []