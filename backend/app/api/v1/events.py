from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_actor
from app.db.session import get_db
from app.models import Product
from app.schemas.event import EventIn, EventOut
from app.services.events import store_event

router = APIRouter(tags=["events"])


@router.post("/events", response_model=EventOut)
def record_event(payload: EventIn, response: Response, actor: Actor = Depends(require_actor),
                 db: Session = Depends(get_db)):
    """201 stored | 200 duplicate (same idempotency key) | 202 not stored (tracking is off)."""
    if payload.product_id is not None and db.get(Product, payload.product_id) is None:
        raise HTTPException(status_code=422, detail="Unknown product_id.")
    status, event_id = store_event(
        db, actor, event_type=payload.event_type, product_id=payload.product_id,
        occurred_at=payload.occurred_at, context=payload.context,
        idempotency_key=payload.idempotency_key,
    )
    if status == "tracking_disabled":
        response.status_code = 202
        return EventOut(stored=False, reason="tracking_disabled")
    if status == "duplicate":
        response.status_code = 200
        return EventOut(stored=True, duplicate=True, event_id=event_id)
    response.status_code = 201
    return EventOut(stored=True, event_id=event_id)
