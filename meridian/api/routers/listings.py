from __future__ import annotations

from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.deps import get_db
from meridian.api.schemas import (
    ListingResponse,
    ListingSearchRequest,
    NearbySearchRequest,
)
from meridian.db.models import Listing
from meridian.db.models.enums import GeoType
from meridian.db.repositories import ListingRepository

router = APIRouter(prefix="/v1/listings", tags=["listings"])


@router.get("", response_model=list[ListingResponse])
async def list_listings(
    response: Response,
    geography: str | None = Query(None),
    geo_type: GeoType | None = Query(None),
    property_types: list[str] | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    beds: int | None = Query(None, ge=0),
    baths: float | None = Query(None, ge=0),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Sequence[Listing]:
    """List listings with optional filters."""
    repo = ListingRepository(db)
    listings, next_cursor = await repo.search_listings(
        geography=geography,
        geo_type=geo_type,
        property_types=property_types,
        min_price=min_price,
        max_price=max_price,
        beds=beds,
        baths=baths,
        status=status,
        limit=limit,
        cursor=cursor,
    )
    if next_cursor is not None:
        response.headers["X-Next-Cursor"] = next_cursor
    return listings


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Listing:
    """Get a listing by ID."""
    repo = ListingRepository(db)
    listing = await repo.get_by_id(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.post("/search", response_model=list[ListingResponse])
async def search_listings(
    request: ListingSearchRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Sequence[Listing]:
    """Advanced search for listings."""
    repo = ListingRepository(db)
    listings, next_cursor = await repo.search_listings(
        geography=request.filters.geography,
        geo_type=request.filters.geo_type,
        property_types=[pt.value for pt in (request.filters.property_types or [])],
        min_price=request.filters.min_price,
        max_price=request.filters.max_price,
        beds=request.filters.beds,
        baths=request.filters.baths,
        status=request.filters.status.value if request.filters.status else None,
        limit=request.limit,
        cursor=request.cursor,
    )
    if next_cursor is not None:
        response.headers["X-Next-Cursor"] = next_cursor
    return listings


@router.post("/nearby", response_model=list[ListingResponse])
async def search_nearby(
    request: NearbySearchRequest,
    db: AsyncSession = Depends(get_db),
) -> Sequence[Listing]:
    """Search listings within a geographic radius."""
    repo = ListingRepository(db)
    return await repo.search_nearby(
        lat=request.lat,
        lon=request.lon,
        radius_miles=request.radius_miles,
        limit=request.limit,
    )
