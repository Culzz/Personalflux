import pytest
import pandas as pd
from features import (
    latest_snapshot, root_category,
    category_distribution, js_divergence, shift_score,
)


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


def test_distribution_ignores_unknown_categories():
    d = category_distribution([1, 1, 2, float("nan")], [1, 1, 2, 5])
    assert d == {1: 0.5, 2: 0.5}


def test_js_identical_is_zero_and_disjoint_is_one():
    assert js_divergence({1: 1.0}, {1: 1.0}) == pytest.approx(0.0)
    assert js_divergence({1: 1.0}, {2: 1.0}) == pytest.approx(1.0)


def test_single_click_does_not_trigger_a_shift():
    long_term = {1: 1.0}                 # 100% category 1 historically
    one_click = {2: 1.0}                 # a single click elsewhere
    assert shift_score(long_term, one_click, n_recent=1) == 0.0


def test_repeated_new_interest_triggers_a_strong_shift():
    long_term = {1: 1.0}
    recent = {2: 1.0}
    assert shift_score(long_term, recent, n_recent=8) == pytest.approx(1.0)


def test_no_shift_when_recent_matches_long_term():
    d = {1: 0.5, 2: 0.5}
    assert shift_score(d, d, n_recent=10) == pytest.approx(0.0)