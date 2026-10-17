import uuid
from datetime import datetime

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, func, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

PREFERENCE_TYPES = ("liked_categories", "blocked_categories", "liked_brands", "price_range")
_TYPES_SQL = ", ".join(f"'{t}'" for t in PREFERENCE_TYPES)


class Preference(Base):
    """A preference the customer stated themselves.

    It belongs to an account or to an anonymous session, so the first-visit
    onboarding works before anyone registers. Inferred preferences are computed
    from events and are never written here.
    """
    __tablename__ = "preferences"
    __table_args__ = (
        CheckConstraint("user_id IS NOT NULL OR session_id IS NOT NULL",
                        name="ck_preferences_has_actor"),
        CheckConstraint("user_id IS NULL OR session_id IS NULL",
                        name="ck_preferences_one_actor"),
        CheckConstraint(f"preference_type IN ({_TYPES_SQL})", name="ck_preferences_type"),
        CheckConstraint("source IN ('explicit', 'inferred')", name="ck_preferences_source"),
        # One row per owner and type. Partial indexes because only one owner column is set.
        Index("uq_preferences_user_type", "user_id", "preference_type", unique=True,
              postgresql_where=text("user_id IS NOT NULL")),
        Index("uq_preferences_session_type", "session_id", "preference_type", unique=True,
              postgresql_where=text("session_id IS NOT NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[str | None] = mapped_column(String(64))
    preference_type: Mapped[str] = mapped_column(String(40))
    preference_value: Mapped[dict | list] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(10), default="explicit", server_default="explicit")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
