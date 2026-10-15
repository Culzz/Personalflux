import uuid

from sqlalchemy import func, select

from app.ml.registry import registry
from app.models import Interaction, RecommendationImpression, SavedItem
from app.tests.conftest import session_headers, user_headers

R = "/api/v1/recommendations"
EV = "/api/v1/events"


def view(client, product, headers=None, event="view"):
    r = client.post(EV, headers=headers or session_headers(),
                    json={"event_type": event, "product_id": str(product.id)})
    assert r.status_code == 201, r.text


def titles(body):
    return [r["product"]["title"] for r in body["recommendations"]]


def test_new_visitor_gets_a_valid_popularity_feed(client, products, model):
    r = client.get(f"{R}/home")
    assert r.status_code == 200
    body = r.json()
    assert body["strategy"] == "popularity" and body["fallback_used"] is True
    assert body["model_version"] == "v1"
    assert titles(body) == ["Item 10", "Item 20", "Item 30", "Item 40"]
    assert {x["source"] for x in body["recommendations"]} == {"popularity_fallback"}
    assert body["recommendations"][0]["explanation"] == "Popular with other shoppers."
    assert [x["rank"] for x in body["recommendations"]] == [1, 2, 3, 4]


def test_what_you_just_viewed_shapes_the_feed_with_a_grounded_explanation(client, products, model):
    view(client, products[10])
    body = client.get(f"{R}/home", headers=session_headers()).json()
    assert body["strategy"] == "session_based"
    assert titles(body)[:2] == ["Item 20", "Item 30"]          # most similar to Item 10 first
    first = body["recommendations"][0]
    assert first["source"] == "similarity"
    assert first["reason_codes"] == ["similar_to_session_items"]
    assert "Item 10" in first["explanation"]                   # names the item it is based on
    assert "Item 10" not in titles(body)                       # what you are viewing is not repeated
    assert body["recommendations"][-1]["source"] == "popularity_fallback"


def test_feed_changes_when_recent_interest_changes(client, db, products, model):
    h = session_headers()
    view(client, products[10], h)
    before = titles(client.get(f"{R}/home", headers=h).json())
    db.query(Interaction).delete()
    db.commit()
    view(client, products[30], h)
    after = titles(client.get(f"{R}/home", headers=h).json())
    assert before[0] == "Item 20" and after[0] == "Item 40" and before != after


def test_other_visitors_do_not_influence_my_feed(client, products, model):
    view(client, products[10], session_headers("sess-aaaaaaaa"))
    mine = client.get(f"{R}/home", headers=session_headers("sess-bbbbbbbb")).json()
    assert mine["strategy"] == "popularity"


def test_inactive_products_are_never_recommended(client, db, products, model):
    view(client, products[10])
    products[20].is_active = False
    db.commit()
    body = client.get(f"{R}/home", headers=session_headers()).json()
    assert "Item 20" not in titles(body) and titles(body)[0] == "Item 30"
    assert "Item 20" not in titles(client.get(f"{R}/trending").json())


def test_purchased_products_are_not_recommended_again(client, products, model):
    view(client, products[10])
    view(client, products[20], event="purchase")
    assert "Item 20" not in titles(client.get(f"{R}/home", headers=session_headers()).json())


def test_dismissed_products_disappear(client, products, model):
    view(client, products[10])
    assert "Item 30" in titles(client.get(f"{R}/home", headers=session_headers()).json())
    r = client.post(f"{R}/feedback", headers=session_headers(),
                    json={"product_id": str(products[30].id), "feedback": "dismiss"})
    assert r.status_code == 201
    assert "Item 30" not in titles(client.get(f"{R}/home", headers=session_headers()).json())


def test_blocked_categories_are_respected(client, db, products, model):
    h = user_headers(client, db, "u@shop.dev", consent=True)
    client.patch("/api/v1/customers/me/preferences", headers=h,
                 json={"blocked_categories": ["Category A"]})
    client.post(EV, headers=h, json={"event_type": "view", "product_id": str(products[30].id)})
    body = client.get(f"{R}/home", headers=h).json()
    assert titles(body) == ["Item 40"]                          # Items 10 and 20 are Category A


def test_stated_category_preference_shapes_cold_start_and_is_explained(client, db, products, model):
    h = user_headers(client, db, "u@shop.dev", consent=False)
    client.patch("/api/v1/customers/me/preferences", headers=h,
                 json={"liked_categories": ["Category B"]})
    body = client.get(f"{R}/home", headers=h).json()
    assert titles(body)[:2] == ["Item 30", "Item 40"]
    assert "matches_stated_preference" in body["recommendations"][0]["reason_codes"]


