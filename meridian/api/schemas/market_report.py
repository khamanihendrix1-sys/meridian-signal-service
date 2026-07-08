from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from meridian.db.models.enums import GeoType, PropertyType


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


class MarketMetric(StrEnum):
    """Supported market-comparison metrics."""

    PRICE = "price"
    DOM = "dom"
    INVENTORY = "inventory"


class ScheduleFrequency(StrEnum):
    """Supported recurring-delivery cadences."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class RiskLevel(StrEnum):
    """Investment risk profile."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReportType(StrEnum):
    """Generated report identifiers persisted for export/history."""

    COMPARABLE_PROPERTIES = "comparable_properties"
    INVESTMENT_SIGNALS = "investment_signals"
    NEIGHBORHOOD_COMPARISON = "neighborhood_comparison"
    FORECAST = "forecast"
    HEAT_INDEX = "heat_index"
    SEASONAL = "seasonal"
    DEMOGRAPHICS = "demographics"
    CUSTOM_DASHBOARD = "custom_dashboard"


class GeneratedReportBase(BaseModel):
    """Common fields returned for generated market report artifacts."""

    id: UUID
    report_type: ReportType
    geography: str | None = None
    geo_type: GeoType | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class ComparableProperty(BaseModel):
    """Comparable property summary row."""

    address: str
    city: str
    state: str
    property_type: PropertyType
    bedrooms: int | None = None
    bathrooms: float | None = None
    list_price: Decimal
    sold_price: Decimal | None = None
    days_on_market: int
    distance_miles: float
    sold_date: date | None = None


class ComparablePropertiesReportResponse(GeneratedReportBase):
    """Response for comparable properties report."""

    average_list_price: Decimal
    average_sold_price: Decimal
    average_days_on_market: float
    comps: list[ComparableProperty] = Field(default_factory=list)


class InvestmentOpportunity(BaseModel):
    """Single investment opportunity signal."""

    signal: str
    score: float = Field(ge=0, le=100)
    estimated_roi: float = Field(ge=0)
    market_heat: float = Field(ge=0, le=100)
    rationale: str


class InvestmentSignalsRequest(BaseModel):
    """Request body for investment opportunity screening."""

    geography: str
    min_roi: float = Field(ge=0)
    max_price: Decimal = Field(gt=0)
    risk_level: RiskLevel = RiskLevel.MEDIUM


class InvestmentSignalsResponse(GeneratedReportBase):
    """Response for investment opportunity signals."""

    min_roi: float
    max_price: Decimal
    risk_level: RiskLevel
    opportunities: list[InvestmentOpportunity] = Field(default_factory=list)


class NeighborhoodComparisonPoint(BaseModel):
    """Single geography comparison row."""

    geography: str
    current_value: float
    trend_6mo: float
    velocity_index: float
    population_growth: float


class NeighborhoodComparisonResponse(GeneratedReportBase):
    """Response for side-by-side neighborhood trend comparison."""

    metric: MarketMetric
    leader: str
    comparisons: list[NeighborhoodComparisonPoint] = Field(default_factory=list)


class ForecastPoint(BaseModel):
    """Predicted market conditions for a future month."""

    month_offset: int = Field(ge=1)
    predicted_median_price: Decimal
    predicted_inventory: int = Field(ge=0)
    predicted_days_on_market: float = Field(ge=0)


class ForecastResponse(GeneratedReportBase):
    """Response for predictive analytics market forecast."""

    months_ahead: int = Field(ge=1, le=12)
    market_cycle: str
    confidence: float = Field(ge=0, le=1)
    monthly_forecast: list[ForecastPoint] = Field(default_factory=list)


class HeatIndexResponse(GeneratedReportBase):
    """Response for market heat index."""

    heat_index: float = Field(ge=0, le=100)
    market_label: str
    trend: str
    indicators: dict[str, float] = Field(default_factory=dict)


class SeasonalPattern(BaseModel):
    """Monthly seasonal pattern summary."""

    month: int = Field(ge=1, le=12)
    average_price_change: float
    listing_velocity: float = Field(ge=0)


class SeasonalAnalysisResponse(GeneratedReportBase):
    """Response for seasonal market analysis."""

    year: int
    month: int = Field(ge=1, le=12)
    best_action: str
    seasonal_price_swing_pct: float
    listing_velocity: float = Field(ge=0)
    monthly_pattern: list[SeasonalPattern] = Field(default_factory=list)


class CorrelationPoint(BaseModel):
    """Demographic correlation summary."""

    label: str
    correlation: float = Field(ge=-1, le=1)
    insight: str


class DemographicProfile(BaseModel):
    """Synthetic demographic inputs used for correlation report."""

    population_density: int = Field(ge=0)
    median_age: float = Field(ge=0)
    median_household_income: int = Field(ge=0)
    annual_population_growth: float


class DemographicCorrelationResponse(GeneratedReportBase):
    """Response for demographic correlation report."""

    demographics: DemographicProfile
    correlation_summary: list[CorrelationPoint] = Field(default_factory=list)


class ScheduleReportRequest(BaseModel):
    """Request schema for scheduling automated reports."""

    geography: str
    frequency: ScheduleFrequency
    email: str
    metrics: list[str] = Field(default_factory=list, min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Apply lightweight email validation without extra dependencies."""
        normalized = value.strip()
        if (
            "@" not in normalized
            or normalized.startswith("@")
            or normalized.endswith("@")
        ):
            raise ValueError("email must be a valid address")
        return normalized


class MarketReportScheduleResponse(BaseModel):
    """Response schema for persisted market report schedules."""

    id: UUID
    geography: str
    frequency: ScheduleFrequency
    email: str
    metrics: list[str] = Field(default_factory=list)
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DateRangeRequest(BaseModel):
    """Custom dashboard date range."""

    start_date: date
    end_date: date

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, value: date, info: Any) -> date:
        """Ensure the date range is not reversed."""
        start_date = info.data.get("start_date")
        if isinstance(start_date, date) and value < start_date:
            raise ValueError("end_date must be on or after start_date")
        return value


class CustomDashboardRequest(BaseModel):
    """Request schema for custom dashboard reports."""

    geography: str
    selected_metrics: list[str] = Field(default_factory=list, min_length=1)
    date_range: DateRangeRequest


class CustomMetricValue(BaseModel):
    """Single selected metric result."""

    metric: str
    value: float
    trend: float


class CustomDashboardResponse(GeneratedReportBase):
    """Response for custom dashboard report."""

    selected_metrics: list[str] = Field(default_factory=list)
    date_range: DateRangeRequest
    metrics: list[CustomMetricValue] = Field(default_factory=list)
    export_formats: list[str] = Field(default_factory=lambda: ["csv", "excel"])
