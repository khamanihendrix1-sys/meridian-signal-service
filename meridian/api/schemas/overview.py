from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from meridian.api.schemas.market_report import MarketReportResponse
from meridian.api.schemas.signal import SignalLogResponse
from meridian.db.models.enums import GeoType


class ListingCounts(BaseModel):
    """Aggregated listing counts broken down by lifecycle status."""

    total: int = 0
    active: int = 0
    pending: int = 0
    sold: int = 0
    expired: int = 0
    withdrawn: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)


class SignalCounts(BaseModel):
    """Aggregated signal-evaluation counts."""

    total_evaluations: int = 0
    fired: int = 0
    definitions: int = 0


class OverviewResponse(BaseModel):
    """Dashboard overview aggregating listings, signals, and market data."""

    geography: str | None = None
    geo_type: GeoType | None = None
    generated_at: datetime
    listings: ListingCounts = Field(default_factory=ListingCounts)
    signals: SignalCounts = Field(default_factory=SignalCounts)
    recent_signals: list[SignalLogResponse] = Field(default_factory=list)
    latest_market_report: MarketReportResponse | None = None
