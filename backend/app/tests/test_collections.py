"""Curated lists: ownership, the limits, and the one signal a new entry writes."""
import uuid

from sqlalchemy import func, select

from app.api.v1 import collections as collections_api
from app.models import Collection, CollectionItem, Interaction, Product
from app.tests.conftest import user_headers

BASE = "/api/v1/customers/me/collections"


def _create(client, headers, name="Winter picks"):
    r = client.post(BASE, headers=headers, json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()


def test_a_new_customer_has_no_lists(client, db):
    h = user_headers(client, db, "lists-empty@example.com")
    assert client.get(BASE, headers=h).json() == []


def test_a_created_list_is_listed_and_starts_empty(client, db):
    h = user_headers(client, db, "lists-create@example.com")
    body = _create(client, h)
    assert body["name"] == "Winter picks"
    assert body["item_count"] == 0
    assert [c["name"] for c in client.get(BASE, headers=h).json()] == ["Winter picks"]


def test_a_name_is_trimmed_before_it_is_stored(client, db):
    h = user_headers(client, db, "lists-trim@example.com")
    assert _create(client, h, "   Winter   picks  ")["name"] == "Winter picks"


def test_the_same_name_cannot_be_used_twice(client, db):
    h = user_headers(client, db, "lists-dupe@example.com")
    _create(client, h, "Gifts")
    r = client.post(BASE, headers=h, json={"name": "Gifts"})
    assert r.status_code == 409
    assert "already have a list" in r.json()["error"]["message"]


def test_a_blank_name_is_refused(client, db):
    h = user_headers(client, db, "lists-blank@example.com")
    assert client.post(BASE, headers=h, json={"name": "   "}).status_code == 422


def test_one_customer_cannot_reach_another_customers_list(client, db):
    mine = user_headers(client, db, "lists-mine@example.com")
    theirs = user_headers(client, db, "lists-theirs@example.com")
    cid = _create(client, mine, "Private")["id"]
    # Reported as missing, not forbidden: that would confirm it exists.
    assert client.get(f"{BASE}/{cid}", headers=theirs).status_code == 404
    assert client.delete(f"{BASE}/{cid}", headers=theirs).status_code == 404
    assert client.get(f"{BASE}/{cid}", headers=mine).status_code == 200


def test_products_can_be_added_and_taken_back_out(client, db, products):
    h = user_headers(client, db, "lists-items@example.com")
    cid = _create(client, h, "Basket")["id"]
    p = products[10]

    assert client.put(f"{BASE}/{cid}/items/{p.id}", headers=h).status_code == 204
    detail = client.get(f"{BASE}/{cid}", headers=h).json()
    assert [i["id"] for i in detail["items"]] == [str(p.id)]
    assert client.get(BASE, headers=h).json()[0]["item_count"] == 1

    # Adding it again is a no-op rather than a duplicate.
    assert client.put(f"{BASE}/{cid}/items/{p.id}", headers=h).status_code == 204
    assert client.get(BASE, headers=h).json()[0]["item_count"] == 1

    assert client.delete(f"{BASE}/{cid}/items/{p.id}", headers=h).status_code == 204
    assert client.get(f"{BASE}/{cid}", headers=h).json()["items"] == []
    assert client.get(BASE, headers=h).json()[0]["item_count"] == 0


def test_an_unknown_product_is_not_added(client, db):
    h = user_headers(client, db, "lists-ghost@example.com")
    cid = _create(client, h, "Nowhere")["id"]
    r = client.put(f"{BASE}/{cid}/items/{uuid.uuid4()}", headers=h)
    assert r.status_code == 404


def test_deleting_a_list_takes_its_entries_and_leaves_the_products(client, db, products):
    h = user_headers(client, db, "lists-delete@example.com")
    cid = _create(client, h, "Temporary")["id"]
    p = products[20]
    client.put(f"{BASE}/{cid}/items/{p.id}", headers=h)

    assert client.delete(f"{BASE}/{cid}", headers=h).status_code == 204
    assert client.get(BASE, headers=h).json() == []
    assert db.scalar(select(func.count()).select_from(CollectionItem)) == 0
    assert db.get(Product, p.id) is not None


def test_renaming_a_list_is_refused_when_the_name_is_taken(client, db):
    h = user_headers(client, db, "lists-rename@example.com")
    first = _create(client, h, "Alpha")["id"]
    _create(client, h, "Beta")

    renamed = client.patch(f"{BASE}/{first}", headers=h, json={"name": "Gamma"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Gamma"

    assert client.patch(f"{BASE}/{first}", headers=h, json={"name": "Beta"}).status_code == 409
    # Keeping the name it already has is not a clash with itself.
    assert client.patch(f"{BASE}/{first}", headers=h, json={"name": "Gamma"}).status_code == 200


def test_the_number_of_lists_is_capped(client, db, monkeypatch):
    monkeypatch.setattr(collections_api, "MAX_LISTS", 2)
    h = user_headers(client, db, "lists-cap@example.com")
    _create(client, h, "One")
    _create(client, h, "Two")
    r = client.post(BASE, headers=h, json={"name": "Three"})
    assert r.status_code == 409
    assert len(client.get(BASE, headers=h).json()) == 2


def test_a_new_entry_records_one_save_signal(client, db, products):
    h = user_headers(client, db, "lists-signal@example.com", consent=True)
    cid = _create(client, h, "Signal")["id"]
    p = products[30]

    client.put(f"{BASE}/{cid}/items/{p.id}", headers=h)
    client.put(f"{BASE}/{cid}/items/{p.id}", headers=h)     # same product again

    saved = db.scalars(select(Interaction).where(Interaction.event_type == "save",
                                                 Interaction.product_id == p.id)).all()
    assert len(saved) == 1
    assert saved[0].context["source"] == "collection"
    assert db.scalar(select(func.count()).select_from(Collection)) == 1


def test_the_data_export_carries_the_lists(client, db, products):
    h = user_headers(client, db, "lists-export@example.com")
    cid = _create(client, h, "Kitchen ideas")["id"]
    p = products[40]
    client.put(f"{BASE}/{cid}/items/{p.id}", headers=h)

    export = client.get("/api/v1/customers/me/export", headers=h).json()
    assert [(x["name"], x["product_ids"]) for x in export["lists"]] == [
        ("Kitchen ideas", [str(p.id)])]
