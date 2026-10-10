"""Baseline recommenders. Start with popularity."""
import pandas as pd


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