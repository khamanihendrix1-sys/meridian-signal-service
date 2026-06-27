from __future__ import annotations

import hashlib
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import AsyncIterator

from shapely.geometry import Point

from meridian.adapters.base import (
    Capability,
    MarketAdapter,
    RawListing,
    RawMarketMetrics,
)
from meridian.db.models.enums import GeoType, ListingStatus, PropertyType


class MockAdapter(MarketAdapter):
    """Mock adapter that generates deterministic, realistic data for development and testing."""

    name = "mock"
    capabilities = {
        Capability.LISTINGS,
        Capability.SOLD_HISTORY,
        Capability.GEO_SEARCH,
        Capability.MARKET_METRICS,
    }

    def __init__(self) -> None:
        self._rng: random.Random | None = None

    async def fetch_listings(
        self,
        *,
        geography: str,
        geo_type: str,
        since: datetime | None = None,
        limit: int = 500,
    ) -> AsyncIterator[RawListing]:
        """Generate mock listings for a geography."""
        self._seed_rng(geography)
        rng = self._require_rng()
        count = min(limit, rng.randint(50, 200))

        for _ in range(count):
            yield self._generate_listing(geography, geo_type)

    async def fetch_sold_comps(
        self,
        *,
        center: tuple[float, float],
        radius_miles: float,
        since: date,
        limit: int = 100,
    ) -> AsyncIterator[RawListing]:
        """Generate mock sold comparables within radius."""
        # Use center as geography seed for determinism
        geo_seed = f"{center[0]:.4f},{center[1]:.4f}"
        self._seed_rng(geo_seed)
        rng = self._require_rng()
        count = min(limit, rng.randint(10, 50))

        for _ in range(count):
            listing = self._generate_listing(geo_seed, GeoType.ZIP.value)
            # Ensure it's sold and within date range
            listing.status = ListingStatus.SOLD.value
            listing.sold_date = since + timedelta(days=rng.randint(0, 365))
            listing.sold_price = listing.list_price * Decimal(
                str(rng.uniform(0.95, 1.05))
            )
            yield listing

    async def fetch_market_metrics(
        self,
        *,
        geography: str,
        geo_type: str,
        as_of: date,
    ) -> RawMarketMetrics:
        """Generate mock market metrics."""
        self._seed_rng(geography)
        rng = self._require_rng()
        base_price = self._get_base_price(geography)

        return RawMarketMetrics(
            median_price=base_price,
            mean_price=base_price * Decimal(str(rng.uniform(0.98, 1.02))),
            active_listings=rng.randint(100, 500),
            sold_last_30d=rng.randint(20, 100),
            avg_days_on_market=rng.uniform(30, 90),
            months_of_inventory=rng.uniform(2, 8),
            absorption_rate=rng.uniform(0.1, 0.5),
            yoy_price_change=rng.uniform(-0.1, 0.15),
            mom_price_change=rng.uniform(-0.05, 0.05),
            list_to_sold_ratio=rng.uniform(0.95, 1.05),
            raw_metrics={},
        )

    async def health(self) -> dict[str, str]:
        """Mock health check."""
        return {"status": "healthy", "adapter": "mock"}

    def _seed_rng(self, geography: str) -> None:
        """Seed the random number generator with geography hash for determinism."""
        seed = int(hashlib.md5(geography.encode()).hexdigest(), 16) % (2**32)
        self._rng = random.Random(seed)

    def _require_rng(self) -> random.Random:
        """Return the seeded RNG."""
        if self._rng is None:
            raise RuntimeError("Random generator is not initialized")
        return self._rng

    def _generate_listing(self, geography: str, geo_type: str) -> RawListing:
        """Generate a single mock listing."""
        rng = self._require_rng()

        # Parse geography for location data
        if geo_type == GeoType.ZIP.value:
            zip_code = geography
            city = self._get_city_for_zip(zip_code)
            state = "GA"  # Atlanta area
            lat, lon = self._get_coords_for_zip(zip_code)
        else:
            # Fallback for other geo types
            city = geography.split("-")[0]
            state = "GA"
            lat = 33.7490 + rng.uniform(-0.5, 0.5)
            lon = -84.3880 + rng.uniform(-0.5, 0.5)
            zip_code = f"{rng.randint(30000, 39999):05d}"

        base_price = self._get_base_price(geography)
        list_price = base_price * Decimal(str(rng.uniform(0.8, 1.5)))

        # Simulate seasonality: higher prices in spring/summer
        today = date.today()
        seasonal_factor = 1 + 0.1 * (1 if 3 <= today.month <= 8 else -1)
        list_price *= Decimal(str(seasonal_factor))

        status = rng.choice([s.value for s in ListingStatus])
        sold_price = None
        sold_date = None
        if status == ListingStatus.SOLD.value:
            sold_price = list_price * Decimal(str(rng.uniform(0.95, 1.05)))
            sold_date = today - timedelta(days=rng.randint(1, 365))

        return RawListing(
            source_id=f"mock-{rng.randint(1000000, 9999999)}",
            mls_number=(
                f"MLS{rng.randint(100000, 999999)}" if rng.random() > 0.1 else None
            ),
            address=f"{rng.randint(100, 9999)} Mock St",
            unit=f"Apt {rng.randint(1, 20)}" if rng.random() > 0.7 else None,
            city=city,
            state=state,
            zip=zip_code,
            zip4=None,
            county=f"{city} County",
            geom=Point(lon, lat),
            property_type=rng.choice([pt.value for pt in PropertyType]),
            beds=rng.randint(1, 6) if rng.random() > 0.1 else None,
            baths=round(rng.uniform(1, 4), 1) if rng.random() > 0.1 else None,
            living_sqft=rng.randint(800, 4000) if rng.random() > 0.8 else None,
            lot_sqft=rng.randint(5000, 50000) if rng.random() > 0.5 else None,
            year_built=rng.randint(1950, 2023) if rng.random() > 0.3 else None,
            list_price=list_price,
            sold_price=sold_price,
            list_date=today - timedelta(days=rng.randint(1, 180)),
            sold_date=sold_date,
            status=status,
            photos=[
                f"https://example.com/photo{i}.jpg" for i in range(rng.randint(0, 10))
            ],
            raw={"mock": True},
        )

    def _get_base_price(self, geography: str) -> Decimal:
        """Get base median price for geography (simplified metro tier logic)."""
        # Atlanta metro tiers: high for downtown, medium for suburbs, low for outer
        if "30301" in geography or "Atlanta" in geography:
            return Decimal("500000")
        elif any(zip in geography for zip in ["30309", "30313", "30324"]):
            return Decimal("400000")
        else:
            return Decimal("300000")

    def _get_city_for_zip(self, zip_code: str) -> str:
        """Mock city lookup for ZIP."""
        cities = ["Atlanta", "Sandy Springs", "Roswell", "Marietta", "Smyrna"]
        rng = self._rng
        return rng.choice(cities) if rng is not None else "Atlanta"

    def _get_coords_for_zip(self, zip_code: str) -> tuple[float, float]:
        """Mock coordinates for ZIP."""
        rng = self._rng
        base_lat, base_lon = 33.7490, -84.3880  # Atlanta center
        lat = base_lat + rng.uniform(-0.2, 0.2) if rng is not None else base_lat
        lon = base_lon + rng.uniform(-0.2, 0.2) if rng is not None else base_lon
        return lat, lon
