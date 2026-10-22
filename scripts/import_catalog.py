"""Import ml/data/processed/catalog_export.csv into the products table.

Run from the backend folder (so it finds backend/.env):
    python ..\\scripts\\import_catalog.py
Safe to run more than once: existing items are skipped.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.services.catalog_import import import_products, read_export  # noqa: E402

CSV_PATH = ROOT / "ml" / "data" / "processed" / "catalog_export.csv"

if not CSV_PATH.exists():
    sys.exit(f"{CSV_PATH} not found. Run ml/src/export_catalog.py first.")

with SessionLocal() as db:
    print(import_products(db, read_export(CSV_PATH)))
