"""Build the item metadata table as of the end of the TRAIN period."""
import pandas as pd
from preprocessing import RAW, PROCESSED
from features import load_item_properties, latest_snapshot, root_category

train = pd.read_parquet(PROCESSED / "train.parquet")
val = pd.read_parquet(PROCESSED / "val.parquet")

cutoff = train["time"].max()
cutoff_ms = int((cutoff - pd.Timestamp("1970-01-01")) // pd.Timedelta(milliseconds=1))
print("Using item properties up to:", cutoff)

props = load_item_properties(cutoff_ms)
print("property rows kept:", len(props))

meta = latest_snapshot(props, cutoff_ms)
meta["category_id"] = pd.to_numeric(meta["categoryid"], errors="coerce")
meta["available"] = pd.to_numeric(meta["available"], errors="coerce")

category_tree_path = RAW / "category_tree.csv"
if category_tree_path.exists():
    tree = pd.read_csv(category_tree_path)
    parent_of = dict(zip(tree["categoryid"], tree["parentid"]))
    meta["root_category_id"] = meta["category_id"].map(
        lambda c: root_category(c, parent_of) if pd.notna(c) else c
    )
else:
    print(
        f"WARNING: {category_tree_path} not found; root_category_id will be missing. "
        "Add category_tree.csv to data/raw to derive root categories."
    )
    meta["root_category_id"] = pd.NA

meta = meta[["category_id", "root_category_id", "available"]]
meta.index.name = "item_id"

# --- coverage report ---
has_cat = set(meta.index[meta["category_id"].notna()])
for name, part in [("TRAIN", train), ("VALIDATION", val)]:
    items = set(part["item_id"])
    share = len(items & has_cat) / len(items)
    print(f"{name}: items with a known category: {share:.1%} of {len(items)}")

print("distinct categories:", meta["category_id"].nunique())
print("distinct root categories:", meta["root_category_id"].nunique())
print("available==1 share:", round((meta["available"] == 1).mean(), 3))
print("\nbiggest root categories (by item count):")
print(meta["root_category_id"].value_counts().head(5).to_string())

meta.to_parquet(PROCESSED / "item_meta.parquet")
print("\nSaved", PROCESSED / "item_meta.parquet")