import uuid
from decimal import Decimal

from sqlalchemy import select

from app.models import AuditLog, Product
from app.tests.conftest import user_headers

P = "/api/v1/products"


def test_list_returns_only_active_products(client, db, products):
    products[40].is_active = False
    db.commit()
    body = client.get(P).json()
    assert body["total"] == 3
    assert all(item["is_active"] for item in body["items"])


def test_filters_sort_and_pagination(client, products):
    assert client.get(P, params={"category": "Category A"}).json()["total"] == 2
    assert client.get(P, params={"min_price": 15, "max_price": 25}).json()["total"] == 1
    prices = [i["price"] for i in client.get(P, params={"sort": "price_asc"}).json()["items"]]
    assert prices == ["9.99", "19.99", "29.99", None]       # exact decimals, missing prices last
    page2 = client.get(P, params={"page_size": 2, "page": 2}).json()
    assert page2["total"] == 4 and len(page2["items"]) == 2 and page2["page"] == 2


def test_brands_lists_only_active_brands_by_count(client, db, products):
    products[10].brand = "Nova"
    products[20].brand = "Nova"
    products[30].brand = "Solo"
    products[40].brand = "Solo"
    products[40].is_active = False           # a retired product's brand is not offered
    db.commit()
    assert client.get(f"{P}/brands").json() == [
        {"brand": "Nova", "products": 2}, {"brand": "Solo", "products": 1},
    ]


def test_page_size_and_sort_are_bounded(client, products):
    assert client.get(P, params={"page_size": 51}).status_code == 422
    assert client.get(P, params={"page": 0}).status_code == 422
    assert client.get(P, params={"sort": "drop table"}).status_code == 422


def test_keyword_search_is_case_insensitive_and_escapes_wildcards(client, products):
    assert client.get(P, params={"q": "ITEM 1"}).json()["total"] == 1
    assert client.get(P, params={"q": "%"}).json()["total"] == 0
    assert client.get(P, params={"q": "_"}).json()["total"] == 0
    assert client.get(P, params={"q": "'; DROP TABLE products; --"}).json()["total"] == 0
    assert client.get(P).json()["total"] == 4


def test_categories_endpoint(client, products):
    cats = {c["category"]: c["products"] for c in client.get(f"{P}/categories").json()}
    assert cats == {"Category A": 2, "Category B": 2}


def test_inactive_products_are_hidden_from_customers(client, db, products):
    products[10].is_active = False
    db.commit()
    assert client.get(f"{P}/{products[10].id}").status_code == 404
    assert client.get(f"{P}/{products[10].id}/related").status_code == 404
    assert client.get(P, params={"include_inactive": True}).status_code == 401
    h = user_headers(client, db, "c@shop.dev")
    assert client.get(P, params={"include_inactive": True}, headers=h).status_code == 403


def test_unknown_product_is_404(client):
    assert client.get(f"{P}/{uuid.uuid4()}").status_code == 404
    assert client.get(f"{P}/not-a-uuid").status_code == 422


def test_related_products_share_the_category(client, products):
    rel = client.get(f"{P}/{products[10].id}/related").json()
    assert [r["title"] for r in rel] == ["Item 20"]


def test_only_admins_manage_the_catalog_and_changes_are_audited(client, db, products):
    body = {"title": "New thing", "category": "Category A", "price": "12.50"}
    assert client.post(P, json=body).status_code == 401
    hc = user_headers(client, db, "c@shop.dev")
    assert client.post(P, json=body, headers=hc).status_code == 403

    ha = user_headers(client, db, "a@shop.dev", role="admin")
    created = client.post(P, json=body, headers=ha)
    assert created.status_code == 201 and created.json()["price"] == "12.50"
    pid = created.json()["id"]

    assert client.patch(f"{P}/{pid}", json={"is_active": False}, headers=ha).status_code == 200
    assert client.get(f"{P}/{pid}").status_code == 404            # now hidden from customers
    assert client.get(f"{P}/{pid}", headers=ha).status_code == 200  # admins still see it
    actions = {a.action for a in db.scalars(select(AuditLog))}
    assert {"product.create", "product.update"} <= actions


def test_product_input_is_validated(client, db):
    ha = user_headers(client, db, "a@shop.dev", role="admin")
    assert client.post(P, json={"title": ""}, headers=ha).status_code == 422
    assert client.post(P, json={"title": "x", "price": "-1"}, headers=ha).status_code == 422
    assert client.post(P, json={"title": "x", "price": "1.234"}, headers=ha).status_code == 422
    assert client.post(P, json={"title": "x", "image_url": "javascript:alert(1)"},
                       headers=ha).status_code == 422
    assert client.patch(f"{P}/{uuid.uuid4()}", json={"title": "x"}, headers=ha).status_code == 404
