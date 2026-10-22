import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.ml.registry import registry
from app.models import ModelVersion
from app.services.evaluation_import import import_evaluation_csv
from app.tests.helpers import EDGES, ITEMS, write_artifact


def boot():
    """Entering the TestClient context runs the real startup code."""
    return TestClient(app)


def test_startup_loads_the_model_named_by_the_pointer_file_and_registers_it(db, tmp_path):
    registry.root_override = tmp_path
    write_artifact(tmp_path, "v1", ITEMS, EDGES)
    (tmp_path / "current_version.txt").write_text("v1")
    with boot() as c:
        assert c.get("/api/v1/ml/health").json()["model_version"] == "v1"
    row = db.scalar(select(ModelVersion).where(ModelVersion.version == "v1"))
    assert row is not None and row.status == "serving"


def test_startup_prefers_the_serving_version_recorded_in_the_database(db, tmp_path):
    registry.root_override = tmp_path
    write_artifact(tmp_path, "v1", ITEMS, EDGES)
    write_artifact(tmp_path, "v2", ITEMS, EDGES)
    (tmp_path / "current_version.txt").write_text("v1")
    db.add(ModelVersion(version="v2", artifact_uri="artifacts/v2", status="serving"))
    db.commit()
    with boot() as c:
        assert c.get("/api/v1/ml/health").json()["model_version"] == "v2"


def test_startup_survives_a_missing_model(db, tmp_path):
    registry.root_override = tmp_path          # empty folder, no pointer file
    with boot() as c:
        assert c.get("/health").status_code == 200
        body = c.get("/api/v1/ml/health").json()
        assert body["status"] == "degraded" and body["reason"] == "no model configured"


def test_startup_survives_a_corrupt_model_and_does_not_serve_it(db, tmp_path):
    registry.root_override = tmp_path
    bad = write_artifact(tmp_path, "v1", ITEMS, EDGES)
    np.save(bad / "items.npy", np.array([1], dtype=np.int64))
    (tmp_path / "current_version.txt").write_text("v1")
    with boot() as c:
        assert c.get("/health").status_code == 200
        body = c.get("/api/v1/ml/health").json()
        assert body["status"] == "degraded" and body["model_loaded"] is False


def test_evaluation_csv_import_is_idempotent(db, tmp_path):
    p = tmp_path / "test_eval.csv"
    p.write_text("set,model,k,sessions,recall,ndcg,mrr,coverage\n"
                 "NEW_all_visitors,session_knn,10,305,0.0989,0.0682,0.0728,0.0112\n"
                 "NEW_all_visitors,popularity_14d,10,305,0.0028,0.0025,0.0055,0.0001\n", encoding="utf-8")
    first = import_evaluation_csv(db, p, "final_test_eval_v0.1")
    second = import_evaluation_csv(db, p, "final_test_eval_v0.1")
    assert first["runs_added"] == 2 and second["skipped"] is True
    from app.models import EvaluationRun
    run = db.scalars(select(EvaluationRun)).first()
    assert isinstance(run.metrics["recall"], float) and isinstance(run.metrics["k"], int)
