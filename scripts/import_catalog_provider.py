"""Import products from the DummyJSON demo store.

Run from the backend folder (so it finds backend/.env):
    python ..\\scripts\\import_catalog_provider.py [limit]

Safe to run more than once: existing items are refreshed, not duplicated.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.services.provider_catalog import fetch_products, to_row, upsert_products  # noqa: E402

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100

with SessionLocal() as db:
    items = fetch_products(limit)
    print(f"fetched {len(items)}: {upsert_products(db, [to_row(i) for i in items])}")
