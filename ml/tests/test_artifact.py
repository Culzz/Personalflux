import numpy as np
import pandas as pd
import pytest
from baselines import PopularityRecommender, ItemKNNRecommender
from artifact import save_artifact, load_artifact


def _tiny():
    pairs = [(1, 10), (1, 20), (2, 10), (2, 20), (3, 10), (3, 30), (4, 20), (4, 30)]
    df = pd.DataFrame(pairs, columns=["user_id", "item_id"])
    df["event"] = "view"
    df["weight"] = 1
    df["time"] = pd.Timestamp("2015-06-01")
    return df


@pytest.fixture
def saved(tmp_path):
    df = _tiny()
    pop = PopularityRecommender(pool=10).fit(df)
    knn = ItemKNNRecommender(min_item_users=2).fit(df)
    folder = save_artifact("test-v1", knn.S, knn.items, pop.ranked, pop.score_map,
                           {"test": True}, {"note": "unit test"}, root=tmp_path)
    return folder, knn


def test_round_trip_matches_in_memory_model(saved):
    folder, knn = saved
    model = load_artifact(folder)
    sims = model.similar_items(10, k=2)
    assert [i for i, _ in sims] == [20, 30]
    assert sims[0][1] > sims[1][1]
    dense = knn.S.toarray()
    pos = {int(it): n for n, it in enumerate(knn.items)}
    assert sims[0][1] == pytest.approx(dense[pos[10], pos[20]], rel=1e-5)


def test_session_recs_exclude_context_and_use_similarity(saved):
    model = load_artifact(saved[0])
    recs = model.recommend_for_session([10], k=2)
    assert [i for i, _, _ in recs] == [20, 30]
    assert all(src == "similarity" for _, _, src in recs)


def test_unknown_items_fall_back_to_popularity(saved):
    model = load_artifact(saved[0])
    recs = model.recommend_for_session([999], k=2)
    assert len(recs) == 2
    assert all(src == "popularity_fallback" for _, _, src in recs)
    assert all(i in {10, 20, 30} for i, _, _ in recs)


def test_tampered_artifact_is_rejected(saved):
    folder = saved[0]
    np.save(folder / "items.npy", np.array([1, 2, 3], dtype=np.int64))
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_artifact(folder)


def test_existing_version_is_never_overwritten(saved, tmp_path):
    df = _tiny()
    pop = PopularityRecommender(pool=10).fit(df)
    knn = ItemKNNRecommender(min_item_users=2).fit(df)
    with pytest.raises(FileExistsError):
        save_artifact("test-v1", knn.S, knn.items, pop.ranked, pop.score_map,
                      {}, {}, root=tmp_path)