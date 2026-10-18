"""An impression means "was displayed", and a click is traced to the model behind it."""
from sqlalchemy import select

from app.models import Interaction, RecommendationImpression
from app.tests.conftest import session_headers, user_headers

R = "/api/v1/recommendations"
A = "/api/v1/analytics"


def _impressions(client, request_id, items, model_version="v1"):
    return client.post(f"{R}/impressions", headers=session_headers(),
                       json={"request_id": request_id, "model_version": model_version,
                             "items": items})


def test_a_replayed_impression_report_is_not_counted_twice(client, db, products, model):
    items = [{"product_id": str(products[10].id), "position": 1},
             {"product_id": str(products[20].id), "position": 2}]
    assert _impressions(client, "req-replay00", items).json()["stored"] == 2
    # A remount, a retry, or a second visibility change reports the same cards again.
    assert _impressions(client, "req-replay00", items).json()["stored"] == 0

    rows = sorted(db.scalars(select(RecommendationImpression)).all(),
                  key=lambda r: r.position)
    assert len(rows) == 2
    assert rows[0].impression_id == f"req-replay00:{products[10].id}"


def test_a_click_is_attributed_to_the_impression_that_was_shown(client, db, products, model):
    product = products[10]
    _impressions(client, "req-click000", [{"product_id": str(product.id), "position": 3}])

    r = client.post("/api/v1/events", headers=session_headers(), json={
        "event_type": "click", "product_id": str(product.id),
        "context": {"source": "recommendation", "request_id": "req-click000",
                    "position": 3, "model_version": "v1"}})
    assert r.status_code == 201

    row = db.scalars(select(Interaction).where(Interaction.event_type == "click")).one()
    assert row.request_id == "req-click000"
    assert row.impression_id == f"req-click000:{product.id}"    # the same key the impression used
    assert row.position == 3 and row.model_version == "v1"


def test_analytics_separates_attributed_clicks_from_plain_ones(client, db, products, model):
    _impressions(client, "req-perf0000", [{"product_id": str(products[10].id), "position": 1}])
    # No model version: this impression came from the popularity fallback.
    _impressions(client, "req-perf0001", [{"product_id": str(products[20].id), "position": 1}],
                 model_version=None)
    client.post("/api/v1/events", headers=session_headers(), json={
        "event_type": "click", "product_id": str(products[10].id),
        "context": {"source": "recommendation", "request_id": "req-perf0000", "position": 1}})

    headers = user_headers(client, db, "an@shop.dev", role="analyst")
    body = client.get(f"{A}/recommendations", headers=headers).json()
    assert body["impressions"] == 2
    assert body["impressions_by_model_version"]["v1"] == 1
    assert body["fallback_impressions"] == 1 and body["fallback_rate"] == 0.5
    assert body["attributed_clicks"] == 1
    assert body["click_through_rate"] == 0.5
    # Every number is explained where it is read.
    assert "impression" in body["definitions"] and "attributed_clicks" in body["definitions"]
