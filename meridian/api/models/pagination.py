from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper used across list endpoints."""

    items: list[T] = Field(..., description="Page of result items")
    next_cursor: str | None = Field(
        None,
        description="Opaque cursor to pass as `cursor` in the next request; null when no more pages",
    )
    has_more: bool = Field(
        ...,
        description="True when additional pages are available",
    )
    total_count: int | None = Field(
        None,
        description="Total number of matching items across all pages (may be omitted for performance)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [],
                "next_cursor": "eyJpZCI6ICI1MCJ9",
                "has_more": True,
                "total_count": None,
            }
        }
    }
