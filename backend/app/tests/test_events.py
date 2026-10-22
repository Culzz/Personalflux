import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models import Interaction
from app.tests.conftest import auth, session_headers, user_headers

EV = "/api/v1/events"


def count(db):
    db.expire_all()
    return db.scalar(select(func.count()).select_from(Interaction))


def test_event_needs_a_token_or_session_id(client, products):
    r = client.post(EV, json={"event_type": "view", "product_id": str(products[10].id)})
    assert r.status_code == 400


def test_anonymous_session_event_is_stored(client, db, products):
    r = client.post(EV, headers=session_headers(),
                    json={"event_type": "view", "product_id": str(products[10].id)})
    assert r.status_code == 201 and r.json()["stored"] is True
    row = db.scalar(select(Interaction))
    assert row.session_id == "sess-aaaaaaaa" and row.user_id is None


def test_bad_session_id_is_rejected(client, products):
    r = client.post(EV, headers={"X-Session-Id": "short"},
                    json={"event_type": "view", "product_id": str(products[10].id)})
    assert r.status_code == 400


def test_invalid_events_are_rejected(client, db, products):
    h = session_headers()
    pid = str(products[10].id)
    assert client.post(EV, headers=h, json={"event_type": "teleport", "product_id": pid}).status_code == 422
    assert client.post(EV, headers=h, json={"event_type": "view"}).status_code == 422          # needs product
    assert client.post(EV, headers=h, json={"event_type": "view",
                                            "product_id": str(uuid.uuid4())}).status_code == 422
    assert count(db) == 0


def test_search_event_needs_no_product_but_never_stores_raw_text(client, db, products):
    h = session_headers()
    ok = client.post(EV, headers=h, json={"event_type": "search", "context": {"category": "Category A"}})
    assert ok.status_code == 201
    bad = client.post(EV, headers=h, json={"event_type": "search", "context": {"query": "secret thing"}})
    assert bad.status_code == 422 and "secret thing" not in bad.text


def test_context_is_size_limited(client, products):
    ctx = {f"k{i}": i for i in range(11)}
    r = client.post(EV, headers=session_headers(),
                    json={"event_type": "view", "product_id": str(products[10].id), "context": ctx})
    assert r.status_code == 422


def test_timestamps_in_the_future_or_far_past_are_rejected(client, products):
    pid = str(products[10].id)
    h = session_headers()
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    assert client.post(EV, headers=h, json={"event_type": "view", "product_id": pid,
                                            "occurred_at": future}).status_code == 422
    assert client.post(EV, headers=h, json={"event_type": "view", "product_id": pid,
                                            "occurred_at": old}).status_code == 422


def test_idempotency_key_prevents_duplicates(client, db, products):
    body = {"event_type": "view", "product_id": str(products[10].id), "idempotency_key": "key-12345678"}
    first = client.post(EV, headers=session_headers(), json=body)
    second = client.post(EV, headers=session_headers(), json=body)
    assert first.status_code == 201
    assert second.status_code == 200 and second.json()["duplicate"] is True
    assert second.json()["event_id"] == first.json()["event_id"]
    assert count(db) == 1


def test_idempotency_key_cannot_be_borrowed_by_someone_else(client, db, products):
    body = {"event_type": "view", "product_id": str(products[10].id), "idempotency_key": "key-12345678"}
    assert client.post(EV, headers=session_headers("sess-aaaaaaaa"), json=body).status_code == 201
    assert client.post(EV, headers=session_headers("sess-bbbbbbbb"), json=body).status_code == 409


def test_events_are_not_stored_without_tracking_consent(client, db, products):
    h = user_headers(client, db, "u@shop.dev", consent=False)
    body = {"event_type": "view", "product_id": str(products[10].id)}
    r = client.post(EV, headers=h, json=body)
    assert r.status_code == 202 and r.json() == {"stored": False, "duplicate": False,
                                                 "reason": "tracking_disabled", "event_id": None}
    assert count(db) == 0
    assert client.patch("/api/v1/customers/me/settings", headers=h,
                        json={"tracking_consent": True}).status_code == 200
    assert client.post(EV, headers=h, json=body).status_code == 201
    assert count(db) == 1


def test_logged_in_events_are_linked_to_the_token_owner_only(client, db, products):
    h = user_headers(client, db, "u@shop.dev", consent=True)
    client.post(EV, headers=h, json={"event_type": "click", "product_id": str(products[20].id)})
    row = db.scalar(select(Interaction))
    me = client.get("/api/v1/auth/me", headers=h).json()
    assert str(row.user_id) == me["id"]
