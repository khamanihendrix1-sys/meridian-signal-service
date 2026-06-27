"""
Example hooks usage demonstrating how to register and use lifecycle events.

This module shows patterns for common monitoring, logging, and integration tasks.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from meridian.hooks import (
    APP_SHUTDOWN,
    APP_STARTUP,
    COMP_COMPUTE_COMPLETE,
    COMP_COMPUTE_FAILED,
    COMP_COMPUTE_START,
    DB_SESSION_CLOSED,
    DB_SESSION_OPENED,
    MARKET_REPORT_REFRESH_COMPLETE,
    MARKET_REPORT_REFRESH_START,
    SIGNAL_RUN_COMPLETE,
    SIGNAL_RUN_START,
    register_hook,
    trigger_hook,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Application Startup Monitoring
# ============================================================================


def on_app_startup(**payload: Any) -> None:
    """Log app startup event and initialize resources."""
    logger.info("✓ Application started - initializing resources")


async def on_app_shutdown(**payload: Any) -> None:
    """Async cleanup on shutdown."""
    logger.info("✓ Application shutting down - closing resources")
    await asyncio.sleep(0.1)  # Simulated cleanup


# ============================================================================
# Example 2: Database Session Tracking
# ============================================================================


def on_db_session_opened(session: Any, **payload: Any) -> None:
    """Track open database sessions."""
    logger.debug(f"📖 Database session opened: {id(session)}")


def on_db_session_closed(session: Any, **payload: Any) -> None:
    """Track closed database sessions."""
    logger.debug(f"📖 Database session closed: {id(session)}")


# ============================================================================
# Example 3: Market Report Refresh Tracking
# ============================================================================


def on_market_report_refresh_start(
    geography: str,
    geo_type: str,
    as_of: Any,
    **payload: Any,
) -> None:
    """Log when market report refresh begins."""
    logger.info(
        f"📊 Market report refresh started for {geography} ({geo_type}) as of {as_of}"
    )


def on_market_report_refresh_complete(
    geography: str,
    geo_type: str,
    report_id: Any,
    **payload: Any,
) -> None:
    """Log when market report refresh completes."""
    logger.info(
        f"✓ Market report refresh completed for {geography} ({geo_type}), report_id={report_id}"
    )


# ============================================================================
# Example 4: Comp Computation Lifecycle
# ============================================================================


def on_comp_compute_start(
    subject_listing_id: Any,
    job_id: Any,
    limit: int,
    **payload: Any,
) -> None:
    """Log when comp computation begins."""
    logger.info(
        f"🔍 Starting comp computation: job_id={job_id}, subject={subject_listing_id}, limit={limit}"
    )


def on_comp_compute_complete(
    job_id: Any,
    subject_listing_id: Any,
    comp_ids: list[str],
    count: int,
    **payload: Any,
) -> None:
    """Log when comp computation completes successfully."""
    logger.info(f"✓ Comp computation completed: job_id={job_id}, found {count} comps")


def on_comp_compute_failed(
    job_id: Any,
    subject_listing_id: Any,
    error: str,
    **payload: Any,
) -> None:
    """Log when comp computation fails."""
    logger.error(f"✗ Comp computation failed: job_id={job_id}, error={error}")


# ============================================================================
# Example 5: Signal Run Tracking
# ============================================================================


async def on_signal_run_start(
    geography: str,
    geo_type: str,
    **payload: Any,
) -> None:
    """Async hook for signal run start (e.g., emit metrics)."""
    logger.info(f"🚀 Signal evaluation started for {geography} ({geo_type})")


async def on_signal_run_complete(
    geography: str,
    geo_type: str,
    log_count: int,
    **payload: Any,
) -> None:
    """Async hook for signal run completion."""
    logger.info(
        f"✓ Signal evaluation completed for {geography} ({geo_type}): {log_count} logs created"
    )


# ============================================================================
# Hook Registration Function
# ============================================================================


def register_all_hooks() -> None:
    """Register all example hooks. Call this during app initialization."""
    # Application lifecycle
    register_hook(APP_STARTUP, on_app_startup)
    register_hook(APP_SHUTDOWN, on_app_shutdown)

    # Database session lifecycle
    register_hook(DB_SESSION_OPENED, on_db_session_opened)
    register_hook(DB_SESSION_CLOSED, on_db_session_closed)

    # Market reports
    register_hook(MARKET_REPORT_REFRESH_START, on_market_report_refresh_start)
    register_hook(MARKET_REPORT_REFRESH_COMPLETE, on_market_report_refresh_complete)

    # Comps
    register_hook(COMP_COMPUTE_START, on_comp_compute_start)
    register_hook(COMP_COMPUTE_COMPLETE, on_comp_compute_complete)
    register_hook(COMP_COMPUTE_FAILED, on_comp_compute_failed)

    # Signals
    register_hook(SIGNAL_RUN_START, on_signal_run_start)
    register_hook(SIGNAL_RUN_COMPLETE, on_signal_run_complete)

    logger.info("✓ All example hooks registered")


# ============================================================================
# Standalone Testing
# ============================================================================


async def test_hooks() -> None:
    """Test hook system with sample events."""
    register_all_hooks()

    print("\n--- Testing Hook System ---\n")

    await trigger_hook(APP_STARTUP)
    await trigger_hook(
        MARKET_REPORT_REFRESH_START,
        geography="Atlanta-GA",
        geo_type="CITY",
        as_of="2026-05-03",
    )
    await trigger_hook(
        MARKET_REPORT_REFRESH_COMPLETE,
        geography="Atlanta-GA",
        geo_type="CITY",
        report_id="abc-123",
    )
    await trigger_hook(
        COMP_COMPUTE_START,
        subject_listing_id="subject-uuid",
        job_id="job-uuid",
        limit=10,
    )
    await trigger_hook(
        COMP_COMPUTE_COMPLETE,
        job_id="job-uuid",
        subject_listing_id="subject-uuid",
        comp_ids=["comp-1", "comp-2", "comp-3"],
        count=3,
    )
    await trigger_hook(
        SIGNAL_RUN_START,
        geography="Atlanta-GA",
        geo_type="CITY",
    )
    await trigger_hook(
        SIGNAL_RUN_COMPLETE,
        geography="Atlanta-GA",
        geo_type="CITY",
        log_count=5,
    )
    await trigger_hook(APP_SHUTDOWN)

    print("\n--- Test Complete ---\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    asyncio.run(test_hooks())
