"""Test helpers: build a tiny, valid model artifact on disk."""
import json
from pathlib import Path

import numpy as np
import scipy.sparse as sp

from app.ml.inference import sha256_of


def write_artifact(root, version, items, edges, ranked=None):
    """items: source item ids. edges: (item_a, item_b, similarity). Returns the folder."""
    folder = Path(root) / version
    folder.mkdir(parents=True)
    n = len(items)
    pos = {item: k for k, item in enumerate(items)}
    rows, cols, vals = [], [], []
    for a, b, v in edges:
        rows += [pos[a], pos[b]]
        cols += [pos[b], pos[a]]
        vals += [v, v]
    S = sp.csr_matrix((np.array(vals, dtype=np.float32), (rows, cols)), shape=(n, n))
    sp.save_npz(folder / "similarity.npz", S)
    np.save(folder / "items.npy", np.array(items, dtype=np.int64))
    ranked = list(ranked or items)
    score_map = {str(i): round(1 - k / len(ranked), 4) for k, i in enumerate(ranked)}
    with open(folder / "popularity.json", "w") as f:
        json.dump({"ranked": ranked, "score_map": score_map}, f)
    files = {name: sha256_of(folder / name)
             for name in ("similarity.npz", "items.npy", "popularity.json")}
    meta = {"version": version, "created_at_utc": "2026-01-01T00:00:00+00:00",
            "config": {}, "trained_on": "unit test", "n_items": n, "files": files}
    with open(folder / "metadata.json", "w") as f:
        json.dump(meta, f)
    return folder


ITEMS = [10, 20, 30, 40, 50]
EDGES = [(10, 20, 0.8), (10, 30, 0.4), (20, 30, 0.5), (30, 40, 0.6)]
