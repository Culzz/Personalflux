from app.tests.conftest import session_headers, user_headers

A = "/api/v1/analytics"
EV = "/api/v1/events"
R = "/api/v1/recommendations"


def seed(client, db, products):
    h = user_headers(client, db, "shopper@shop.dev", consent=True)
    for p, ev in [(products[10], "view"), (products[10], "view"), (products[20], "add_to_cart"),
                  (products[30], "purchase")]:
        client.post(EV, headers=h, json={"event_type": ev, "product_id": str(p.id)})
    client.post(EV, headers=session_headers(), json={"event_type": "view", "product_id": str(products[40].id)})
    body = {"request_id": "req-12345678",
            "items": [{"product_id": str(products[10].id), "position": 1},
                      {"product_id": str(products[20].id), "position": 2}]}
    client.post(f"{R}/impressions", headers=session_headers(), json=body)
    client.post(EV, headers=session_headers(), json={
        "event_type": "click", "product_id": str(products[10].id),
        "context": {"source": "recommendation", "request_id": "req-12345678"}})


def test_overview_counts_live_activity(client, db, products):
    seed(client, db, products)
    ha = user_headers(client, db, "analyst@shop.dev", role="analyst")
    body = client.get(f"{A}/overview", headers=ha).json()
    assert body["kind"] == "live_activity"
    assert body["events_by_type"] == {"view": 3, "add_to_cart": 1, "purchase": 1, "click": 1}
    assert body["events_total"] == 6
    assert body["products_active"] == 4 and body["active_customers"] == 1
    assert body["anonymous_sessions"] == 1 and body["impressions"] == 2


def test_categories_breakdown(client, db, products):
    seed(client, db, products)
    ha = user_headers(client, db, "analyst@shop.dev", role="analyst")
    cats = {c["category"]: c for c in client.get(f"{A}/categories", headers=ha).json()["categories"]}
    assert cats["Category A"]["events"] == 4 and cats["Category A"]["views"] == 2
    assert cats["Category B"]["purchases"] == 1


def test_segments_are_counts_only(client, db, products):
    seed(client, db, products)
    ha = user_headers(client, db, "analyst@shop.dev", role="analyst")
    segs = client.get(f"{A}/segments", headers=ha).json()["segments"]
    assert segs == [{"segment": "light (1-5 events)", "customers": 1}]


def test_recommendation_performance_is_live_data_with_ctr(client, db, products):
    seed(client, db, products)
    ha = user_headers(client, db, "analyst@shop.dev", role="analyst")
    body = client.get(f"{A}/recommendations", headers=ha).json()
    assert body["impressions"] == 2 and body["recommendation_requests_with_impressions"] == 1
    assert body["engagement_from_recommendations"] == {"click": 1}
    assert body["click_through_rate"] == 0.5
    assert "Not an offline model evaluation" in body["note"]


def test_analytics_never_expose_individuals(client, db, products):
    seed(client, db, products)
    ha = user_headers(client, db, "analyst@shop.dev", role="analyst")
    for path in ("overview", "categories", "segments", "recommendations"):
        text = client.get(f"{A}/{path}", headers=ha).text
        assert "shopper@shop.dev" not in text and "user_id" not in text and "session" not in text.replace("anonymous_sessions", "")


def test_window_is_bounded(client, db):
    ha = user_headers(client, db, "analyst@shop.dev", role="analyst")
    assert client.get(f"{A}/overview", headers=ha, params={"days": 0}).status_code == 422
    assert client.get(f"{A}/overview", headers=ha, params={"days": 366}).status_code == 422
