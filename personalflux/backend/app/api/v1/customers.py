"""Everything here acts on the logged-in customer only. There is no user id in any path:
identity comes from the token, so one customer cannot reach another's data."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.api.deps import Actor, get_current_user
from app.api.v1.auth import COOKIE, _cookie_path
from app.core.security import verify_password
from app.db.session import get_db
from app.models import (Interaction, Product, RecommendationImpression,
                        SavedItem, User)
from app.schemas.auth import UserOut
from app.schemas.customer import (DeleteAccountIn, InferredProfile, PreferencesOut,
                                  PreferencesPatch, SavedOut, SettingsPatch)
from app.schemas.product import ViewedProduct
from app.services import preferences as prefs
from app.services.events import store_event
from app.services.profile import build_inferred_profile

router = APIRouter(prefix="/customers/me", tags=["customer"])

_HISTORY_EVENTS = ["view", "click", "compare", "add_to_cart", "save"]


def _preferences_out(db: Session, user: User) -> PreferencesOut:
    return PreferencesOut(
        explicit=prefs.explicit_prefs(db, Actor(user=user, session_id=None)),
        inferred=InferredProfile(**build_inferred_profile(db, user)),
        profile_reset_at=user.profile_reset_at,
    )


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _preferences_out(db, user)


@router.patch("/preferences", response_model=PreferencesOut)
def update_preferences(payload: PreferencesPatch, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    actor = Actor(user=user, session_id=None)
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
    return _preferences_out(db, user)


@router.delete("/preferences", response_model=PreferencesOut)
def reset_preferences(include_explicit: bool = False, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """Resets what was inferred. Add ?include_explicit=true to also clear stated preferences."""
    prefs.reset(db, Actor(user=user, session_id=None), include_explicit)
    db.commit()
    return _preferences_out(db, user)


@router.patch("/settings", response_model=UserOut)
def update_settings(payload: SettingsPatch, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    user.tracking_consent = payload.tracking_consent
    db.commit()
    db.refresh(user)
    return user


@router.get("/history", response_model=list[ViewedProduct])
def get_history(limit: int = Query(30, ge=1, le=100), user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    last_seen = func.max(Interaction.occurred_at).label("last_seen")
    rows = db.execute(
        select(Product, last_seen).join(Interaction, Interaction.product_id == Product.id)
        .where(Interaction.user_id == user.id, Interaction.event_type.in_(_HISTORY_EVENTS))
        .group_by(Product.id).order_by(last_seen.desc()).limit(limit)
    ).all()
    return [ViewedProduct(product=p, last_seen=ts) for p, ts in rows]


@router.delete("/history", status_code=204)
def clear_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(delete(Interaction).where(Interaction.user_id == user.id))
    db.execute(delete(RecommendationImpression).where(RecommendationImpression.user_id == user.id))
    db.commit()


@router.delete("/history/{product_id}", status_code=204)
def remove_from_history(product_id: uuid.UUID, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    db.execute(delete(Interaction).where(Interaction.user_id == user.id,
                                         Interaction.product_id == product_id))
    db.commit()


@router.get("/saved", response_model=list[SavedOut])
def list_saved(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Product, SavedItem.created_at).join(SavedItem, SavedItem.product_id == Product.id)
        .where(SavedItem.user_id == user.id).order_by(SavedItem.created_at.desc())
    ).all()
    return [SavedOut(product=p, saved_at=ts) for p, ts in rows]


@router.put("/saved/{product_id}", status_code=204)
def save_item(product_id: uuid.UUID, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if p is None or not p.is_active:
        raise HTTPException(status_code=404, detail="Product not found.")
    db.execute(pg_insert(SavedItem).values(user_id=user.id, product_id=p.id)
               .on_conflict_do_nothing())
    db.commit()
    # A save is also a signal for recommendations, but only if tracking is on.
    store_event(db, Actor(user=user, session_id=None), event_type="save", product_id=p.id,
                occurred_at=None, context={"source": "saved_items"}, idempotency_key=None)


@router.delete("/saved/{product_id}", status_code=204)
def unsave_item(product_id: uuid.UUID, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    db.execute(delete(SavedItem).where(SavedItem.user_id == user.id,
                                       SavedItem.product_id == product_id))
    db.commit()


@router.get("/export")
def export_my_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Everything stored about the logged-in customer (up to 5000 recent events)."""
    events = db.execute(
        select(Interaction.event_type, Interaction.product_id, Interaction.occurred_at,
               Interaction.context)
        .where(Interaction.user_id == user.id).order_by(Interaction.occurred_at.desc()).limit(5000)
    ).all()
    saved = db.scalars(select(SavedItem.product_id).where(SavedItem.user_id == user.id)).all()
    prefs = _preferences_out(db, user)
    body = {
        "profile": UserOut.model_validate(user).model_dump(),
        "preferences": prefs.model_dump(),
        "saved_product_ids": list(saved),
        "events": [{"event_type": e, "product_id": p, "occurred_at": t, "context": c}
                   for e, p, t, c in events],
    }
    return JSONResponse(jsonable_encoder(body))


@router.post("/delete", status_code=204)
def delete_account(payload: DeleteAccountIn, response: Response,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deletes the account. Events, preferences, saved items, impressions and sessions are
    removed by database cascade. Password confirmation is required."""
    if not verify_password(user.password_hash, payload.password):
        raise HTTPException(status_code=403, detail="Incorrect password.")
    db.delete(user)
    db.commit()
    response.delete_cookie(COOKIE, path=_cookie_path())
