import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

EventType = Literal["view", "click", "search", "compare", "add_to_cart", "purchase", "save", "dismiss"]
# Raw search text is never stored (SRS section 11.2)
FORBIDDEN_CONTEXT_KEYS = {"query", "q", "search", "search_term", "text", "keywords"}


class EventIn(BaseModel):
    event_type: EventType
    product_id: uuid.UUID | None = None
    occurred_at: datetime | None = None
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=64,
                                        pattern=r"^[A-Za-z0-9_-]+$")
    context: dict[str, str | int | float | bool] | None = None

    @field_validator("context")
    @classmethod
    def _small_safe_context(cls, v):
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("context may have at most 10 keys")
        for key, val in v.items():
            if len(key) > 40 or key.lower() in FORBIDDEN_CONTEXT_KEYS:
                raise ValueError(f"context key not allowed: {key[:40]}")
            if isinstance(val, str) and len(val) > 100:
                raise ValueError("context values may be at most 100 characters")
        return v

    @model_validator(mode="after")
    def _product_required_unless_search(self):
        if self.event_type != "search" and self.product_id is None:
            raise ValueError("product_id is required for this event type")
        return self


class EventOut(BaseModel):
    stored: bool
    duplicate: bool = False
    reason: str | None = None
    event_id: uuid.UUID | None = None
