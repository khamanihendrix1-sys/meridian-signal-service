from __future__ import annotations

from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.deps import get_db, get_redis
from meridian.api.schemas import (
    ListingResponse,
    ListingSearchRequest,
    NearbySearchRequest,
)
from meridian.cache.helpers import cache_control_header, cache_get, cache_set
from meridian.cache.keys import make_cache_key
from meridian.cache.strategies import CacheNamespace, CacheStrategy, resolve_ttl
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
    redis_client: Redis = Depends(get_redis),
) -> Sequence[ListingResponse]:
    """List listings with optional filters."""
    ttl = resolve_ttl(CacheStrategy.LISTINGS_LIST)
    cache_key = make_cache_key(
        CacheNamespace.LISTINGS,
        "list",
        geography=geography,
        geo_type=geo_type.value if geo_type else None,
        property_types=sorted(property_types) if property_types else None,
        min_price=min_price,
        max_price=max_price,
        beds=beds,
        baths=baths,
        status=status,
        limit=limit,
        cursor=cursor,
    )
    cached = await cache_get(redis_client, cache_key)
    if isinstance(cached, dict):
        payload = cached.get("items", [])
        if cached.get("next_cursor"):
            response.headers["X-Next-Cursor"] = str(cached["next_cursor"])
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = cache_control_header(ttl)
        return [ListingResponse.model_validate(item) for item in payload]

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
    models = [ListingResponse.model_validate(item) for item in listings]
    await cache_set(
        redis_client,
        cache_key,
        {
            "items": [model.model_dump(mode="json") for model in models],
            "next_cursor": next_cursor,
        },
        ttl,
    )
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    if next_cursor:
        response.headers["X-Next-Cursor"] = next_cursor
    return models


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> ListingResponse:
    """Get a listing by ID."""
    ttl = resolve_ttl(CacheStrategy.LISTING_DETAIL)
    cache_key = make_cache_key(CacheNamespace.LISTINGS, "detail", listing_id=listing_id)
    cached = await cache_get(redis_client, cache_key)
    if isinstance(cached, dict):
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = cache_control_header(ttl)
        return ListingResponse.model_validate(cached)

    repo = ListingRepository(db)
    listing = await repo.get_by_id(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    payload = ListingResponse.model_validate(listing)
    await cache_set(redis_client, cache_key, payload.model_dump(mode="json"), ttl)
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload


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
    if next_cursor:
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
