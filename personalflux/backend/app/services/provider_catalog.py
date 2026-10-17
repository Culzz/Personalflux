"""Import a catalog from a public product API into the products table.

DummyJSON is a free, keyless demo store: realistic photos, prices and stock,
but not real brands. Rows are namespaced and upserted by ``source_item_id``,
so running this again refreshes price and stock instead of duplicating rows.

The mapping is deliberately small. eBay Browse (or another provider) can be
added behind the same shape: fetch items, map each to a row, upsert.
"""
import uuid
from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Product

DUMMYJSON_BASE = "https://dummyjson.com"
SOURCE_BASE = 800_000          # namespaced so ids never clash with other providers
CURRENCY = "USD"

_UPDATE_COLS = ("title", "description", "category", "price", "image_url",
                "brand", "stock", "currency", "external_url", "catalog_source", "is_active")


def fetch_products(limit: int = 100, base: str = DUMMYJSON_BASE, timeout: float = 15.0) -> list[dict]:
    """Fetch products from the provider. Network is the only side effect."""
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(f"{base}/products", params={"limit": limit, "skip": 0})
        resp.raise_for_status()
        return resp.json().get("products", [])


def _decimal(value) -> Decimal | None:
    try:
        return Decimal(str(value)) if value is not None else None
    except (InvalidOperation, ValueError):
        return None


def to_row(item: dict) -> dict:
    """Map one DummyJSON product onto a products row."""
    item_id = int(item["id"])
    images = item.get("images") or []
    raw_stock = item.get("stock")
    stock = int(raw_stock) if isinstance(raw_stock, (int, float)) else None
    category = (item.get("category") or "").strip()
    return {
        "id": uuid.uuid4(),
        "source_item_id": SOURCE_BASE + item_id,
        "catalog_source": "dummyjson",
        "title": item.get("title") or f"DummyJSON item {item_id}",
        "description": item.get("description"),
        "category": category.title() if category else None,
        "price": _decimal(item.get("price")),
        "image_url": item.get("thumbnail") or (images[0] if images else None),
        "brand": item.get("brand"),
        "stock": stock,
        "currency": CURRENCY,
        "external_url": f"{DUMMYJSON_BASE}/products/{item_id}",
        # An out-of-stock item stays in the catalog but is not recommended.
        "is_active": stock > 0 if stock is not None else True,
    }


def upsert_products(db: Session, rows: list[dict]) -> dict:
    """Insert new rows and refresh existing ones (matched on source_item_id)."""
    if not rows:
        return {"rows": 0, "inserted": 0, "updated": 0}
    ids = [r["source_item_id"] for r in rows]
    known = set(db.scalars(select(Product.source_item_id).where(Product.source_item_id.in_(ids))))
    stmt = pg_insert(Product.__table__).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["source_item_id"],
        set_={c: stmt.excluded[c] for c in _UPDATE_COLS} | {"updated_at": func.now()},
    )
    db.execute(stmt)
    db.commit()
    inserted = sum(1 for i in ids if i not in known)
    return {"rows": len(rows), "inserted": inserted, "updated": len(rows) - inserted}
