from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from meridian.adapters import registry
from meridian.db.models import MarketReport
from meridian.db.repositories import MarketReportRepository
from meridian.hooks import MARKET_REPORT_REFRESH_START, trigger_hook


class MarketReportService:
    """Service for market report operations, including adapter integration."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MarketReportRepository(session)

    async def get_latest_report(
        self,
        *,
        geography: str,
        geo_type: str,
    ) -> MarketReport | None:
        """Get the latest market report for a geography."""
        from meridian.db.models.enums import GeoType

        geo_type_enum = GeoType(geo_type)
        return await self.repo.get_latest(geography=geography, geo_type=geo_type_enum)

    async def refresh_report(
        self,
        *,
        geography: str,
        geo_type: str,
        as_of: date | None = None,
    ) -> MarketReport:
        """Refresh market report by calling the resolved adapter."""
        from meridian.db.models.enums import GeoType

        geo_type_enum = GeoType(geo_type)
        as_of_date = as_of or date.today()

        await trigger_hook(
            MARKET_REPORT_REFRESH_START,
            geography=geography,
            geo_type=geo_type,
            as_of=as_of_date,
        )

        # Resolve adapter for geography
        adapter = registry.for_geography(geography)

        # Fetch metrics from adapter
        raw_metrics = await adapter.fetch_market_metrics(
            geography=geography,
            geo_type=geo_type,
            as_of=as_of_date,
        )

        # Create new report
        report = MarketReport(
            id=uuid4(),
            geography=geography,
            geo_type=geo_type_enum,
            report_date=as_of_date,
            median_price=raw_metrics.median_price,
            mean_price=raw_metrics.mean_price,
            active_listings=raw_metrics.active_listings,
            sold_last_30d=raw_metrics.sold_last_30d,
            avg_days_on_market=raw_metrics.avg_days_on_market,
            months_of_inventory=raw_metrics.months_of_inventory,
            absorption_rate=raw_metrics.absorption_rate,
            yoy_price_change=raw_metrics.yoy_price_change,
            mom_price_change=raw_metrics.mom_price_change,
            list_to_sold_ratio=raw_metrics.list_to_sold_ratio,
            raw_metrics=raw_metrics.raw_metrics,
            created_at=datetime.utcnow(),
        )

        return await self.repo.create_report(report)
