"""Simple in-memory sliding-window limiter (single process; fine for a demo).

Memory is bounded: buckets for clients that went quiet are dropped, and the
table is swept once it grows past ``max_keys``. Move this to Redis before
running more than one worker, or each worker will keep its own count.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import settings


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int, max_keys: int = 10_000):
        self.max_calls = max_calls
        self.window = window_seconds
        self.max_keys = max_keys
        self.hits: dict[str, deque] = defaultdict(deque)

    def clear(self) -> None:
        self.hits.clear()

    def _sweep(self, now: float) -> None:
        """Drop buckets whose newest hit is already outside the window."""
        stale = [ip for ip, q in self.hits.items() if not q or now - q[-1] > self.window]
        for ip in stale:
            del self.hits[ip]

    def _trim_to_cap(self, now: float) -> None:
        self._sweep(now)
        if len(self.hits) <= self.max_keys:
            return
        # Every bucket is still active: evict the coldest ones so a flood of
        # client addresses cannot grow the table without bound.
        overflow = len(self.hits) - self.max_keys
        coldest = sorted(self.hits.items(), key=lambda kv: kv[1][-1] if kv[1] else 0.0)
        for ip, _ in coldest[:overflow]:
            del self.hits[ip]

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
        if len(self.hits) > self.max_keys:
            self._trim_to_cap(now)


auth_limiter = RateLimiter(max_calls=10, window_seconds=60)      # login / register / refresh
reco_limiter = RateLimiter(max_calls=120, window_seconds=60)     # recommendation endpoints
ALL_LIMITERS = [auth_limiter, reco_limiter]
