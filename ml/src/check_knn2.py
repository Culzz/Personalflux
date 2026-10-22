"""Is the bug in score_items, or in the hybrid blending?"""
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

# Test 1: rank using score_items ONLY (no popularity at all)
recs_scores = {}
short = 0
for u in truth:
    s = knn.score_items(u)
    if len(s) < 10:
        short += 1
    recs_scores[u] = sorted(s, key=s.get, reverse=True)[:10]
m = evaluate(recs_scores, truth, k=10, catalog_size=len(catalog))
print("score_items only :", {k: round(v, 4) for k, v in m.items()})
print("users with <10 personal candidates:", short, "/", len(truth))

# Test 2: how many hybrid slots come from items with ZERO personal score?
zero_slots, total_slots = 0, 0
for u in truth:
    personal = knn.score_items(u)
    for item in hyb.recommend(u, k=10):
        total_slots += 1
        if item not in personal:
            zero_slots += 1
print(f"hybrid slots filled by non-personal items: {zero_slots}/{total_slots}")

# Test 3: look at one differing user in detail
u = 24840
personal = knn.score_items(u)
print("\nuser", u, "- top personal scores:")
for item, s in list(personal.items())[:8]:
    print("  ", item, round(s, 4))
print("hybrid top 10:", [int(i) for i in hyb.recommend(u, k=10)])
print("knn.recommend :", [int(i) for i in knn.recommend(u, k=10)])