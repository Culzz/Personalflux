"""Run cleaning + splitting, print a report, save the splits."""
import pandas as pd
from preprocessing import (
    PROCESSED, load_events, clean_events, chronological_split,
)


def describe(name: str, df: pd.DataFrame) -> None:
    print(f"\n--- {name} ---")
    print("rows:      ", len(df))
    print("users:     ", df["user_id"].nunique())
    print("items:     ", df["item_id"].nunique())
    print("date range:", df["time"].min(), "->", df["time"].max())
    print(df["event"].value_counts().to_string())


raw = load_events()
events = clean_events(raw)
print(f"raw rows: {len(raw)} | after cleaning: {len(events)} "
      f"| removed: {len(raw) - len(events)}")

train, val, test = chronological_split(events)
describe("TRAIN", train)
describe("VALIDATION", val)
describe("TEST", test)

# How much of the future can we actually personalise?
train_users = set(train["user_id"])
train_items = set(train["item_id"])
for name, part in [("VALIDATION", val), ("TEST", test)]:
    users = set(part["user_id"])
    seen = users & train_users
    cold_items = set(part["item_id"]) - train_items
    positives = part[part["event"].isin(["addtocart", "transaction"])]
    eligible = set(positives["user_id"]) & train_users
    print(f"\n[{name}] users seen in train: {len(seen)}/{len(users)}")
    print(f"[{name}] items never seen in train: {len(cold_items)}")
    print(f"[{name}] users with a cart/purchase AND train history: {len(eligible)}")

PROCESSED.mkdir(parents=True, exist_ok=True)
train.to_parquet(PROCESSED / "train.parquet")
val.to_parquet(PROCESSED / "val.parquet")
test.to_parquet(PROCESSED / "test.parquet")
print("\nSaved train/val/test to", PROCESSED)