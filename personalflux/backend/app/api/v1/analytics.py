"""Aggregated, live activity for analysts. No endpoint here returns an individual's data."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import Interaction, Product, RecommendationImpression, User

router = APIRouter(prefix="/analytics", tags=["analytics"],
                   dependencies=[Depends(require_roles("analyst", "admin"))])

LIVE_NOTE = "Live activity recorded by this application. Not an offline model evaluation."


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


@router.get("/overview")
def overview(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    since = _since(days)
    by_type = dict(db.execute(
        select(Interaction.event_type, func.count()).where(Interaction.occurred_at >= since)
        .group_by(Interaction.event_type)).all())
    return {
        "kind": "live_activity", "note": LIVE_NOTE, "window_days": days,
        "customers_total": db.scalar(select(func.count()).select_from(User)),
        "customers_with_tracking_consent": db.scalar(
            select(func.count()).select_from(User).where(User.tracking_consent.is_(True))),
        "products_active": db.scalar(select(func.count()).select_from(Product)
                                     .where(Product.is_active.is_(True))),
        "products_inactive": db.scalar(select(func.count()).select_from(Product)
                                       .where(Product.is_active.is_(False))),
        "events_by_type": by_type,
        "events_total": sum(by_type.values()),
        "active_customers": db.scalar(select(func.count(func.distinct(Interaction.user_id)))
                                      .where(Interaction.occurred_at >= since)),
        "anonymous_sessions": db.scalar(select(func.count(func.distinct(Interaction.session_id)))
                                        .where(Interaction.occurred_at >= since,
                                               Interaction.user_id.is_(None))),
        "impressions": db.scalar(select(func.count()).select_from(RecommendationImpression)
                                 .where(RecommendationImpression.created_at >= since)),
    }


@router.get("/categories")
def categories(days: int = Query(30, ge=1, le=365), limit: int = Query(20, ge=1, le=100),
               db: Session = Depends(get_db)):
    def n(event):
        return func.count().filter(Interaction.event_type == event)
    rows = db.execute(
        select(Product.category, func.count().label("events"), n("view").label("views"),
               n("add_to_cart").label("add_to_cart"), n("purchase").label("purchases"))
        .join(Product, Interaction.product_id == Product.id)
        .where(Interaction.occurred_at >= _since(days), Product.category.is_not(None))
        .group_by(Product.category).order_by(func.count().desc()).limit(limit)
    ).all()
    return {"kind": "live_activity", "note": LIVE_NOTE, "window_days": days,
            "categories": [dict(category=c, events=e, views=v, add_to_cart=a, purchases=p)
                           for c, e, v, a, p in rows]}


@router.get("/segments")
def segments(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Behavioural segments by activity level, as counts only."""
    per_user = (select(Interaction.user_id, func.count().label("n"))
                .where(Interaction.occurred_at >= _since(days), Interaction.user_id.is_not(None))
                .group_by(Interaction.user_id).subquery())
    bucket = case((per_user.c.n <= 5, "light (1-5 events)"),
                  (per_user.c.n <= 20, "regular (6-20 events)"), else_="heavy (21+ events)")
    rows = db.execute(select(bucket, func.count()).group_by(bucket)).all()
    return {"kind": "live_activity", "note": LIVE_NOTE, "window_days": days,
            "segments": [{"segment": s, "customers": c} for s, c in rows]}


@router.get("/recommendations")
def recommendation_performance(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Recommendation performance for merchants.

    Every number is computed from stored impressions and events, and every label
    below states how it is defined. No model-quality claim is made here: this is
    live activity, not the offline evaluation, which lives under /ml/experiments.
    """
    since = _since(days)

    impressions = db.scalar(select(func.count()).select_from(RecommendationImpression)
                            .where(RecommendationImpression.created_at >= since)) or 0
    requests = db.scalar(select(func.count(func.distinct(RecommendationImpression.request_id)))
                         .where(RecommendationImpression.created_at >= since)) or 0
    distinct_shown = db.scalar(select(func.count(func.distinct(RecommendationImpression.product_id)))
                               .where(RecommendationImpression.created_at >= since)) or 0
    active_products = db.scalar(select(func.count()).select_from(Product)
                                .where(Product.is_active.is_(True))) or 0

    by_version = dict(db.execute(
        select(RecommendationImpression.model_version, func.count())
        .where(RecommendationImpression.created_at >= since)
        .group_by(RecommendationImpression.model_version)).all())

    engaged = dict(db.execute(
        select(Interaction.event_type, func.count())
        .where(Interaction.occurred_at >= since,
               Interaction.context["source"].as_string() == "recommendation")
        .group_by(Interaction.event_type)).all())

    # A click is *attributed* when it names an impression that was really stored.
    attributed = db.scalar(
        select(func.count()).select_from(Interaction)
        .where(Interaction.occurred_at >= since, Interaction.event_type == "click",
               Interaction.impression_id.is_not(None),
               Interaction.impression_id.in_(
                   select(RecommendationImpression.impression_id)
                   .where(RecommendationImpression.created_at >= since)))) or 0
    clicks = engaged.get("click", 0)
    fallback_impressions = by_version.get(None, 0)

    return {
        "kind": "live_activity", "note": LIVE_NOTE, "window_days": days,
        "impressions": impressions,
        "recommendation_requests_with_impressions": requests,
        "distinct_products_shown": distinct_shown,
        "impressions_per_request": round(impressions / requests, 2) if requests else None,
        "catalogue_coverage_ratio": round(distinct_shown / active_products, 4) if active_products else None,
        "impressions_by_model_version": {str(k): v for k, v in by_version.items()},
        "fallback_impressions": fallback_impressions,
        "fallback_rate": round(fallback_impressions / impressions, 4) if impressions else None,
        "engagement_from_recommendations": engaged,
        "clicks_from_recommendations": clicks,
        "attributed_clicks": attributed,
        "click_through_rate": round(clicks / impressions, 4) if impressions else None,
        "definitions": {
            "impression": "a product that was displayed to a person (at least half the card, "
                          "on screen for a short dwell), not merely returned by the API",
            "recommendation_requests_with_impressions": "distinct recommendation requests that "
                                                        "produced at least one impression",
            "catalogue_coverage_ratio": "distinct products shown / active products",
            "click_through_rate": "clicks from recommendations / impressions",
            "attributed_clicks": "clicks whose impression id matches a stored impression, so the "
                                 "request and model version behind the click are known",
            "fallback_rate": "impressions with no model version / all impressions; these were "
                             "served by database popularity while the model was unavailable",
            "sample_size_caveat": "small windows can move sharply; read the absolute counts, "
                                  "not only the ratios",
        },
    }
