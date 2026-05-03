from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from shapely.geometry import Point

from meridian.db.models.enums import GeoType, ListingStatus, PropertyType


class ListingBase(BaseModel):
    """Base schema for listing data."""
    source: str
    source_id: str
    mls_number: Optional[str] = None
    address: str
    unit: Optional[str] = None
    city: str
    state: str
    zip: str
    zip4: Optional[str] = None
    county: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    property_type: PropertyType
    beds: Optional[int] = None
    baths: Optional[float] = None
    living_sqft: Optional[int] = None
    lot_sqft: Optional[int] = None
    year_built: Optional[int] = None
    list_price: Decimal
    sold_price: Optional[Decimal] = None
    list_date: date
    sold_date: Optional[date] = None
    status: ListingStatus
    days_on_market: int = Field(default=0)
    photos: list[str] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Convert ORM object to schema, handling geom."""
        data = super().from_orm(obj).__dict__
        if obj.geom and isinstance(obj.geom, Point):
            data["lat"] = obj.geom.y
            data["lon"] = obj.geom.x
        return cls(**data)


class ListingResponse(ListingBase):
    """Response schema for listing data."""
    id: UUID


class ListingCreate(BaseModel):
    """Schema for creating a listing."""
    source: str
    source_id: str
    mls_number: Optional[str] = None
    address: str
    unit: Optional[str] = None
    city: str
    state: str
    zip: str
    zip4: Optional[str] = None
    county: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    property_type: PropertyType
    beds: Optional[int] = None
    baths: Optional[float] = None
    living_sqft: Optional[int] = None
    lot_sqft: Optional[int] = None
    year_built: Optional[int] = None
    list_price: Decimal
    sold_price: Optional[Decimal] = None
    list_date: date
    sold_date: Optional[date] = None
    status: ListingStatus
    photos: list[str] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)


class ListingSearchFilters(BaseModel):
    """Filters for listing search."""
    geography: Optional[str] = None
    geo_type: Optional[GeoType] = None
    property_types: Optional[list[PropertyType]] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    beds: Optional[int] = None
    baths: Optional[float] = None
    status: Optional[ListingStatus] = None


class ListingSearchRequest(BaseModel):
    """Request schema for listing search."""
    filters: ListingSearchFilters = Field(default_factory=ListingSearchFilters)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class NearbySearchRequest(BaseModel):
    """Request schema for nearby listing search."""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius_miles: float = Field(..., gt=0, le=50)
    limit: int = Field(default=50, ge=1, le=500)