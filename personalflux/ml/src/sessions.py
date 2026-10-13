"""Sessionization and session-based evaluation examples."""
import pandas as pd

POSITIVE = {"addtocart", "transaction"}


def add_session_ids(df, gap_minutes=30):
    """A new session starts when the visitor changes or the gap exceeds N minutes."""
    df = df.sort_values(["user_id", "time"]).copy()
    new_user = df["user_id"] != df["user_id"].shift()
    big_gap = df["time"].diff() > pd.Timedelta(minutes=gap_minutes)
    df["session_id"] = (new_user | big_gap).cumsum()
    return df


def build_session_examples(df, min_context=2):
    """One example per session with a cart/purchase.

    context = unique items viewed BEFORE the first cart/purchase (in order)
    target  = items carted/bought from the first cart/purchase onward
    """
    has_pos = df.loc[df["event"].isin(POSITIVE), "session_id"].unique()
    df = df[df["session_id"].isin(has_pos)]

    examples = []
    for sid, g in df.groupby("session_id", sort=False):
        events = g["event"].tolist()
        items = g["item_id"].tolist()
        p = next(i for i, e in enumerate(events) if e in POSITIVE)
        context = list(dict.fromkeys(items[:p]))     # unique, keeps order
        if len(context) < min_context:
            continue
        target = {items[i] for i in range(p, len(items)) if events[i] in POSITIVE}
        examples.append({
            "session_id": sid,
            "user_id": g["user_id"].iloc[0],
            "context": context,
            "target": target,
        })
    return examples