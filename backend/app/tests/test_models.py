from sqlalchemy import Numeric

import app.models  # noqa: F401  (registers the tables)
from app.db.session import Base
from app.models.interaction import EVENT_TYPES


def test_tables_registered():
    expected = {"users", "products", "interactions", "preferences", "saved_items",
                "recommendation_impressions", "refresh_tokens", "model_versions",
                "experiments", "evaluation_runs", "audit_logs"}
    assert expected <= set(Base.metadata.tables)


def test_price_is_fixed_precision_decimal():
    assert isinstance(Base.metadata.tables["products"].c.price.type, Numeric)


def test_event_types_match_the_srs():
    assert set(EVENT_TYPES) == {
        "view", "click", "search", "compare",
        "add_to_cart", "purchase", "save", "dismiss",
    }
