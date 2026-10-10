"""Baseline recommenders. Start with popularity."""
import numpy as np
import pandas as pd
import scipy.sparse as sp


class PopularityRecommender:
    """Rank items by weighted event count (view=1, cart=4, purchase=5).

    recent_days=None  -> use the whole training period
    recent_days=14    -> use only the last 14 days of training (trending)
    """

    def __init__(self, recent_days=None, pool=500):
        self.recent_days = recent_days
        self.pool = pool

    def fit(self, train: pd.DataFrame):
        df = train
        if self.recent_days:
            cutoff = df["time"].max() - pd.Timedelta(days=self.recent_days)
            df = df[df["time"] >= cutoff]
        scores = df.groupby("item_id")["weight"].sum().sort_values(ascending=False)
        self.ranked = scores.index[: self.pool].tolist()
        top = scores.iloc[: self.pool]
        self.score_map = (top / top.max()).to_dict()

        purchases = train[train["event"] == "transaction"]
        self.bought = purchases.groupby("user_id")["item_id"].apply(set).to_dict()
        return self

    def recommend(self, user_id, k=10):
        already_bought = self.bought.get(user_id, set())
        out = []
        for item in self.ranked:
            if item not in already_bought:
                out.append(item)
                if len(out) == k:
                    break
        return out


class ItemKNNRecommender:
    """Item-to-item collaborative filtering using cosine similarity."""

    def __init__(self, max_user_items=50, min_item_users=3, fallback=None):
        self.max_user_items = max_user_items
        self.min_item_users = min_item_users
        self.fallback = fallback

    def fit(self, train: pd.DataFrame):
        # one row per (user, item): strongest event weight
        ui = (
            train.groupby(["user_id", "item_id"])["weight"]
            .max()
            .reset_index()
        )
        self.items = np.sort(ui["item_id"].unique())
        item_pos = {item: i for i, item in enumerate(self.items)}
        users = np.sort(ui["user_id"].unique())
        self.user_index = {u: i for i, u in enumerate(users)}

        rows = ui["user_id"].map(self.user_index).to_numpy()
        cols = ui["item_id"].map(item_pos).to_numpy()
        shape = (len(users), len(self.items))

        # Q: each user's weighted history (used when scoring)
        self.Q = sp.csr_matrix(
            (ui["weight"].to_numpy(dtype=np.float32), (rows, cols)), shape=shape
        )

        # B: binary matrix used to learn similarity (filtered)
        n_items_per_user = ui.groupby("user_id")["item_id"].transform("size")
        keep = (n_items_per_user >= 2) & (n_items_per_user <= self.max_user_items)
        users_per_item = ui[keep].groupby("item_id")["user_id"].transform("size")
        keep_rows = keep.copy()
        keep_rows[keep] = users_per_item >= self.min_item_users
        keep_rows = keep_rows.to_numpy()

        B = sp.csr_matrix(
            (np.ones(keep_rows.sum(), dtype=np.float32),
             (rows[keep_rows], cols[keep_rows])),
            shape=shape,
        )
        degree = np.asarray(B.sum(axis=0)).ravel()
        inv_norm = np.divide(
            1.0, np.sqrt(degree), out=np.zeros_like(degree), where=degree > 0
        )
        Bn = B @ sp.diags(inv_norm.astype(np.float32))
        S = (Bn.T @ Bn).tocsr()          # cosine similarity between items
        S.setdiag(0)
        S.eliminate_zeros()
        self.S = S

        purchases = train[train["event"] == "transaction"]
        self.bought = purchases.groupby("user_id")["item_id"].apply(set).to_dict()
        self.n_total = 0
        self.n_personalized = 0
        return self

    def recommend(self, user_id, k=10):
        self.n_total += 1
        if k <= 0:
            return []
        out = list(self.score_items(user_id, n=k))
        if out:
            self.n_personalized += 1
        if len(out) < k and self.fallback is not None:
            for item in self.fallback.recommend(user_id, k=k * 3):
                if item not in self.bought.get(user_id, set()) and item not in out:
                    out.append(item)
                    if len(out) == k:
                        break
        return out

    def score_items(self, user_id, n=200):
        """Return {item: score} for this user's top-n items, scaled to 0-1."""
        row = self.user_index.get(user_id)
        if row is None:
            return {}
        scores = (self.Q[row] @ self.S).tocoo()
        order = np.lexsort((scores.col, -scores.data))
        bought = self.bought.get(user_id, set())
        out = {}
        for idx in order:
            item = self.items[scores.col[idx]]
            if item not in bought:
                out[item] = float(scores.data[idx])
                if len(out) == n:
                    break
        if out:
            top = max(out.values())
            out = {i: s / top for i, s in out.items()}
        return out


class HybridRecommender:
    """final = alpha * personal (item-KNN) + (1 - alpha) * recent popularity."""

    def __init__(self, knn, pop, alpha=0.5):
        self.knn = knn
        self.pop = pop
        self.alpha = alpha

    def recommend(self, user_id, k=10):
        bought = self.pop.bought.get(user_id, set())
        combined = {}
        for item, s in self.knn.score_items(user_id).items():
            combined[item] = self.alpha * s
        for item, s in self.pop.score_map.items():
            if item not in bought:
                combined[item] = combined.get(item, 0.0) + (1 - self.alpha) * s
        ranked = sorted(combined, key=combined.get, reverse=True)
        return ranked[:k]