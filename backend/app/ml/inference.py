"""Load and query a verified model artifact (the format written by ml/src/artifact.py).

The artifact holds only item-level data: no user ids, no interaction history.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import scipy.sparse as sp


def sha256_of(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_metadata(folder: Path) -> dict:
    meta_path = Path(folder) / "metadata.json"
    if not meta_path.exists():
        raise ValueError("artifact has no metadata.json")
    with open(meta_path) as f:
        return json.load(f)


def verify_checksums(folder: Path, metadata: dict) -> None:
    """Raises ValueError if any file is missing or has been altered."""
    for name, expected in metadata.get("files", {}).items():
        path = Path(folder) / name
        if not path.exists():
            raise ValueError(f"missing file: {name}")
        if sha256_of(path) != expected:
            raise ValueError(f"checksum mismatch for {name}")


class LoadedModel:
    """Item-to-item similarity model plus a popularity list."""

    def __init__(self, folder, metadata, S, items, ranked, score_map):
        self.folder = Path(folder)
        self.metadata = metadata
        self.version = metadata["version"]
        self.S = S
        self.items = items
        self.pos = {int(item): i for i, item in enumerate(items)}
        self.ranked = [int(i) for i in ranked]
        self.score_map = {int(k): float(v) for k, v in score_map.items()}

    def has_item(self, source_id: int) -> bool:
        return int(source_id) in self.pos

    def _scores(self, weights: dict[int, float], n: int) -> dict[int, float]:
        """Weighted sum of similarity rows, scaled so the best candidate is 1.0."""
        idx, vals = [], []
        for item, w in weights.items():
            p = self.pos.get(int(item))
            if p is not None and w > 0:
                idx.append(p)
                vals.append(w)
        if not idx:
            return {}
        q = sp.csr_matrix(
            (np.array(vals, dtype=np.float32), ([0] * len(idx), idx)),
            shape=(1, len(self.items)),
        )
        s = (q @ self.S).tocoo()
        if s.nnz == 0:
            return {}
        order = np.argsort(-s.data, kind="stable")[:n]
        top = float(s.data[order[0]])
        if top <= 0:
            return {}
        return {int(self.items[s.col[j]]): float(s.data[j]) / top for j in order}

    def score_session(self, item_ids: list[int], n: int = 300) -> dict[int, float]:
        """Scores from what was looked at in the current session."""
        return self._scores({int(i): 1.0 for i in item_ids}, n)

    def score_history(self, weighted: dict[int, float], n: int = 300) -> dict[int, float]:
        """Scores from older history, weighted by event strength."""
        return self._scores(weighted, n)

    def similar_items(self, item_id: int, k: int = 10) -> list[tuple[int, float]]:
        p = self.pos.get(int(item_id))
        if p is None:
            return []
        row = self.S[p].tocoo()
        order = np.argsort(-row.data, kind="stable")[:k]
        return [(int(self.items[row.col[j]]), float(row.data[j])) for j in order]

    def strongest_link(self, candidate: int, context: list[int]) -> int | None:
        """Which context item is the candidate most similar to? (for explanations)"""
        p = self.pos.get(int(candidate))
        if p is None:
            return None
        best, best_s = None, 0.0
        for c in context:
            cp = self.pos.get(int(c))
            if cp is None:
                continue
            s = float(self.S[cp, p])
            if s > best_s:
                best, best_s = int(c), s
        return best


def load_artifact(folder, verify: bool = True) -> LoadedModel:
    folder = Path(folder)
    metadata = read_metadata(folder)
    if verify:
        verify_checksums(folder, metadata)
    S = sp.load_npz(folder / "similarity.npz").tocsr()
    items = np.load(folder / "items.npy")
    with open(folder / "popularity.json") as f:
        pop = json.load(f)
    if S.shape != (len(items), len(items)):
        raise ValueError("similarity matrix shape does not match the item list")
    if not np.all(np.isfinite(S.data)):
        raise ValueError("similarity matrix contains NaN or infinite values")
    return LoadedModel(folder, metadata, S, items, pop["ranked"], pop["score_map"])
