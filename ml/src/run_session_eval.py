"""Session-based evaluation on the VALIDATION window (train-fitted models)."""
import numpy as np
import pandas as pd
import scipy.sparse as sp
from preprocessing import PROCESSED
from baselines import PopularityRecommender, ItemKNNRecommender
from sessions import add_session_ids, build_session_examples
from evaluate import evaluate, recall_at_k

K_LIST = (10, 20)
ALPHA = 0.5

train = pd.read_parquet(PROCESSED / "train.parquet")
val = pd.read_parquet(PROCESSED / "val.parquet")
catalog = set(train["item_id"])

pop = PopularityRecommender(recent_days=14).fit(train)
knn = ItemKNNRecommender().fit(train)
item_pos = {item: i for i, item in enumerate(knn.items)}

examples = build_session_examples(add_session_ids(val), min_context=2)
for ex in examples:                       # keep only recommendable items
    ex["context"] = [i for i in ex["context"] if i in catalog]
    ex["target"] = {i for i in ex["target"] if i in catalog}
examples = [ex for ex in examples if ex["context"] and ex["target"]]
print(f"session examples: {len(examples)}")
print(f"mean context length: {np.mean([len(e['context']) for e in examples]):.1f}")


def knn_scores(ctx, n=300):
    idx = [item_pos[i] for i in ctx if i in item_pos]
    if not idx:
        return {}
    q = sp.csr_matrix(
        (np.ones(len(idx), dtype=np.float32), ([0] * len(idx), idx)),
        shape=(1, len(knn.items)),
    )
    s = (q @ knn.S).tocoo()
    order = np.argsort(-s.data, kind="stable")[:n]
    return {knn.items[s.col[j]]: float(s.data[j]) for j in order}


def rank(scores, exclude, k=20):
    ranked = sorted(scores, key=scores.get, reverse=True)
    return [i for i in ranked if i not in exclude][:k]


def m_popularity(ctx, exclude):
    return [i for i in pop.ranked if i not in exclude][:20]


def m_recent_views(ctx, exclude):
    return [i for i in reversed(ctx) if i not in exclude][:20]


def m_session_knn(ctx, exclude):
    return rank(knn_scores(ctx), exclude)


def m_session_hybrid(ctx, exclude):
    s = knn_scores(ctx)
    top = max(s.values()) if s else 1.0
    combined = {i: ALPHA * v / top for i, v in s.items()}
    for i, v in pop.score_map.items():
        combined[i] = combined.get(i, 0.0) + (1 - ALPHA) * v
    return rank(combined, exclude)


def run(models, variant):
    rows = []
    for name, fn in models.items():
        recs, truth = {}, {}
        for n, ex in enumerate(examples):
            ctx = ex["context"]
            if variant == "NEW":
                exclude, target = set(ctx), ex["target"] - set(ctx)
                if not target:
                    continue
            else:
                exclude, target = set(), ex["target"]
            truth[n] = target
            recs[n] = fn(ctx, exclude)
        for k in K_LIST:
            m = evaluate(recs, truth, k=k, catalog_size=len(catalog))
            rows.append({
                "variant": variant, "model": name, "k": k, "examples": m["users"],
                "recall": m[f"recall@{k}"], "ndcg": m[f"ndcg@{k}"],
                "mrr": m[f"mrr@{k}"], "coverage": m[f"coverage@{k}"],
            })
    return rows


all_models = {
    "popularity_14d": m_popularity,
    "recently_viewed": m_recent_views,
    "session_knn": m_session_knn,
    "session_hybrid": m_session_hybrid,
}
new_models = {k: v for k, v in all_models.items() if k != "recently_viewed"}

table = pd.DataFrame(run(all_models, "ALL") + run(new_models, "NEW"))
print(table.round(4).to_string(index=False))


# ---- significance check + history coverage ----
train_users = set(train["user_id"])
n_hist = sum(ex["user_id"] in train_users for ex in examples)
print(f"\nsessions whose visitor has train history: {n_hist}/{len(examples)}")

# per-example Recall@10 on the NEW variant
new_ex = [(ex, ex["target"] - set(ex["context"])) for ex in examples]
new_ex = [(ex, t) for ex, t in new_ex if t]
per = {}
for name, fn in new_models.items():
    per[name] = np.array([
        recall_at_k(fn(ex["context"], set(ex["context"])), t, 10)
        for ex, t in new_ex
    ])
users = np.array([ex["user_id"] for ex, _ in new_ex])

# resample USERS, not sessions: sessions of one visitor are not independent
uniq = np.unique(users)
by_user = {u: np.where(users == u)[0] for u in uniq}
rng = np.random.default_rng(42)
draws = []
for _ in range(2000):
    chosen = rng.choice(uniq, size=len(uniq), replace=True)
    draws.append(np.concatenate([by_user[u] for u in chosen]))


def compare(a, b):
    diffs = np.array([per[a][d].mean() - per[b][d].mean() for d in draws])
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    verdict = "clear difference" if lo > 0 or hi < 0 else "NOT distinguishable"
    print(f"NEW Recall@10 {a} minus {b}: {per[a].mean() - per[b].mean():+.4f} "
          f"95% CI [{lo:+.4f}, {hi:+.4f}] -> {verdict}")


compare("session_knn", "popularity_14d")
compare("session_hybrid", "popularity_14d")
compare("session_hybrid", "session_knn")