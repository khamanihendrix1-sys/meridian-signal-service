from __future__ import annotations

from datetime import datetime
from typing import Sequence
from uuid import uuid4

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.db.models import MarketReport, SignalDefinition, SignalLog
from meridian.db.repositories import MarketReportRepository
from meridian.signals.base import SignalEngine, SignalEvaluator


class PersistentSignalEngine(SignalEngine):
    """Signal engine with persistence and Redis-based locking."""

    def __init__(
        self,
        evaluators: dict[str, SignalEvaluator],
        session: AsyncSession,
        redis_client: redis.Redis,
    ) -> None:
        super().__init__(evaluators)
        self.session = session
        self.redis = redis_client
        self.market_repo = MarketReportRepository(session)

    async def run_all_signals(
        self,
        geography: str,
        geo_type: str,
        run_id: str | None = None,
    ) -> list[SignalLog]:
        """Run all active signals for a geography."""
        run_id = run_id or str(uuid4())

        # Get all signal definitions
        from sqlalchemy import select

        stmt = select(SignalDefinition)
        result = await self.session.execute(stmt)
        definitions = result.scalars().all()

        # Get historical market data
        from meridian.db.models.enums import GeoType

        geo_type_enum = GeoType(geo_type)
        history = await self.market_repo.get_reports_for_geography(
            geography=geography,
            geo_type=geo_type_enum,
            limit=100,  # Last 100 reports for analysis
        )

        logs: list[SignalLog] = []
        for definition in definitions:
            log = await self._evaluate_and_log_signal(
                definition, geography, geo_type_enum, history, run_id
            )
            logs.append(log)

        if logs:
            self.session.add_all(logs)
            await self.session.commit()

        return logs

    async def _evaluate_and_log_signal(
        self,
        definition: SignalDefinition,
        geography: str,
        geo_type: str,
        history: Sequence[MarketReport],
        run_id: str,
    ) -> SignalLog:
        """Evaluate a signal and persist the log."""
        # Redis lock key for idempotency
        lock_key = f"signal:{definition.id}:{geography}:{run_id}"
        acquired = await self.redis.set(lock_key, "1", ex=3600, nx=True)
        if not acquired:
            # Already running or ran recently
            raise ValueError(
                f"Signal {definition.name} already running for {geography}"
            )

        try:
            # Evaluate signal
            result = await self.evaluate_signal(definition.name, geography, history)

            # Create log
            log = SignalLog(
                id=uuid4(),
                signal_id=definition.id,
                geography=geography,
                geo_type=geo_type,
                timestamp=datetime.utcnow(),
                raw_value=result.raw_value,
                computed_output=result.computed_output,
                confidence=result.confidence,
                fired=result.fired,
                created_at=datetime.utcnow(),
            )

            return log
        finally:
            await self.redis.delete(lock_key)
