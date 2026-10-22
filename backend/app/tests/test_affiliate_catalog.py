"""The affiliate importer maps a real feed and refuses to run without credentials."""
from decimal import Decimal

import pytest

from app.core.config import settings
from app.models import Product
from app.services import affiliate_catalog as aff
from app.tests.conftest import user_headers  # noqa: F401  (keeps the fixture import surface tidy)


def test_it_refuses_to_run_without_credentials(monkeypatch):
    monkeypatch.setattr(settings, "ebay_client_id", None)
    monkeypatch.setattr(settings, "ebay_client_secret", None)
    with pytest.raises(aff.AffiliateError) as err:
        aff.credentials()
    assert "EBAY_CLIENT_ID" in str(err.value)


def test_provider_ids_are_stable_and_cannot_clash_with_other_sources():
    first = aff.source_item_id("v1|1234567890|0")
    assert first == aff.source_item_id("v1|1234567890|0")        # stable
    assert first != aff.source_item_id("v1|9999999999|0")        # distinct
    assert first > 10 ** 9                                        # outside the retailrocket id space
    assert first <= 2 ** 63 - 1                                   # fits a signed BIGINT


def test_an_item_maps_onto_a_product_row():
    row = aff.to_row({
        "itemId": "v1|1234567890|0",
        "title": "Sony WH-1000XM4 Wireless Headphones",
        "itemWebUrl": "https://www.ebay.com/itm/1234567890",
        "image": {"imageUrl": "https://i.ebayimg.com/images/g/abc/s-l500.jpg"},
        "price": {"value": "229.99", "currency": "USD"},
        "categoryPath": "Consumer Electronics|Portable Audio & Headphones|Headphones",
        "condition": "Pre-owned",
        "seller": {"username": "audio-deals"},
    })
    assert row["catalog_source"] == "ebay"
    assert row["price"] == Decimal("229.99") and row["currency"] == "USD"
    assert row["category"] == "Headphones"
    assert row["image_url"].endswith("s-l500.jpg")
    assert row["external_url"] == "https://www.ebay.com/itm/1234567890"
    assert row["stock"] is None                                   # the API does not promise one


def test_an_item_without_a_price_stores_no_price():
    row = aff.to_row({"itemId": "v1|1|0", "title": "Mystery lot",
                      "itemWebUrl": "https://www.ebay.com/itm/1"})
    assert row["price"] is None and row["currency"] is None


def test_the_campaign_id_decorates_the_item_link(monkeypatch):
    monkeypatch.setattr(settings, "affiliate_campaign_id", "5338000000")
    row = aff.to_row({"itemId": "v1|5|0", "title": "Item",
                      "itemWebUrl": "https://www.ebay.com/itm/5?hash=x"})
    assert "campaign_id=5338000000" in row["external_url"]
    assert row["external_url"].startswith("https://www.ebay.com/itm/5?hash=x&")


def test_import_upserts_and_is_idempotent(db, monkeypatch):
    items = [
        {"itemId": "v1|1|0", "title": "Rain shell", "itemWebUrl": "https://www.ebay.com/itm/1",
         "price": {"value": "80.00", "currency": "USD"}, "categoryPath": "Clothing|Jackets"},
        {"itemId": "v1|2|0", "title": "Trail shoes", "itemWebUrl": "https://www.ebay.com/itm/2",
         "price": {"value": "120.00", "currency": "USD"}, "categoryPath": "Clothing|Shoes"},
    ]
    monkeypatch.setattr(aff, "get_access_token", lambda: "token")
    monkeypatch.setattr(aff, "fetch_items", lambda query, limit=50, offset=0, token=None: items)

    first = aff.import_items(db, ["outdoor gear"], per_query=10)
    assert first == {"rows": 2, "inserted": 2, "updated": 0}

    items[0]["price"] = {"value": "70.00", "currency": "USD"}          # a price drop
    again = aff.import_items(db, ["outdoor gear"], per_query=10)
    assert again == {"rows": 2, "inserted": 0, "updated": 2}           # refreshed, not duplicated
    assert db.query(Product).filter(Product.catalog_source == "ebay").count() == 2
    row = db.query(Product).filter(
        Product.source_item_id == aff.source_item_id("v1|1|0")).one()
    assert row.price == Decimal("70.00")
