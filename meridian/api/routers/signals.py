from __future__ import annotations

from typing import Sequence

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.deps import get_db, get_redis
from meridian.api.schemas import (
    SignalDefinitionResponse,
    SignalEvaluateRequest,
    SignalLogResponse,
)
from meridian.db.models import SignalDefinition, SignalLog
from meridian.signals.engine import PersistentSignalEngine
from meridian.signals.evaluators import LowInventoryEvaluator, PriceDrop30dEvaluator
from redis.asyncio import Redis

router = APIRouter(prefix="/v1/signals", tags=["signals"])


@router.get("", response_model=list[SignalDefinitionResponse])
async def list_signal_definitions(
    db: AsyncSession = Depends(get_db),
) -> Sequence[SignalDefinition]:
    """List all signal definitions."""
    stmt = select(SignalDefinition)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{signal_id}/logs", response_model=list[SignalLogResponse])
async def get_signal_logs(
    signal_id: str,
    geography: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> Sequence[SignalLog]:
    """Get recent logs for a signal."""
    stmt = select(SignalLog).where(SignalLog.signal_id == signal_id)

    if geography:
        stmt = stmt.where(SignalLog.geography == geography)

    stmt = stmt.order_by(SignalLog.timestamp.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


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

    return logs
