from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from redis.asyncio import Redis

from meridian.db.session import async_session_factory
from meridian.hooks import SIGNAL_RUN_COMPLETE, SIGNAL_RUN_START, trigger_hook
from meridian.settings import settings
from meridian.signals.engine import PersistentSignalEngine
from meridian.signals.evaluators import LowInventoryEvaluator, PriceDrop30dEvaluator

logger = logging.getLogger(__name__)


class SignalScheduler:
    """Scheduler for running signal evaluations."""

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self.redis = Redis.from_url(settings.redis_url)
        self.evaluators = {
            "price_drop_30d": PriceDrop30dEvaluator(),
            "low_inventory": LowInventoryEvaluator(),
        }

    async def start(self) -> None:
        """Start the scheduler."""
        self.scheduler.add_job(
            self._run_signals_job,
            CronTrigger(hour="*/6"),
            id="run_signals",
            name="Run all signals",
        )

        self.scheduler.start()
        logger.info("Signal scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self.scheduler.shutdown()
        await self.redis.close()
        logger.info("Signal scheduler stopped")

    async def _run_signals_job(self) -> None:
        """Job to run signals for all geographies."""
        geographies = [
            ("Atlanta-GA", "CITY"),
            ("30301", "ZIP"),
            ("30309", "ZIP"),
        ]

        async with async_session_factory() as session:
            engine = PersistentSignalEngine(
                evaluators=self.evaluators,
                session=session,
                redis_client=self.redis,
            )

            for geography, geo_type in geographies:
                try:
                    await trigger_hook(
                        SIGNAL_RUN_START,
                        geography=geography,
                        geo_type=geo_type,
                    )
                    logs = await engine.run_all_signals(geography, geo_type)
                    await trigger_hook(
                        SIGNAL_RUN_COMPLETE,
                        geography=geography,
                        geo_type=geo_type,
                        log_count=len(logs),
                    )
                    logger.info(
                        f"Ran signals for {geography}: {len(logs)} logs created"
                    )
                except Exception as e:
                    logger.exception(f"Failed to run signals for {geography}: {e}")


def run_scheduler() -> None:
    """Run the signal scheduler."""
    import asyncio

    scheduler = SignalScheduler()

    async def main() -> None:
        await scheduler.start()
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            await scheduler.stop()

    asyncio.run(main())
