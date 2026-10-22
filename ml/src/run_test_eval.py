"""FINAL evaluation on the TEST window. Pre-declared protocol; run ONCE.
Models are fit on train + validation. Nothing here is tuned."""
import sys
import numpy as np
import pandas as pd
import scipy.sparse as sp
from preprocessing import PROCESSED, ROOT
from baselines import PopularityRecommender, ItemKNNRecommender
from sessions import add_session_ids, build_session_examples
from features import category_distribution, shift_score
from adaptive import long_term_weight, blend
from evaluate import evaluate, recall_at_k

REPORTS = ROOT / "reports"
OUT = REPORTS / "test_eval.csv"
if OUT.exists():
    sys.exit(f"{OUT} already exists: the test set has been used. Not rerunning.")

BETA = 0.5
MIN_EVENTS, FULL_EVIDENCE = 2, 4
K_LIST = (10, 20)

train = pd.read_parquet(PROCESSED / "train.parquet")
val = pd.read_parquet(PROCESSED / "val.parquet")
test = pd.read_parquet(PROCESSED / "test.parquet")
meta = pd.read_parquet(PROCESSED / "item_meta.parquet")
root_map = meta["root_category_id"].to_dict()

fit_df = pd.concat([train, val], ignore_index=True)
catalog = set(fit_df["item_id"])
fit_users = set(fit_df["user_id"])

pop = PopularityRecommender(recent_days=14).fit(fit_df)
knn = ItemKNNRecommender().fit(fit_df)
item_pos = {item: i for i, item in enumerate(knn.items)}

# ---- test session examples ----
examples = []
for ex in build_session_examples(add_session_ids(test), min_context=2):
    ctx = [i for i in ex["context"] if i in catalog]
    target_all = {i for i in ex["target"] if i in catalog}
    if ctx and target_all:
        examples.append({**ex, "context": ctx, "target_all": target_all,
                         "target_new": target_all - set(ctx)})
new_ex = [e for e in examples if e["target_new"]]
hist_ex = [e for e in new_ex if e["user_id"] in fit_users]
print(f"test sessions: ALL {len(examples)} | NEW {len(new_ex)} | "
      f"NEW with history {len(hist_ex)} from {len({e['user_id'] for e in hist_ex})} visitors")

# ---- long-term category mix (history visitors) ----
need = {e["user_id"] for e in hist_ex}
sub = fit_df[fit_df["user_id"].isin(need)].copy()
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
    ranked = [i for i in sorted(scores, key=scores.get, reverse=True)
              if i not in exclude][:k]
    for i in pop.ranked:                      # popularity only pads short lists
        if len(ranked) >= k:
            break
        if i not in exclude and i not in ranked:
            ranked.append(i)
    return ranked


cache = {}


def signals(ex):
    sid = ex["session_id"]
    if sid not in cache:
        ctx = ex["context"]
        ses_d = category_distribution([root_map.get(i, np.nan) for i in ctx])
        sh = shift_score(long_dist.get(ex["user_id"], {}), ses_d, len(ctx),
                         MIN_EVENTS, FULL_EVIDENCE)
        cache[sid] = (knn_scores(ctx), knn.score_items(ex["user_id"]), sh)
    return cache[sid]


def m_pop(ex, exclude):
    return [i for i in pop.ranked if i not in exclude][:20]


def m_recent(ex, exclude):
    return [i for i in reversed(ex["context"]) if i not in exclude][:20]


def m_sknn(ex, exclude):
    return final_rank(signals(ex)[0], exclude)


def m_long(ex, exclude):
    return final_rank(signals(ex)[1], exclude)


def make_blend(adaptive):
    def fn(ex, exclude):
        s, l, sh = signals(ex)
        return final_rank(blend(s, l, long_term_weight(BETA, sh, adaptive)), exclude)
    return fn


def run(set_name, exs, models, variant, pairs):
    truth, recs = {}, {m: {} for m in models}
    for n, ex in enumerate(exs):
        exclude = set(ex["context"]) if variant == "NEW" else set()
        truth[n] = ex["target_new"] if variant == "NEW" else ex["target_all"]
        for name, fn in models.items():
            recs[name][n] = fn(ex, exclude)

    rows = []
    for name in models:
        for k in K_LIST:
            m = evaluate(recs[name], truth, k=k, catalog_size=len(catalog))
            rows.append({"set": set_name, "model": name, "k": k,
                         "sessions": m["users"], "recall": m[f"recall@{k}"],
                         "ndcg": m[f"ndcg@{k}"], "mrr": m[f"mrr@{k}"],
                         "coverage": m[f"coverage@{k}"]})

    per = {n: np.array([recall_at_k(recs[n][i], truth[i], 10) for i in range(len(exs))])
           for n in models}
    users = np.array([ex["user_id"] for ex in exs])
    uniq = np.unique(users)
    by_user = {u: np.where(users == u)[0] for u in uniq}
    rng = np.random.default_rng(42)
    draws = [np.concatenate([by_user[u] for u in rng.choice(uniq, len(uniq))])
             for _ in range(2000)]

    print(f"\n=== {set_name} ===")
    print(pd.DataFrame(rows).drop(columns="set").round(4).to_string(index=False))
    for a, b in pairs:
        d = np.array([per[a][x].mean() - per[b][x].mean() for x in draws])
        lo, hi = np.percentile(d, [2.5, 97.5])
        verdict = "clear" if lo > 0 or hi < 0 else "NOT distinguishable"
        print(f"Recall@10 {a} minus {b}: {per[a].mean() - per[b].mean():+.4f} "
              f"CI [{lo:+.4f}, {hi:+.4f}] -> {verdict}")
    return rows


rows = []
rows += run("NEW_all_visitors", new_ex,
            {"popularity_14d": m_pop, "session_knn": m_sknn}, "NEW",
            [("session_knn", "popularity_14d")])
rows += run("NEW_with_history", hist_ex,
            {"popularity_14d": m_pop, "session_knn": m_sknn,
             "fixed_b0.5": make_blend(False), "adaptive_b0.5": make_blend(True),
             "long_term_only": m_long}, "NEW",
            [("session_knn", "popularity_14d"), ("fixed_b0.5", "session_knn"),
             ("adaptive_b0.5", "session_knn"), ("adaptive_b0.5", "fixed_b0.5")])
rows += run("ALL_targets_reference", examples,
            {"popularity_14d": m_pop, "recently_viewed": m_recent,
             "session_knn": m_sknn}, "ALL",
            [("session_knn", "popularity_14d")])

REPORTS.mkdir(exist_ok=True)
pd.DataFrame(rows).to_csv(OUT, index=False)
print("\nSaved", OUT, "(delete it only if you knowingly want to rerun)")