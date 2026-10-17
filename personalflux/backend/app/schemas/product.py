import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str | None = None
    category: str | None = None
    price: Decimal | None = None          # JSON string such as "12.50": exact, not a float
    image_url: str | None = None
    brand: str | None = None
    stock: int | None = None
    currency: str | None = None
    external_url: str | None = None
    is_active: bool
    catalog_source: str


class ProductPage(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int


class CategoryCount(BaseModel):
    category: str
    products: int


class ProductCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, max_length=100)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    image_url: str | None = Field(default=None, max_length=500, pattern=r"^https?://")
    is_active: bool = True


class ProductUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, max_length=100)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    image_url: str | None = Field(default=None, max_length=500, pattern=r"^https?://")
    is_active: bool | None = None


class ViewedProduct(BaseModel):
    product: ProductOut
    last_seen: datetime
