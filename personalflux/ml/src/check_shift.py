"""Does the shift score tell us when RECENT beats LONG-TERM at predicting
the user's next category? Train + validation only (no test split)."""
import pandas as pd
from preprocessing import PROCESSED
from features import category_distribution, shift_score

RECENT_DAYS = 7

train = pd.read_parquet(PROCESSED / "train.parquet")
val = pd.read_parquet(PROCESSED / "val.parquet")
meta = pd.read_parquet(PROCESSED / "item_meta.parquet")

root = meta["root_category_id"]
train = train.assign(cat=train["item_id"].map(root))
val = val.assign(cat=val["item_id"].map(root))

split = train["time"].max() - pd.Timedelta(days=RECENT_DAYS)
older = train[train["time"] < split]
recent = train[train["time"] >= split]


def profiles(df):
    return (df.dropna(subset=["cat"]).groupby("user_id")
              .agg(cats=("cat", list), w=("weight", list)))


o, r = profiles(older), profiles(recent)

# each user's FIRST cart/purchase in validation (with a known category)
first_pos = (
    val[val["event"].isin(["addtocart", "transaction"]) & val["cat"].notna()]
    .sort_values("time").drop_duplicates("user_id", keep="first")
    .set_index("user_id")["cat"]
)

users = o.index.intersection(r.index).intersection(first_pos.index)
print(f"users with older history, recent activity AND a validation cart/purchase: {len(users)}")

rows = []
for u in users:
    long_d = category_distribution(o.at[u, "cats"], o.at[u, "w"])
    rec_d = category_distribution(r.at[u, "cats"], r.at[u, "w"])
    n_recent = len(r.at[u, "cats"])
    target = first_pos[u]
    rows.append({
        "shift": shift_score(long_d, rec_d, n_recent),
        "long_hit": max(long_d, key=long_d.get) == target,
        "recent_hit": max(rec_d, key=rec_d.get) == target,
    })

df = pd.DataFrame(rows)
df["bucket"] = pd.cut(df["shift"], [-0.001, 0.0, 0.2, 0.5, 1.0],
                      labels=["none(0)", "low(0-0.2)", "medium(0.2-0.5)", "high(0.5-1)"])

summary = df.groupby("bucket", observed=True).agg(
    users=("shift", "size"),
    long_term_acc=("long_hit", "mean"),
    recent_acc=("recent_hit", "mean"),
)
print("\nTop-1 root-category accuracy by shift bucket:")
print(summary.round(3).to_string())
print("\noverall:", df[["long_hit", "recent_hit"]].mean().round(3).to_dict())