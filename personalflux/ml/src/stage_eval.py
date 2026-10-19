"""Where a recommendation is lost: the generator or the ranking step.

The served feed is built in two stages. A generator proposes a bounded set of
candidates from the model's similarity rows, and the ranking step then orders
those candidates, drops what the visitor must not see, and cuts the list at k.

A relevant item missing from the top k can therefore be missing for two
different reasons, and the two call for different work:

  * the generator never proposed it -- a retrieval problem, fixed by widening or
    improving the generator
  * the generator proposed it and it was ranked below k -- an ordering problem,
    fixed in the ranking step

Candidate recall is an upper bound on recall@k for any k inside the candidate
budget, which is what makes the split worth reporting: it is the ceiling the
ranking step is working against. Nothing here touches a model or a file, so the
arithmetic can be checked on its own.
"""


def candidate_recall(candidates, relevant) -> float:
    """Share of the relevant items the generator proposed."""
    relevant = set(relevant)
    if not relevant:
        return 0.0
    return len(set(candidates) & relevant) / len(relevant)


def decompose(candidates, ranked, relevant, k) -> dict:
    """Split one session into hits, retrieval misses and ranking misses.

    `candidates` is what the generator proposed, `ranked` the final ordered
    list, and `relevant` the items the visitor actually carted or bought.
    """
    relevant = set(relevant)
    proposed = set(candidates)
    top = set(ranked[:k])
    return {
        "relevant": len(relevant),
        "hits": len(top & relevant),
        "retrieval_misses": len(relevant - proposed),
        "ranking_misses": len((proposed & relevant) - top),
    }


def summarise(counters, k) -> dict:
    """Aggregate per-session decompositions into rates.

    Recall figures are averaged per session, the same way evaluate.evaluate()
    does it, so they can be compared with the existing reports. The miss split
    is by item, answering "of everything we failed to surface, how much was
    never retrieved"; the two session rates answer the different question "how
    many sessions were affected by each kind" and are reported too, because a
    handful of sessions with many targets can otherwise hide the pattern.
    """
    counters = [c for c in counters if c["relevant"]]
    n = len(counters)
    if not n:
        return {"sessions": 0}

    recall = sum(c["hits"] / c["relevant"] for c in counters) / n
    ceiling = sum(
        (c["relevant"] - c["retrieval_misses"]) / c["relevant"] for c in counters
    ) / n
    retrieval = sum(c["retrieval_misses"] for c in counters)
    ranking = sum(c["ranking_misses"] for c in counters)
    lost = retrieval + ranking

    return {
        "sessions": n,
        f"recall@{k}": recall,
        "candidate_recall": ceiling,
        "headroom_used": (recall / ceiling) if ceiling else 0.0,
        "misses": lost,
        "lost_to_retrieval": (retrieval / lost) if lost else 0.0,
        "lost_to_ranking": (ranking / lost) if lost else 0.0,
        "sessions_with_retrieval_miss": sum(
            1 for c in counters if c["retrieval_misses"]
        ) / n,
        "sessions_with_ranking_miss": sum(
            1 for c in counters if c["ranking_misses"]
        ) / n,
    }
