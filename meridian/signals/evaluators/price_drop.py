from __future__ import annotations

from datetime import date, timedelta
from typing import Sequence

from meridian.db.models import MarketReport
from meridian.signals.base import SignalEvaluator, SignalResult


class PriceDrop30dEvaluator(SignalEvaluator):
    """Evaluates price_drop_30d signal: median price decreased ≥ threshold over 30-day window."""

    name = "price_drop_30d"

    async def evaluate(
        self,
        geography: str,
        history: Sequence[MarketReport],
    ) -> SignalResult:
        """Evaluate price drop over 30 days."""
        cutoff = date.today() - timedelta(days=30)
        recent_reports = [
            r for r in history
            if r.report_date >= cutoff
            and r.median_price is not None
        ]

        if len(recent_reports) < 2:
            return SignalResult(
                raw_value=0.0,
                computed_output={"error": "insufficient_data"},
                confidence=0.0,
                fired=False,
            )

        recent_reports.sort(key=lambda r: r.report_date)

        oldest_price = recent_reports[0].median_price
        newest_price = recent_reports[-1].median_price

        if oldest_price == 0:
            price_change_pct = 0.0
        else:
            price_change_pct = float(((newest_price - oldest_price) / oldest_price) * 100)

        threshold = -5.0
        fired = price_change_pct <= threshold

        return SignalResult(
            raw_value=price_change_pct,
            computed_output={
                "oldest_price": float(oldest_price),
                "newest_price": float(newest_price),
                "threshold": threshold,
                "days_window": 30,
            },
            confidence=min(1.0, len(recent_reports) / 10.0),
            fired=fired,
        )
