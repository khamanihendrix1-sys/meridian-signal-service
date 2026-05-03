from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from meridian.db.models import Listing
from meridian.db.models.enums import GeoType


class ListingRepository:
    """Repository for listing database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, listing_id: UUID) -> Listing | None:
        """Get a listing by ID."""
        stmt = select(Listing).where(Listing.id == listing_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_listings(
        self,
        *,
        geography: str | None = None,
        geo_type: GeoType | None = None,
        property_types: list[str] | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        beds: int | None = None,
        baths: float | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Listing]:
        """Search listings with filters."""
        stmt = select(Listing)

        if geography and geo_type:
            if geo_type == GeoType.ZIP:
                stmt = stmt.where(Listing.zip == geography)
            elif geo_type == GeoType.CITY:
                stmt = stmt.where(Listing.city == geography)
            elif geo_type == GeoType.COUNTY:
                stmt = stmt.where(Listing.county == geography)
            # Add more geo types as needed

        if property_types:
            stmt = stmt.where(Listing.property_type.in_(property_types))

        if min_price is not None:
            stmt = stmt.where(Listing.list_price >= min_price)

        if max_price is not None:
            stmt = stmt.where(Listing.list_price <= max_price)

        if beds is not None:
            stmt = stmt.where(Listing.beds >= beds)

        if baths is not None:
            stmt = stmt.where(Listing.baths >= baths)

        if status:
            stmt = stmt.where(Listing.status == status)

        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search_nearby(
        self,
        *,
        lat: float,
        lon: float,
        radius_miles: float,
        limit: int = 50,
    ) -> Sequence[Listing]:
        """Search listings within radius using PostGIS."""
        # ST_DWithin uses meters, convert miles to meters
        radius_meters = radius_miles * 1609.34

        stmt = select(Listing).where(
            Listing.geom.ST_DWithin(f"SRID=4326;POINT({lon} {lat})", radius_meters)
        ).limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_listing(self, listing: Listing) -> Listing:
        """Create a new listing."""
        self.session.add(listing)
        await self.session.commit()
        await self.session.refresh(listing)
        return listing

    async def update_listing(self, listing: Listing) -> Listing:
        """Update an existing listing."""
        await self.session.commit()
        await self.session.refresh(listing)
        return listing

    async def delete_listing(self, listing: Listing) -> None:
        """Delete a listing."""
        await self.session.delete(listing)
        await self.session.commit()