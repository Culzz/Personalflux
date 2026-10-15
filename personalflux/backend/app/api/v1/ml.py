import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core import metrics
from app.db.session import get_db
from app.ml.registry import registry
from app.models import EvaluationRun, Experiment, ModelVersion, User
from app.services import audit
from app.services.model_admin import PromotionError, promote_version, scan_versions

router = APIRouter(prefix="/ml", tags=["ml"])

readers = require_roles("analyst", "ml_engineer", "admin")
operators = require_roles("ml_engineer", "admin")


def _version_out(v: ModelVersion) -> dict:
    return {"version": v.version, "status": v.status, "details": v.details,
            "created_at": v.created_at, "promoted_at": v.promoted_at}


@router.get("/health")
def ml_health():
    """Readiness of the model service. Public, and contains no sensitive details."""
    m = registry.model
    return {
        "status": "ready" if m else "degraded",
        "model_loaded": m is not None,
        "model_version": m.version if m else None,
        "fallback_mode": None if m else "database_popularity",
        "reason": None if m else registry.error,
        "recommendation_latency": metrics.summary("recommendations"),
    }


@router.get("/models", dependencies=[Depends(readers)])
def list_models(db: Session = Depends(get_db)):
    rows = db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc())).all()
    return {"serving": registry.model.version if registry.model else None,
            "versions": [_version_out(v) for v in rows]}


@router.post("/models/scan")
def scan_models(user: User = Depends(operators), db: Session = Depends(get_db)):
    """Register artifact versions found on disk (validated, as candidates)."""
    added = scan_versions(db)
    return {"added": [_version_out(v) for v in added]}


@router.post("/models/{version}/promote")
def promote(version: str, user: User = Depends(operators), db: Session = Depends(get_db)):
    """Validate and serve this version. Promoting an older version is a rollback."""
    try:
        registry.folder_for(version)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid version name.")
    try:
        row = promote_version(db, user.id, version)
    except PromotionError as e:
        raise HTTPException(status_code=422,
                            detail=f"Validation failed; the current model keeps serving. ({e})")
    return _version_out(row)


@router.get("/experiments", dependencies=[Depends(readers)])
def list_experiments(db: Session = Depends(get_db)):
    """Offline evaluation results, kept separate from live engagement metrics."""
    exps = db.scalars(select(Experiment).order_by(Experiment.created_at.desc())).all()
    out = []
    for e in exps:
        runs = db.scalars(select(EvaluationRun).where(EvaluationRun.experiment_id == e.id)
                          .order_by(EvaluationRun.created_at)).all()
        out.append({"id": e.id, "name": e.name, "configuration": e.configuration,
                    "created_at": e.created_at, "kind": "offline_evaluation",
                    "runs": [{"model_version": r.model_version, "metrics": r.metrics}
                             for r in runs]})
    return out


@router.post("/training-runs")
def request_training_run(user: User = Depends(operators), db: Session = Depends(get_db)):
    """Not implemented on purpose. Training needs a background job runner, which the SRS
    defers until it is needed. Run ml/src/train_model.py, then POST /ml/models/scan."""
    audit.record(db, user.id, "training.request", "training_run", None, {"outcome": "not_implemented"})
    db.commit()
    raise HTTPException(
        status_code=501,
        detail="Training is run offline with ml/src/train_model.py, then registered with POST /ml/models/scan.")
