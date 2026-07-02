from __future__ import annotations

from typing import Any, Sequence

from fastapi import APIRouter, Depends, Query, Response, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.auth import get_current_token
from meridian.api.deps import get_db, get_redis
from meridian.api.models.errors import ErrorResponse
from meridian.api.schemas import (
    SignalDefinitionResponse,
    SignalEvaluateRequest,
    SignalLogResponse,
)
from meridian.cache.helpers import cache_control_header, cache_get, cache_set
from meridian.cache.invalidation import invalidate_signals_cache
from meridian.cache.keys import make_cache_key
from meridian.cache.strategies import CacheNamespace, CacheStrategy, resolve_ttl
from meridian.db.models import SignalDefinition, SignalLog
from meridian.signals.engine import PersistentSignalEngine
from meridian.signals.evaluators import LowInventoryEvaluator, PriceDrop30dEvaluator

router = APIRouter(prefix="/v1/signals", tags=["signals"])

_error_responses: dict[int | str, dict[str, Any]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token",
    },
    422: {"model": ErrorResponse, "description": "Request validation error"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
}


@router.get(
    "",
    response_model=list[SignalDefinitionResponse],
    summary="List signal definitions",
    description="Return all configured signal definitions.",
    responses={
        200: {"description": "List of signal definitions"},
        **_error_responses,
    },
)
async def list_signal_definitions(
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> Sequence[SignalDefinitionResponse]:
    """List all signal definitions."""
    ttl = resolve_ttl(CacheStrategy.SIGNAL_DEFINITIONS)
    cache_key = make_cache_key(CacheNamespace.SIGNALS, "definitions")
    cached = await cache_get(redis_client, cache_key)
    if isinstance(cached, list):
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = cache_control_header(ttl)
        return [SignalDefinitionResponse.model_validate(item) for item in cached]

    stmt = select(SignalDefinition)
    result = await db.execute(stmt)
    definitions = result.scalars().all()
    payload = [SignalDefinitionResponse.model_validate(item) for item in definitions]
    await cache_set(
        redis_client,
        cache_key,
        [item.model_dump(mode="json") for item in payload],
        ttl,
    )
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload


@router.get(
    "/{signal_id}/logs",
    response_model=list[SignalLogResponse],
    summary="Get signal logs",
    description=(
        "Return recent evaluation logs for a specific signal, optionally filtered "
        "by geography.  Results are ordered newest-first."
    ),
    responses={
        200: {"description": "Signal evaluation logs"},
        404: {"model": ErrorResponse, "description": "Signal not found"},
        **_error_responses,
    },
)
async def get_signal_logs(
    signal_id: str,
    response: Response,
    geography: str | None = Query(
        None, description="Filter logs by geography identifier"
    ),
    limit: int = Query(
        50, ge=1, le=500, description="Maximum number of log entries to return"
    ),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> Sequence[SignalLogResponse]:
    """Get recent logs for a signal."""
    ttl = resolve_ttl(CacheStrategy.SIGNAL_LOGS)
    cache_key = make_cache_key(
        CacheNamespace.SIGNALS,
        "logs",
        signal_id=signal_id,
        geography=geography,
        limit=limit,
    )
    cached = await cache_get(redis_client, cache_key)
    if isinstance(cached, list):
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = cache_control_header(ttl)
        return [SignalLogResponse.model_validate(item) for item in cached]

    stmt = select(SignalLog).where(SignalLog.signal_id == signal_id)

    if geography:
        stmt = stmt.where(SignalLog.geography == geography)

    stmt = stmt.order_by(SignalLog.timestamp.desc()).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    payload = [SignalLogResponse.model_validate(item) for item in logs]
    await cache_set(
        redis_client,
        cache_key,
        [item.model_dump(mode="json") for item in payload],
        ttl,
    )
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload


@router.post(
    "/evaluate",
    response_model=list[SignalLogResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger signal evaluation",
    description=(
        "Enqueue a signal evaluation run for the specified geography and geo type. "
        "Returns ``202 Accepted`` immediately with the generated log entries."
    ),
    responses={
        202: {"description": "Evaluation accepted and logs returned"},
        **_error_responses,
    },
)
async def evaluate_signals(
    request: SignalEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> Sequence[SignalLog]:
    """Trigger signal evaluation for a geography."""
    evaluators = {
        "price_drop_30d": PriceDrop30dEvaluator(),
        "low_inventory": LowInventoryEvaluator(),
    }

    engine = PersistentSignalEngine(
        evaluators=evaluators,
        session=db,
        redis_client=redis_client,
    )

    logs = await engine.run_all_signals(
        geography=request.geography,
        geo_type=request.geo_type.value,
        run_id=request.run_id,
    )

    await invalidate_signals_cache(redis_client)
    return logs
