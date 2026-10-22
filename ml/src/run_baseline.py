"""Evaluate popularity baselines on the VALIDATION window only.
(The test set stays untouched until final evaluation.)"""
import pandas as pd
from preprocessing import PROCESSED
from baselines import PopularityRecommender, ItemKNNRecommender
from evaluate import build_ground_truth, evaluate

train = pd.read_parquet(PROCESSED / "train.parquet")
val = pd.read_parquet(PROCESSED / "val.parquet")

catalog = set(train["item_id"])
truth = build_ground_truth(val, train, catalog=catalog)

# How many positives did the catalog filter drop?
raw_truth = build_ground_truth(val, train, catalog=None)
raw_n = sum(len(v) for v in raw_truth.values())
kept_n = sum(len(v) for v in truth.values())
print(f"Eval users: {len(truth)} (before catalog filter: {len(raw_truth)})")
print(f"Relevant items: {kept_n} kept of {raw_n} "
      f"({raw_n - kept_n} unseen-in-train items dropped)\n")

pop14 = PopularityRecommender(recent_days=14)
models = {
    "popularity_all_train": PopularityRecommender(),
    "popularity_last_14d": pop14,
    "item_knn": ItemKNNRecommender(fallback=pop14),
}

rows = []
for name, model in models.items():
    model.fit(train)
    for k in (10, 20):
        recs = {user: model.recommend(user, k=k) for user in truth}
        metrics = evaluate(recs, truth, k=k, catalog_size=len(catalog))
        rows.append({"model": name, "k": k, **metrics})

# rename k-specific columns so they line up in one table
table = pd.DataFrame(rows)
for metric in ("recall", "ndcg", "mrr", "coverage"):
    table[metric] = table.filter(like=f"{metric}@").bfill(axis=1).iloc[:, 0]
table = table[["model", "k", "users", "recall", "ndcg", "mrr", "coverage"]]
print(table.round(4).to_string(index=False))

knn = models["item_knn"]
print(f"\nitem_knn: personalised results for {knn.n_personalized}/{knn.n_total} "
      f"calls (the rest were popularity fallback)")