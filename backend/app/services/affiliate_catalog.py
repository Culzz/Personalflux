"""Import a real affiliate catalogue from the eBay Browse API.

Credentials come from the environment (`EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`).
Item ids are hashed into their own 56-bit namespace so they never collide with
another source, and rows are upserted by `source_item_id`, so re-running
refreshes price, image and availability instead of duplicating rows.

Nothing here invents data. With no credentials the importer raises, and with an
item that carries no price it stores no price. The affiliate link is the item's
own URL, optionally decorated with your campaign id.
"""
import hashlib
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.provider_catalog import upsert_products

EBAY_API = "https://api.ebay.com"
TOKEN_URL = f"{EBAY_API}/identity/v1/oauth2/token"
SEARCH_URL = f"{EBAY_API}/buy/browse/v1/item_summary/search"

# A distinct namespace: a 56-bit hash of the provider id. It cannot reach the
# small ids the Retailrocket importer uses, and it fits a signed BIGINT.
SOURCE_PREFIX = "ebay"
_MAX_BIGINT = 2 ** 63 - 1


class AffiliateError(Exception):
    """Raised when the feed cannot be used, with a message that says what to fix."""


def credentials() -> tuple[str, str]:
    client_id = (settings.ebay_client_id or "").strip()
    client_secret = (settings.ebay_client_secret or "").strip()
    if not client_id or not client_secret:
        raise AffiliateError(
            "EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set to import a live "
            "affiliate feed. Create an application key set at developer.ebay.com.")
    return client_id, client_secret


def source_item_id(item_id: str) -> int:
    """Stable, collision-resistant id for a provider item id."""
    digest = hashlib.blake2b(f"{SOURCE_PREFIX}:{item_id}".encode(), digest_size=7).digest()
    value = int.from_bytes(digest, "big")
    return value if value <= _MAX_BIGINT else value % _MAX_BIGINT


def _request_json(method: str, url: str, *, headers=None, data=None,
                  auth=None, timeout: float = 20.0) -> dict:
    """One HTTP call. Isolated so tests can drive the importer without a network."""
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.request(method, url, headers=headers, data=data, auth=auth)
        response.raise_for_status()
        return response.json()


def get_access_token() -> str:
    """Client-credentials OAuth token. eBay tokens last about two hours."""
    client_id, client_secret = credentials()
    body = {"grant_type": "client_credentials", "scope": settings.ebay_oauth_scope}
    payload = _request_json("POST", TOKEN_URL, data=body, auth=(client_id, client_secret))
    token = payload.get("access_token")
    if not token:
        raise AffiliateError("eBay returned no access token.")
    return token


def fetch_items(query: str, limit: int = 50, offset: int = 0, token: str | None = None) -> list[dict]:
    """Search the marketplace. Returns raw item summaries."""
    limit = max(1, min(limit, 200))
    token = token or get_access_token()
    params = {"q": query, "limit": str(limit), "offset": str(offset)}
    payload = _request_json(
        "GET", f"{SEARCH_URL}?{urlencode(params)}",
        headers={"Authorization": f"Bearer {token}",
                 "X-EBAY-C-MARKETPLACE-ID": settings.ebay_marketplace_id,
                 "Accept": "application/json"},
    )
    return payload.get("itemSummaries", []) or []


def _affiliate_url(item_url: str | None) -> str | None:
    if not item_url:
        return None
    campaign = (settings.affiliate_campaign_id or "").strip()
    if not campaign:
        return item_url
    separator = "&" if "?" in item_url else "?"
    return f"{item_url}{separator}{urlencode({'mkcid': '1', 'campaign_id': campaign})}"


def _price(item: dict) -> tuple[Decimal | None, str | None]:
    price = (item.get("price") or {})
    raw = price.get("value")
    currency = (price.get("currency") or "").strip().upper() or None
    try:
        return (Decimal(str(raw)) if raw is not None else None), currency
    except (InvalidOperation, ValueError):
        return None, currency


def _category(item: dict, fallback: str) -> str | None:
    path = (item.get("categoryPath") or "").strip()
    if path:
        leaf = path.split("|")[-1].strip()
        if leaf:
            return leaf[:100]
    leaf2 = (item.get("leafCategoryIds") or None)
    if leaf2:
        return None
    return fallback[:100] if fallback else None


def to_row(item: dict, fallback_category: str | None = None) -> dict:
    """Map one eBay item summary onto a products row."""
    item_id = str(item.get("itemId") or "").strip()
    if not item_id:
        raise AffiliateError("eBay returned an item without an id.")
    price, currency = _price(item)
    image = (item.get("image") or {}).get("imageUrl")
    seller = (item.get("seller") or {}).get("username")
    condition = (item.get("condition") or "").strip() or None
    return {
        "source_item_id": source_item_id(item_id),
        "catalog_source": "ebay",
        "title": (item.get("title") or f"eBay item {item_id}")[:300],
        "description": condition,
        "category": _category(item, fallback_category or ""),
        "price": price,
        "image_url": image,
        "brand": (item.get("brand") or seller or None),
        "stock": None,               # the Browse API does not promise a stock figure
        "currency": currency,
        "external_url": _affiliate_url(item.get("itemWebUrl")),
        "is_active": True,
    }


def import_items(db: Session, queries: list[str], per_query: int = 50) -> dict:
    """Fetch each query and upsert. Returns how many rows were inserted or refreshed."""
    token = get_access_token()
    rows: list[dict] = []
    for query in queries:
        for item in fetch_items(query, limit=per_query, token=token):
            try:
                rows.append(to_row(item, fallback_category=query))
            except AffiliateError:
                continue
    return upsert_products(db, rows)
