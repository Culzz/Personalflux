import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.product import ProductOut


class PriceRange(BaseModel):
    min: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    max: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)

    @model_validator(mode="after")
    def _ordered(self):
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must not be greater than max")
        return self


class PreferencesPatch(BaseModel):
    """Send only what you want to change. null or [] clears that preference."""
    liked_categories: list[str] | None = Field(default=None, max_length=20)
    blocked_categories: list[str] | None = Field(default=None, max_length=20)
    liked_brands: list[str] | None = Field(default=None, max_length=20)
    price_range: PriceRange | None = None


class CategoryShare(BaseModel):
    category: str
    share: float


class InferredProfile(BaseModel):
    long_term_categories: list[CategoryShare]
    recent_categories: list[CategoryShare]
    events_considered: int
    note: str = "Inferred from your activity. You can reset it at any time."


class PreferencesOut(BaseModel):
    explicit: dict
    inferred: InferredProfile
    profile_reset_at: datetime | None


class SettingsPatch(BaseModel):
    tracking_consent: bool


class DeleteAccountIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class SavedOut(BaseModel):
    product: ProductOut
    saved_at: datetime
