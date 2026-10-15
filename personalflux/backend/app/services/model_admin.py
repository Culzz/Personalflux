"""Model registry operations: scan disk, validate, promote, roll back, bootstrap at startup."""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.ml.registry import registry
from app.models import ModelVersion
from app.services import audit

logger = logging.getLogger("personaflux")

_SUMMARY_KEYS = ("trained_on", "data_window", "n_events", "n_items", "n_similarity_pairs",
                 "code_version", "created_at_utc", "evaluation_report")


class PromotionError(Exception):
    pass


def _summary(meta: dict) -> dict:
    return {k: meta[k] for k in _SUMMARY_KEYS if k in meta}


def scan_versions(db: Session) -> list[ModelVersion]:
    """Register artifact folders on disk that the database does not know yet."""
    known = set(db.scalars(select(ModelVersion.version)))
    added = []
    for version in registry.list_on_disk():
        if version in known:
            continue
        try:
            meta = registry.verify_version(version)
            status, details = "candidate", _summary(meta)
        except Exception as e:
            status, details = "failed_validation", {"error": str(e)[:200]}
        row = ModelVersion(version=version, artifact_uri=f"artifacts/{version}",
                           status=status, details=details)
        db.add(row)
        added.append(row)
    db.commit()
    return added


def promote_version(db: Session, actor_id: uuid.UUID | None, version: str) -> ModelVersion:
    """Validate (checksums + shape), then make this version the one that serves.

    Promoting an older version is how you roll back. A version that fails
    validation never becomes the serving model, and the current one keeps serving.
    """
    try:
        model = registry.load_version(version)
    except Exception as e:
        row = db.scalar(select(ModelVersion).where(ModelVersion.version == version))
        if row is not None and row.status != "serving":
            row.status = "failed_validation"
            row.details = {**(row.details or {}), "error": str(e)[:200]}
            db.commit()
        raise PromotionError(str(e)[:200])

    row = db.scalar(select(ModelVersion).where(ModelVersion.version == version))
    if row is None:
        row = ModelVersion(version=version, artifact_uri=f"artifacts/{version}",
                           status="candidate", details=_summary(model.metadata))
        db.add(row)
        db.flush()
    previous = db.scalars(select(ModelVersion).where(
        ModelVersion.status == "serving", ModelVersion.version != version)).all()
    for p in previous:
        p.status = "retired"
    row.status = "serving"
    row.promoted_at = datetime.now(timezone.utc)
    audit.record(db, actor_id, "model.promote", "model_version", version,
                 {"previous": [p.version for p in previous]})
    db.commit()
    registry.set_model(model)       # only after the database change succeeded
    return row


def startup_load_model() -> None:
    """Called once when the API starts. Never raises: a missing model means fallback mode."""
    version = None
    try:
        with SessionLocal() as db:
            row = db.scalar(select(ModelVersion).where(ModelVersion.status == "serving"))
            if row is not None:
                version = row.version
    except Exception:
        logger.warning("could not read the serving model from the database")
    if version is None:
        pointer = registry.artifact_root / "current_version.txt"
        if pointer.exists():
            version = pointer.read_text().strip()
    if not version:
        registry.set_model(None, "no model configured")
        return
    try:
        model = registry.load_version(version)
    except Exception as e:
        logger.error("model %s failed to load: %s", version, str(e)[:200])
        registry.set_model(None, "model failed validation or could not be loaded")
        return
    registry.set_model(model)
    try:
        with SessionLocal() as db:
            row = db.scalar(select(ModelVersion).where(ModelVersion.version == version))
            other = db.scalar(select(ModelVersion).where(
                ModelVersion.status == "serving", ModelVersion.version != version))
            now = datetime.now(timezone.utc)
            if row is None:
                db.add(ModelVersion(
                    version=version, artifact_uri=f"artifacts/{version}",
                    status="serving" if other is None else "candidate",
                    details=_summary(model.metadata),
                    promoted_at=now if other is None else None))
            elif row.status != "serving" and other is None:
                row.status, row.promoted_at = "serving", now
            db.commit()
    except Exception:
        logger.warning("could not record the serving model in the database")
