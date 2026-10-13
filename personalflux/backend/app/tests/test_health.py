from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


class BrokenDb:
    def execute(self, *args, **kwargs):
        raise RuntimeError("secret internal db error")


def test_health_db_degrades_gracefully_and_hides_details():
    app.dependency_overrides[get_db] = lambda: BrokenDb()
    try:
        r = client.get("/health/db")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert "secret internal db error" not in r.text