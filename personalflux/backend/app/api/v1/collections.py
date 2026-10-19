"""A customer's lists.

As everywhere else under /customers/me, the customer comes from the token and
never from the path, so one account cannot reach another's lists: someone else's
list is reported as missing rather than forbidden, which also avoids confirming
that it exists.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.api.deps import Actor, get_current_user
from app.db.session import get_db
from app.models import Collection, CollectionItem, Product, User
from app.schemas.collection import CollectionDetail, CollectionIn, CollectionOut
from app.services.events import store_event

router = APIRouter(prefix="/customers/me/collections", tags=["collections"])

MAX_LISTS = 20
MAX_ITEMS = 100


def _owned(db: Session, user: User, collection_id: uuid.UUID) -> Collection:
    c = db.get(Collection, collection_id)
    if c is None or c.user_id != user.id:
        raise HTTPException(status_code=404, detail="List not found.")
    return c


def _name_taken(db: Session, user: User, name: str, exclude: uuid.UUID | None = None) -> bool:
    q = select(func.count()).select_from(Collection).where(
        Collection.user_id == user.id, Collection.name == name)
    if exclude is not None:
        q = q.where(Collection.id != exclude)
    return bool(db.scalar(q))


def _count(db: Session, collection_id: uuid.UUID) -> int:
    return db.scalar(select(func.count()).select_from(CollectionItem)
                     .where(CollectionItem.collection_id == collection_id)) or 0


def _out(c: Collection, count: int) -> CollectionOut:
    return CollectionOut(id=c.id, name=c.name, item_count=count,
                         created_at=c.created_at, updated_at=c.updated_at)


def _touch(c: Collection) -> None:
    """Bump updated_at by hand: the change happened on the other table."""
    c.updated_at = datetime.now(timezone.utc)


@router.get("", response_model=list[CollectionOut])
def list_collections(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Collection).where(Collection.user_id == user.id)
                      .order_by(Collection.created_at)).all()
    counts = dict(db.execute(
        select(CollectionItem.collection_id, func.count())
        .where(CollectionItem.collection_id.in_([c.id for c in rows]))
        .group_by(CollectionItem.collection_id)
    ).all()) if rows else {}
    return [_out(c, counts.get(c.id, 0)) for c in rows]


@router.post("", response_model=CollectionOut, status_code=201)
def create_collection(payload: CollectionIn, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    held = db.scalar(select(func.count()).select_from(Collection)
                     .where(Collection.user_id == user.id)) or 0
    if held >= MAX_LISTS:
        raise HTTPException(status_code=409, detail=f"You can keep up to {MAX_LISTS} lists.")
    if _name_taken(db, user, payload.name):
        raise HTTPException(status_code=409, detail="You already have a list with that name.")
    c = Collection(user_id=user.id, name=payload.name)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _out(c, 0)


@router.get("/{collection_id}", response_model=CollectionDetail)
def get_collection(collection_id: uuid.UUID, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    c = _owned(db, user, collection_id)
    items = db.scalars(
        select(Product).join(CollectionItem, CollectionItem.product_id == Product.id)
        .where(CollectionItem.collection_id == c.id)
        .order_by(CollectionItem.added_at.desc(), Product.id)
    ).all()
    return CollectionDetail(id=c.id, name=c.name, items=items,
                            created_at=c.created_at, updated_at=c.updated_at)


@router.patch("/{collection_id}", response_model=CollectionOut)
def rename_collection(collection_id: uuid.UUID, payload: CollectionIn,
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _owned(db, user, collection_id)
    if payload.name != c.name and _name_taken(db, user, payload.name, exclude=c.id):
        raise HTTPException(status_code=409, detail="You already have a list with that name.")
    c.name = payload.name
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return _out(c, _count(db, c.id))


@router.delete("/{collection_id}", status_code=204)
def delete_collection(collection_id: uuid.UUID, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """Deletes the list and its entries. The products themselves are untouched."""
    c = _owned(db, user, collection_id)
    db.delete(c)
    db.commit()


@router.put("/{collection_id}/items/{product_id}", status_code=204)
def add_item(collection_id: uuid.UUID, product_id: uuid.UUID,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _owned(db, user, collection_id)
    p = db.get(Product, product_id)
    if p is None or not p.is_active:
        raise HTTPException(status_code=404, detail="Product not found.")
    if _count(db, c.id) >= MAX_ITEMS:
        raise HTTPException(status_code=409, detail=f"A list holds up to {MAX_ITEMS} products.")

    # RETURNING yields a row only on a real insert, so a product already on the
    # list changes nothing and is not recorded as a second signal.
    inserted = db.execute(
        pg_insert(CollectionItem).values(collection_id=c.id, product_id=p.id)
        .on_conflict_do_nothing()
        .returning(CollectionItem.product_id)
    ).scalar()
    if inserted is None:
        return
    _touch(c)
    db.commit()
    store_event(db, Actor(user=user, session_id=None), event_type="save", product_id=p.id,
                occurred_at=None, context={"source": "collection"}, idempotency_key=None)


@router.delete("/{collection_id}/items/{product_id}", status_code=204)
def remove_item(collection_id: uuid.UUID, product_id: uuid.UUID,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _owned(db, user, collection_id)
    db.execute(delete(CollectionItem).where(CollectionItem.collection_id == c.id,
                                            CollectionItem.product_id == product_id))
    _touch(c)
    db.commit()
