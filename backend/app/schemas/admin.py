import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Role = Literal["customer", "analyst", "admin", "ml_engineer"]


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime


class AdminUserPatch(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    target_type: str
    target_id: str | None
    details: dict | None
    created_at: datetime
