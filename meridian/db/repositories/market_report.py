from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.db.models import MarketReport
from meridian.db.models.enums import GeoType


class MarketReportRepository:
    """Repository for market report database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, report_id: str) -> MarketReport | None:
        """Get a market report by ID."""
        stmt = select(MarketReport).where(MarketReport.id == report_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest(
        self,
        *,
        geography: str,
        geo_type: GeoType,
    ) -> MarketReport | None:
        """Get the latest market report for a geography."""
        stmt = (
            select(MarketReport)
            .where(
                MarketReport.geography == geography,
                MarketReport.geo_type == geo_type,
            )
            .order_by(MarketReport.report_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_report(self, report: MarketReport) -> MarketReport:
        """Create a new market report."""
        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def get_reports_for_geography(
        self,
        *,
        geography: str,
        geo_type: GeoType,
        limit: int = 10,
    ) -> Sequence[MarketReport]:
        """Get recent reports for a geography."""
        stmt = (
            select(MarketReport)
            .where(
                MarketReport.geography == geography,
                MarketReport.geo_type == geo_type,
            )
            .order_by(MarketReport.report_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()