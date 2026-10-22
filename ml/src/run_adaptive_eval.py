"""Does the long-term profile (with shift-aware weighting) help session-based
discovery? VALIDATION window, train-fitted models only. No test split."""
import numpy as np
import pandas as pd
import scipy.sparse as sp
from preprocessing import PROCESSED
from baselines import PopularityRecommender, ItemKNNRecommender
from sessions import add_session_ids, build_session_examples
from features import category_distribution, shift_score
from adaptive import long_term_weight, blend
from evaluate import evaluate, recall_at_k

BETAS = (0.25, 0.5, 1.0)
MIN_EVENTS, FULL_EVIDENCE = 2, 4   # sessions are short
K_LIST = (10, 20)

train = pd.read_parquet(PROCESSED / "train.parquet")
val = pd.read_parquet(PROCESSED / "val.parquet")
meta = pd.read_parquet(PROCESSED / "item_meta.parquet")
root_map = meta["root_category_id"].to_dict()

catalog = set(train["item_id"])
train_users = set(train["user_id"])

pop = PopularityRecommender(recent_days=14).fit(train)
knn = ItemKNNRecommender().fit(train)
item_pos = {item: i for i, item in enumerate(knn.items)}

# ---- session examples: NEW targets, visitors WITH train history ----
examples = build_session_examples(add_session_ids(val), min_context=2)
kept = []
for ex in examples:
    ctx = [i for i in ex["context"] if i in catalog]
    target = {i for i in ex["target"] if i in catalog} - set(ctx)
    if ctx and target and ex["user_id"] in train_users:
        kept.append({**ex, "context": ctx, "new_target": target})
examples = kept
print(f"evaluation sessions (history + NEW target): {len(examples)} "
      f"from {len({e['user_id'] for e in examples})} visitors")

# ---- long-term category mix per visitor (train only) ----
needed = {ex["user_id"] for ex in examples}
sub = train[train["user_id"].isin(needed)].copy()
sub["cat"] = sub["item_id"].map(root_map)
hist = (sub.dropna(subset=["cat"]).groupby("user_id")
           .agg(cats=("cat", list), w=("weight", list)))
long_dist = {u: category_distribution(r["cats"], r["w"]) for u, r in hist.iterrows()}


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
    scores = {knn.items[s.col[j]]: float(s.data[j]) for j in order}
    if scores:
        top = max(scores.values())
        scores = {i: v / top for i, v in scores.items()}
    return scores


def final_rank(scores, exclude, k=20):
    """Rank by score; popularity only PADS lists that are too short."""
    ranked = [i for i in sorted(scores, key=scores.get, reverse=True)
              if i not in exclude][:k]
    if len(ranked) < k:
        for i in pop.ranked:
            if i not in exclude and i not in ranked:
                ranked.append(i)
                if len(ranked) == k:
                    break
    return ranked


# ---- precompute S, L and shift once per session ----
pre = []
for ex in examples:
    ctx = ex["context"]
    s = knn_scores(ctx)
    l = knn.score_items(ex["user_id"])
    ses_d = category_distribution([root_map.get(i, np.nan) for i in ctx])
    sh = shift_score(long_dist.get(ex["user_id"], {}), ses_d, len(ctx),
                     MIN_EVENTS, FULL_EVIDENCE)
    pre.append((ex, s, l, sh))

shifts = np.array([p[3] for p in pre])
print(f"sessions with shift > 0: {(shifts > 0).mean():.0%} | "
      f"mean shift: {shifts.mean():.3f} | max: {shifts.max():.3f}")
print(f"sessions with no long-term scores: {np.mean([not p[2] for p in pre]):.0%} | "
      f"no session-KNN scores: {np.mean([not p[1] for p in pre]):.0%}")

# ---- models ----
configs = {"session_knn": (0.0, False)}
for b in BETAS:
    configs[f"fixed_b{b}"] = (b, False)
    configs[f"adaptive_b{b}"] = (b, True)

truth = {n: ex["new_target"] for n, (ex, *_rest) in enumerate(pre)}
all_recs = {}
for name, (beta, adaptive) in configs.items():
    all_recs[name] = {
        n: final_rank(blend(s, l, long_term_weight(beta, sh, adaptive)),
                      set(ex["context"]))
        for n, (ex, s, l, sh) in enumerate(pre)
    }
all_recs["long_term_only"] = {
    n: final_rank(l, set(ex["context"])) for n, (ex, s, l, sh) in enumerate(pre)
}

rows = []
for name, recs in all_recs.items():
    for k in K_LIST:
        m = evaluate(recs, truth, k=k, catalog_size=len(catalog))
        rows.append({"model": name, "k": k, "sessions": m["users"],
                     "recall": m[f"recall@{k}"], "ndcg": m[f"ndcg@{k}"],
                     "mrr": m[f"mrr@{k}"], "coverage": m[f"coverage@{k}"]})
print("\n" + pd.DataFrame(rows).round(4).to_string(index=False))

# ---- bootstrap over VISITORS (their sessions are not independent) ----
per = {name: np.array([recall_at_k(recs[n], truth[n], 10) for n in range(len(pre))])
       for name, recs in all_recs.items()}
users = np.array([ex["user_id"] for ex, *_ in pre])
uniq = np.unique(users)
by_user = {u: np.where(users == u)[0] for u in uniq}
rng = np.random.default_rng(42)
draws = [np.concatenate([by_user[u] for u in rng.choice(uniq, len(uniq))])
         for _ in range(2000)]


def compare(a, b):
    diffs = np.array([per[a][d].mean() - per[b][d].mean() for d in draws])
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    verdict = "clear" if lo > 0 or hi < 0 else "NOT distinguishable"
    print(f"Recall@10 {a:>14} minus {b:<12} {per[a].mean() - per[b].mean():+.4f} "
          f"CI [{lo:+.4f}, {hi:+.4f}] -> {verdict}")


print("\nBootstrap (visitors resampled):")
for b in BETAS:
    compare(f"fixed_b{b}", "session_knn")
for b in BETAS:
    compare(f"adaptive_b{b}", "session_knn")
for b in BETAS:
    compare(f"adaptive_b{b}", f"fixed_b{b}")