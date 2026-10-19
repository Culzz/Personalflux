"""Two-stage evaluation on the VALIDATION window.

End-to-end recall@10 says a model missed, not why. This run reports the
generator's candidate recall beside the ranking metrics, so a low number can be
read as retrieval (the item was never proposed) or as ordering (it was proposed
and ranked below k). The test window is left alone: run_test_eval.py owns it and
is meant to be run once.
"""
import numpy as np
import pandas as pd
import scipy.sparse as sp
from preprocessing import PROCESSED, ROOT
from baselines import PopularityRecommender, ItemKNNRecommender
from sessions import add_session_ids, build_session_examples
from evaluate import evaluate
from stage_eval import decompose, summarise

K = 10
N_CANDIDATES = 300
ALPHA = 0.5
REPORTS = ROOT / "reports"

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
print(f"validation sessions: {len(examples)}")


def knn_scores(ctx, n=N_CANDIDATES):
    """Ordered {item: score} over the session's items, top n only."""
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


def popularity_candidates(ex):
    return list(pop.ranked)


def session_candidates(ex):
    return list(knn_scores(ex["context"]))


def hybrid_candidates(ex):
    """What the served blend proposes: session similarity plus popularity."""
    s = knn_scores(ex["context"])
    top = max(s.values()) if s else 1.0
    combined = {i: ALPHA * v / top for i, v in s.items()}
    for i, v in pop.score_map.items():
        combined[i] = combined.get(i, 0.0) + (1 - ALPHA) * v
    return sorted(combined, key=combined.get, reverse=True)


def run(models):
    counters = {name: [] for name in models}
    proposed = {name: [] for name in models}
    recs = {name: {} for name in models}
    truth = {}

    for n, ex in enumerate(examples):
        exclude = set(ex["context"])           # NEW variant: what is already seen
        target = ex["target"] - exclude
        if not target:
            continue
        truth[n] = target
        for name, propose in models.items():
            candidates = propose(ex)
            ranked = [i for i in candidates if i not in exclude][:K]
            counters[name].append(decompose(candidates, ranked, target, K))
            proposed[name].append(len(candidates))
            recs[name][n] = ranked

    rows = []
    for name in models:
        s = summarise(counters[name], K)
        m = evaluate(recs[name], truth, k=K, catalog_size=len(catalog))
        # summarise() and evaluate() share no code, so agreeing on recall is a
        # real check that the decomposition lost nothing along the way.
        assert abs(s[f"recall@{K}"] - m[f"recall@{K}"]) < 1e-9, name
        rows.append({
            "window": "VAL", "variant": "NEW", "model": name,
            "candidates": round(float(np.mean(proposed[name])), 1), **s,
            f"ndcg@{K}": m[f"ndcg@{K}"], f"mrr@{K}": m[f"mrr@{K}"],
            f"coverage@{K}": m[f"coverage@{K}"],
        })
    return rows


table = pd.DataFrame(run({
    "popularity_14d": popularity_candidates,
    "session_knn": session_candidates,
    "session_hybrid": hybrid_candidates,
}))
print(table.round(4).to_string(index=False))

REPORTS.mkdir(exist_ok=True)
out = REPORTS / "stage_eval.csv"
table.to_csv(out, index=False)
print("\nSaved", out)
