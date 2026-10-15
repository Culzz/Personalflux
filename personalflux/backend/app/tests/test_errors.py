import uuid

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_not_found_uses_the_standard_error_shape(client):
    r = client.get(f"/api/v1/products/{uuid.uuid4()}")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "not_found" and err["request_id"] == r.headers["x-request-id"]


def test_client_request_id_is_echoed(client):
    r = client.get("/health", headers={"X-Request-ID": "abc-12345678"})
    assert r.headers["x-request-id"] == "abc-12345678"


def test_invalid_request_id_is_replaced(client):
    r = client.get("/health", headers={"X-Request-ID": "bad id with spaces!"})
    assert r.headers["x-request-id"] != "bad id with spaces!"


def test_validation_errors_do_not_echo_submitted_values(client):
    r = client.post("/api/v1/auth/register",
                    json={"email": "not-an-email-SECRETVALUE", "password": "x"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert "SECRETVALUE" not in r.text


def test_oversized_body_is_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "max_request_bytes", 100)
    r = client.post("/api/v1/auth/login", json={"email": "a@shop.dev", "password": "x" * 500})
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "payload_too_large"


def test_unhandled_errors_hide_details(client):
    @app.get("/boom-test")
    def boom():
        raise RuntimeError("secret internal detail")

    try:
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/boom-test")
    finally:
        app.router.routes.pop()
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert "secret internal detail" not in r.text
