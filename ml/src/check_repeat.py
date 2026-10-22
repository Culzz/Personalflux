"""How many hits are items the user already touched in train?"""
import pandas as pd
from preprocessing import PROCESSED
from baselines import PopularityRecommender, ItemKNNRecommender
from evaluate import build_ground_truth, evaluate

train = pd.read_parquet(PROCESSED / "train.parquet")
val = pd.read_parquet(PROCESSED / "val.parquet")
catalog = set(train["item_id"])
truth = build_ground_truth(val, train, catalog=catalog)

touched = train.groupby("user_id")["item_id"].apply(set).to_dict()
total = sum(len(v) for v in truth.values())
repeat = sum(len(truth[u] & touched.get(u, set())) for u in truth)
print(f"relevant pairs that are repeat items: {repeat}/{total} ({repeat/total:.1%})")

pop = PopularityRecommender(recent_days=14).fit(train)
knn = ItemKNNRecommender().fit(train)

# NEW-ITEM-ONLY evaluation: truth minus items the user touched in train,
# and recommendations also filtered to items the user has not touched.
truth_new = {u: t - touched.get(u, set()) for u, t in truth.items()}
truth_new = {u: t for u, t in truth_new.items() if t}
print(f"users with at least one NEW relevant item: {len(truth_new)}")

for name, model in [("popularity_last_14d", pop), ("item_knn", knn)]:
    recs = {}
    for u in truth_new:
        seen = touched.get(u, set())
        recs[u] = [i for i in model.recommend(u, k=60) if i not in seen][:10]
    m = evaluate(recs, truth_new, k=10, catalog_size=len(catalog))
    print(name, {k: round(v, 4) for k, v in m.items()})
