from __future__ import annotations

from typing import Sequence

from fastapi import APIRouter, Depends, Query, Response
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.deps import get_db, get_redis
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


@router.get("", response_model=list[SignalDefinitionResponse])
async def list_signal_definitions(
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
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


@router.get("/{signal_id}/logs", response_model=list[SignalLogResponse])
async def get_signal_logs(
    signal_id: str,
    response: Response,
    geography: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
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


@router.post("/evaluate", response_model=list[SignalLogResponse])
async def evaluate_signals(
    request: SignalEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
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
