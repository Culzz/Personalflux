"""Ranking metrics and ground-truth construction.

Protocol: for each user with train history who had a cart/purchase in the
evaluation window, relevant items = items they carted/bought in that window
(restricted to items present in the training catalog).
"""
import math
import pandas as pd

POSITIVE_EVENTS = {"addtocart", "transaction"}


def build_ground_truth(window, train, catalog=None, positive_events=POSITIVE_EVENTS):
    """Return {user_id: set(relevant item_ids)}."""
    pos = window[window["event"].isin(positive_events)]
    pos = pos[pos["user_id"].isin(set(train["user_id"]))]  # users with history
    if catalog is not None:
        pos = pos[pos["item_id"].isin(catalog)]           # recommendable items
    return pos.groupby("user_id")["item_id"].apply(set).to_dict()


def recall_at_k(recommended, relevant, k):
    if not relevant:
        return 0.0
    hits = len(set(recommended[:k]) & relevant)
    return hits / len(relevant)


def ndcg_at_k(recommended, relevant, k):
    dcg = sum(
        1.0 / math.log2(rank + 2)
        for rank, item in enumerate(recommended[:k])
        if item in relevant
    )
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(rank + 2) for rank in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def reciprocal_rank(recommended, relevant, k):
    for rank, item in enumerate(recommended[:k]):
        if item in relevant:
            return 1.0 / (rank + 1)
    return 0.0


def evaluate(recs, truth, k=10, catalog_size=None):
    """recs: {user_id: ranked list}; truth: {user_id: set}. Returns metric dict."""
    users = list(truth)
    n = len(users)
    result = {
        "users": n,
        f"recall@{k}": sum(recall_at_k(recs[u], truth[u], k) for u in users) / n,
        f"ndcg@{k}": sum(ndcg_at_k(recs[u], truth[u], k) for u in users) / n,
        f"mrr@{k}": sum(reciprocal_rank(recs[u], truth[u], k) for u in users) / n,
    }
    if catalog_size:
        unique_items = {item for u in users for item in recs[u][:k]}
        result[f"coverage@{k}"] = len(unique_items) / catalog_size
    return result