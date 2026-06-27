from __future__ import annotations

from typing import Sequence

from meridian.db.models import MarketReport
from meridian.signals.base import SignalEvaluator, SignalResult


class LowInventoryEvaluator(SignalEvaluator):
    """Evaluates low_inventory signal: months of inventory < threshold."""

    name = "low_inventory"

    async def evaluate(
        self,
        geography: str,
        history: Sequence[MarketReport],
    ) -> SignalResult:
        """Evaluate low inventory signal."""
        # Get latest report
        if not history:
            return SignalResult(
                raw_value=0.0,
                computed_output={"error": "no_data"},
                confidence=0.0,
                fired=False,
            )

        latest_report = max(history, key=lambda r: r.report_date)

        months_of_inventory = latest_report.months_of_inventory

        # Threshold from config (default 2.0)
        threshold = 2.0  # TODO: load from config

        fired = months_of_inventory < threshold

        return SignalResult(
            raw_value=months_of_inventory,
            computed_output={
                "threshold": threshold,
                "active_listings": latest_report.active_listings,
                "sold_last_30d": latest_report.sold_last_30d,
                "absorption_rate": latest_report.absorption_rate,
            },
            confidence=1.0 if latest_report.active_listings > 0 else 0.0,
            fired=fired,
        )
