"""Model scores -> database rules -> grounded explanations.

Fallback hierarchy (SRS 7.7):
  1. personalised hybrid   (current-session signal + older-history signal)
  2. session-based / history-based (only one signal exists)
  3. popularity in the requested or preferred category
  4. plain popularity, then database popularity if no model is loaded
A ranking score is NOT a purchase probability, and scores from different
sources (similarity vs popularity) are not comparable with each other.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import Actor
from app.ml.registry import registry
from app.models import Interaction, Preference, Product
from app.services.profile import EVENT_WEIGHTS

logger = logging.getLogger("personaflux")

SESSION_WINDOW = timedelta(minutes=30)   # what counts as "this session"
CONTEXT_ITEMS = 10
HISTORY_ITEMS = 50
BETA = 0.5                               # weight of older history (the evaluated setting)
N_CANDIDATES = 300
CONTEXT_EVENTS = {"view", "click", "compare", "save", "add_to_cart"}


@dataclass
class Rec:
    product: Product
    score: float
    source: str                  # similarity | popularity | popularity_fallback
    reason_codes: list[str]
    explanation: str


@dataclass
class RecResult:
    items: list[Rec]
    strategy: str
    model_version: str | None
    fallback_used: bool


@dataclass
class Signals:
    ctx: list[tuple] = field(default_factory=list)     # (product_id, source_item_id, title)
    hist: dict[int, float] = field(default_factory=dict)
    exclude_pids: set = field(default_factory=set)
    liked: set = field(default_factory=set)
    blocked: set = field(default_factory=set)
    price_range: dict | None = None


def _explicit_prefs(db: Session, user) -> dict:
    if user is None:
        return {}
    rows = db.scalars(select(Preference).where(
        Preference.user_id == user.id, Preference.source == "explicit")).all()
    return {r.preference_type: r.preference_value for r in rows}


def gather_signals(db: Session, actor: Actor, now: datetime) -> Signals:
    sig = Signals()
    prefs = _explicit_prefs(db, actor.user)
    sig.liked = set(prefs.get("liked_categories") or [])
    sig.blocked = set(prefs.get("blocked_categories") or [])
    sig.price_range = prefs.get("price_range")

    conds = []
    if actor.user is not None:
        conds.append(Interaction.user_id == actor.user.id)
    if actor.session_id:
        conds.append(Interaction.session_id == actor.session_id)
    if not conds:
        return sig

    q = (select(Interaction.event_type, Interaction.occurred_at, Product.id,
                Product.source_item_id, Product.title)
         .join(Product, Interaction.product_id == Product.id)
         .where(or_(*conds), Interaction.event_type.in_(list(EVENT_WEIGHTS) + ["dismiss"])))
    if actor.user is not None and actor.user.profile_reset_at is not None:
        q = q.where(Interaction.occurred_at >= actor.user.profile_reset_at)
    rows = db.execute(q.order_by(Interaction.occurred_at.desc()).limit(500)).all()

    ctx_seen = set()
    for r in rows:                                   # newest first
        if r.event_type == "dismiss":
            sig.exclude_pids.add(r.id)
            continue
        if r.event_type == "purchase":
            sig.exclude_pids.add(r.id)
        if r.source_item_id is None:
            continue
        in_session = (now - r.occurred_at) <= SESSION_WINDOW
        if in_session and r.event_type in CONTEXT_EVENTS:
            if r.id not in ctx_seen and len(sig.ctx) < CONTEXT_ITEMS:
                ctx_seen.add(r.id)
                sig.ctx.append((r.id, r.source_item_id, r.title))
            continue
        w = EVENT_WEIGHTS[r.event_type]
        if r.source_item_id in sig.hist or len(sig.hist) < HISTORY_ITEMS:
            sig.hist[r.source_item_id] = max(sig.hist.get(r.source_item_id, 0.0), w)
    sig.exclude_pids |= ctx_seen
    return sig


def _allowed(p: Product, sig: Signals, category: str | None) -> bool:
    if p.id in sig.exclude_pids:
        return False
    if p.category is not None and p.category in sig.blocked:
        return False
    if category is not None and p.category != category:
        return False
    pr = sig.price_range
    if pr and p.price is not None:
        if pr.get("min") is not None and p.price < Decimal(str(pr["min"])):
            return False
        if pr.get("max") is not None and p.price > Decimal(str(pr["max"])):
            return False
    return True


def _products_by_source(db: Session, source_ids) -> dict[int, Product]:
    ids = list(source_ids)
    if not ids:
        return {}
    rows = db.scalars(select(Product).where(
        Product.source_item_id.in_(ids), Product.is_active.is_(True))).all()
    return {p.source_item_id: p for p in rows}


def _db_popular(db: Session, sig: Signals, category: str | None, need: int,
                used: set, source: str) -> list[Rec]:
    """No-model fallback: most-interacted active products, then newest."""
    since = datetime.now(timezone.utc) - timedelta(days=14)
    counts = (select(Interaction.product_id.label("pid"), func.count().label("n"))
              .where(Interaction.occurred_at >= since, Interaction.product_id.is_not(None))
              .group_by(Interaction.product_id).subquery())
    n_col = func.coalesce(counts.c.n, 0)
    q = (select(Product, n_col).outerjoin(counts, counts.c.pid == Product.id)
         .where(Product.is_active.is_(True)))
    if category is not None:
        q = q.where(Product.category == category)
    q = q.order_by(n_col.desc(), Product.created_at.desc(), Product.id).limit(200)
    out = []
    for p, n in db.execute(q).all():
        if p.id in used or not _allowed(p, sig, category):
            continue
        if n > 0:
            reasons = ["popular_in_category" if category else "popular"]
            expl = ("Popular in the category you are exploring." if category
                    else "Popular with other shoppers.")
        else:
            reasons, expl = ["catalog_default"], "From our catalog."
        out.append(Rec(p, 0.0, source, reasons, expl))
        if len(out) == need:
            break
    return out


def _popular(db: Session, sig: Signals, category: str | None, need: int,
             used: set, source: str) -> list[Rec]:
    out: list[Rec] = []
    model = registry.model
    if model is not None and need > 0:
        prods = _products_by_source(db, model.ranked)
        ordered = [prods[i] for i in model.ranked if i in prods]
        if category is None and sig.liked:       # stable sort: liked categories first
            ordered.sort(key=lambda p: 0 if p.category in sig.liked else 1)
        for p in ordered:
            if p.id in used or not _allowed(p, sig, category):
                continue
            if category is not None and p.category == category:
                reasons, expl = ["popular_in_category"], "Popular in the category you are exploring."
            elif p.category in sig.liked:
                reasons, expl = ["popular", "matches_stated_preference"], "Popular in a category you said you like."
            else:
                reasons, expl = ["popular"], "Popular with other shoppers."
            out.append(Rec(p, round(model.score_map.get(p.source_item_id, 0.0), 4),
                           source, reasons, expl))
            if len(out) == need:
                break
    if len(out) < need:
        used2 = used | {r.product.id for r in out}
        out += _db_popular(db, sig, category, need - len(out), used2, source)
    return out


def recommend_home(db: Session, actor: Actor, limit: int, category: str | None = None) -> RecResult:
    now = datetime.now(timezone.utc)
    model = registry.model
    sig = gather_signals(db, actor, now)
    results: list[Rec] = []
    strategy = "popularity"

    if model is not None:
        s = model.score_session([c[1] for c in sig.ctx]) if sig.ctx else {}
        l = model.score_history(sig.hist) if sig.hist else {}
        combined = dict(s)
        for item, v in l.items():
            combined[item] = combined.get(item, 0.0) + BETA * v
        if combined:
            ranked_ids = sorted(combined, key=combined.get, reverse=True)[:N_CANDIDATES]
            prods = _products_by_source(db, ranked_ids)
            ctx_src = [c[1] for c in sig.ctx]
            titles = {c[1]: c[2] for c in sig.ctx}
            for sid in ranked_ids:
                p = prods.get(sid)
                if p is None or not _allowed(p, sig, category):
                    continue
                reasons, expl = [], ""
                if sid in s:
                    reasons.append("similar_to_session_items")
                    link = model.strongest_link(sid, ctx_src)
                    expl = (f'Similar to "{titles[link]}", which you looked at recently.'
                            if link in titles else "Similar to items you looked at recently.")
                if sid in l:
                    reasons.append("similar_to_history")
                    if not expl:
                        expl = "Similar to items you have interacted with before."
                if p.category is not None and p.category in sig.liked:
                    reasons.append("matches_stated_preference")
                results.append(Rec(p, round(combined[sid], 4), "similarity", reasons, expl))
                if len(results) == limit:
                    break
            if results:
                strategy = ("personalized_hybrid" if (s and l)
                            else "session_based" if s else "history_based")

    if len(results) < limit:
        used = {r.product.id for r in results}
        results += _popular(db, sig, category, limit - len(results), used, "popularity_fallback")

    return RecResult(
        items=results, strategy=strategy,
        model_version=model.version if model else None,
        fallback_used=any(r.source == "popularity_fallback" for r in results),
    )


def recommend_home_safe(db: Session, actor: Actor, limit: int,
                        category: str | None = None) -> RecResult:
    """Never fails the page: if ranking breaks, serve a safe database fallback."""
    try:
        return recommend_home(db, actor, limit, category)
    except Exception:
        logger.exception("personalised ranking failed; serving database fallback")
        db.rollback()
        try:
            sig = gather_signals(db, actor, datetime.now(timezone.utc))
        except Exception:
            db.rollback()
            sig = Signals()
        items = _db_popular(db, sig, category, limit, set(), "popularity_fallback")
        return RecResult(items=items, strategy="popularity", model_version=None, fallback_used=True)


def recommend_similar(db: Session, product: Product, limit: int) -> RecResult:
    model = registry.model
    results: list[Rec] = []
    if model is not None and product.source_item_id is not None and model.has_item(product.source_item_id):
        cands = model.similar_items(product.source_item_id, k=N_CANDIDATES)
        prods = _products_by_source(db, [c[0] for c in cands])
        top = cands[0][1] if cands else 1.0
        for sid, score in cands:
            p = prods.get(sid)
            if p is None or p.id == product.id:
                continue
            results.append(Rec(p, round(score / top, 4), "similarity", ["item_similarity"],
                               f'Often looked at together with "{product.title}".'))
            if len(results) == limit:
                break
    if len(results) < limit:
        used = {product.id} | {r.product.id for r in results}
        results += _popular(db, Signals(), product.category, limit - len(results),
                            used, "popularity_fallback")
    return RecResult(
        items=results,
        strategy="item_similarity" if any(r.source == "similarity" for r in results) else "popularity",
        model_version=model.version if model else None,
        fallback_used=any(r.source == "popularity_fallback" for r in results),
    )


def recommend_trending(db: Session, limit: int, category: str | None = None) -> RecResult:
    model = registry.model
    items = _popular(db, Signals(), category, limit, set(), "popularity")
    return RecResult(items=items, strategy="popularity",
                     model_version=model.version if model else None, fallback_used=False)
