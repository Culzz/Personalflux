import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog


def record(db: Session, actor_id: uuid.UUID | None, action: str,
           target_type: str, target_id: str | None = None, details: dict | None = None) -> None:
    """Adds an audit row to the current transaction (the caller commits)."""
    db.add(AuditLog(actor_user_id=actor_id, action=action, target_type=target_type,
                    target_id=target_id, details=details))
