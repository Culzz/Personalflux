"""Compare ItemKNN ranking steps on the validation window."""
import numpy as np
import pandas as pd
from preprocessing import PROCESSED
from baselines import PopularityRecommender, ItemKNNRecommender
from evaluate import build_ground_truth


train = pd.read_parquet(PROCESSED / "train.parquet")
val = pd.read_parquet(PROCESSED / "val.parquet")
catalog = set(train["item_id"])
truth = build_ground_truth(val, train, catalog=catalog)

pop = PopularityRecommender(recent_days=14).fit(train)
knn = ItemKNNRecommender().fit(train)


def old_recommend_path(user_id, k=10):
    """Reproduce the pre-fix candidate filter for comparison."""
    row = knn.user_index.get(user_id)
    if row is None:
        return [], [], None, None
    user_history = knn.Q[row]
    scores = (user_history @ knn.S).tocoo()
    order = np.argsort(-scores.data)
    seen = set(knn.items[user_history.indices])
    candidates = [
        knn.items[scores.col[idx]]
        for idx in order
        if knn.items[scores.col[idx]] not in seen
    ]
    return candidates[:k], candidates, scores, (order, seen)


differences = []
for user_id in truth:
    score_map = knn.score_items(user_id)
    personal_top = list(score_map)[:10]
    old_top, _, _, _ = old_recommend_path(user_id)
    if personal_top != old_top:
        differences.append(user_id)
    if len(differences) == 5:
        break

if not differences:
    print("No users differ between the score ranking and reproduced old path.")

for user_id in differences:
    row = knn.user_index[user_id]
    user_history = knn.Q[row]
    sparse_scores = (user_history @ knn.S).tocoo()
    dense_scores = np.asarray((user_history @ knn.S).toarray()).ravel()
    dense_order = np.argsort(-dense_scores, kind="stable")
    bought = knn.bought.get(user_id, set())
    seen = set(knn.items[user_history.indices])
    score_map = knn.score_items(user_id)
    old_top, old_candidates, sparse_scores, state = old_recommend_path(user_id)
    sparse_order, _ = state
    sparse_top = [
        (knn.items[sparse_scores.col[idx]], float(sparse_scores.data[idx]))
        for idx in sparse_order[:15]
    ]
    dense_top = [
        (knn.items[idx], float(dense_scores[idx]))
        for idx in dense_order
        if dense_scores[idx] > 0
    ][:15]
    reference = [
        knn.items[idx]
        for idx in dense_order
        if dense_scores[idx] > 0 and knn.items[idx] not in bought
    ][:10]

    print(f"\nUser {user_id}")
    print("Q[row] item history:", list(zip(knn.items[user_history.indices],
                                          user_history.data.tolist())))
    print("Sparse Q[row] @ S top 15 (item, raw score):", sparse_top)
    print("Dense reference top 15 (item, raw score):", dense_top)
    print("Purchased exclusion:", sorted(bought))
    print("Old recommend() history exclusion:", sorted(seen))
    print("Dense reference after purchased exclusion:", reference)
    print("score_items() top 10:", list(score_map)[:10])
    print("score_items matches dense reference:",
          list(score_map)[:10] == reference)
    print("Reproduced old recommend() personal top 10:", old_top)
    print("Current recommend() top 10:", knn.recommend(user_id, k=10))
    print("Popularity fallback top 10:", pop.recommend(user_id, k=10))
    print("First old-path candidates skipped but retained by reference:",
          [item for item in reference if item in seen][:10])
