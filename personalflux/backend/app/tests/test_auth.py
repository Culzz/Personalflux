from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.models import AuditLog, RefreshToken, User
from app.tests.conftest import PASSWORD, auth, login, make_user

URL = "/api/v1/auth"


def register(client, email="alice@shop.dev", password=PASSWORD, consent=False):
    return client.post(f"{URL}/register",
                       json={"email": email, "password": password, "tracking_consent": consent})


def test_register_returns_token_and_sets_httponly_cookie(client, db):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer" and body["user"]["role"] == "customer"
    assert "password" not in r.text
    set_cookie = r.headers["set-cookie"].lower()
    assert "refresh_token=" in set_cookie and "httponly" in set_cookie and "samesite=strict" in set_cookie


def test_password_is_stored_as_argon2id_hash(client, db):
    register(client)
    user = db.scalar(select(User).where(User.email == "alice@shop.dev"))
    assert user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in user.password_hash


def test_duplicate_email_conflicts_even_with_different_case(client):
    assert register(client).status_code == 201
    assert register(client, email="ALICE@shop.dev").status_code == 409


def test_weak_password_and_bad_email_are_rejected(client):
    assert register(client, password="short").status_code == 422
    assert register(client, email="not-an-email").status_code == 422


def test_login_is_case_insensitive_on_email_and_uses_generic_errors(client):
    register(client)
    ok = client.post(f"{URL}/login", json={"email": "ALICE@shop.dev", "password": PASSWORD})
    assert ok.status_code == 200
    wrong = client.post(f"{URL}/login", json={"email": "alice@shop.dev", "password": "wrong-password-1"})
    unknown = client.post(f"{URL}/login", json={"email": "nobody@shop.dev", "password": "wrong-password-1"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]


def test_me_requires_a_valid_token(client, db):
    assert client.get(f"{URL}/me").status_code == 401
    token = register(client).json()["access_token"]
    r = client.get(f"{URL}/me", headers=auth(token))
    assert r.status_code == 200 and r.json()["email"] == "alice@shop.dev"
    assert client.get(f"{URL}/me", headers=auth("garbage")).status_code == 401


def test_expired_and_forged_tokens_are_rejected(client, db):
    user = make_user(db, "bob@shop.dev")
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user.id), "type": "access", "iat": now,
              "exp": now - timedelta(minutes=1)}
    expired = jwt.encode(claims, settings.jwt_secret_key, algorithm="HS256")
    forged = jwt.encode({**claims, "exp": now + timedelta(minutes=5)},
                        "some-other-secret-some-other-secret-1234", algorithm="HS256")
    assert client.get(f"{URL}/me", headers=auth(expired)).status_code == 401
    assert client.get(f"{URL}/me", headers=auth(forged)).status_code == 401


def test_deactivated_user_token_stops_working(client, db):
    user = make_user(db, "carol@shop.dev")
    token = login(client, "carol@shop.dev")
    user.is_active = False
    db.commit()
    assert client.get(f"{URL}/me", headers=auth(token)).status_code == 401


def test_refresh_rotates_and_reuse_revokes_every_session(client, db):
    register(client)
    old = client.cookies.get("refresh_token")
    assert old
    r = client.post(f"{URL}/refresh")
    assert r.status_code == 200 and r.json()["access_token"]
    new = client.cookies.get("refresh_token")
    assert new and new != old

    thief = TestClient(app)          # replays the already-used token
    stolen = thief.post(f"{URL}/refresh", headers={"Cookie": f"refresh_token={old}"})
    assert stolen.status_code == 401
    assert client.post(f"{URL}/refresh").status_code == 401      # new token revoked too


def test_logout_revokes_the_refresh_token(client, db):
    register(client)
    old = client.cookies.get("refresh_token")
    assert client.post(f"{URL}/logout").status_code == 204
    other = TestClient(app)
    assert other.post(f"{URL}/refresh", headers={"Cookie": f"refresh_token={old}"}).status_code == 401
    assert db.scalar(select(RefreshToken).where(RefreshToken.revoked_at.is_not(None))) is not None


def test_refresh_without_cookie_is_401(client):
    assert client.post(f"{URL}/refresh").status_code == 401


def test_a_cross_site_refresh_is_refused_even_with_a_valid_cookie(client):
    register(client)
    r = client.post(f"{URL}/refresh", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403                      # SameSite=Strict, plus this check


def test_a_refresh_from_the_configured_origin_is_allowed(client):
    register(client)
    r = client.post(f"{URL}/refresh", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200


def test_a_retired_token_reused_after_the_grace_window_revokes_the_family(client, db, monkeypatch):
    monkeypatch.setattr(settings, "refresh_reuse_grace_seconds", 0)
    register(client)
    old = client.cookies.get("refresh_token")
    assert client.post(f"{URL}/refresh").status_code == 200      # old is retired here

    thief = TestClient(app)                                      # replays the retired token
    assert thief.post(f"{URL}/refresh", headers={"Cookie": f"refresh_token={old}"}).status_code == 401
    assert client.post(f"{URL}/refresh").status_code == 401      # the winner is revoked too
    db.expire_all()
    assert any(t.revoked_reason == "reuse_detected" for t in db.scalars(select(RefreshToken)))
    assert any(a.action == "auth.refresh_reuse" for a in db.scalars(select(AuditLog)))


def test_two_tabs_refreshing_at_once_do_not_log_the_user_out(client, monkeypatch):
    monkeypatch.setattr(settings, "refresh_reuse_grace_seconds", 60)
    register(client)
    old = client.cookies.get("refresh_token")
    assert client.post(f"{URL}/refresh").status_code == 200      # tab A wins the race

    loser = TestClient(app)                                      # tab B used the same cookie
    assert loser.post(f"{URL}/refresh", headers={"Cookie": f"refresh_token={old}"}).status_code == 401
    assert client.post(f"{URL}/refresh").status_code == 200      # the session survives


def test_rotation_stays_inside_one_family_per_login(client, db):
    register(client)
    for _ in range(3):
        assert client.post(f"{URL}/refresh").status_code == 200
    rows = list(db.scalars(select(RefreshToken)))
    assert len({t.family_id for t in rows}) == 1                 # one chain, four tokens
    assert [t.revoked_reason for t in rows].count("rotated") == 3


def test_logout_ends_the_whole_family_not_just_the_current_token(client, db):
    register(client)
    old = client.cookies.get("refresh_token")
    assert client.post(f"{URL}/refresh").status_code == 200
    assert client.post(f"{URL}/logout").status_code == 204

    other = TestClient(app)
    assert other.post(f"{URL}/refresh", headers={"Cookie": f"refresh_token={old}"}).status_code == 401
    db.expire_all()
    assert all(t.revoked_at is not None for t in db.scalars(select(RefreshToken)))


def test_an_expired_refresh_token_is_rejected_without_crying_theft(client, db):
    register(client)
    row = db.scalar(select(RefreshToken))
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    old = client.cookies.get("refresh_token")

    expired = TestClient(app)
    assert expired.post(f"{URL}/refresh", headers={"Cookie": f"refresh_token={old}"}).status_code == 401
    db.expire_all()
    assert db.scalar(select(RefreshToken)).revoked_reason is None    # no false alarm recorded


def test_auth_endpoints_are_rate_limited(client, db, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    codes = [client.post(f"{URL}/login", json={"email": "x@shop.dev", "password": "nope-nope-nope"}).status_code
             for _ in range(11)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429
