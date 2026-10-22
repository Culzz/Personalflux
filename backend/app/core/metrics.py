"""Tiny in-process metrics: rolling latency and error counts per route group."""
from collections import defaultdict, deque

_WINDOW = 500
_latency = defaultdict(lambda: deque(maxlen=_WINDOW))
_status = defaultdict(lambda: defaultdict(int))


def record(group: str, duration_ms: float, status: int) -> None:
    _latency[group].append(duration_ms)
    _status[group][f"{status // 100}xx"] += 1


def summary(group: str) -> dict:
    vals = sorted(_latency[group])
    if not vals:
        return {"count": 0, "p50_ms": None, "p95_ms": None, "status": {}}
    pick = lambda q: round(vals[min(len(vals) - 1, int(q * len(vals)))], 1)
    return {"count": len(vals), "p50_ms": pick(0.5), "p95_ms": pick(0.95),
            "status": dict(_status[group])}


def reset() -> None:
    _latency.clear()
    _status.clear()