def test_category_context_filters_the_feed(client, products, model):
    body = client.get(f"{R}/home", params={"category": "Category B"}).json()
    assert titles(body) == ["Item 30", "Item 40"]
    assert body["recommendations"][0]["explanation"] == "Popular in the category you are exploring."


def test_long_term_history_contributes_when_the_session_is_empty(client, db, products, model):
    h = user_headers(client, db, "u@shop.dev", consent=True)
    from datetime import datetime, timedelta, timezone
    old = datetime.now(timezone.utc) - timedelta(days=3)
    client.post(EV, headers=h, json={"event_type": "add_to_cart", "product_id": str(products[10].id),
                                     "occurred_at": old.isoformat()})
    body = client.get(f"{R}/home", headers=h).json()
    assert body["strategy"] == "history_based"
    assert body["recommendations"][0]["reason_codes"] == ["similar_to_history"]


def test_without_a_model_the_api_still_serves_a_safe_feed(client, products):
    assert registry.model is None
    r = client.get(f"{R}/home")
    assert r.status_code == 200
    body = r.json()
    assert body["model_version"] is None and body["fallback_used"] is True
    assert len(body["recommendations"]) == 4
    assert client.get("/api/v1/ml/health").json()["status"] == "degraded"


def test_a_failing_ranker_falls_back_instead_of_erroring(client, products, model, monkeypatch):
    view(client, products[10])

    def boom(*a, **k):
        raise RuntimeError("ranker exploded")

    monkeypatch.setattr(model, "score_session", boom)
    r = client.get(f"{R}/home", headers=session_headers())
    assert r.status_code == 200
    assert r.json()["fallback_used"] is True and r.json()["model_version"] is None
    assert "ranker exploded" not in r.text


def test_similar_products_endpoint(client, products, model):
    body = client.get(f"{R}/similar/{products[10].id}").json()
    assert titles(body) == ["Item 20", "Item 30"]
    assert body["strategy"] == "item_similarity"
    assert "Item 10" in body["recommendations"][0]["explanation"]
    assert client.get(f"{R}/similar/{uuid.uuid4()}").status_code == 404


def test_similar_for_inactive_product_is_404(client, db, products, model):
    products[10].is_active = False
    db.commit()
    assert client.get(f"{R}/similar/{products[10].id}").status_code == 404


def test_trending(client, products, model):
    body = client.get(f"{R}/trending").json()
    assert titles(body) == ["Item 10", "Item 20", "Item 30", "Item 40"]
    assert body["fallback_used"] is False
    assert titles(client.get(f"{R}/trending", params={"category": "Category B"}).json()) == ["Item 30", "Item 40"]


def test_limit_is_bounded(client, products, model):
    assert client.get(f"{R}/home", params={"limit": 51}).status_code == 422
    assert client.get(f"{R}/home", params={"limit": 0}).status_code == 422
    assert len(client.get(f"{R}/home", params={"limit": 2}).json()["recommendations"]) == 2


def test_scores_are_ranking_scores_in_unit_range(client, products, model):
    view(client, products[10])
    for rec in client.get(f"{R}/home", headers=session_headers()).json()["recommendations"]:
        assert 0.0 <= rec["score"] <= 1.0


def test_impressions_are_recorded_with_positions(client, db, products, model):
    body = {"request_id": "req-12345678", "model_version": "v1",
            "items": [{"product_id": str(products[10].id), "position": 1},
                      {"product_id": str(products[20].id), "position": 2}]}
    r = client.post(f"{R}/impressions", headers=session_headers(), json=body)
    assert r.status_code == 201 and r.json()["stored"] == 2
    rows = db.scalars(select(RecommendationImpression).order_by(RecommendationImpression.position)).all()
    assert [x.position for x in rows] == [1, 2] and rows[0].session_id == "sess-aaaaaaaa"


def test_impressions_reject_unknown_products_and_missing_identity(client, products):
    bad = {"request_id": "req-12345678", "items": [{"product_id": str(uuid.uuid4()), "position": 1}]}
    assert client.post(f"{R}/impressions", headers=session_headers(), json=bad).status_code == 422
    ok = {"request_id": "req-12345678", "items": [{"product_id": str(products[10].id), "position": 1}]}
    assert client.post(f"{R}/impressions", json=ok).status_code == 400


def test_saving_from_a_recommendation_adds_to_saved_items(client, db, products, model):
    h = user_headers(client, db, "u@shop.dev", consent=True)
    r = client.post(f"{R}/feedback", headers=h,
                    json={"product_id": str(products[20].id), "feedback": "save", "request_id": "req-1234"})
    assert r.status_code == 201
    assert db.scalar(select(func.count()).select_from(SavedItem)) == 1
