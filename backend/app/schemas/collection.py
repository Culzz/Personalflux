import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.product import ProductOut

MAX_NAME = 80


class CollectionIn(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_NAME)

    @field_validator("name")
    @classmethod
    def _clean(cls, value: str) -> str:
        """Trim and collapse whitespace so "  Winter  picks " is not a second list."""
        name = " ".join(value.split())
        if not name:
            raise ValueError("a list needs a name")
        return name


class CollectionOut(BaseModel):
    id: uuid.UUID
    name: str
    item_count: int
    created_at: datetime
    updated_at: datetime


class CollectionDetail(BaseModel):
    id: uuid.UUID
    name: str
    items: list[ProductOut]
    created_at: datetime
    updated_at: datetime
