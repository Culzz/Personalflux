"""Fit the serving model on train + validation and save it as a versioned artifact."""
import platform
import subprocess
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import scipy
import sklearn

from preprocessing import PROCESSED, ROOT, EVENT_WEIGHTS
from baselines import PopularityRecommender, ItemKNNRecommender
from artifact import ARTIFACTS, save_artifact, load_artifact

CONFIG = {
    "max_user_items": 50,
    "min_item_users": 3,
    "popularity_recent_days": 14,
    "popularity_pool": 500,
    "blend_beta": 0.5,
    "event_weights": EVENT_WEIGHTS,
}


def git_state():
    """Short commit hash, marked +dirty if there are uncommitted changes."""
    try:
        run = lambda *a: subprocess.run(
            ["git", *a], capture_output=True, text=True, cwd=ROOT, check=True
        ).stdout.strip()
        commit = run("rev-parse", "--short", "HEAD")
        return commit + ("+dirty" if run("status", "--porcelain") else "")
    except Exception:
        return "unknown"


train = pd.read_parquet(PROCESSED / "train.parquet")
val = pd.read_parquet(PROCESSED / "val.parquet")
fit_df = pd.concat([train, val], ignore_index=True)

print("fitting on", len(fit_df), "events ...")
pop = PopularityRecommender(
    recent_days=CONFIG["popularity_recent_days"], pool=CONFIG["popularity_pool"]
).fit(fit_df)
knn = ItemKNNRecommender(
    max_user_items=CONFIG["max_user_items"], min_item_users=CONFIG["min_item_users"]
).fit(fit_df)

version = "personaflux-v0.1-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
info = {
    "trained_on": "train+validation (the test window was not used)",
    "data_window": {"start": str(fit_df["time"].min()), "end": str(fit_df["time"].max())},
    "n_events": int(len(fit_df)),
    "n_items": int(len(knn.items)),
    "n_similarity_pairs": int(knn.S.nnz),
    "code_version": git_state(),
    "environment": {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "pandas": pd.__version__,
        "scikit-learn": sklearn.__version__,
    },
    "evaluation_report": "ml/reports/test_eval.csv",
    "status": "candidate",
    "limitations": [
        "Offline-evaluated only; no live-customer evidence.",
        "Items unseen in training have no similarity scores.",
        "Shift-aware weighting is not validated and is not used for serving.",
    ],
}

folder = save_artifact(
    version, knn.S, knn.items, pop.ranked, pop.score_map, CONFIG, info,
    extra_files={"item_meta.parquet": PROCESSED / "item_meta.parquet"},
)
size_mb = sum(p.stat().st_size for p in folder.glob("*")) / 1e6
print(f"saved {folder} ({size_mb:.1f} MB)")

# Reload with verification and run a smoke test
model = load_artifact(folder)
print("reload + checksum verification: OK")
top_item = int(model.ranked[0])
print("most popular item:", top_item)
print("5 most similar:", model.similar_items(top_item, k=5))
print("session recs for [top two popular items]:",
      model.recommend_for_session(model.ranked[:2], k=5))
print("cold session recs (unknown item):",
      model.recommend_for_session([-1], k=3))

with open(ARTIFACTS / "current_version.txt", "w") as f:
    f.write(version)
print("current version ->", version)