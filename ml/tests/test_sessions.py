import pandas as pd
from sessions import add_session_ids, build_session_examples


def test_sessions_split_on_gap_and_user():
    df = pd.DataFrame({
        "user_id": [1, 1, 1, 2],
        "time": pd.to_datetime(["2015-06-01 10:00", "2015-06-01 10:10",
                                "2015-06-01 12:00", "2015-06-01 10:05"]),
    })
    out = add_session_ids(df)
    ids = out.sort_values(["user_id", "time"])["session_id"].tolist()
    assert ids[0] == ids[1]          # 10 min apart: same session
    assert ids[2] != ids[1]          # 110 min gap: new session
    assert ids[3] not in ids[:3]     # different visitor: new session


def test_examples_use_only_events_before_first_positive():
    df = pd.DataFrame({
        "session_id": [1, 1, 1, 1, 2, 2],
        "user_id": [7] * 6,
        "event": ["view", "view", "addtocart", "view", "view", "addtocart"],
        "item_id": [1, 2, 3, 4, 5, 6],
    })
    ex = build_session_examples(df, min_context=2)
    assert len(ex) == 1                        # session 2 has only 1 context item
    assert ex[0]["context"] == [1, 2]
    assert ex[0]["target"] == {3}              # later view of item 4 is not a target