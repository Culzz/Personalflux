"""Export the catalog (item ids + root categories) for the backend importer."""
import pandas as pd

from artifact import ARTIFACTS, load_artifact
from preprocessing import PROCESSED

version = (ARTIFACTS / "current_version.txt").read_text().strip()
model = load_artifact(ARTIFACTS / version)
meta = pd.read_parquet(model.folder / "item_meta.parquet")

df = pd.DataFrame({"source_item_id": model.items.astype("int64")})
df["category_id"] = df["source_item_id"].map(meta["root_category_id"]).astype("Int64")

out = PROCESSED / "catalog_export.csv"
df.to_csv(out, index=False)

avail = df["source_item_id"].map(meta["available"])
print("artifact version:", version)
print("items exported:  ", len(df))
print(f"with a category: {df['category_id'].notna().mean():.1%}")
print("availability snapshot (1=available, 0=not, NaN=unknown):")
print(avail.value_counts(dropna=False).to_string())
print("saved", out)
