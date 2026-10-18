"""Model registry operations: scan disk, validate, promote, roll back, bootstrap at startup.

Promotion writes the chosen version to the database under an advisory lock, so
only one promotion can run at a time and at most one version is ever marked
serving. Each worker then discovers the change on its next poll and hot-swaps,
which is what makes a promotion (or a rollback) reach every process without a
restart. The artefact itself is immutable, so a worker that is mid-request keeps
serving the version it already has until the swap completes.
"""
import logging
import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.ml.registry import registry
from app.models import ModelVersion
from app.services import audit

logger = logging.getLogger("personaflux")

# Any constant works; it only has to be the same number in every process.
_PROMOTION_LOCK_KEY = 0x9E3779B1

_SUMMARY_KEYS = ("trained_on", "data_window", "n_events", "n_items", "n_similarity_pairs",
                 "code_version", "created_at_utc", "evaluation_report")


class PromotionError(Exception):
    pass


def _summary(meta: dict) -> dict:
    return {k: meta[k] for k in _SUMMARY_KEYS if k in meta}


def serving_version(db: Session) -> str | None:
    """The version the database says should serve, regardless of what this worker has loaded."""
    return db.scalar(select(ModelVersion.version).where(ModelVersion.status == "serving"))



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
    Serialised with a Postgres advisory lock so two operators cannot interleave.
    """
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _PROMOTION_LOCK_KEY})
    try:
        model = registry.load_version(version)   # verify checksums + shape before touching the pointer
    except Exception as e:
        row = db.scalar(select(ModelVersion).where(ModelVersion.version == version))
        if row is not None and row.status != "serving":
            row.status = "failed_validation"
            row.details = {**(row.details or {}), "error": str(e)[:200]}
            db.commit()
        raise PromotionError(str(e)[:200])

    # Retire the current one first: the partial unique index allows exactly one
    # serving row, so the old status must change before the new one is set.
    previous = list(db.scalars(select(ModelVersion.version).where(
        ModelVersion.status == "serving", ModelVersion.version != version)))
    db.execute(update(ModelVersion)
               .where(ModelVersion.status == "serving", ModelVersion.version != version)
               .values(status="retired"))
    row = db.scalar(select(ModelVersion).where(ModelVersion.version == version))
    if row is None:
        row = ModelVersion(version=version, artifact_uri=f"artifacts/{version}",
                           status="serving", details=_summary(model.metadata))
        db.add(row)
    else:
        row.status = "serving"
        row.details = _summary(model.metadata)
    row.promoted_at = datetime.now(timezone.utc)
    db.flush()
    audit.record(db, actor_id, "model.promote", "model_version", version,
                 {"previous_serving": previous})
    db.commit()

    # Only after the pointer is durable does this worker swap what it serves.
    registry.set_model(model)
    registry.desired_version = version
    registry.mark_checked()
    return row


def enforce_single_serving(db: Session) -> None:
    """Defensive tidy-up for a database that predates the unique index."""
    serving = db.scalars(select(ModelVersion).where(ModelVersion.status == "serving")
                         .order_by(ModelVersion.promoted_at.desc().nulls_last())).all()
    for extra in serving[1:]:
        extra.status = "retired"
    db.commit()


def poll_once() -> str | None:
    """Compare the database pointer with this worker's model and hot-swap if needed.

    Never raises: a failed poll leaves the current model in place so requests keep
    working, and records the error for /ml/health.
    """
    try:
        with SessionLocal() as db:
            target = serving_version(db)
    except Exception as e:
        logger.warning("model version poll could not read the database: %s", str(e)[:200])
        registry.mark_checked(f"database read failed: {str(e)[:200]}")
        return registry.serving_version

    registry.desired_version = target
    if target is None:
        registry.mark_checked("no version is marked serving")
        return registry.serving_version
    if target == registry.serving_version:
        registry.mark_checked()
        return target
    try:
        model = registry.load_version(target)     # immutable artefact: verify, then swap
    except Exception as e:
        logger.error("model %s could not be loaded; keeping %s: %s",
                     target, registry.serving_version, str(e)[:200])
        registry.mark_checked(f"{target} failed to load: {str(e)[:200]}")
        return registry.serving_version
    registry.set_model(model)
    logger.info("hot-swapped the serving model to %s", target)
    registry.mark_checked()
    return target


_stop = threading.Event()
_thread: threading.Thread | None = None


def _run_poller() -> None:
    while not _stop.wait(settings.model_poll_seconds):
        poll_once()


def start_version_poller() -> None:
    """One daemon thread per worker. Off by default in tests."""
    global _thread
    if not settings.enable_model_poller:
        return
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_run_poller, name="model-version-poller", daemon=True)
    _thread.start()


def stop_version_poller() -> None:
    _stop.set()


def startup_load_model() -> None:
    """Called once when the API starts. Never raises: a missing model means fallback mode."""
    version = None
    try:
        with SessionLocal() as db:
            version = serving_version(db)
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
    registry.desired_version = version
    registry.mark_checked()
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
