import pandas as pd
from preprocessing import clean_events, chronological_split


def make_raw():
    return pd.DataFrame({
        "timestamp": [1_433_221_332_000 + i * 86_400_000 * 3 for i in range(30)],
        "visitorid": [1] * 30,
        "event": ["view"] * 29 + ["bogus"],
        "itemid": list(range(30)),
        "transactionid": [None] * 30,
    })


def test_invalid_events_removed():
    cleaned = clean_events(make_raw())
    assert set(cleaned["event"]) == {"view"}


def test_duplicates_removed():
    raw = make_raw()
    raw = pd.concat([raw, raw.iloc[[0]]])  # add an exact duplicate
    assert len(clean_events(raw)) == 29


def test_split_has_no_time_overlap():
    cleaned = clean_events(make_raw())
    train, val, test = chronological_split(cleaned)
    assert len(train) > 0 and len(val) > 0 and len(test) > 0
    assert train["time"].max() < val["time"].min()
    assert val["time"].max() < test["time"].min()