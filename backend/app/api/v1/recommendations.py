import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Actor, get_actor, require_actor
from app.core.rate_limit import reco_limiter
from app.db.session import get_db
from app.models import Product, RecommendationImpression
from app.schemas.product import ProductOut
from app.schemas.recommendation import (FeedbackIn, ImpressionsIn, RecommendationItem,
                                        RecommendationResponse, StatedPreferences,
                                        StatedPreferencesPatch)
from app.services import preferences as prefs
from app.services import recommendation as reco
from app.services.events import store_event

router = APIRouter(prefix="/recommendations", tags=["recommendations"],
                   dependencies=[Depends(reco_limiter)])


def _respond(request: Request, result: reco.RecResult) -> RecommendationResponse:
    return RecommendationResponse(
        request_id=getattr(request.state, "request_id", None),
        model_version=result.model_version,
        strategy=result.strategy,
        fallback_used=result.fallback_used,
        recommendations=[
            RecommendationItem(
                product_id=r.product.id, product=ProductOut.model_validate(r.product),
                rank=i + 1, score=r.score, source=r.source,
                reason_codes=r.reason_codes, explanation=r.explanation)
            for i, r in enumerate(result.items)
        ],
    )


def _stated(db: Session, actor: Actor) -> StatedPreferences:
    values = prefs.explicit_prefs(db, actor)
    return StatedPreferences(
        liked_categories=values.get("liked_categories") or [],
        blocked_categories=values.get("blocked_categories") or [],
        liked_brands=values.get("liked_brands") or [],
        price_range=values.get("price_range"),
    )


@router.get("/home", response_model=RecommendationResponse)
def home_feed(request: Request, limit: int = Query(12, ge=1, le=50),
              category: str | None = Query(None, max_length=100),
              actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    return _respond(request, reco.recommend_home_safe(db, actor, limit, category))


@router.get("/similar/{product_id}", response_model=RecommendationResponse)
def similar(request: Request, product_id: uuid.UUID, limit: int = Query(8, ge=1, le=24),
            db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found.")
    return _respond(request, reco.recommend_similar(db, product, limit))


@router.get("/trending", response_model=RecommendationResponse)
def trending(request: Request, limit: int = Query(12, ge=1, le=50),
             category: str | None = Query(None, max_length=100),
             db: Session = Depends(get_db)):
    return _respond(request, reco.recommend_trending(db, limit, category))


@router.get("/preferences", response_model=StatedPreferences)
def get_stated_preferences(actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    """Stated preferences for whoever is asking: an account, or an anonymous session."""
    return _stated(db, actor)


@router.patch("/preferences", response_model=StatedPreferences)
def update_stated_preferences(payload: StatedPreferencesPatch,
                              actor: Actor = Depends(require_actor),
                              db: Session = Depends(get_db)):
    """Sets stated preferences without requiring an account, so first-visit
    onboarding works before anyone registers. Send only what changes."""
    for ptype in payload.model_fields_set:
        value = getattr(payload, ptype)
        if ptype in prefs.NAME_TYPES:
            names = prefs.clean_names(value)
            if names:
                prefs.set_pref(db, actor, ptype, names)
            else:
                prefs.clear_pref(db, actor, ptype)
        elif ptype == "price_range":
            if value is None or (value.min is None and value.max is None):
                prefs.clear_pref(db, actor, ptype)
            else:
                prefs.set_pref(db, actor, ptype, {
                    "min": str(value.min) if value.min is not None else None,
                    "max": str(value.max) if value.max is not None else None})
    db.commit()
    return _stated(db, actor)


@router.post("/impressions")
def record_impressions(payload: ImpressionsIn, response: Response,
                       actor: Actor = Depends(require_actor), db: Session = Depends(get_db)):
    """Called by the frontend with items that were actually displayed, and where.

    Each item becomes an impression keyed by `request_id:product_id`. A repeated
    report (a retry, a remount) is ignored rather than counted twice, and a later
    click on the same product carries the same key, so clicks can be matched to
    the impressions they came from.
    """
    if actor.user is not None and not actor.user.tracking_consent:
        response.status_code = 202
        return {"stored": 0, "reason": "tracking_disabled"}
    ids = {i.product_id for i in payload.items}
    found = set(db.scalars(select(Product.id).where(Product.id.in_(ids))))
    if found != ids:
        raise HTTPException(status_code=422, detail="Unknown product_id in items.")
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    rows = [{
        "user_id": actor.user.id if actor.user else None,
        "session_id": actor.session_id,
        "product_id": item.product_id,
        "request_id": payload.request_id,
        "impression_id": f"{payload.request_id}:{item.product_id}"[:120],
        "model_version": payload.model_version,
        "position": item.position,
    } for item in payload.items]
    result = db.execute(pg_insert(RecommendationImpression).values(rows)
                        .on_conflict_do_nothing(index_elements=["impression_id"])
                        .returning(RecommendationImpression.impression_id))
    db.commit()
    stored = len(result.scalars().all())      # only rows that were actually inserted
    response.status_code = 201
    return {"stored": stored}


@router.post("/feedback")
def record_feedback(payload: FeedbackIn, response: Response,
                    actor: Actor = Depends(require_actor), db: Session = Depends(get_db)):
    """Save or dismiss a recommended product. Dismissed products stop being recommended."""
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=422, detail="Unknown product_id.")
    context = {"source": "recommendation"}
    if payload.request_id:
        context["request_id"] = payload.request_id
    status, event_id = store_event(
        db, actor, event_type=payload.feedback, product_id=product.id, occurred_at=None,
        context=context, idempotency_key=payload.idempotency_key)
    if status == "tracking_disabled":
        response.status_code = 202
        return {"stored": False, "reason": "tracking_disabled"}
    if payload.feedback == "save" and actor.user is not None and product.is_active:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from app.models import SavedItem
        db.execute(pg_insert(SavedItem).values(user_id=actor.user.id, product_id=product.id)
                   .on_conflict_do_nothing())
        db.commit()
    response.status_code = 200 if status == "duplicate" else 201
    return {"stored": True, "duplicate": status == "duplicate"}
