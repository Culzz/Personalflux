import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

PREFERENCE_TYPES = ("liked_categories", "blocked_categories", "price_range")
_TYPES_SQL = ", ".join(f"'{t}'" for t in PREFERENCE_TYPES)


class Preference(Base):
    """Explicit preferences the customer stated. Inferred ones are computed, not stored."""
    __tablename__ = "preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "preference_type", name="uq_preferences_user_type"),
        CheckConstraint(f"preference_type IN ({_TYPES_SQL})", name="ck_preferences_type"),
        CheckConstraint("source IN ('explicit', 'inferred')", name="ck_preferences_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    preference_type: Mapped[str] = mapped_column(String(40))
    preference_value: Mapped[dict | list] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(10), default="explicit", server_default="explicit")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
