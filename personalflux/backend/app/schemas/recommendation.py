import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.product import ProductOut


class RecommendationItem(BaseModel):
    product_id: uuid.UUID
    product: ProductOut
    rank: int
    score: float          # a ranking score, NOT a purchase probability
    source: Literal["similarity", "popularity", "popularity_fallback"]
    reason_codes: list[str]
    explanation: str


class RecommendationResponse(BaseModel):
    request_id: str | None
    model_version: str | None
    strategy: str
    fallback_used: bool
    recommendations: list[RecommendationItem]


class ImpressionItem(BaseModel):
    product_id: uuid.UUID
    position: int = Field(ge=1, le=200)


class ImpressionsIn(BaseModel):
    request_id: str = Field(min_length=1, max_length=64)
    model_version: str | None = Field(default=None, max_length=100)
    items: list[ImpressionItem] = Field(min_length=1, max_length=100)


class FeedbackIn(BaseModel):
    product_id: uuid.UUID
    feedback: Literal["save", "dismiss"]
    request_id: str | None = Field(default=None, max_length=64)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=64,
                                        pattern=r"^[A-Za-z0-9_-]+$")
