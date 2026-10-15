"""Inferred preferences: computed from events, never stored (so a reset is clean)."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Interaction, Product, User

# Event strengths: starting hypotheses (SRS 5.4), not learned values
EVENT_WEIGHTS = {"view": 1.0, "click": 2.0, "compare": 2.0, "save": 3.0,
                 "add_to_cart": 4.0, "purchase": 5.0}
RECENT_DAYS = 7


def _shares(totals: dict[str, float], top: int = 5) -> list[dict]:
    total = sum(totals.values())
    if total <= 0:
        return []
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:top]
    return [{"category": c, "share": round(v / total, 3)} for c, v in ranked]


def build_inferred_profile(db: Session, user: User) -> dict:
    q = (select(Interaction.event_type, Interaction.occurred_at, Product.category)
         .join(Product, Interaction.product_id == Product.id)
         .where(Interaction.user_id == user.id,
                Interaction.event_type.in_(list(EVENT_WEIGHTS)),
                Product.category.is_not(None)))
    if user.profile_reset_at is not None:
        q = q.where(Interaction.occurred_at >= user.profile_reset_at)
    rows = db.execute(q.order_by(Interaction.occurred_at.desc()).limit(2000)).all()

    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)
    long_term, recent = defaultdict(float), defaultdict(float)
    for event_type, occurred_at, category in rows:
        target = recent if occurred_at >= cutoff else long_term
        target[category] += EVENT_WEIGHTS[event_type]
    return {
        "long_term_categories": _shares(long_term),
        "recent_categories": _shares(recent),
        "events_considered": len(rows),
    }
