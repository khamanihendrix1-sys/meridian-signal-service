from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from meridian.db.models.enums import GeoType, SignalCategory


class SignalDefinitionBase(BaseModel):
    """Base schema for signal definition data."""
    name: str
    category: SignalCategory
    description: str
    refresh_frequency: str
    output_schema: dict = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class SignalDefinitionResponse(SignalDefinitionBase):
    """Response schema for signal definition data."""
    id: UUID


class SignalLogBase(BaseModel):
    """Base schema for signal log data."""
    signal_id: UUID
    geography: str
    geo_type: GeoType
    timestamp: datetime
    raw_value: float
    computed_output: dict = Field(default_factory=dict)
    confidence: float
    fired: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SignalLogResponse(SignalLogBase):
    """Response schema for signal log data."""
    id: UUID


class SignalEvaluateRequest(BaseModel):
    """Request schema for triggering signal evaluation."""
    geography: str
    geo_type: GeoType
    run_id: Optional[str] = None