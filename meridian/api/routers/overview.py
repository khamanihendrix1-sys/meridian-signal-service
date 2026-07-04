from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.auth import get_current_token
from meridian.api.deps import get_db, get_redis
from meridian.api.models.errors import ErrorResponse
from meridian.api.schemas import OverviewResponse
from meridian.api.schemas.overview import ListingCounts, SignalCounts
from meridian.api.schemas.market_report import MarketReportResponse
from meridian.api.schemas.signal import SignalLogResponse
from meridian.cache.helpers import cache_control_header, cache_get, cache_set
from meridian.cache.keys import make_cache_key
from meridian.cache.strategies import CacheNamespace, CacheStrategy, resolve_ttl
from meridian.db.models import SignalDefinition, SignalLog
from meridian.db.models.enums import GeoType, ListingStatus
from meridian.db.repositories import ListingRepository
from meridian.services import MarketReportService

router = APIRouter(prefix="/v1/overview", tags=["overview"])

_error_responses: dict[int | str, dict[str, Any]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token",
    },
    422: {"model": ErrorResponse, "description": "Request validation error"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
}

_RECENT_SIGNALS_LIMIT = 10


def _build_listing_counts(status_counts: dict[str, int]) -> ListingCounts:
    """Map raw status→count into the ListingCounts schema."""
    return ListingCounts(
        total=sum(status_counts.values()),
        active=status_counts.get(ListingStatus.ACTIVE.value, 0),
        pending=status_counts.get(ListingStatus.PENDING.value, 0),
        sold=status_counts.get(ListingStatus.SOLD.value, 0),
        expired=status_counts.get(ListingStatus.EXPIRED.value, 0),
        withdrawn=status_counts.get(ListingStatus.WITHDRAWN.value, 0),
        by_status=status_counts,
    )


@router.get(
    "",
    response_model=OverviewResponse,
    summary="Dashboard overview",
    description=(
        "Aggregate dashboard metrics in a single call: listing counts by status, "
        "signal-evaluation totals, the most recent fired/evaluated signals, and the "
        "latest market report for the requested geography. Results are cached; see "
        "the ``Cache-Control`` and ``X-Cache`` response headers."
    ),
    responses={
        200: {"description": "Aggregated dashboard overview"},
        **_error_responses,
    },
)
async def get_overview(
    response: Response,
    geography: str | None = Query(
        None, description="Optional geography filter (e.g. 'Austin', '78701')"
    ),
    geo_type: GeoType | None = Query(
        None, description="Geography type — required when geography is provided"
    ),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> OverviewResponse:
    """Return aggregated dashboard metrics."""
    ttl = resolve_ttl(CacheStrategy.OVERVIEW)
    cache_key = make_cache_key(
        CacheNamespace.OVERVIEW,
        "summary",
        geography=geography,
        geo_type=geo_type.value if geo_type else None,
    )
    cached = await cache_get(redis_client, cache_key)
    if isinstance(cached, dict):
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = cache_control_header(ttl)
        return OverviewResponse.model_validate(cached)

    # --- Listing counts by status -------------------------------------------
    listing_repo = ListingRepository(db)
    status_counts = await listing_repo.count_by_status(
        geography=geography, geo_type=geo_type
    )
    listing_counts = _build_listing_counts(status_counts)

    # --- Signal aggregates ---------------------------------------------------
    log_filters = []
    if geography:
        log_filters.append(SignalLog.geography == geography)
    if geo_type:
        log_filters.append(SignalLog.geo_type == geo_type)

    total_stmt = select(func.count()).select_from(SignalLog)
    fired_stmt = (
        select(func.count()).select_from(SignalLog).where(SignalLog.fired.is_(True))
    )
    for condition in log_filters:
        total_stmt = total_stmt.where(condition)
        fired_stmt = fired_stmt.where(condition)

    total_evaluations = int((await db.execute(total_stmt)).scalar_one())
    fired = int((await db.execute(fired_stmt)).scalar_one())
    definitions = int(
        (
            await db.execute(select(func.count()).select_from(SignalDefinition))
        ).scalar_one()
    )

    signal_counts = SignalCounts(
        total_evaluations=total_evaluations,
        fired=fired,
        definitions=definitions,
    )

    # --- Recent signal logs --------------------------------------------------
    recent_stmt = select(SignalLog)
    for condition in log_filters:
        recent_stmt = recent_stmt.where(condition)
    recent_stmt = recent_stmt.order_by(SignalLog.timestamp.desc()).limit(
        _RECENT_SIGNALS_LIMIT
    )
    recent_logs = (await db.execute(recent_stmt)).scalars().all()
    recent_signals = [SignalLogResponse.model_validate(log) for log in recent_logs]

    # --- Latest market report (only when a geography is specified) -----------
    latest_market_report: MarketReportResponse | None = None
    if geography and geo_type:
        service = MarketReportService(db)
        report = await service.get_latest_report(
            geography=geography, geo_type=geo_type.value
        )
        if report:
            latest_market_report = MarketReportResponse.model_validate(report)

    payload = OverviewResponse(
        geography=geography,
        geo_type=geo_type,
        generated_at=datetime.now(timezone.utc),
        listings=listing_counts,
        signals=signal_counts,
        recent_signals=recent_signals,
        latest_market_report=latest_market_report,
    )
    await cache_set(redis_client, cache_key, payload.model_dump(mode="json"), ttl)
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload
