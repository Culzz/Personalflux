import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RecommendationImpression(Base):
    """A product a person actually saw, and where it sat in the list.

    `impression_id` is derived as `request_id:product_id`, so it is stable across
    retries and a later click can name the exact impression it came from. That is
    what makes a click attributable rather than merely countable.
    """
    __tablename__ = "recommendation_impressions"
    __table_args__ = (
        CheckConstraint(
            "user_id IS NOT NULL OR session_id IS NOT NULL", name="ck_impressions_has_actor"
        ),
        Index("ix_impressions_created", "created_at"),
        Index("ix_impressions_request", "request_id"),
        Index("ix_impressions_product_time", "product_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[str | None] = mapped_column(String(64))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    request_id: Mapped[str] = mapped_column(String(64))
    # Stable join key for the click that follows. Unique, so a replayed impression
    # report (a retry, a remount) cannot inflate the numbers.
    impression_id: Mapped[str] = mapped_column(String(120), unique=True)
    model_version: Mapped[str | None] = mapped_column(String(100))
    position: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
