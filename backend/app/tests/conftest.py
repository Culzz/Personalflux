import os

# Tests ALWAYS use a separate database, never the development one.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://personalflux:change-me-dev-only@localhost:5432/personalflux_test",
)
# A developer with a Neon project has both URLs in .env.local. The direct one is
# not part of the test database choice, and leaving it set would let a test run
# reach a hosted database.
os.environ.pop("DATABASE_URL_UNPOOLED", None)
os.environ["JWT_SECRET_KEY"] = "test-secret-key-test-secret-key-0123456789"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["ENABLE_MODEL_POLLER"] = "false"   # tests drive polls explicitly
os.environ["REFRESH_REUSE_GRACE_SECONDS"] = "0"
# The statement timeout protects production from a stuck query. In tests the
# per-test TRUNCATE is the longest statement, and a short timeout only makes the
# suite flaky on a loaded machine, so it is off here.
os.environ["DB_STATEMENT_TIMEOUT_MS"] = "0"
os.environ["APP_ENV"] = "test"

from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import app.models  # noqa: E402,F401
from app.core import metrics  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.rate_limit import ALL_LIMITERS  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.ml.inference import load_artifact  # noqa: E402
from app.ml.registry import registry  # noqa: E402
from app.models import Product, User  # noqa: E402
from app.tests.helpers import EDGES, ITEMS, write_artifact  # noqa: E402

PASSWORD = "correct-horse-battery"


@pytest.fixture(scope="session")
def _schema():
    assert engine.url.database.endswith("_test"), "refusing to touch a non-test database"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def _cleanup():
    with engine.begin() as c:
        names = ", ".join(t.name for t in Base.metadata.sorted_tables)
        c.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    registry.set_model(None)
    registry.desired_version = None
    registry.poll_error = None
    registry.last_check_at = None
    registry.root_override = None
    for limiter in ALL_LIMITERS:
        limiter.clear()
    metrics.reset()
    settings.rate_limit_enabled = False


@pytest.fixture
def db(_schema):
    _cleanup()
    session = SessionLocal()
    yield session
    session.close()
    _cleanup()


@pytest.fixture
def client(db):
    return TestClient(fastapi_app)


def make_user(db, email, role="customer", consent=False, password=PASSWORD):
    user = User(email=email, password_hash=hash_password(password), role=role,
                tracking_consent=consent)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(client, email, password=PASSWORD) -> str:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token) -> dict:
    return {"Authorization": f"Bearer {token}"}


def user_headers(client, db, email, role="customer", consent=False) -> dict:
    make_user(db, email, role=role, consent=consent)
    return auth(login(client, email))


def session_headers(name="sess-aaaaaaaa") -> dict:
    return {"X-Session-Id": name}


@pytest.fixture
def products(db):
    """Four active products. Source ids 10/20 are Category A, 30/40 are Category B."""
    spec = [(10, "Category A", Decimal("9.99")), (20, "Category A", Decimal("19.99")),
            (30, "Category B", Decimal("29.99")), (40, "Category B", None)]
    out = {}
    for source_id, category, price in spec:
        p = Product(source_item_id=source_id, title=f"Item {source_id}",
                    category=category, price=price)
        db.add(p)
        out[source_id] = p
    db.commit()
    for p in out.values():
        db.refresh(p)
    return out


@pytest.fixture
def model(tmp_path):
    """A small valid artifact, loaded as the serving model."""
    folder = write_artifact(tmp_path, "v1", ITEMS, EDGES)
    registry.root_override = tmp_path
    loaded = load_artifact(folder)
    registry.set_model(loaded)
    return loaded
