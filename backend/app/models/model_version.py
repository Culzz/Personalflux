import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

MODEL_STATUSES = ("candidate", "serving", "retired", "failed_validation")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('candidate', 'serving', 'retired', 'failed_validation')",
            name="ck_model_versions_status",
        ),
        # At most one version serves at a time. The partial unique index enforces
        # that in the database, so a race between two promotions cannot leave the
        # system with two active models.
        Index("uq_model_versions_one_serving", "status", unique=True,
              postgresql_where=text("status = 'serving'")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    version: Mapped[str] = mapped_column(String(100), unique=True)
    artifact_uri: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="candidate", server_default="candidate")
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
