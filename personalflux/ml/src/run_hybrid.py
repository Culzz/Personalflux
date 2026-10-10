"""Sweep the blend weight alpha on the VALIDATION window."""
import pandas as pd
from preprocessing import PROCESSED
from baselines import PopularityRecommender, ItemKNNRecommender, HybridRecommender
from evaluate import build_ground_truth, evaluate

train = pd.read_parquet(PROCESSED / "train.parquet")
val = pd.read_parquet(PROCESSED / "val.parquet")

catalog = set(train["item_id"])
truth = build_ground_truth(val, train, catalog=catalog)
print(f"Eval users: {len(truth)}")

pop = PopularityRecommender(recent_days=14).fit(train)
knn = ItemKNNRecommender().fit(train)

rows = []
for alpha in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0):
    model = HybridRecommender(knn, pop, alpha=alpha)
    recs = {user: model.recommend(user, k=20) for user in truth}
    for k in (10, 20):
        m = evaluate(recs, truth, k=k, catalog_size=len(catalog))
        rows.append({
            "alpha": alpha, "k": k,
            "recall": m[f"recall@{k}"], "ndcg": m[f"ndcg@{k}"],
            "mrr": m[f"mrr@{k}"], "coverage": m[f"coverage@{k}"],
        })

print(pd.DataFrame(rows).round(4).to_string(index=False))
