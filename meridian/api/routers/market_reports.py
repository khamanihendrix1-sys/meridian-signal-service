from __future__ import annotations

from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.deps import get_db, get_redis
from meridian.api.schemas import MarketReportRefreshRequest, MarketReportResponse
from meridian.cache.helpers import cache_control_header, cache_get, cache_set
from meridian.cache.invalidation import invalidate_market_reports_cache
from meridian.cache.keys import make_cache_key
from meridian.cache.strategies import CacheNamespace, CacheStrategy, resolve_ttl
from meridian.db.models import MarketReport
from meridian.db.repositories import MarketReportRepository
from meridian.services import MarketReportService

router = APIRouter(prefix="/v1/market-reports", tags=["market-reports"])


@router.get("/latest", response_model=MarketReportResponse)
async def get_latest_report(
    response: Response,
    geography: str = Query(..., description="Geography identifier"),
    geo_type: str = Query(..., description="Geography type (METRO, ZIP, etc.)"),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
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
        raise HTTPException(status_code=404, detail="No market report found")
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


@router.get("/{report_id}", response_model=MarketReportResponse)
async def get_report(
    report_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
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
        raise HTTPException(status_code=404, detail="Market report not found")
    payload = MarketReportResponse.model_validate(report)
    await cache_set(redis_client, cache_key, payload.model_dump(mode="json"), ttl)
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload


@router.post("/refresh", response_model=MarketReportResponse)
async def refresh_report(
    request: MarketReportRefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
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


@router.get("", response_model=list[MarketReportResponse])
async def list_reports(
    response: Response,
    geography: str = Query(..., description="Geography identifier"),
    geo_type: str = Query(..., description="Geography type (METRO, ZIP, etc.)"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
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
