from __future__ import annotations

from typing import Any, Sequence

from fastapi import APIRouter, Depends, Query, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.auth import get_current_token
from meridian.api.deps import get_db, get_redis
from meridian.api.exceptions import BadRequestError, NotFoundError
from meridian.api.models.errors import ErrorCode, ErrorResponse
from meridian.api.schemas import (
    ComparablePropertiesReportResponse,
    CustomDashboardRequest,
    CustomDashboardResponse,
    DemographicCorrelationResponse,
    ForecastResponse,
    HeatIndexResponse,
    InvestmentSignalsRequest,
    InvestmentSignalsResponse,
    MarketMetric,
    MarketReportRefreshRequest,
    MarketReportResponse,
    MarketReportScheduleResponse,
    NeighborhoodComparisonResponse,
    ScheduleReportRequest,
    SeasonalAnalysisResponse,
)
from meridian.cache.helpers import cache_control_header, cache_get, cache_set
from meridian.cache.invalidation import invalidate_market_reports_cache
from meridian.cache.keys import make_cache_key
from meridian.cache.strategies import CacheNamespace, CacheStrategy, resolve_ttl
from meridian.db.models import MarketReportArtifact
from meridian.db.models.enums import GeoType, PropertyType
from meridian.db.repositories import MarketReportRepository
from meridian.services import MarketReportService

router = APIRouter(prefix="/v1/market-reports", tags=["market-reports"])

_error_responses: dict[int | str, dict[str, Any]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token",
    },
    404: {"model": ErrorResponse, "description": "Market report not found"},
    422: {"model": ErrorResponse, "description": "Request validation error"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
}


def _artifact_kwargs(artifact: MarketReportArtifact) -> dict[str, Any]:
    """Return common response fields for generated market report artifacts."""

    return {
        "id": artifact.id,
        "report_type": artifact.report_type,
        "geography": artifact.geography,
        "geo_type": artifact.geo_type,
        "parameters": artifact.parameters,
        "created_at": artifact.created_at,
    }


