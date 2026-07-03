from __future__ import annotations

from typing import Any, Sequence

from fastapi import APIRouter, Depends, Query, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.auth import get_current_token
from meridian.api.deps import get_db, get_redis
from meridian.api.exceptions import NotFoundError
from meridian.api.models.errors import ErrorCode, ErrorResponse
from meridian.api.schemas import MarketReportRefreshRequest, MarketReportResponse
from meridian.cache.helpers import cache_control_header, cache_get, cache_set
from meridian.cache.invalidation import invalidate_market_reports_cache
from meridian.cache.keys import make_cache_key
from meridian.cache.strategies import CacheNamespace, CacheStrategy, resolve_ttl
from meridian.db.models import MarketReport
from meridian.db.repositories import MarketReportRepository
from meridian.services import MarketReportService

router = APIRouter(prefix="/v1/market-reports", tags=["market-reports"])

_error_responses: dict[int | str, dict[str, Any]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token",
    },
    404: {"model": ErrorResponse, "description": "Market report not found"},
    422: {"model": ErrorResponse, "description": "Request validation error"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
}


@router.get(
    "/latest",
    response_model=MarketReportResponse,
    summary="Get latest market report",
    description=(
        "Retrieve the most recent market report for the specified geography and "
        "geography type. Results are cached; see ``Cache-Control`` and ``X-Cache`` "
        "response headers."
    ),
    responses={
        200: {"description": "Latest market report"},
        **_error_responses,
    },
)
async def get_latest_report(
    response: Response,
    geography: str = Query(
        ...,
        description="Geography identifier (e.g. 'Austin', 'TX', '78701')",
        examples=["Austin"],
    ),
    geo_type: str = Query(
        ...,
        description="Geography type — one of METRO, ZIP, CITY, STATE",
        examples=["CITY"],
    ),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> MarketReportResponse:
    """Get the latest market report for a geography."""
    ttl = resolve_ttl(CacheStrategy.MARKET_REPORT_LATEST)
    cache_key = make_cache_key(
        CacheNamespace.MARKET_REPORTS,
        "latest",
        geography=geography,
        geo_type=geo_type,
    )
    cached = await cache_get(redis_client, cache_key)
    if isinstance(cached, dict):
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = cache_control_header(ttl)
        return MarketReportResponse.model_validate(cached)

    service = MarketReportService(db)
    report = await service.get_latest_report(geography=geography, geo_type=geo_type)
    if not report:
        raise NotFoundError(
            "No market report found for the specified geography",
            error_code=ErrorCode.MARKET_REPORT_NOT_FOUND,
        )
    payload = MarketReportResponse.model_validate(report)
    await cache_set(redis_client, cache_key, payload.model_dump(mode="json"), ttl)
    detail_key = make_cache_key(
        CacheNamespace.MARKET_REPORTS,
        "detail",
        report_id=payload.id,
    )
    await cache_set(
        redis_client,
        detail_key,
        payload.model_dump(mode="json"),
        resolve_ttl(CacheStrategy.MARKET_REPORT_DETAIL),
    )
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload


@router.get(
    "/{report_id}",
    response_model=MarketReportResponse,
    summary="Get market report by ID",
    description="Retrieve a specific market report by its unique identifier.",
    responses={
        200: {"description": "Market report details"},
        **_error_responses,
    },
)
async def get_report(
    report_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> MarketReportResponse:
    """Get a market report by ID."""
    ttl = resolve_ttl(CacheStrategy.MARKET_REPORT_DETAIL)
    cache_key = make_cache_key(
        CacheNamespace.MARKET_REPORTS,
        "detail",
        report_id=report_id,
    )
    cached = await cache_get(redis_client, cache_key)
    if isinstance(cached, dict):
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = cache_control_header(ttl)
        return MarketReportResponse.model_validate(cached)

    repo = MarketReportRepository(db)
    report = await repo.get_by_id(report_id)
    if not report:
        raise NotFoundError(
            "Market report not found",
            error_code=ErrorCode.MARKET_REPORT_NOT_FOUND,
        )
    payload = MarketReportResponse.model_validate(report)
    await cache_set(redis_client, cache_key, payload.model_dump(mode="json"), ttl)
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload


@router.post(
    "/refresh",
    response_model=MarketReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh market report",
    description=(
        "Pull fresh data from the upstream adapter for the given geography and "
        "persist a new market report.  Invalidates the relevant cache entries."
    ),
    responses={
        200: {"description": "Refreshed market report"},
        400: {"model": ErrorResponse, "description": "Invalid geography or geo_type"},
        **_error_responses,
    },
)
async def refresh_report(
    request: MarketReportRefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> MarketReport:
    """Refresh market report by pulling fresh data from adapter."""
    service = MarketReportService(db)
    report = await service.refresh_report(
        geography=request.geography,
        geo_type=request.geo_type.value,
        as_of=request.as_of,
    )
    await invalidate_market_reports_cache(redis_client)
    return report


@router.get(
    "",
    response_model=list[MarketReportResponse],
    summary="List market reports",
    description=(
        "Return a list of recent market reports for the specified geography. "
        "Results are ordered by report date descending."
    ),
    responses={
        200: {"description": "List of market reports"},
        **_error_responses,
    },
)
async def list_reports(
    response: Response,
    geography: str = Query(..., description="Geography identifier"),
    geo_type: str = Query(..., description="Geography type (METRO, ZIP, CITY, STATE)"),
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of reports to return"
    ),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> Sequence[MarketReportResponse]:
    """List recent market reports for a geography."""
    ttl = resolve_ttl(CacheStrategy.MARKET_REPORTS_LIST)
    cache_key = make_cache_key(
        CacheNamespace.MARKET_REPORTS,
        "list",
        geography=geography,
        geo_type=geo_type,
        limit=limit,
    )
    cached = await cache_get(redis_client, cache_key)
    if isinstance(cached, list):
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = cache_control_header(ttl)
        return [MarketReportResponse.model_validate(item) for item in cached]

    from meridian.db.models.enums import GeoType

    geo_type_enum = GeoType(geo_type)
    repo = MarketReportRepository(db)
    reports = await repo.get_reports_for_geography(
        geography=geography,
        geo_type=geo_type_enum,
        limit=limit,
    )
    payload = [MarketReportResponse.model_validate(report) for report in reports]
    await cache_set(
        redis_client,
        cache_key,
        [item.model_dump(mode="json") for item in payload],
        ttl,
    )
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload
