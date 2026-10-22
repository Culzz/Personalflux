from sqlalchemy import select

from app.models import AuditLog, User
from app.tests.conftest import auth, login, make_user, user_headers

API = "/api/v1"


def test_protected_endpoints_reject_anonymous_requests(client):
    for method, path in [("get", "/customers/me/preferences"), ("get", "/customers/me/saved"),
                         ("get", "/customers/me/history"), ("get", "/analytics/overview"),
                         ("get", "/admin/users"), ("get", "/ml/models"),
                         ("post", "/ml/models/scan")]:
        assert getattr(client, method)(API + path).status_code == 401, path


def test_customers_cannot_use_staff_endpoints(client, db):
    h = user_headers(client, db, "cust@shop.dev")
    for method, path in [("get", "/analytics/overview"), ("get", "/analytics/categories"),
                         ("get", "/admin/users"), ("get", "/admin/audit-logs"),
                         ("get", "/ml/models"), ("get", "/ml/experiments"),
                         ("post", "/ml/models/scan"), ("post", "/ml/training-runs")]:
        assert getattr(client, method)(API + path, headers=h).status_code == 403, path


def test_analysts_can_read_analytics_but_not_administer(client, db):
    h = user_headers(client, db, "analyst@shop.dev", role="analyst")
    assert client.get(f"{API}/analytics/overview", headers=h).status_code == 200
    assert client.get(f"{API}/ml/experiments", headers=h).status_code == 200
    assert client.get(f"{API}/admin/users", headers=h).status_code == 403
    assert client.post(f"{API}/ml/models/scan", headers=h).status_code == 403


def test_a_client_supplied_user_id_is_ignored(client, db, products):
    a = make_user(db, "a@shop.dev", consent=True)
    ha = auth(login(client, "a@shop.dev"))
    hb = user_headers(client, db, "b@shop.dev")
    client.patch(f"{API}/customers/me/preferences", headers=ha,
                 json={"liked_categories": ["Category A"]})
    r = client.get(f"{API}/customers/me/preferences", params={"user_id": str(a.id)}, headers=hb)
    assert r.status_code == 200 and r.json()["explicit"] == {}


def test_saved_items_are_private_to_each_customer(client, db, products):
    ha = user_headers(client, db, "a@shop.dev")
    hb = user_headers(client, db, "b@shop.dev")
    pid = str(products[10].id)
    assert client.put(f"{API}/customers/me/saved/{pid}", headers=ha).status_code == 204
    assert len(client.get(f"{API}/customers/me/saved", headers=ha).json()) == 1
    assert client.get(f"{API}/customers/me/saved", headers=hb).json() == []


def test_admin_changes_roles_and_everything_is_audited(client, db):
    ha = user_headers(client, db, "admin@shop.dev", role="admin")
    target = make_user(db, "t@shop.dev")
    r = client.patch(f"{API}/admin/users/{target.id}", headers=ha, json={"role": "analyst"})
    assert r.status_code == 200 and r.json()["role"] == "analyst"
    log = db.scalar(select(AuditLog).where(AuditLog.action == "user.update"))
    assert log is not None and str(log.target_id) == str(target.id)


def test_admin_cannot_change_their_own_role(client, db):
    ha = user_headers(client, db, "admin@shop.dev", role="admin")
    me = db.scalar(select(User).where(User.email == "admin@shop.dev"))
    r = client.patch(f"{API}/admin/users/{me.id}", headers=ha, json={"role": "customer"})
    assert r.status_code == 400


def test_role_values_are_validated(client, db):
    ha = user_headers(client, db, "admin@shop.dev", role="admin")
    target = make_user(db, "t@shop.dev")
    assert client.patch(f"{API}/admin/users/{target.id}", headers=ha,
                        json={"role": "superuser"}).status_code == 422


def test_deactivating_a_user_ends_their_access(client, db):
    ha = user_headers(client, db, "admin@shop.dev", role="admin")
    target = make_user(db, "t@shop.dev")
    tt = login(client, "t@shop.dev")
    assert client.get(f"{API}/auth/me", headers=auth(tt)).status_code == 200
    client.patch(f"{API}/admin/users/{target.id}", headers=ha, json={"is_active": False})
    assert client.get(f"{API}/auth/me", headers=auth(tt)).status_code == 401
    r = client.post(f"{API}/auth/login", json={"email": "t@shop.dev", "password": "correct-horse-battery"})
    assert r.status_code == 401
