import pytest
from stage_eval import candidate_recall, decompose, summarise


def test_candidate_recall_counts_only_what_was_proposed():
    assert candidate_recall([1, 2, 3], {2, 3, 4, 5}) == 0.5


def test_candidate_recall_without_relevant_items_is_zero():
    assert candidate_recall([1, 2], set()) == 0.0


def test_decompose_separates_the_two_kinds_of_miss():
    # 1 was a hit, 2 was proposed but sat outside the top 2, 9 was never proposed.
    d = decompose(candidates=[1, 2, 3], ranked=[1, 3, 2], relevant={1, 2, 9}, k=2)
    assert d == {"relevant": 3, "hits": 1, "retrieval_misses": 1, "ranking_misses": 1}


def test_decompose_counts_a_relevant_item_below_the_cut_as_a_ranking_miss():
    d = decompose(candidates=[1, 2], ranked=[1, 2], relevant={2}, k=1)
    assert d == {"relevant": 1, "hits": 0, "retrieval_misses": 0, "ranking_misses": 1}


def test_an_item_the_generator_missed_cannot_be_blamed_on_the_ranking():
    # The distinction only means something if a retrieval miss is never also
    # counted as a ranking miss, whatever the ranked list contains.
    d = decompose(candidates=[1], ranked=[1, 9], relevant={9}, k=2)
    assert d["retrieval_misses"] == 1
    assert d["ranking_misses"] == 0


def test_candidate_recall_is_an_upper_bound_on_recall_at_k():
    candidates, relevant = [1, 2, 3], {2, 9}
    ranked = [1, 2, 3]
    hit_rate = len(set(ranked[:2]) & relevant) / len(relevant)
    assert candidate_recall(candidates, relevant) >= hit_rate


def test_summarise_blames_ordering_when_the_item_was_retrieved():
    # The only relevant item was proposed first in the candidate set but the
    # final list put it third, so every miss is an ordering miss.
    s = summarise([decompose([3, 1, 2], [1, 2, 3], {3}, k=2)], k=2)
    assert s["recall@2"] == 0.0
    assert s["candidate_recall"] == 1.0
    assert s["headroom_used"] == 0.0
    assert s["lost_to_ranking"] == 1.0
    assert s["lost_to_retrieval"] == 0.0
    assert s["sessions_with_ranking_miss"] == 1.0
    assert s["sessions_with_retrieval_miss"] == 0.0


def test_summarise_blames_retrieval_when_the_item_was_never_proposed():
    s = summarise([decompose([1, 2], [1, 2], {7}, k=2)], k=2)
    assert s["candidate_recall"] == 0.0
    assert s["lost_to_retrieval"] == 1.0
    assert s["lost_to_ranking"] == 0.0
    # With nothing retrieved there is no ceiling to have used up, and no
    # division by zero either.
    assert s["headroom_used"] == 0.0


def test_summarise_averages_recall_per_session():
    counters = [
        decompose([1], [1], {1}, k=10),      # that session is complete
        decompose([2, 3], [2, 3], {2, 3}, k=10),
        decompose([4], [4], {4, 5}, k=10),   # half of two relevant items
    ]
    assert summarise(counters, k=10)["recall@10"] == pytest.approx(2.5 / 3)


def test_summarise_ignores_sessions_with_nothing_relevant():
    assert summarise([decompose([], [], set(), k=10)], k=10) == {"sessions": 0}


def test_summarise_totals_the_misses_it_splits():
    counters = [
        decompose([1, 2], [1, 2], {1, 9}, k=1),   # one retrieval miss
        decompose([3], [3], {4, 5}, k=1),         # two retrieval misses
        decompose([7, 6], [6, 7], {7}, k=1),      # one ranking miss: 7 was proposed
    ]
    s = summarise(counters, k=1)
    assert s["misses"] == 4
    assert s["lost_to_retrieval"] == pytest.approx(0.75)
    assert s["lost_to_ranking"] == pytest.approx(0.25)
