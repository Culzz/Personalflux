"""Do ItemKNN.recommend and Hybrid(alpha=1.0) agree? They should."""
import pandas as pd
from preprocessing import PROCESSED
from baselines import PopularityRecommender, ItemKNNRecommender, HybridRecommender
from evaluate import build_ground_truth, evaluate

train = pd.read_parquet(PROCESSED / "train.parquet")
val = pd.read_parquet(PROCESSED / "val.parquet")
catalog = set(train["item_id"])
truth = build_ground_truth(val, train, catalog=catalog)

pop = PopularityRecommender(recent_days=14).fit(train)
knn = ItemKNNRecommender().fit(train)
hyb = HybridRecommender(knn, pop, alpha=1.0)

same, diff = 0, []
for u in truth:
    if knn.recommend(u, k=10) == hyb.recommend(u, k=10):
        same += 1
    else:
        diff.append(u)
print(f"identical top-10 lists: {same}/{len(truth)}")

for u in diff[:3]:
    print("\nuser", u)
    print(" knn   :", knn.recommend(u, k=10))
    print(" hybrid:", hyb.recommend(u, k=10))
    print(" truth :", truth[u])

recs = {u: knn.recommend(u, k=10) for u in truth}
print("\nknn alone:", evaluate(recs, truth, k=10, catalog_size=len(catalog)))