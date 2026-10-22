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
from baselines import PopularityRecommender, ItemKNNRecommender, HybridRecommender


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
    assert 20 not in model.recommend(3, k=1)


def test_hybrid_excludes_purchased():
    df = _tiny_train(with_purchase=True)
    df["time"] = pd.Timestamp("2015-06-01")
    pop = PopularityRecommender(pool=10).fit(df)
    knn = ItemKNNRecommender(min_item_users=2).fit(df)
    recs = HybridRecommender(knn, pop, alpha=0.5).recommend(3, k=5)
    assert 20 not in recs


def test_knn_recommend_matches_score_items_for_multiple_users():
    df = pd.DataFrame(
        [
            (1, 10, "view", 1), (1, 20, "view", 1),
            (2, 10, "view", 1), (2, 20, "view", 1), (2, 30, "view", 1),
            (3, 10, "view", 1), (3, 30, "view", 1), (3, 40, "view", 1),
            (4, 10, "view", 1), (4, 40, "view", 1), (4, 50, "view", 1),
        ],
        columns=["user_id", "item_id", "event", "weight"],
    )
    model = ItemKNNRecommender(min_item_users=1).fit(df)

    for user_id in (1, 2, 3, 4):
        scores = model.score_items(user_id)
        expected = sorted(scores, key=scores.get, reverse=True)[:3]
        assert model.recommend(user_id, k=3) == expected


def test_knn_score_items_and_recommend_exclude_purchased_items():
    model = ItemKNNRecommender(min_item_users=2).fit(_tiny_train(with_purchase=True))

    assert 20 not in model.score_items(3)
    assert 20 not in model.recommend(3, k=5)


def test_hybrid_alpha_one_matches_knn_recommend_without_popularity_overlap():
    df = _tiny_train(with_purchase=True)
    pop = PopularityRecommender(pool=1).fit(df)
    knn = ItemKNNRecommender(min_item_users=2, fallback=pop).fit(df)

    assert 20 not in knn.score_items(3)
    assert HybridRecommender(knn, pop, alpha=1.0).recommend(3, k=5) == (
        knn.recommend(3, k=5)
    )


def test_knn_fallback_fills_remaining_slots_and_counts_personalized_calls():
    df = _tiny_train(with_purchase=True)
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    (4, 60, "transaction", 5),
                    (5, 60, "transaction", 5),
                    (6, 60, "transaction", 5),
                ],
                columns=["user_id", "item_id", "event", "weight"],
            ),
        ],
        ignore_index=True,
    )
    pop = PopularityRecommender(pool=10).fit(df)
    knn = ItemKNNRecommender(min_item_users=2, fallback=pop).fit(df)

    recs = knn.recommend(3, k=2)

    assert recs == [10, 60]
    assert knn.n_total == 1
    assert knn.n_personalized == 1