from __future__ import annotations

from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.deps import get_db
from meridian.api.schemas import MarketReportRefreshRequest, MarketReportResponse
from meridian.db.models import MarketReport
from meridian.db.repositories import MarketReportRepository
from meridian.services import MarketReportService

router = APIRouter(prefix="/v1/market-reports", tags=["market-reports"])


@router.get("/latest", response_model=MarketReportResponse)
async def get_latest_report(
    geography: str = Query(..., description="Geography identifier"),
    geo_type: str = Query(..., description="Geography type (METRO, ZIP, etc.)"),
    db: AsyncSession = Depends(get_db),
) -> MarketReport:
    """Get the latest market report for a geography."""
    service = MarketReportService(db)
    report = await service.get_latest_report(geography=geography, geo_type=geo_type)
    if not report:
        raise HTTPException(status_code=404, detail="No market report found")
    return report


@router.get("/{report_id}", response_model=MarketReportResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
) -> MarketReport:
    """Get a market report by ID."""
    repo = MarketReportRepository(db)
    report = await repo.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Market report not found")
    return report


@router.post("/refresh", response_model=MarketReportResponse)
async def refresh_report(
    request: MarketReportRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> MarketReport:
    """Refresh market report by pulling fresh data from adapter."""
    service = MarketReportService(db)
    return await service.refresh_report(
        geography=request.geography,
        geo_type=request.geo_type.value,
        as_of=request.as_of,
    )


@router.get("", response_model=list[MarketReportResponse])
async def list_reports(
    geography: str = Query(..., description="Geography identifier"),
    geo_type: str = Query(..., description="Geography type (METRO, ZIP, etc.)"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Sequence[MarketReport]:
    """List recent market reports for a geography."""
    from meridian.db.models.enums import GeoType
    geo_type_enum = GeoType(geo_type)
    repo = MarketReportRepository(db)
    return await repo.get_reports_for_geography(
        geography=geography,
        geo_type=geo_type_enum,
        limit=limit,
    )