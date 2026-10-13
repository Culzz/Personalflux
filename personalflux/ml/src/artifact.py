"""Save, load and verify a versioned model artifact."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy.sparse as sp

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
REQUIRED = ("similarity.npz", "items.npy", "popularity.json")


def sha256_of(path):
    """Fingerprint of a file. Any change to the file changes this value."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save_artifact(version, S, items, ranked, score_map, config, info,
                  extra_files=None, root=ARTIFACTS):
    """Write a new artifact folder. Refuses to overwrite an existing version."""
    folder = Path(root) / version
    if folder.exists():
        raise FileExistsError(f"{folder} already exists; versions are never overwritten")
    folder.mkdir(parents=True)

    sp.save_npz(folder / "similarity.npz", S.tocsr().astype(np.float32))
    np.save(folder / "items.npy", np.asarray(items, dtype=np.int64))
    with open(folder / "popularity.json", "w") as f:
        json.dump({
            "ranked": [int(i) for i in ranked],
            "score_map": {str(int(k)): float(v) for k, v in score_map.items()},
        }, f)
    for name, src in (extra_files or {}).items():
        shutil.copy2(src, folder / name)

    names = list(REQUIRED) + list((extra_files or {}).keys())
    metadata = {
        "version": version,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": config,
        **info,
        "files": {name: sha256_of(folder / name) for name in names},
    }
    with open(folder / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    return folder


class LoadedModel:
    """A verified artifact, ready to answer recommendation questions."""

    def __init__(self, folder, metadata, S, items, ranked, score_map):
        self.folder = folder
        self.metadata = metadata
        self.version = metadata["version"]
        self.S = S
        self.items = items
        self.pos = {int(item): i for i, item in enumerate(items)}
        self.ranked = ranked
        self.score_map = score_map

    def similar_items(self, item_id, k=10):
        """Items most similar to one item: [(item_id, score), ...]."""
        p = self.pos.get(int(item_id))
        if p is None:
            return []
        row = self.S[p].tocoo()
        order = np.argsort(-row.data, kind="stable")[:k]
        return [(int(self.items[row.col[j]]), float(row.data[j])) for j in order]

    def recommend_for_session(self, context, k=10, exclude=None, n_candidates=300):
        """Rank items for a session. Returns [(item_id, score, source), ...].

        source is "similarity" (from the session's items) or
        "popularity_fallback" (used only to pad a list that is too short).
        """
        exclude = set(int(i) for i in (exclude or [])) | set(int(i) for i in context)
        idx = [self.pos[int(i)] for i in context if int(i) in self.pos]
        out = []
        if idx:
            q = sp.csr_matrix(
                (np.ones(len(idx), dtype=np.float32), ([0] * len(idx), idx)),
                shape=(1, len(self.items)),
            )
            s = (q @ self.S).tocoo()
            order = np.argsort(-s.data, kind="stable")[:n_candidates]
            if len(order):
                top = float(s.data[order[0]])
                for j in order:
                    item = int(self.items[s.col[j]])
                    if item not in exclude:
                        out.append((item, float(s.data[j]) / top, "similarity"))
                        if len(out) == k:
                            break
        if len(out) < k:
            taken = {i for i, _, _ in out}
            for item in self.ranked:
                if item not in exclude and item not in taken:
                    out.append((item, self.score_map.get(str(item), 0.0),
                                "popularity_fallback"))
                    if len(out) == k:
                        break
        return out


def load_artifact(folder, verify=True):
    """Load an artifact. Raises ValueError if anything is missing or altered."""
    folder = Path(folder)
    meta_path = folder / "metadata.json"
    if not meta_path.exists():
        raise ValueError(f"{folder} has no metadata.json")
    with open(meta_path) as f:
        metadata = json.load(f)

    if verify:
        for name, expected in metadata["files"].items():
            path = folder / name
            if not path.exists():
                raise ValueError(f"missing file: {name}")
            if sha256_of(path) != expected:
                raise ValueError(f"checksum mismatch for {name}: artifact altered or corrupt")

    S = sp.load_npz(folder / "similarity.npz").tocsr()
    items = np.load(folder / "items.npy")
    with open(folder / "popularity.json") as f:
        pop = json.load(f)

    if S.shape != (len(items), len(items)):
        raise ValueError("similarity matrix shape does not match the item list")
    if not np.all(np.isfinite(S.data)):
        raise ValueError("similarity matrix contains NaN or infinite values")

    return LoadedModel(folder, metadata, S, items, pop["ranked"], pop["score_map"])