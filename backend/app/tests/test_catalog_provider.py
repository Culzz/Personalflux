from decimal import Decimal

from sqlalchemy import select

from app.models import Product
from app.services import provider_catalog as pc


def sample(**over) -> dict:
    item = {
        "id": 7, "title": "Stoneware Mug", "description": "A hand-glazed mug.",
        "category": "kitchen", "price": 9.99, "stock": 12, "brand": "Acme",
        "thumbnail": "https://cdn.example/mug.jpg", "images": ["https://cdn.example/mug.jpg"],
    }
    item.update(over)
    return item


def test_row_maps_provider_fields():
    row = pc.to_row(sample())
    assert row["catalog_source"] == "dummyjson"
    assert row["source_item_id"] == pc.SOURCE_BASE + 7       # namespaced
    assert row["price"] == Decimal("9.99")
    assert row["brand"] == "Acme" and row["stock"] == 12 and row["currency"] == "USD"
    assert row["category"] == "Kitchen"                       # title-cased for display
    assert row["external_url"].endswith("/products/7")
    assert row["is_active"] is True


def test_out_of_stock_is_kept_but_not_active():
    row = pc.to_row(sample(stock=0, thumbnail=None))
    assert row["stock"] == 0 and row["is_active"] is False
    assert row["image_url"] == "https://cdn.example/mug.jpg"   # falls back to the first image


def test_import_is_idempotent_and_refreshes_price_and_stock(db):
    pc.upsert_products(db, [pc.to_row(sample(price=10.0, stock=5))])
    result = pc.upsert_products(db, [pc.to_row(sample(price=8.0, stock=0))])
    assert result["inserted"] == 0 and result["updated"] == 1

    rows = db.scalars(select(Product).where(Product.catalog_source == "dummyjson")).all()
    assert len(rows) == 1                                      # updated, not duplicated
    assert rows[0].price == Decimal("8.00")
    assert rows[0].stock == 0 and rows[0].is_active is False
