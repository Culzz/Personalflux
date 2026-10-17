from starlette.requests import Request

from app.core.config import settings
from app.core.rate_limit import RateLimiter


def _req(ip: str) -> Request:
    return Request({"type": "http", "client": (ip, 1234), "headers": []})


def test_blocks_after_the_limit_and_leaves_other_clients_alone(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    limiter = RateLimiter(max_calls=3, window_seconds=60)
    for _ in range(3):
        limiter(_req("10.0.0.1"))
    try:
        limiter(_req("10.0.0.1"))
    except Exception as exc:  # HTTPException from FastAPI
        assert getattr(exc, "status_code", None) == 429
    else:
        raise AssertionError("the fourth call should have been blocked")
    limiter(_req("10.0.0.2"))  # a different client keeps working


def test_table_does_not_grow_without_bound(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    limiter = RateLimiter(max_calls=5, window_seconds=60, max_keys=4)
    for i in range(50):
        limiter(_req(f"10.0.1.{i}"))
    assert len(limiter.hits) <= 4
