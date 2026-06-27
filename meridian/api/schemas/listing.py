from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from meridian.db.models.enums import GeoType, ListingStatus, PropertyType


class ListingBase(BaseModel):
    """Base schema for listing data."""

    source: str
    source_id: str
    mls_number: str | None = None
    address: str
    unit: str | None = None
    city: str
    state: str
    zip: str
    zip4: str | None = None
    county: str | None = None
    lat: float | None = None
    lon: float | None = None
    property_type: PropertyType
    beds: int | None = None
    baths: float | None = None
    living_sqft: int | None = None
    lot_sqft: int | None = None
    year_built: int | None = None
    list_price: Decimal
    sold_price: Decimal | None = None
    list_date: date
    sold_date: date | None = None
    status: ListingStatus
    days_on_market: int = Field(default=0)
    photos: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ListingResponse(ListingBase):
    """Response schema for listing data."""

    id: UUID


class ListingCreate(BaseModel):
    """Schema for creating a listing."""

    source: str
    source_id: str
    mls_number: str | None = None
    address: str
    unit: str | None = None
    city: str
    state: str
    zip: str
    zip4: str | None = None
    county: str | None = None
    lat: float | None = None
    lon: float | None = None
    property_type: PropertyType
    beds: int | None = None
    baths: float | None = None
    living_sqft: int | None = None
    lot_sqft: int | None = None
    year_built: int | None = None
    list_price: Decimal
    sold_price: Decimal | None = None
    list_date: date
    sold_date: date | None = None
    status: ListingStatus
    photos: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class ListingSearchFilters(BaseModel):
    """Filters for listing search."""

    geography: str | None = None
    geo_type: GeoType | None = None
    property_types: list[PropertyType] | None = None
    min_price: float | None = None
    max_price: float | None = None
    beds: int | None = None
    baths: float | None = None
    status: ListingStatus | None = None


class ListingSearchRequest(BaseModel):
    """Request schema for listing search."""

    filters: ListingSearchFilters = Field(default_factory=ListingSearchFilters)
    limit: int = Field(default=50, ge=1, le=500)
    cursor: str | None = None


class NearbySearchRequest(BaseModel):
    """Request schema for nearby listing search."""

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_miles: float = Field(..., gt=0, le=50)
    limit: int = Field(default=50, ge=1, le=500)
