import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Numeric, String, Text, Uuid, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # The dataset's own item id, kept separate from our UUID (SRS section 6.2)
    source_item_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    # Marks where a row came from, so demo data is never mistaken for real data
    catalog_source: Mapped[str] = mapped_column(String(30), default="retailrocket", server_default="retailrocket")
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))  # exact decimals for money
    image_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
