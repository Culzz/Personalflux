import pandas as pd
from features import latest_snapshot, root_category


def test_snapshot_ignores_future_and_takes_latest():
    props = pd.DataFrame({
        "timestamp": [100, 200, 300],
        "itemid": [1, 1, 1],
        "property": ["categoryid"] * 3,
        "value": ["10", "20", "99"],
    })
    wide = latest_snapshot(props, cutoff_ms=250)
    assert wide.loc[1, "categoryid"] == "20"   # 300 is in the future, ignored


def test_root_category_walks_up():
    parent_of = {3: 2, 2: 1, 1: float("nan")}
    assert root_category(3, parent_of) == 1