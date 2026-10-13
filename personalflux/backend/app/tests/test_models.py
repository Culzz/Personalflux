from sqlalchemy import Numeric

import app.models  # noqa: F401
from app.db.session import Base
from app.models.interaction import EVENT_TYPES


def test_tables_registered():
    assert {"users", "products", "interactions"} <= set(Base.metadata.tables)


def test_price_is_fixed_precision_decimal():
    assert isinstance(Base.metadata.tables["products"].c.price.type, Numeric)


def test_event_types_match_the_srs():
    assert set(EVENT_TYPES) == {
        "view",
        "click",
        "search",
        "compare",
        "add_to_cart",
        "purchase",
        "save",
        "dismiss",
    }
