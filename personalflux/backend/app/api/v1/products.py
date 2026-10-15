import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user, require_roles
from app.db.session import get_db
from app.models import Product, User
from app.schemas.product import (CategoryCount, ProductCreate, ProductOut, ProductPage,
                                 ProductUpdate)
from app.services import audit

router = APIRouter(prefix="/products", tags=["catalog"])

Sort = Literal["newest", "price_asc", "price_desc", "title"]


def _like(text: str) -> str:
    """Escape LIKE wildcards so a customer typing % or _ searches for those characters."""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _is_admin(user: User | None) -> bool:
    return user is not None and user.role == "admin"


@router.get("", response_model=ProductPage)
def list_products(
    q: str | None = Query(None, max_length=100),
    category: str | None = Query(None, max_length=100),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    sort: Sort = "newest",
    page: int = Query(1, ge=1, le=10_000),
    page_size: int = Query(20, ge=1, le=50),
    include_inactive: bool = False,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if include_inactive and not _is_admin(user):
        raise HTTPException(status_code=403 if user else 401,
                            detail="Only administrators can list inactive products.")
    stmt = select(Product)
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    if q and q.strip():
        pat = _like(q.strip())
        stmt = stmt.where(or_(Product.title.ilike(pat, escape="\\"),
                              Product.category.ilike(pat, escape="\\")))
    if category:
        stmt = stmt.where(Product.category == category)
    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = {
        "newest": [Product.created_at.desc()],
        "price_asc": [Product.price.asc().nulls_last()],
        "price_desc": [Product.price.desc().nulls_last()],
        "title": [Product.title.asc()],
    }[sort]
    items = db.scalars(stmt.order_by(*order, Product.id)
                       .offset((page - 1) * page_size).limit(page_size)).all()
    return ProductPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/categories", response_model=list[CategoryCount])
def list_categories(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Product.category, func.count().label("n"))
        .where(Product.is_active.is_(True), Product.category.is_not(None))
        .group_by(Product.category).order_by(func.count().desc(), Product.category)
    ).all()
    return [CategoryCount(category=c, products=n) for c, n in rows]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, user: User | None = Depends(get_optional_user),
                db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if p is None or (not p.is_active and not _is_admin(user)):
        raise HTTPException(status_code=404, detail="Product not found.")
    return p


@router.get("/{product_id}/related", response_model=list[ProductOut])
def related_products(product_id: uuid.UUID, limit: int = Query(8, ge=1, le=24),
                     db: Session = Depends(get_db)):
    """Catalog relation (same category). The learned model lives under /recommendations."""
    p = db.get(Product, product_id)
    if p is None or not p.is_active:
        raise HTTPException(status_code=404, detail="Product not found.")
    if p.category is None:
        return []
    return db.scalars(
        select(Product).where(Product.is_active.is_(True), Product.category == p.category,
                              Product.id != p.id)
        .order_by(Product.created_at.desc(), Product.id).limit(limit)
    ).all()


@router.post("", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate, admin: User = Depends(require_roles("admin")),
                   db: Session = Depends(get_db)):
    p = Product(**payload.model_dump(), catalog_source="admin")
    db.add(p)
    db.flush()
    audit.record(db, admin.id, "product.create", "product", str(p.id))
    db.commit()
    db.refresh(p)
    return p


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: uuid.UUID, payload: ProductUpdate,
                   admin: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    changes = payload.model_dump(exclude_unset=True)
    if "title" in changes and changes["title"] is None:
        raise HTTPException(status_code=422, detail="title cannot be null.")
    if "is_active" in changes and changes["is_active"] is None:
        raise HTTPException(status_code=422, detail="is_active cannot be null.")
    for field, value in changes.items():
        setattr(p, field, value)
    audit.record(db, admin.id, "product.update", "product", str(p.id),
                 {"fields": sorted(changes)})
    db.commit()
    db.refresh(p)
    return p
