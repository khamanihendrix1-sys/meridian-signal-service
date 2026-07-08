from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from pydantic import ValidationError

from meridian.api.schemas.market_report import (
    ComparablePropertiesReportResponse,
    CustomDashboardRequest,
    CustomDashboardResponse,
    ForecastResponse,
    HeatIndexResponse,
    ScheduleReportRequest,
)
from meridian.db.models.enums import GeoType, PropertyType
from meridian.services.market_report import MarketReportService


class _FakeMarketReportRepo:
    def __init__(self) -> None:
        self._artifacts: dict[str, Any] = {}

    async def create_generated_report(self, report: Any) -> Any:
        if getattr(report, "created_at", None) is None:
            report.created_at = datetime.now(UTC)
        self._artifacts[str(report.id)] = report
        return report

    async def create_schedule(self, schedule: Any) -> Any:
        if getattr(schedule, "created_at", None) is None:
            schedule.created_at = datetime.now(UTC)
        return schedule

    async def get_generated_report(self, report_id: str) -> Any:
        return self._artifacts.get(report_id)

    async def get_by_id(self, report_id: str) -> Any:
        return None


def _build_service() -> MarketReportService:
    service = MarketReportService(cast(Any, None))
    service.repo = cast(Any, _FakeMarketReportRepo())
    return service


@pytest.mark.asyncio
async def test_generate_comparable_properties_report_returns_filtered_payload() -> None:
    service = _build_service()

    artifact = await service.generate_comparable_properties_report(
        lat=33.749,
        lon=-84.388,
        radius_miles=3.5,
        property_type=PropertyType.SFR,
        bedrooms=3,
    )
    payload = ComparablePropertiesReportResponse.model_validate(
        {
            "id": artifact.id,
            "report_type": artifact.report_type,
            "geography": artifact.geography,
            "geo_type": artifact.geo_type,
            "parameters": artifact.parameters,
            "created_at": artifact.created_at,
            **artifact.payload,
        }
    )

    assert payload.report_type == "comparable_properties"
    assert payload.parameters["bedrooms"] == 3
    assert payload.comps
    assert all(comp.property_type == PropertyType.SFR for comp in payload.comps)


@pytest.mark.asyncio
async def test_generate_forecast_respects_requested_horizon() -> None:
    service = _build_service()

    artifact = await service.generate_forecast(
        geography="Atlanta",
        months_ahead=4,
    )
    payload = ForecastResponse.model_validate(
        {
            "id": artifact.id,
            "report_type": artifact.report_type,
            "geography": artifact.geography,
            "geo_type": artifact.geo_type,
            "parameters": artifact.parameters,
            "created_at": artifact.created_at,
            **artifact.payload,
        }
    )

    assert payload.months_ahead == 4
    assert len(payload.monthly_forecast) == 4
    assert payload.market_cycle in {"expansion", "cooling", "stabilizing"}


@pytest.mark.asyncio
async def test_heat_index_stays_in_expected_range() -> None:
    service = _build_service()

    artifact = await service.generate_heat_index(
        geography="Atlanta",
        geo_type=GeoType.CITY.value,
    )
    payload = HeatIndexResponse.model_validate(
        {
            "id": artifact.id,
            "report_type": artifact.report_type,
            "geography": artifact.geography,
            "geo_type": artifact.geo_type,
            "parameters": artifact.parameters,
            "created_at": artifact.created_at,
            **artifact.payload,
        }
    )

    assert 0 <= payload.heat_index <= 100
    assert payload.market_label in {"hot", "warm", "cold"}


@pytest.mark.asyncio
async def test_export_report_pdf_returns_pdf_bytes() -> None:
    service = _build_service()
    request = CustomDashboardRequest.model_validate(
        {
            "geography": "Atlanta",
            "selected_metrics": ["median_price", "inventory"],
            "date_range": {
                "start_date": "2024-01-01",
                "end_date": "2024-06-30",
            },
        }
    )
    artifact = await service.generate_custom_dashboard(
        geography=request.geography,
        selected_metrics=request.selected_metrics,
        date_range=request.date_range.model_dump(mode="json"),
    )

    payload = CustomDashboardResponse.model_validate(
        {
            "id": artifact.id,
            "report_type": artifact.report_type,
            "geography": artifact.geography,
            "geo_type": artifact.geo_type,
            "parameters": artifact.parameters,
            "created_at": artifact.created_at,
            **artifact.payload,
        }
    )
    pdf_bytes = await service.export_report_pdf(str(artifact.id))

    assert payload.selected_metrics == ["median_price", "inventory"]
    assert payload.export_formats == ["csv", "excel"]
    assert pdf_bytes.startswith(b"%PDF")


def test_schedule_request_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        ScheduleReportRequest.model_validate(
            {
                "geography": "Atlanta",
                "frequency": "weekly",
                "email": "invalid-email",
                "metrics": ["median_price"],
            }
        )
