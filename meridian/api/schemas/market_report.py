from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from meridian.db.models.enums import GeoType


class MarketReportBase(BaseModel):
    """Base schema for market report data."""

    geography: str
    geo_type: GeoType
    report_date: date
    median_price: Decimal
    mean_price: Decimal
    active_listings: int
    sold_last_30d: int
    avg_days_on_market: float
    months_of_inventory: float
    absorption_rate: float
    yoy_price_change: float
    mom_price_change: float
    list_to_sold_ratio: float
    raw_metrics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketReportResponse(MarketReportBase):
    """Response schema for market report data."""

    id: UUID


class MarketReportRefreshRequest(BaseModel):
    """Request schema for refreshing market reports."""

    geography: str
    geo_type: GeoType
    as_of: date | None = None
