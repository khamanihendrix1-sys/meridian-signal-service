from __future__ import annotations

from typing import Any, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.auth import get_current_token
from meridian.api.deps import get_db, get_redis
from meridian.api.exceptions import NotFoundError
from meridian.api.models.errors import ErrorCode, ErrorResponse
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

_error_responses: dict[int | str, dict[str, Any]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token",
    },
    404: {"model": ErrorResponse, "description": "Listing not found"},
    422: {"model": ErrorResponse, "description": "Request validation error"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
}


@router.get(
    "",
    response_model=list[ListingResponse],
    summary="List listings",
    description=(
        "Return a filtered, cursor-paginated list of property listings. "
        "Pass the `X-Next-Cursor` response header value back as the `cursor` query "
        "parameter to retrieve the next page."
    ),
    responses={
        200: {"description": "Paginated list of listings"},
        **_error_responses,
    },
)
async def list_listings(
    response: Response,
    geography: str | None = Query(
        None, description="Geography identifier (e.g. 'Austin', '78701')"
    ),
    geo_type: GeoType | None = Query(
        None, description="Geography type — METRO, ZIP, CITY, or STATE"
    ),
    property_types: list[str] | None = Query(
        None, description="Filter by property type(s)"
    ),
    min_price: float | None = Query(None, ge=0, description="Minimum list price (USD)"),
    max_price: float | None = Query(None, ge=0, description="Maximum list price (USD)"),
    beds: int | None = Query(None, ge=0, description="Minimum number of bedrooms"),
    baths: float | None = Query(None, ge=0, description="Minimum number of bathrooms"),
    status: str | None = Query(
        None, description="Listing status filter (e.g. ACTIVE, SOLD)"
    ),
    limit: int = Query(
        50, ge=1, le=500, description="Maximum number of results to return"
    ),
    cursor: str | None = Query(
        None, description="Pagination cursor from a previous response"
    ),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
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


@router.get(
    "/{listing_id}",
    response_model=ListingResponse,
    summary="Get listing by ID",
    description="Retrieve the full details of a single listing by its UUID.",
    responses={
        200: {"description": "Listing details"},
        **_error_responses,
    },
)
async def get_listing(
    listing_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
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
        raise NotFoundError("Listing not found", error_code=ErrorCode.LISTING_NOT_FOUND)
    payload = ListingResponse.model_validate(listing)
    await cache_set(redis_client, cache_key, payload.model_dump(mode="json"), ttl)
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload


@router.post(
    "/search",
    response_model=list[ListingResponse],
    summary="Advanced listing search",
    description=(
        "Run an advanced search for listings using a structured request body with "
        "combined filters. Supports cursor-based pagination via the `cursor` field."
    ),
    responses={
        200: {"description": "Matching listings"},
        **_error_responses,
    },
)
async def search_listings(
    request: ListingSearchRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _token: dict[str, Any] = Depends(get_current_token),
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


@router.post(
    "/nearby",
    response_model=list[ListingResponse],
    summary="Nearby listing search",
    description=(
        "Return listings within a specified radius of a geographic coordinate. "
        "Useful for map-based proximity searches."
    ),
    responses={
        200: {"description": "Listings within the specified radius"},
        **_error_responses,
    },
)
async def search_nearby(
    request: NearbySearchRequest,
    db: AsyncSession = Depends(get_db),
    _token: dict[str, Any] = Depends(get_current_token),
) -> Sequence[Listing]:
    """Search listings within a geographic radius."""
    repo = ListingRepository(db)
    return await repo.search_nearby(
        lat=request.lat,
        lon=request.lon,
        radius_miles=request.radius_miles,
        limit=request.limit,
    )
