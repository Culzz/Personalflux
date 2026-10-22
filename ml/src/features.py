"""Item metadata features (leakage-safe snapshots) and recent-intent signals."""
import numpy as np
import pandas as pd
from preprocessing import RAW

KEEP_PROPS = ("categoryid", "available")


def load_item_properties(cutoff_ms, raw_dir=RAW, chunksize=1_000_000):
    """Read the big property files in chunks, keeping only what we need."""
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


def category_distribution(cats, weights=None):
    """List of category ids (+ optional event weights) -> {category: share}.
    Unknown (NaN) categories are ignored."""
    totals = {}
    if weights is None:
        weights = [1.0] * len(cats)
    for c, w in zip(cats, weights):
        if pd.isna(c):
            continue
        totals[c] = totals.get(c, 0.0) + float(w)
    total = sum(totals.values())
    return {c: v / total for c, v in totals.items()} if total > 0 else {}


def js_divergence(p, q):
    """Jensen-Shannon divergence, base 2: 0 = identical, 1 = no overlap."""
    keys = set(p) | set(q)
    if not keys:
        return 0.0
    pa = np.array([p.get(k, 0.0) for k in keys])
    qa = np.array([q.get(k, 0.0) for k in keys])
    m = 0.5 * (pa + qa)

    def kl(a, b):
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))

    return 0.5 * kl(pa, m) + 0.5 * kl(qa, m)


def shift_score(long_dist, recent_dist, n_recent, min_events=3, full_evidence=8):
    """0 = no evidence of a shift, 1 = strong, well-supported shift.

    - below min_events recent events -> 0 (one stray click changes nothing)
    - evidence ramps up linearly until full_evidence recent events
    """
    if not long_dist or not recent_dist or n_recent < min_events:
        return 0.0
    evidence = min(1.0, n_recent / full_evidence)
    return js_divergence(long_dist, recent_dist) * evidence