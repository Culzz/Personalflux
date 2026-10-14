"""Load catalog rows into the products table. Safe to run more than once."""
import csv
import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Product

BATCH = 2000


def build_product_row(source_item_id: int, category_id: str | None) -> dict:
    """One products row. Fields the dataset does not have stay missing."""
    cat = (category_id or "").strip()
    return {
        "id": uuid.uuid4(),
        "source_item_id": source_item_id,
        "catalog_source": "retailrocket",
        "title": f"Retailrocket item {source_item_id}",
        "category": f"Category {cat}" if cat else None,
        "is_active": True,
    }


def read_export(path: Path):
    """Yield product rows from the CSV written by ml/src/export_catalog.py."""
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            yield build_product_row(int(row["source_item_id"]), row.get("category_id"))


def _flush(db: Session, batch: list[dict]) -> None:
    stmt = insert(Product.__table__).values(batch)
    db.execute(stmt.on_conflict_do_nothing(index_elements=["source_item_id"]))
    db.commit()


def import_products(db: Session, rows) -> dict:
    before = db.scalar(select(func.count()).select_from(Product))
    batch, read = [], 0
    for row in rows:
        batch.append(row)
        read += 1
        if len(batch) >= BATCH:
            _flush(db, batch)
            batch = []
    if batch:
        _flush(db, batch)
    after = db.scalar(select(func.count()).select_from(Product))
    return {
        "rows_read": read,
        "inserted": after - before,
        "skipped_existing": read - (after - before),
    }
