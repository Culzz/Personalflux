"""Named lists a customer curates out of the products they keep."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Collection(Base):
    """One list. A customer can keep several, each with its own name."""

    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_collections_user_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CollectionItem(Base):
    """A product on a list. The product row itself is never owned or removed here."""

    __tablename__ = "collection_items"

    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
