from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from meridian.db.models.enums import CompJobStatus


class CompRequest(BaseModel):
    """Request schema for comp job creation."""
    subject_listing_id: UUID
    limit: int = Field(default=10, ge=1, le=50)


class CompResponse(BaseModel):
    """Response schema for a computed comparable."""
    id: UUID
    job_id: UUID
    subject_listing_id: UUID
    comp_listing_id: UUID
    distance_miles: float
    sold_date_delta_days: int
    raw_similarity: float
    adjustments: list[dict[str, Any]]
    adjusted_price: Decimal
    rank: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CompJobResponse(BaseModel):
    """Response schema for a comp job status."""
    id: UUID
    subject_listing_id: UUID
    status: CompJobStatus
    comp_ids: list[UUID]
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    comps: list[CompResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
