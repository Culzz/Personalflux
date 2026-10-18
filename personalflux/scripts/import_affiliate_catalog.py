"""Import a live affiliate catalogue from the eBay Browse API.

Run from the backend folder (so it finds backend/.env):
    python ..\\scripts\\import_affiliate_catalog.py "wireless headphones" "running shoes"

Needs EBAY_CLIENT_ID and EBAY_CLIENT_SECRET. Optionally set AFFILIATE_CAMPAIGN_ID
to decorate the item links with your eBay Partner Network campaign.

Safe to run more than once: items are matched on source_item_id and refreshed,
never duplicated. Items that leave the feed keep their rows; mark them inactive
by hand or add a retirement rule when you have a stable feed to compare against.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.services.affiliate_catalog import AffiliateError, import_items  # noqa: E402

queries = sys.argv[1:] or ["wireless headphones"]
per_query = 50

try:
    with SessionLocal() as db:
        result = import_items(db, queries, per_query=per_query)
except AffiliateError as e:
    print(f"cannot import: {e}")
    raise SystemExit(1)

print(f"{len(queries)} queried: {result}")
