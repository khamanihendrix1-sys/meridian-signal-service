from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import AsyncIterator

from shapely.geometry import Point


class Capability(StrEnum):
    """Capabilities that market adapters may support."""
    LISTINGS = "LISTINGS"
    SOLD_HISTORY = "SOLD_HISTORY"
    GEO_SEARCH = "GEO_SEARCH"
    MARKET_METRICS = "MARKET_METRICS"


@dataclass
class RawListing:
    """Raw listing data from an adapter, before transformation to internal models."""
    source_id: str
    mls_number: str | None
    address: str
    unit: str | None
    city: str
    state: str
    zip: str
    zip4: str | None
    county: str | None
    geom: Point | None
    property_type: str  # Will map to PropertyType enum
    beds: int | None
    baths: float | None
    living_sqft: int | None
    lot_sqft: int | None
    year_built: int | None
    list_price: Decimal
    sold_price: Decimal | None
    list_date: date
    sold_date: date | None
    status: str  # Will map to ListingStatus enum
    photos: list[str]
    raw: dict


@dataclass
class RawMarketMetrics:
    """Raw market metrics from an adapter."""
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
    raw_metrics: dict


class MarketAdapter(ABC):
    """Every market data source implements this interface."""

    name: str
    capabilities: set[Capability]

    @abstractmethod
    async def fetch_listings(
        self,
        *,
        geography: str,
        geo_type: str,  # Will map to GeoType
        since: datetime | None = None,
        limit: int = 500,
    ) -> AsyncIterator[RawListing]:
        """Fetch listings for a geography."""
        ...

    @abstractmethod
    async def fetch_sold_comps(
        self,
        *,
        center: tuple[float, float],  # (lat, lon)
        radius_miles: float,
        since: date,
        limit: int = 100,
    ) -> AsyncIterator[RawListing]:
        """Fetch sold comparables within a radius."""
        ...

    @abstractmethod
    async def fetch_market_metrics(
        self,
        *,
        geography: str,
        geo_type: str,
        as_of: date,
    ) -> RawMarketMetrics:
        """Fetch market metrics snapshot."""
        ...

    @abstractmethod
    async def health(self) -> dict:
        """Return adapter health status."""
        ...