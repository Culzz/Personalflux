import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import AuditLog, RefreshToken, User
from app.schemas.admin import AdminUserOut, AdminUserPatch, AuditLogOut
from app.services import audit

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_roles("admin")


@router.get("/users", response_model=list[AdminUserOut])
def list_users(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
               admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.created_at.desc(), User.id)
                      .offset((page - 1) * page_size).limit(page_size)).all()


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(user_id: uuid.UUID, payload: AdminUserPatch,
                admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot change your own role or status.")
    changes = payload.model_dump(exclude_unset=True)
    if any(v is None for v in changes.values()):
        raise HTTPException(status_code=422, detail="Fields cannot be null.")
    for field, value in changes.items():
        setattr(target, field, value)
    if changes.get("is_active") is False:      # deactivated users lose their sessions
        db.execute(update(RefreshToken)
                   .where(RefreshToken.user_id == target.id, RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=datetime.now(timezone.utc)))
    audit.record(db, admin.id, "user.update", "user", str(target.id), changes)
    db.commit()
    db.refresh(target)
    return target


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(limit: int = Query(100, ge=1, le=500), admin: User = Depends(admin_only),
               db: Session = Depends(get_db)):
    return db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
