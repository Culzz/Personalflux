"""End-to-end smoke test against a running API.

    python scripts/smoke_test.py https://api.example.com

Checks the things that break when the pieces are wired together: the service is
up, the database is reachable, the catalogue answers, an account can be created,
the personalised feed answers for that account, stated preferences can be saved
for an anonymous session, an event is accepted, and a comparison resolves.

Exit code 0 means every check passed. Non-zero means the first failure, printed
with the response body, so it can go straight into a deploy gate.
"""
import json
import sys
import urllib.error
import urllib.request
import uuid

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
API = f"{BASE}/api/v1"
TIMEOUT = 20

_passed = 0
_failed = 0


def call(method: str, path: str, *, body=None, headers=None, expect=None) -> tuple[int, dict]:
    url = path if path.startswith("http") else f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            raw = response.read().decode() or "{}"
            return response.status, (json.loads(raw) if raw.strip().startswith(("{", "[")) else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:200]}


def check(name: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed += 1
        print(f"  FAIL  {name}  {detail}")


print(f"smoke test against {BASE}")

status, body = call("GET", "/health")
check("liveness /health", status == 200 and body.get("status") == "ok", f"{status} {body}")

status, body = call("GET", "/health/db")
check("readiness /health/db", status == 200, f"{status} {body}")

status, body = call("GET", f"{API}/ml/health")
check("model /api/v1/ml/health answers", status == 200, f"{status} {body}")
if status == 200 and not body.get("model_loaded"):
    print(f"  NOTE  model not loaded; recommending from database popularity ({body.get('fallback_mode')})")

status, body = call("GET", f"{API}/products?page_size=3")
items = body.get("items", []) if isinstance(body, dict) else []
check("catalogue lists products", status == 200 and len(items) > 0, f"{status} {body}")

status, body = call("GET", f"{API}/products/categories")
check("categories answer", status == 200 and isinstance(body, list), f"{status} {body}")

# A fresh account, so the run never depends on existing data.
email = f"smoke-{uuid.uuid4().hex[:10]}@example.com"
status, body = call("POST", f"{API}/auth/register",
                    body={"email": email, "password": "smoke-test-password-1",
                          "tracking_consent": True})
token = body.get("access_token") if isinstance(body, dict) else None
check("register a new account", status == 201 and bool(token), f"{status} {body}")
bearer = {"Authorization": f"Bearer {token}"} if token else {}

status, body = call("GET", f"{API}/recommendations/home?limit=5", headers=bearer)
recs = body.get("recommendations", []) if isinstance(body, dict) else []
check("personalised feed answers", status == 200 and isinstance(recs, list), f"{status} {body}")
if recs:
    check("feed items carry an explanation",
          all("explanation" in r for r in recs), "an item had no explanation")

session = {"X-Session-Id": f"smoke-{uuid.uuid4().hex[:12]}"}
status, body = call("PATCH", f"{API}/recommendations/preferences", headers=session,
                    body={"liked_categories": ["Headphones"]})
check("anonymous stated preferences save", status == 200, f"{status} {body}")

status, body = call("POST", f"{API}/events", headers=session,
                    body={"event_type": "view", "product_id": items[0]["id"] if items else None,
                          "idempotency_key": f"smoke-{uuid.uuid4().hex}"})
check("event ingest accepts an event", status in (200, 201, 202), f"{status} {body}")

if len(items) >= 2:
    ids = ",".join(i["id"] for i in items[:2])
    status, body = call("GET", f"{API}/products/compare?ids={ids}")
    check("comparison resolves", status == 200 and isinstance(body, list) and len(body) == 2,
          f"{status} {body}")

print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
