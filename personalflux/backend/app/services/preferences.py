"""Stated preferences, for an account or an anonymous session.

One place so the signed-in dashboard and the first-visit onboarding (which runs
before anyone registers) read and write the same rows. Inferred preferences are
computed from events and are never stored here.
"""
from datetime import datetime, timezone

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.api.deps import Actor
from app.models import Preference

# Types that hold a list of names, as opposed to price_range.
NAME_TYPES = ("liked_categories", "blocked_categories", "liked_brands")


def clean_names(values: list[str] | None) -> list[str]:
    """Trim, drop blanks, cap at 100 chars, and drop duplicates."""
    seen, out = set(), []
    for v in values or []:
        v = v.strip()
        if v and len(v) <= 100 and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _owner_conds(actor: Actor) -> list:
    conds = []
    if actor.user is not None:
        conds.append(Preference.user_id == actor.user.id)
    if actor.session_id:
        conds.append(Preference.session_id == actor.session_id)
    return conds


def explicit_prefs(db: Session, actor: Actor) -> dict:
    """Merged view. A statement made while signed in wins over an anonymous one."""
    conds = _owner_conds(actor)
    if not conds:
        return {}
    rows = db.scalars(select(Preference).where(
        or_(*conds), Preference.source == "explicit")).all()
    merged: dict = {}
    for row in sorted(rows, key=lambda r: r.user_id is not None):  # session first, account last
        merged[row.preference_type] = row.preference_value
    return merged


def _own_filter(actor: Actor) -> list:
    """Where this actor's own rows live: the account if signed in, else the session."""
    if actor.user is not None:
        return [Preference.user_id == actor.user.id]
    return [Preference.session_id == actor.session_id]


def set_pref(db: Session, actor: Actor, ptype: str, value) -> None:
    row = db.scalar(select(Preference).where(
        *_own_filter(actor), Preference.preference_type == ptype))
    if row is None:
        db.add(Preference(
            user_id=actor.user.id if actor.user else None,
            session_id=None if actor.user else actor.session_id,
            preference_type=ptype, preference_value=value, source="explicit"))
    else:
        row.preference_value = value


def clear_pref(db: Session, actor: Actor, ptype: str) -> None:
    db.execute(delete(Preference).where(
        *_own_filter(actor), Preference.preference_type == ptype))


def reset(db: Session, actor: Actor, include_explicit: bool) -> None:
    """Stop using past activity. Stated preferences go only if asked for."""
    if actor.user is not None:
        actor.user.profile_reset_at = datetime.now(timezone.utc)
    if include_explicit:
        conds = _owner_conds(actor)
        if conds:
            db.execute(delete(Preference).where(or_(*conds)))
