from pathlib import Path
import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

# A DataFrame is a table: rows = records, columns = fields
events = pd.read_csv(RAW / "events.csv")

print("=== SHAPE (rows, columns) ===")
print(events.shape)

print("\n=== FIRST 5 ROWS ===")
print(events.head())

print("\n=== COLUMN TYPES ===")
print(events.dtypes)

print("\n=== EVENT TYPE COUNTS ===")
print(events["event"].value_counts())

print("\n=== UNIQUE VISITORS / ITEMS ===")
print("visitors:", events["visitorid"].nunique())
print("items:   ", events["itemid"].nunique())

print("\n=== MISSING VALUES PER COLUMN ===")
print(events.isna().sum())

# Timestamps are in milliseconds since 1970. Convert to real dates.
events["time"] = pd.to_datetime(events["timestamp"], unit="ms")
print("\n=== DATE RANGE ===")
print(events["time"].min(), "->", events["time"].max())