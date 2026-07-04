from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime
from typing import Sequence
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import and_, cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.db.models import Listing
from meridian.db.models.enums import GeoType

METERS_PER_MILE = 1609.34
WGS84_SRID = 4326


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
        cursor: str | None = None,
    ) -> tuple[Sequence[Listing], str | None]:
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

        if cursor:
            cursor_created_at, cursor_id = self._decode_cursor(cursor)
            # Keyset condition must stay aligned with DESC ordering below.
            stmt = stmt.where(
                or_(
                    Listing.created_at < cursor_created_at,
                    and_(
                        Listing.created_at == cursor_created_at,
                        Listing.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(desc(Listing.created_at), desc(Listing.id)).limit(
            limit + 1
        )
        result = await self.session.execute(stmt)
        listings = result.scalars().all()
        has_next = len(listings) > limit
        page = listings[:limit]
        next_cursor = self._encode_cursor(page[-1]) if has_next and page else None
        return page, next_cursor

    async def count_by_status(
        self,
        *,
        geography: str | None = None,
        geo_type: GeoType | None = None,
    ) -> dict[str, int]:
        """Return listing counts grouped by status, optionally geo-filtered."""
        stmt = select(Listing.status, func.count()).select_from(Listing)

        if geography and geo_type:
            if geo_type == GeoType.ZIP:
                stmt = stmt.where(Listing.zip == geography)
            elif geo_type == GeoType.CITY:
                stmt = stmt.where(Listing.city == geography)
            elif geo_type == GeoType.COUNTY:
                stmt = stmt.where(Listing.county == geography)

        stmt = stmt.group_by(Listing.status)
        result = await self.session.execute(stmt)
        return {str(status): int(count) for status, count in result.all()}

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
        radius_meters = radius_miles * METERS_PER_MILE
        # ST_MakePoint uses (x, y) = (longitude, latitude).
        search_point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), WGS84_SRID)
        listing_geography = cast(Listing.geom, Geography)
        point_geography = cast(search_point, Geography)

        stmt = (
            select(Listing)
            .where(Listing.geom.is_not(None))
            .where(func.ST_DWithin(listing_geography, point_geography, radius_meters))
            .order_by(func.ST_Distance(listing_geography, point_geography))
            .limit(limit)
        )

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

    @staticmethod
    def _encode_cursor(listing: Listing) -> str:
        payload = {
            "created_at": listing.created_at.isoformat(),
            "id": str(listing.id),
        }
        encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8"))
        return encoded.decode("utf-8")

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
        try:
            decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
            payload = json.loads(decoded)
            return datetime.fromisoformat(payload["created_at"]), UUID(payload["id"])
        except (
            KeyError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
            binascii.Error,
        ) as exc:
            raise ValueError("Invalid cursor") from exc
