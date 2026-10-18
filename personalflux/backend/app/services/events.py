"""Storing interaction events: consent, idempotency and time checks in one place."""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import Actor
from app.models import Interaction

MAX_AGE = timedelta(days=7)
MAX_FUTURE = timedelta(minutes=5)


def normalise_time(occurred_at: datetime | None) -> datetime:
    now = datetime.now(timezone.utc)
    if occurred_at is None:
        return now
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    if occurred_at > now + MAX_FUTURE:
        raise HTTPException(status_code=422, detail="occurred_at is in the future.")
    if occurred_at < now - MAX_AGE:
        raise HTTPException(status_code=422, detail="occurred_at is too old.")
    return occurred_at


def _same_actor(ev: Interaction, actor: Actor) -> bool:
    if actor.user is not None:
        return ev.user_id == actor.user.id
    return ev.user_id is None and ev.session_id == actor.session_id


def _existing(db: Session, key: str) -> Interaction | None:
    return db.scalar(select(Interaction).where(Interaction.idempotency_key == key))


def _attribution(context: dict | None, product_id: uuid.UUID | None) -> dict:
    """Pull the recommendation trail out of an event's context.

    Returns request_id / impression_id / position / model_version. A click that
    carries a request id therefore points at the exact impression that was shown,
    which is what lets a click be attributed to a recommendation and a model
    version rather than merely counted.
    """
    context = context or {}
    request_id = context.get("request_id")
    request_id = request_id[:64] if isinstance(request_id, str) and request_id else None
    model_version = context.get("model_version")
    model_version = model_version[:100] if isinstance(model_version, str) and model_version else None
    position = context.get("position")
    position = position if isinstance(position, int) and not isinstance(position, bool) else None
    impression_id = f"{request_id}:{product_id}"[:120] if request_id and product_id else None
    return {"request_id": request_id, "impression_id": impression_id,
            "position": position, "model_version": model_version}


def store_event(db: Session, actor: Actor, *, event_type: str, product_id: uuid.UUID | None,
                occurred_at: datetime | None, context: dict | None,
                idempotency_key: str | None) -> tuple[str, uuid.UUID | None]:
    """Returns ("stored" | "duplicate" | "tracking_disabled", event id)."""
    if actor.user is not None and not actor.user.tracking_consent:
        return "tracking_disabled", None
    when = normalise_time(occurred_at)

    if idempotency_key:
        ex = _existing(db, idempotency_key)
        if ex is not None:
            if _same_actor(ex, actor):
                return "duplicate", ex.id
            raise HTTPException(status_code=409, detail="That idempotency key is already in use.")

    ev = Interaction(
        user_id=actor.user.id if actor.user else None, session_id=actor.session_id,
        product_id=product_id, event_type=event_type, context=context,
        idempotency_key=idempotency_key, occurred_at=when,
        **_attribution(context, product_id),
    )
    db.add(ev)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        ex = _existing(db, idempotency_key) if idempotency_key else None   # lost a race
        if ex is not None and _same_actor(ex, actor):
            return "duplicate", ex.id
        raise HTTPException(status_code=422, detail="Event could not be stored.")
    return "stored", ev.id
