"""Blending of the session signal and the long-term signal."""


def long_term_weight(beta, shift, adaptive):
    """How much the long-term profile counts.

    fixed:    beta
    adaptive: beta * (1 - shift), so a strong, well-supported shift turns
              the long-term part down.
    """
    if adaptive:
        return beta * (1.0 - min(max(shift, 0.0), 1.0))
    return beta


def blend(session_scores, long_scores, weight):
    """score = session + weight * long_term, over the union of items."""
    combined = dict(session_scores)
    for item, s in long_scores.items():
        combined[item] = combined.get(item, 0.0) + weight * s
    return combined