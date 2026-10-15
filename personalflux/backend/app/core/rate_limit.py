"""Simple in-memory sliding-window limiter (single process; fine for a demo)."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import settings


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window = window_seconds
        self.hits: dict[str, deque] = defaultdict(deque)

    def clear(self) -> None:
        self.hits.clear()

    def __call__(self, request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        q = self.hits[ip]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max_calls:
            raise HTTPException(
                status_code=429, detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(self.window)},
            )
        q.append(now)


auth_limiter = RateLimiter(max_calls=10, window_seconds=60)      # login / register / refresh
reco_limiter = RateLimiter(max_calls=120, window_seconds=60)     # recommendation endpoints
ALL_LIMITERS = [auth_limiter, reco_limiter]
