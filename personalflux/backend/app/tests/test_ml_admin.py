import numpy as np
from sqlalchemy import select

from app.ml.registry import registry
from app.models import AuditLog, EvaluationRun, Experiment, ModelVersion
from app.tests.conftest import user_headers
from app.tests.helpers import EDGES, ITEMS, write_artifact

ML = "/api/v1/ml"


def serving(client, headers):
    return client.get(f"{ML}/models", headers=headers).json()["serving"]


def test_health_is_public_and_reports_degraded_without_a_model(client):
    r = client.get(f"{ML}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded" and body["fallback_mode"] == "database_popularity"


def test_health_reports_ready_with_a_model(client, model):
    body = client.get(f"{ML}/health").json()
    assert body["status"] == "ready" and body["model_version"] == "v1"
    assert "recommendation_latency" in body


def test_scan_registers_validated_candidates(client, db, tmp_path):
    registry.root_override = tmp_path
    write_artifact(tmp_path, "v1", ITEMS, EDGES)
    write_artifact(tmp_path, "v2", ITEMS, EDGES)
    h = user_headers(client, db, "ml@shop.dev", role="ml_engineer")
    added = client.post(f"{ML}/models/scan", headers=h).json()["added"]
    assert sorted(v["version"] for v in added) == ["v1", "v2"]
    assert {v["status"] for v in added} == {"candidate"}
    assert client.post(f"{ML}/models/scan", headers=h).json()["added"] == []   # idempotent


def test_promotion_and_rollback(client, db, tmp_path):
    registry.root_override = tmp_path
    write_artifact(tmp_path, "v1", ITEMS, EDGES)
    write_artifact(tmp_path, "v2", ITEMS, EDGES)
    h = user_headers(client, db, "ml@shop.dev", role="ml_engineer")
    client.post(f"{ML}/models/scan", headers=h)

    assert client.post(f"{ML}/models/v1/promote", headers=h).json()["status"] == "serving"
    assert client.get(f"{ML}/health").json()["model_version"] == "v1"

    client.post(f"{ML}/models/v2/promote", headers=h)
    status = {v["version"]: v["status"] for v in client.get(f"{ML}/models", headers=h).json()["versions"]}
    assert status == {"v1": "retired", "v2": "serving"}

    client.post(f"{ML}/models/v1/promote", headers=h)               # rollback
    assert serving(client, h) == "v1"
    assert client.get(f"{ML}/health").json()["model_version"] == "v1"
    assert sum(1 for a in db.scalars(select(AuditLog)) if a.action == "model.promote") == 3


def test_a_tampered_model_is_never_promoted(client, db, tmp_path):
    registry.root_override = tmp_path
    write_artifact(tmp_path, "v1", ITEMS, EDGES)
    bad = write_artifact(tmp_path, "v2", ITEMS, EDGES)
    h = user_headers(client, db, "ml@shop.dev", role="ml_engineer")
    client.post(f"{ML}/models/scan", headers=h)
    client.post(f"{ML}/models/v1/promote", headers=h)

    np.save(bad / "items.npy", np.array([1, 2, 3], dtype=np.int64))   # corrupt after scanning
    r = client.post(f"{ML}/models/v2/promote", headers=h)
    assert r.status_code == 422 and "keeps serving" in r.json()["error"]["message"]
    assert serving(client, h) == "v1"                                   # previous model untouched
    assert client.get(f"{ML}/health").json()["model_version"] == "v1"
    db.expire_all()
    assert db.scalar(select(ModelVersion).where(ModelVersion.version == "v2")).status == "failed_validation"


def test_a_corrupt_artifact_is_flagged_at_scan_time(client, db, tmp_path):
    registry.root_override = tmp_path
    bad = write_artifact(tmp_path, "v9", ITEMS, EDGES)
    np.save(bad / "items.npy", np.array([1, 2], dtype=np.int64))
    h = user_headers(client, db, "ml@shop.dev", role="ml_engineer")
    added = client.post(f"{ML}/models/scan", headers=h).json()["added"]
    assert added[0]["status"] == "failed_validation"


def test_version_names_cannot_reach_other_paths(client, db, tmp_path):
    registry.root_override = tmp_path
    h = user_headers(client, db, "ml@shop.dev", role="ml_engineer")
    for name in ("bad$name", "x;y", "a b"):
        assert client.post(f"{ML}/models/{name}/promote", headers=h).status_code == 422
    assert client.post(f"{ML}/models/does-not-exist/promote", headers=h).status_code == 422


def test_only_operators_can_promote(client, db, tmp_path):
    registry.root_override = tmp_path
    write_artifact(tmp_path, "v1", ITEMS, EDGES)
    h = user_headers(client, db, "an@shop.dev", role="analyst")
    assert client.post(f"{ML}/models/v1/promote", headers=h).status_code == 403
    assert client.get(f"{ML}/models", headers=h).status_code == 200      # read-only is fine


def test_experiments_are_listed_separately_as_offline_results(client, db):
    exp = Experiment(name="final_test_eval", configuration={"protocol": "pre-registered"})
    db.add(exp)
    db.flush()
    db.add(EvaluationRun(experiment_id=exp.id, model_version="v1",
                         metrics={"set": "NEW_all_visitors", "model": "session_knn", "recall": 0.099}))
    db.commit()
    h = user_headers(client, db, "an@shop.dev", role="analyst")
    body = client.get(f"{ML}/experiments", headers=h).json()
    assert body[0]["kind"] == "offline_evaluation"
    assert body[0]["runs"][0]["metrics"]["recall"] == 0.099


def test_training_through_the_api_is_explicitly_not_implemented_and_is_audited(client, db):
    h = user_headers(client, db, "ml@shop.dev", role="ml_engineer")
    r = client.post(f"{ML}/training-runs", headers=h)
    assert r.status_code == 501
    assert any(a.action == "training.request" for a in db.scalars(select(AuditLog)))