@router.get(
    "/latest",
    response_model=MarketReportResponse,
    summary="Get latest market report",
    description=(
        "Retrieve the most recent market report for the specified geography and "
        "geography type. Results are cached; see ``Cache-Control`` and ``X-Cache`` "
        "response headers."
    ),
    responses={
        200: {"description": "Latest market report"},
        **_error_responses,
    },
)
async def get_latest_report(
    response: Response,
    geography: str = Query(
        ...,
        description="Geography identifier (e.g. 'Austin', 'TX', '78701')",
        examples=["Austin"],
    ),
    geo_type: str = Query(
        ...,
        description=(
            "Geography type — one of METRO, ZIP, COUNTY, NEIGHBORHOOD, or CITY"
        ),
        examples=["CITY"],
    ),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> MarketReportResponse:
    """Get the latest market report for a geography."""
    ttl = resolve_ttl(CacheStrategy.MARKET_REPORT_LATEST)
    cache_key = make_cache_key(
        CacheNamespace.MARKET_REPORTS,
        "latest",
        geography=geography,
        geo_type=geo_type,
    )
    cached = await cache_get(redis_client, cache_key)
    if isinstance(cached, dict):
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = cache_control_header(ttl)
        return MarketReportResponse.model_validate(cached)

    service = MarketReportService(db)
    report = await service.get_latest_report(geography=geography, geo_type=geo_type)
    if not report:
        raise NotFoundError(
            "No market report found for the specified geography",
            error_code=ErrorCode.MARKET_REPORT_NOT_FOUND,
        )
    payload = MarketReportResponse.model_validate(report)
    await cache_set(redis_client, cache_key, payload.model_dump(mode="json"), ttl)
    detail_key = make_cache_key(
        CacheNamespace.MARKET_REPORTS,
        "detail",
        report_id=payload.id,
    )
    await cache_set(
        redis_client,
        detail_key,
        payload.model_dump(mode="json"),
        resolve_ttl(CacheStrategy.MARKET_REPORT_DETAIL),
    )
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload


@router.get(
    "/comps",
    response_model=ComparablePropertiesReportResponse,
    summary="Generate comparable properties report",
    responses={
        200: {"description": "Comparable properties report"},
        **_error_responses,
    },
)
async def get_comparable_properties_report(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_miles: float = Query(..., gt=0, le=50),
    property_type: PropertyType = Query(...),
    bedrooms: int | None = Query(None, ge=0, le=20),
    db: AsyncSession = Depends(get_db),
    _token: dict[str, Any] = Depends(get_current_token),
) -> ComparablePropertiesReportResponse:
    """Generate comparable properties nearby using the configured adapter."""
    service = MarketReportService(db)
    artifact = await service.generate_comparable_properties_report(
        lat=lat,
        lon=lon,
        radius_miles=radius_miles,
        property_type=property_type,
        bedrooms=bedrooms,
    )
    return ComparablePropertiesReportResponse.model_validate(
        {
            **_artifact_kwargs(artifact),
            **artifact.payload,
        }
    )


@router.post(
    "/investment-signals",
    response_model=InvestmentSignalsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate investment opportunity signals",
    responses={201: {"description": "Investment signals report"}, **_error_responses},
)
async def create_investment_signals_report(
    request: InvestmentSignalsRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> InvestmentSignalsResponse:
    """Generate investment opportunity signals and persist the report artifact."""
    service = MarketReportService(db)
    artifact = await service.generate_investment_signals(
        geography=request.geography,
        min_roi=request.min_roi,
        max_price=request.max_price,
        risk_level=request.risk_level.value,
    )
    await invalidate_market_reports_cache(redis_client)
    return InvestmentSignalsResponse.model_validate(
        {
            **_artifact_kwargs(artifact),
            **artifact.payload,
        }
    )


@router.get(
    "/compare",
    response_model=NeighborhoodComparisonResponse,
    summary="Compare neighborhood trends",
    responses={
        200: {"description": "Neighborhood comparison report"},
        **_error_responses,
    },
)
async def compare_neighborhood_trends(
    geographies: list[str] = Query(..., min_length=2),
    metric: MarketMetric = Query(...),
    db: AsyncSession = Depends(get_db),
    _token: dict[str, Any] = Depends(get_current_token),
) -> NeighborhoodComparisonResponse:
    """Compare multiple markets side by side."""
    service = MarketReportService(db)
    artifact = await service.compare_neighborhood_trends(
        geographies=geographies,
        metric=metric.value,
    )
    return NeighborhoodComparisonResponse.model_validate(
        {
            **_artifact_kwargs(artifact),
            **artifact.payload,
        }
    )


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Forecast market conditions",
    responses={200: {"description": "Predictive analytics report"}, **_error_responses},
)
async def get_market_forecast(
    geography: str = Query(...),
    months_ahead: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    _token: dict[str, Any] = Depends(get_current_token),
) -> ForecastResponse:
    """Forecast market conditions for the requested horizon."""
    service = MarketReportService(db)
    artifact = await service.generate_forecast(
        geography=geography,
        months_ahead=months_ahead,
    )
    return ForecastResponse.model_validate(
        {
            **_artifact_kwargs(artifact),
            **artifact.payload,
        }
    )


@router.get(
    "/heat-index",
    response_model=HeatIndexResponse,
    summary="Get market heat index",
    responses={200: {"description": "Market heat index report"}, **_error_responses},
)
async def get_market_heat_index(
    geography: str = Query(...),
    geo_type: GeoType = Query(...),
    db: AsyncSession = Depends(get_db),
    _token: dict[str, Any] = Depends(get_current_token),
) -> HeatIndexResponse:
    """Compute a single market heat score for a geography."""
    service = MarketReportService(db)
    artifact = await service.generate_heat_index(
        geography=geography,
        geo_type=geo_type.value,
    )
    return HeatIndexResponse.model_validate(
        {
            **_artifact_kwargs(artifact),
            **artifact.payload,
        }
    )


@router.get(
    "/seasonal",
    response_model=SeasonalAnalysisResponse,
    summary="Generate seasonal analysis report",
    responses={200: {"description": "Seasonal analysis report"}, **_error_responses},
)
async def get_seasonal_analysis_report(
    geography: str = Query(...),
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    _token: dict[str, Any] = Depends(get_current_token),
) -> SeasonalAnalysisResponse:
    """Analyze seasonal patterns for a geography."""
    service = MarketReportService(db)
    artifact = await service.generate_seasonal_analysis(
        geography=geography,
        year=year,
        month=month,
    )
    return SeasonalAnalysisResponse.model_validate(
        {
            **_artifact_kwargs(artifact),
            **artifact.payload,
        }
    )


@router.get(
    "/demographics",
    response_model=DemographicCorrelationResponse,
    summary="Generate demographic correlation report",
    responses={
        200: {"description": "Demographic correlation report"},
        **_error_responses,
    },
)
async def get_demographic_correlation_report(
    geography: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _token: dict[str, Any] = Depends(get_current_token),
) -> DemographicCorrelationResponse:
    """Link market metrics to demographic trends."""
    service = MarketReportService(db)
    artifact = await service.generate_demographic_correlation(geography=geography)
    return DemographicCorrelationResponse.model_validate(
        {
            **_artifact_kwargs(artifact),
            **artifact.payload,
        }
    )


@router.post(
    "/schedules",
    response_model=MarketReportScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule automated market reports",
    responses={201: {"description": "Scheduled report created"}, **_error_responses},
)
async def create_market_report_schedule(
    request: ScheduleReportRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> MarketReportScheduleResponse:
    """Create a recurring report schedule."""
    service = MarketReportService(db)
    schedule = await service.create_schedule(
        geography=request.geography,
        frequency=request.frequency.value,
        email=request.email,
        metrics=request.metrics,
    )
    await invalidate_market_reports_cache(redis_client)
    return MarketReportScheduleResponse.model_validate(schedule)


@router.post(
    "/custom",
    response_model=CustomDashboardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate custom dashboard report",
    responses={201: {"description": "Custom dashboard report"}, **_error_responses},
)
async def create_custom_dashboard_report(
    request: CustomDashboardRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> CustomDashboardResponse:
    """Generate a custom dashboard report for selected metrics."""
    service = MarketReportService(db)
    artifact = await service.generate_custom_dashboard(
        geography=request.geography,
        selected_metrics=request.selected_metrics,
        date_range=request.date_range.model_dump(mode="json"),
    )
    await invalidate_market_reports_cache(redis_client)
    return CustomDashboardResponse.model_validate(
        {
            **_artifact_kwargs(artifact),
            **artifact.payload,
        }
    )


@router.post(
    "/refresh",
    response_model=MarketReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh market report",
    description=(
        "Pull fresh data from the upstream adapter for the given geography and "
        "persist a new market report. Invalidates the relevant cache entries."
    ),
    responses={
        200: {"description": "Refreshed market report"},
        400: {"model": ErrorResponse, "description": "Invalid geography or geo_type"},
        **_error_responses,
    },
)
async def refresh_report(
    request: MarketReportRefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> MarketReportResponse:
    """Refresh market report by pulling fresh data from adapter and clearing cache."""
    service = MarketReportService(db)
    report = await service.refresh_report(
        geography=request.geography,
        geo_type=request.geo_type.value,
        as_of=request.as_of,
    )
    await invalidate_market_reports_cache(redis_client)
    return MarketReportResponse.model_validate(report)


@router.get(
    "",
    response_model=list[MarketReportResponse],
    summary="List market reports",
    description=(
        "Return a list of recent market reports for the specified geography. "
        "Results are ordered by report date descending."
    ),
    responses={
        200: {"description": "List of market reports"},
        **_error_responses,
    },
)
async def list_reports(
    response: Response,
    geography: str = Query(..., description="Geography identifier"),
    geo_type: str = Query(
        ...,
        description=(
            "Geography type — one of METRO, ZIP, COUNTY, NEIGHBORHOOD, or CITY"
        ),
    ),
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of reports to return"
    ),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> Sequence[MarketReportResponse]:
    """List recent market reports for a geography."""
    ttl = resolve_ttl(CacheStrategy.MARKET_REPORTS_LIST)
    cache_key = make_cache_key(
        CacheNamespace.MARKET_REPORTS,
        "list",
        geography=geography,
        geo_type=geo_type,
        limit=limit,
    )
    cached = await cache_get(redis_client, cache_key)
    if isinstance(cached, list):
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = cache_control_header(ttl)
        return [MarketReportResponse.model_validate(item) for item in cached]

    geo_type_enum = GeoType(geo_type)
    repo = MarketReportRepository(db)
    reports = await repo.get_reports_for_geography(
        geography=geography,
        geo_type=geo_type_enum,
        limit=limit,
    )
    payload = [MarketReportResponse.model_validate(report) for report in reports]
    await cache_set(
        redis_client,
        cache_key,
        [item.model_dump(mode="json") for item in payload],
        ttl,
    )
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload


@router.get(
    "/{report_id}/export",
    summary="Export report as PDF",
    responses={
        200: {"description": "PDF export"},
        400: {"model": ErrorResponse, "description": "Unsupported export format"},
        **_error_responses,
    },
)
async def export_market_report(
    report_id: str,
    export_format: str = Query("pdf", alias="format"),
    db: AsyncSession = Depends(get_db),
    _token: dict[str, Any] = Depends(get_current_token),
) -> Response:
    """Export a stored market report or generated artifact as PDF."""
    if export_format.lower() != "pdf":
        raise BadRequestError(
            "Only PDF export is supported",
            error_code=ErrorCode.BAD_REQUEST,
        )

    service = MarketReportService(db)
    try:
        pdf_bytes = await service.export_report_pdf(report_id)
    except LookupError as exc:
        raise NotFoundError(
            str(exc),
            error_code=ErrorCode.MARKET_REPORT_NOT_FOUND,
        ) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="market-report-{report_id}.pdf"'
        },
    )


@router.get(
    "/{report_id}",
    response_model=MarketReportResponse,
    summary="Get market report by ID",
    description="Retrieve a specific market report by its unique identifier.",
    responses={
        200: {"description": "Market report details"},
        **_error_responses,
    },
)
async def get_report(
    report_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> MarketReportResponse:
    """Get a market report by ID."""
    ttl = resolve_ttl(CacheStrategy.MARKET_REPORT_DETAIL)
    cache_key = make_cache_key(
        CacheNamespace.MARKET_REPORTS,
        "detail",
        report_id=report_id,
    )
    cached = await cache_get(redis_client, cache_key)
    if isinstance(cached, dict):
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = cache_control_header(ttl)
        return MarketReportResponse.model_validate(cached)

    repo = MarketReportRepository(db)
    report = await repo.get_by_id(report_id)
    if not report:
        raise NotFoundError(
            "Market report not found",
            error_code=ErrorCode.MARKET_REPORT_NOT_FOUND,
        )
    payload = MarketReportResponse.model_validate(report)
    await cache_set(redis_client, cache_key, payload.model_dump(mode="json"), ttl)
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload
