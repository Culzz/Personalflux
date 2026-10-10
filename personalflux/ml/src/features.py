"""Item metadata features (leakage-safe snapshots)."""
import pandas as pd
from preprocessing import RAW

KEEP_PROPS = ("categoryid", "available")


def load_item_properties(cutoff_ms, raw_dir=RAW, chunksize=1_000_000):
    """Read the big property files in chunks, keeping only what we need.

    The files have ~20M rows, so we filter each chunk before storing it.
    """
    frames = []
    for name in ("item_properties_part1.csv", "item_properties_part2.csv"):
        for chunk in pd.read_csv(raw_dir / name, chunksize=chunksize,
                                 dtype={"value": str}):
            keep = chunk["property"].isin(KEEP_PROPS) & (chunk["timestamp"] <= cutoff_ms)
            frames.append(chunk[keep])
    return pd.concat(frames, ignore_index=True)


def latest_snapshot(props, cutoff_ms):
    """Latest known value of each property per item, using only records up to cutoff."""
    props = props[props["timestamp"] <= cutoff_ms].sort_values("timestamp")
    latest = props.drop_duplicates(subset=["itemid", "property"], keep="last")
    wide = latest.pivot(index="itemid", columns="property", values="value")
    wide.columns.name = None
    return wide


def root_category(cat, parent_of, max_depth=20):
    """Walk up the category tree to the top-level category."""
    steps = 0
    while cat in parent_of and not pd.isna(parent_of[cat]) and steps < max_depth:
        cat = parent_of[cat]
        steps += 1
    return cat