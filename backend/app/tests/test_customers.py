from sqlalchemy import func, select

from app.models import Interaction, Preference, RefreshToken, SavedItem, User
from app.tests.conftest import PASSWORD, auth, login, make_user, user_headers

C = "/api/v1/customers/me"
EV = "/api/v1/events"


def test_explicit_preferences_can_be_set_changed_and_cleared(client, db):
    h = user_headers(client, db, "u@shop.dev")
    r = client.patch(f"{C}/preferences", headers=h, json={
        "liked_categories": [" Category A ", "Category A", ""],
        "price_range": {"min": "5", "max": "50"}})
    assert r.status_code == 200
    explicit = r.json()["explicit"]
    assert explicit["liked_categories"] == ["Category A"]
    assert explicit["price_range"] == {"min": "5", "max": "50"}

    r = client.patch(f"{C}/preferences", headers=h, json={"liked_categories": []})
    assert "liked_categories" not in r.json()["explicit"]
    assert "price_range" in r.json()["explicit"]               # untouched fields stay


def test_price_range_is_validated(client, db):
    h = user_headers(client, db, "u@shop.dev")
    assert client.patch(f"{C}/preferences", headers=h,
                        json={"price_range": {"min": "50", "max": "5"}}).status_code == 422
    assert client.patch(f"{C}/preferences", headers=h,
                        json={"price_range": {"min": "-1"}}).status_code == 422


def test_inferred_preferences_are_separate_and_resettable(client, db, products):
    h = user_headers(client, db, "u@shop.dev", consent=True)
    client.patch(f"{C}/preferences", headers=h, json={"liked_categories": ["Category B"]})
    for p in (products[10], products[10], products[20]):
        client.post(EV, headers=h, json={"event_type": "view", "product_id": str(p.id)})

    prefs = client.get(f"{C}/preferences", headers=h).json()
    assert prefs["explicit"]["liked_categories"] == ["Category B"]            # stated
    assert prefs["inferred"]["recent_categories"][0]["category"] == "Category A"  # inferred
    assert prefs["inferred"]["events_considered"] == 3

    r = client.delete(f"{C}/preferences", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["profile_reset_at"] is not None
    assert body["inferred"]["events_considered"] == 0
    assert body["explicit"]["liked_categories"] == ["Category B"]            # stated ones survive

    client.post(EV, headers=h, json={"event_type": "view", "product_id": str(products[30].id)})
    assert client.get(f"{C}/preferences", headers=h).json()["inferred"]["events_considered"] == 1

    r = client.delete(f"{C}/preferences", headers=h, params={"include_explicit": True})
    assert r.json()["explicit"] == {}


def test_history_lists_recent_products_and_supports_deletion(client, db, products):
    h = user_headers(client, db, "u@shop.dev", consent=True)
    for p in (products[10], products[20], products[10]):
        client.post(EV, headers=h, json={"event_type": "view", "product_id": str(p.id)})
    hist = client.get(f"{C}/history", headers=h).json()
    assert [x["product"]["title"] for x in hist] == ["Item 10", "Item 20"]   # distinct, newest first

    assert client.delete(f"{C}/history/{products[10].id}", headers=h).status_code == 204
    assert [x["product"]["title"] for x in client.get(f"{C}/history", headers=h).json()] == ["Item 20"]
    assert client.delete(f"{C}/history", headers=h).status_code == 204
    assert client.get(f"{C}/history", headers=h).json() == []


def test_saved_items_flow(client, db, products):
    h = user_headers(client, db, "u@shop.dev", consent=True)
    pid = str(products[10].id)
    assert client.put(f"{C}/saved/{pid}", headers=h).status_code == 204
    assert client.put(f"{C}/saved/{pid}", headers=h).status_code == 204       # idempotent
    saved = client.get(f"{C}/saved", headers=h).json()
    assert len(saved) == 1 and saved[0]["product"]["title"] == "Item 10"
    assert client.delete(f"{C}/saved/{pid}", headers=h).status_code == 204
    assert client.get(f"{C}/saved", headers=h).json() == []


def test_cannot_save_inactive_or_unknown_products(client, db, products):
    h = user_headers(client, db, "u@shop.dev")
    products[10].is_active = False
    db.commit()
    assert client.put(f"{C}/saved/{products[10].id}", headers=h).status_code == 404


def test_export_contains_the_customers_own_data_only(client, db, products):
    h = user_headers(client, db, "u@shop.dev", consent=True)
    other = user_headers(client, db, "other@shop.dev", consent=True)
    client.post(EV, headers=h, json={"event_type": "view", "product_id": str(products[10].id)})
    client.post(EV, headers=other, json={"event_type": "view", "product_id": str(products[20].id)})
    data = client.get(f"{C}/export", headers=h).json()
    assert data["profile"]["email"] == "u@shop.dev"
    assert len(data["events"]) == 1 and "password" not in str(data)


def test_account_deletion_removes_everything_linked_to_the_customer(client, db, products):
    h = user_headers(client, db, "u@shop.dev", consent=True)
    client.post(EV, headers=h, json={"event_type": "view", "product_id": str(products[10].id)})
    client.put(f"{C}/saved/{products[10].id}", headers=h)
    client.patch(f"{C}/preferences", headers=h, json={"liked_categories": ["Category A"]})

    assert client.post(f"{C}/delete", headers=h, json={"password": "wrong-password-1"}).status_code == 403
    assert db.scalar(select(func.count()).select_from(User)) == 1

    assert client.post(f"{C}/delete", headers=h, json={"password": PASSWORD}).status_code == 204
    db.expire_all()
    for table in (User, Interaction, SavedItem, Preference, RefreshToken):
        assert db.scalar(select(func.count()).select_from(table)) == 0, table
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401


def test_other_customers_survive_an_account_deletion(client, db, products):
    h1 = user_headers(client, db, "u1@shop.dev", consent=True)
    h2 = user_headers(client, db, "u2@shop.dev", consent=True)
    client.post(EV, headers=h2, json={"event_type": "view", "product_id": str(products[10].id)})
    client.post(f"{C}/delete", headers=h1, json={"password": PASSWORD})
    assert db.scalar(select(func.count()).select_from(Interaction)) == 1
    assert client.get("/api/v1/auth/me", headers=h2).status_code == 200
