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
                                        RecommendationResponse)
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


@router.post("/impressions")
def record_impressions(payload: ImpressionsIn, response: Response,
                       actor: Actor = Depends(require_actor), db: Session = Depends(get_db)):
    """Called by the frontend with what was actually shown, and at which position."""
    if actor.user is not None and not actor.user.tracking_consent:
        response.status_code = 202
        return {"stored": 0, "reason": "tracking_disabled"}
    ids = {i.product_id for i in payload.items}
    found = set(db.scalars(select(Product.id).where(Product.id.in_(ids))))
    if found != ids:
        raise HTTPException(status_code=422, detail="Unknown product_id in items.")
    for item in payload.items:
        db.add(RecommendationImpression(
            user_id=actor.user.id if actor.user else None, session_id=actor.session_id,
            product_id=item.product_id, request_id=payload.request_id,
            model_version=payload.model_version, position=item.position))
    db.commit()
    response.status_code = 201
    return {"stored": len(payload.items)}


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
