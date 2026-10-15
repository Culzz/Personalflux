import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

EVENT_TYPES = (
    "view", "click", "search", "compare",
    "add_to_cart", "purchase", "save", "dismiss",
)
_TYPES_SQL = ", ".join(f"'{t}'" for t in EVENT_TYPES)


class Interaction(Base):
    __tablename__ = "interactions"
    __table_args__ = (
        CheckConstraint(f"event_type IN ({_TYPES_SQL})", name="ck_interactions_event_type"),
        CheckConstraint(
            "user_id IS NOT NULL OR session_id IS NOT NULL", name="ck_interactions_has_actor"
        ),
        CheckConstraint(
            "event_type = 'search' OR product_id IS NOT NULL", name="ck_interactions_has_product"
        ),
        Index("ix_interactions_user_time", "user_id", "occurred_at"),
        Index("ix_interactions_session_time", "session_id", "occurred_at"),
        Index("ix_interactions_product", "product_id"),
        Index("ix_interactions_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Deleting a user deletes their events (supports the account-deletion workflow)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[str | None] = mapped_column(String(64))
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    event_type: Mapped[str] = mapped_column(String(20))
    context: Mapped[dict | None] = mapped_column(JSONB)
    # A client-supplied key so a retried request is not stored twice (SRS FR-03)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
