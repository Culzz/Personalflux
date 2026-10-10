"""Bootstrap: resample users to see if metric differences are stable."""
import numpy as np
import pandas as pd
from preprocessing import PROCESSED
from baselines import PopularityRecommender, ItemKNNRecommender, HybridRecommender
from evaluate import build_ground_truth, recall_at_k

train = pd.read_parquet(PROCESSED / "train.parquet")
val = pd.read_parquet(PROCESSED / "val.parquet")
truth = build_ground_truth(val, train, catalog=set(train["item_id"]))
users = list(truth)

pop = PopularityRecommender(recent_days=14).fit(train)
knn = ItemKNNRecommender().fit(train)


def per_user_recall(alpha):
    model = HybridRecommender(knn, pop, alpha=alpha)
    return np.array(
        [recall_at_k(model.recommend(u, k=10), truth[u], 10) for u in users]
    )


r = {a: per_user_recall(a) for a in (0.0, 0.4, 0.5, 0.6, 1.0)}

rng = np.random.default_rng(42)
idx = rng.integers(0, len(users), size=(2000, len(users)))  # 2000 resamples


def compare(a, b):
    diff = r[a][idx].mean(axis=1) - r[b][idx].mean(axis=1)
    lo, hi = np.percentile(diff, [2.5, 97.5])
    verdict = "clear difference" if lo > 0 or hi < 0 else "NOT distinguishable"
    print(f"Recall@10 alpha={a} minus alpha={b}: "
          f"{r[a].mean() - r[b].mean():+.4f}  "
          f"95% CI [{lo:+.4f}, {hi:+.4f}]  -> {verdict}")


compare(1.0, 0.0)   # personal vs popularity-only
compare(0.5, 1.0)   # hybrid vs pure personal
compare(0.5, 0.0)   # hybrid vs popularity-only
