from __future__ import annotations

import hashlib
import io
import random
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
from reportlab.pdfgen import canvas  # type: ignore[import-untyped]
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.adapters import registry
from meridian.db.models import MarketReport, MarketReportArtifact, MarketReportSchedule
from meridian.db.models.enums import GeoType, PropertyType
from meridian.db.repositories import MarketReportRepository

MAX_PDF_LINE_LENGTH = 110


def _clip(value: float, lower: float, upper: float) -> float:
    """Clamp a numeric value to an inclusive range."""

    return max(lower, min(upper, value))


def _average_decimal(values: list[Decimal]) -> Decimal:
    """Return the average for decimal values or zero when empty."""

    if not values:
        return Decimal("0.00")
    return sum(values) / Decimal(len(values))


def _average_float(values: list[float]) -> float:
    """Return the average for floats or zero when empty."""

    if not values:
        return 0.0
    return sum(values) / len(values)


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
        geo_type_enum = GeoType(geo_type)
        as_of_date = as_of or date.today()

        adapter = registry.for_geography(geography)
        raw_metrics = await adapter.fetch_market_metrics(
            geography=geography,
            geo_type=geo_type,
            as_of=as_of_date,
        )

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
            created_at=datetime.now(UTC),
        )

        return await self.repo.create_report(report)

    async def generate_comparable_properties_report(
        self,
        *,
        lat: float,
        lon: float,
        radius_miles: float,
        property_type: PropertyType,
        bedrooms: int | None,
    ) -> MarketReportArtifact:
        """Generate a nearby comparable properties report."""
        adapter = registry.for_geography(f"{lat:.4f},{lon:.4f}")
        since = date.today() - timedelta(days=180)
        comps: list[dict[str, Any]] = []
        rng = self._rng_for_seed(f"comps:{lat}:{lon}:{property_type}:{bedrooms}")

        async for listing in adapter.fetch_sold_comps(
            center=(lat, lon),
            radius_miles=radius_miles,
            since=since,
            limit=24,
        ):
            if listing.property_type != property_type.value:
                continue
            if bedrooms is not None and listing.beds != bedrooms:
                continue

            sold_date = listing.sold_date
            days_on_market = (
                (sold_date - listing.list_date).days
                if sold_date is not None
                else rng.randint(10, 75)
            )
            comps.append(
                {
                    "address": listing.address,
                    "city": listing.city,
                    "state": listing.state,
                    "property_type": listing.property_type,
                    "bedrooms": listing.beds,
                    "bathrooms": listing.baths,
                    "list_price": str(listing.list_price),
                    "sold_price": (
                        str(listing.sold_price)
                        if listing.sold_price is not None
                        else None
                    ),
                    "days_on_market": days_on_market,
                    "distance_miles": round(rng.uniform(0.1, radius_miles), 2),
                    "sold_date": (
                        sold_date.isoformat() if sold_date is not None else None
                    ),
                }
            )
            if len(comps) == 8:
                break

        if not comps:
            comps = self._fallback_comps(
                rng=rng,
                radius_miles=radius_miles,
                property_type=property_type,
                bedrooms=bedrooms,
            )

        list_prices = [Decimal(item["list_price"]) for item in comps]
        sold_prices = [
            Decimal(item["sold_price"])
            for item in comps
            if item["sold_price"] is not None
        ]
        payload = {
            "average_list_price": str(
                _average_decimal(list_prices).quantize(Decimal("0.01"))
            ),
            "average_sold_price": str(
                _average_decimal(sold_prices).quantize(Decimal("0.01"))
            ),
            "average_days_on_market": round(
                _average_float([float(item["days_on_market"]) for item in comps]), 2
            ),
            "comps": comps,
        }
        return await self._store_generated_report(
            report_type="comparable_properties",
            geography=f"{lat:.4f},{lon:.4f}",
            geo_type=None,
            parameters={
                "lat": lat,
                "lon": lon,
                "radius_miles": radius_miles,
                "property_type": property_type.value,
                "bedrooms": bedrooms,
            },
            payload=payload,
        )

    async def generate_investment_signals(
        self,
        *,
        geography: str,
        min_roi: float,
        max_price: Decimal,
        risk_level: str,
    ) -> MarketReportArtifact:
        """Generate investment opportunity signals for a geography."""
        adapter = registry.for_geography(geography)
        metrics = await adapter.fetch_market_metrics(
            geography=geography,
            geo_type=GeoType.CITY.value,
            as_of=date.today(),
        )
        heat_index = self._heat_index_from_metrics(metrics)
        price_ratio = float(max_price / metrics.median_price)
        roi_boost = max(metrics.yoy_price_change, 0) * 100 + heat_index / 5
        risk_modifier = {"low": 0.85, "medium": 1.0, "high": 1.15}[risk_level]
        opportunities = [
            {
                "signal": "undervalued_neighborhood",
                "score": round(_clip(62 + price_ratio * 12, 0, 100), 2),
                "estimated_roi": round(
                    max(min_roi, roi_boost * 0.7 * risk_modifier), 2
                ),
                "market_heat": round(heat_index, 2),
                "rationale": "Pricing sits below projected appreciation momentum.",
            },
            {
                "signal": "fast_moving_market",
                "score": round(_clip(100 - metrics.avg_days_on_market, 0, 100), 2),
                "estimated_roi": round(
                    max(min_roi, (heat_index / 4) * risk_modifier),
                    2,
                ),
                "market_heat": round(heat_index, 2),
                "rationale": "Low days on market indicates strong demand velocity.",
            },
            {
                "signal": "cash_flow_potential",
                "score": round(
                    _clip(
                        55
                        + metrics.absorption_rate * 60
                        - metrics.months_of_inventory * 3,
                        0,
                        100,
                    ),
                    2,
                ),
                "estimated_roi": round(
                    max(min_roi, (metrics.list_to_sold_ratio * 8) * risk_modifier),
                    2,
                ),
                "market_heat": round(heat_index, 2),
                "rationale": "Tighter inventory supports rent and resale resilience.",
            },
        ]
        filtered = [
            item
            for item in opportunities
            if Decimal(str(item["estimated_roi"])) >= Decimal(str(min_roi))
            and metrics.median_price <= max_price * Decimal("1.20")
        ]
        if not filtered:
            filtered = opportunities[:1]

        return await self._store_generated_report(
            report_type="investment_signals",
            geography=geography,
            geo_type=GeoType.CITY,
            parameters={
                "geography": geography,
                "min_roi": min_roi,
                "max_price": str(max_price),
                "risk_level": risk_level,
            },
            payload={
                "min_roi": min_roi,
                "max_price": str(max_price),
                "risk_level": risk_level,
                "opportunities": filtered,
            },
        )

    async def compare_neighborhood_trends(
        self,
        *,
        geographies: list[str],
        metric: str,
    ) -> MarketReportArtifact:
        """Compare multiple neighborhoods side by side."""
        comparisons: list[dict[str, Any]] = []

        for geography in geographies:
            adapter = registry.for_geography(geography)
            metrics = await adapter.fetch_market_metrics(
                geography=geography,
                geo_type=GeoType.CITY.value,
                as_of=date.today(),
            )
            rng = self._rng_for_seed(f"compare:{geography}:{metric}")
            current_value = {
                "price": float(metrics.median_price),
                "dom": float(metrics.avg_days_on_market),
                "inventory": float(metrics.active_listings),
            }[metric]
            comparisons.append(
                {
                    "geography": geography,
                    "current_value": round(current_value, 2),
                    "trend_6mo": round(metrics.yoy_price_change * 100 / 2, 2),
                    "velocity_index": round(
                        _clip(100 - metrics.avg_days_on_market, 0, 100), 2
                    ),
                    "population_growth": round(rng.uniform(0.5, 4.5), 2),
                }
            )

        leader = max(
            comparisons,
            key=lambda item: (
                -item["current_value"] if metric == "dom" else item["current_value"]
            ),
        )["geography"]
        return await self._store_generated_report(
            report_type="neighborhood_comparison",
            geography=",".join(geographies),
            geo_type=GeoType.CITY,
            parameters={"geographies": geographies, "metric": metric},
            payload={
                "metric": metric,
                "leader": leader,
                "comparisons": comparisons,
            },
        )

    async def generate_forecast(
        self,
        *,
        geography: str,
        months_ahead: int,
    ) -> MarketReportArtifact:
        """Forecast market conditions for the given horizon."""
        adapter = registry.for_geography(geography)
        metrics = await adapter.fetch_market_metrics(
            geography=geography,
            geo_type=GeoType.CITY.value,
            as_of=date.today(),
        )
        growth_rate = (metrics.yoy_price_change + metrics.mom_price_change * 12) / 2
        inventory_growth = max(-0.2, min(0.3, metrics.months_of_inventory / 20 - 0.1))
        forecast: list[dict[str, Any]] = []

        for offset in range(1, months_ahead + 1):
            forecast.append(
                {
                    "month_offset": offset,
                    "predicted_median_price": str(
                        (
                            metrics.median_price
                            * Decimal(str(1 + growth_rate * (offset / 12)))
                        ).quantize(Decimal("0.01"))
                    ),
                    "predicted_inventory": max(
                        0,
                        int(
                            metrics.active_listings
                            * (1 + inventory_growth * offset / 6)
                        ),
                    ),
                    "predicted_days_on_market": round(
                        max(
                            5.0,
                            metrics.avg_days_on_market
                            * (1 - metrics.mom_price_change * offset),
                        ),
                        2,
                    ),
                }
            )

        if growth_rate > 0.05:
            market_cycle = "expansion"
        elif growth_rate < -0.02:
            market_cycle = "cooling"
        else:
            market_cycle = "stabilizing"

        return await self._store_generated_report(
            report_type="forecast",
            geography=geography,
            geo_type=GeoType.CITY,
            parameters={"geography": geography, "months_ahead": months_ahead},
            payload={
                "months_ahead": months_ahead,
                "market_cycle": market_cycle,
                "confidence": round(_clip(0.92 - months_ahead * 0.04, 0.45, 0.92), 2),
                "monthly_forecast": forecast,
            },
        )

    async def generate_heat_index(
        self,
        *,
        geography: str,
        geo_type: str,
    ) -> MarketReportArtifact:
        """Generate a market heat index report."""
        adapter = registry.for_geography(geography)
        metrics = await adapter.fetch_market_metrics(
            geography=geography,
            geo_type=geo_type,
            as_of=date.today(),
        )
        heat_index = self._heat_index_from_metrics(metrics)
        if heat_index >= 75:
            market_label = "hot"
        elif heat_index >= 50:
            market_label = "warm"
        else:
            market_label = "cold"

        trend = "rising" if metrics.mom_price_change >= 0 else "cooling"
        indicators = {
            "price_momentum": round(
                _clip(50 + metrics.yoy_price_change * 200, 0, 100), 2
            ),
            "velocity": round(_clip(100 - metrics.avg_days_on_market, 0, 100), 2),
            "inventory_pressure": round(
                _clip(100 - metrics.months_of_inventory * 12, 0, 100), 2
            ),
            "demand_strength": round(
                _clip(
                    (metrics.sold_last_30d / max(metrics.active_listings, 1)) * 100,
                    0,
                    100,
                ),
                2,
            ),
        }

        return await self._store_generated_report(
            report_type="heat_index",
            geography=geography,
            geo_type=GeoType(geo_type),
            parameters={"geography": geography, "geo_type": geo_type},
            payload={
                "heat_index": round(heat_index, 2),
                "market_label": market_label,
                "trend": trend,
                "indicators": indicators,
            },
        )

    async def generate_seasonal_analysis(
        self,
        *,
        geography: str,
        year: int,
        month: int,
    ) -> MarketReportArtifact:
        """Generate a seasonal market analysis report."""
        rng = self._rng_for_seed(f"seasonal:{geography}:{year}")
        monthly_pattern = [
            {
                "month": current_month,
                "average_price_change": round(
                    (
                        0.8
                        if 3 <= current_month <= 6
                        else -0.4 if current_month in {11, 12} else 0.2
                    )
                    + rng.uniform(-0.6, 0.6),
                    2,
                ),
                "listing_velocity": round(
                    40
                    + (
                        15
                        if 3 <= current_month <= 6
                        else -10 if current_month in {11, 12} else 0
                    )
                    + rng.uniform(-5, 5),
                    2,
                ),
            }
            for current_month in range(1, 13)
        ]
        selected_month = monthly_pattern[month - 1]
        best_action = (
            "sell" if month in {4, 5, 6} else "buy" if month in {10, 11, 12} else "hold"
        )
        return await self._store_generated_report(
            report_type="seasonal",
            geography=geography,
            geo_type=GeoType.CITY,
            parameters={"geography": geography, "year": year, "month": month},
            payload={
                "year": year,
                "month": month,
                "best_action": best_action,
                "seasonal_price_swing_pct": selected_month["average_price_change"],
                "listing_velocity": selected_month["listing_velocity"],
                "monthly_pattern": monthly_pattern,
            },
        )

    async def generate_demographic_correlation(
        self,
        *,
        geography: str,
    ) -> MarketReportArtifact:
        """Generate a demographic correlation report."""
        adapter = registry.for_geography(geography)
        metrics = await adapter.fetch_market_metrics(
            geography=geography,
            geo_type=GeoType.CITY.value,
            as_of=date.today(),
        )
        rng = self._rng_for_seed(f"demographics:{geography}")
        demographics = {
            "population_density": rng.randint(1200, 9500),
            "median_age": round(rng.uniform(31, 44), 1),
            "median_household_income": rng.randint(62000, 155000),
            "annual_population_growth": round(rng.uniform(-0.3, 4.8), 2),
        }
        correlation_summary = [
            {
                "label": "density_vs_prices",
                "correlation": round(_clip(metrics.yoy_price_change * 3, -1, 1), 2),
                "insight": "Denser submarkets are supporting premium pricing.",
            },
            {
                "label": "age_vs_dom",
                "correlation": round(
                    _clip((40 - demographics["median_age"]) / 20, -1, 1), 2
                ),
                "insight": "Younger buyer cohorts correlate with faster listing turnover.",
            },
            {
                "label": "income_vs_listing_prices",
                "correlation": round(
                    _clip(
                        (demographics["median_household_income"] / 100000) - 0.5, -1, 1
                    ),
                    2,
                ),
                "insight": "Household income remains strongly aligned with asking prices.",
            },
        ]
        return await self._store_generated_report(
            report_type="demographics",
            geography=geography,
            geo_type=GeoType.CITY,
            parameters={"geography": geography},
            payload={
                "demographics": demographics,
                "correlation_summary": correlation_summary,
            },
        )

    async def create_schedule(
        self,
        *,
        geography: str,
        frequency: str,
        email: str,
        metrics: list[str],
    ) -> MarketReportSchedule:
        """Persist an automated report schedule."""
        schedule = MarketReportSchedule(
            id=uuid4(),
            geography=geography,
            frequency=frequency,
            email=email,
            metrics=metrics,
            active=True,
            created_at=datetime.now(UTC),
        )
        return await self.repo.create_schedule(schedule)

    async def generate_custom_dashboard(
        self,
        *,
        geography: str,
        selected_metrics: list[str],
        date_range: dict[str, str],
    ) -> MarketReportArtifact:
        """Generate a custom dashboard report for selected metrics."""
        adapter = registry.for_geography(geography)
        metrics = await adapter.fetch_market_metrics(
            geography=geography,
            geo_type=GeoType.CITY.value,
            as_of=date.today(),
        )
        metric_values = {
            "median_price": float(metrics.median_price),
            "mean_price": float(metrics.mean_price),
            "days_on_market": float(metrics.avg_days_on_market),
            "inventory": float(metrics.active_listings),
            "absorption_rate": float(metrics.absorption_rate),
            "list_to_sold_ratio": float(metrics.list_to_sold_ratio),
        }
        payload_metrics = [
            {
                "metric": metric_name,
                "value": round(metric_values.get(metric_name, 0.0), 2),
                "trend": round(
                    {
                        "median_price": metrics.yoy_price_change * 100,
                        "mean_price": metrics.mom_price_change * 100,
                        "days_on_market": -metrics.mom_price_change * 100,
                        "inventory": -metrics.absorption_rate * 100,
                        "absorption_rate": metrics.absorption_rate * 100,
                        "list_to_sold_ratio": (metrics.list_to_sold_ratio - 1) * 100,
                    }.get(metric_name, 0.0),
                    2,
                ),
            }
            for metric_name in selected_metrics
        ]
        return await self._store_generated_report(
            report_type="custom_dashboard",
            geography=geography,
            geo_type=GeoType.CITY,
            parameters={
                "geography": geography,
                "selected_metrics": selected_metrics,
                "date_range": date_range,
            },
            payload={
                "selected_metrics": selected_metrics,
                "date_range": date_range,
                "metrics": payload_metrics,
                "export_formats": ["csv", "excel"],
            },
        )

    async def export_report_pdf(self, report_id: str) -> bytes:
        """Render a stored market report or generated artifact as PDF bytes."""
        artifact = await self.repo.get_generated_report(report_id)
        if artifact is not None:
            title = artifact.report_type.replace("_", " ").title()
            report_lines = self._flatten_for_pdf(
                artifact.parameters, prefix="Parameters"
            )
            report_lines.extend(
                self._flatten_for_pdf(artifact.payload, prefix="Payload")
            )
            return self._build_pdf(title=title, lines=report_lines)

        report = await self.repo.get_by_id(report_id)
        if report is None:
            raise LookupError("Report not found")

        payload = {
            "geography": report.geography,
            "geo_type": report.geo_type.value,
            "report_date": report.report_date.isoformat(),
            "median_price": str(report.median_price),
            "mean_price": str(report.mean_price),
            "active_listings": report.active_listings,
            "sold_last_30d": report.sold_last_30d,
            "avg_days_on_market": float(report.avg_days_on_market),
            "months_of_inventory": float(report.months_of_inventory),
            "absorption_rate": float(report.absorption_rate),
            "yoy_price_change": float(report.yoy_price_change),
            "mom_price_change": float(report.mom_price_change),
            "list_to_sold_ratio": float(report.list_to_sold_ratio),
        }
        return self._build_pdf(
            title="Market Report",
            lines=self._flatten_for_pdf(payload, prefix="Summary"),
        )

    async def _store_generated_report(
        self,
        *,
        report_type: str,
        geography: str | None,
        geo_type: GeoType | None,
        parameters: dict[str, Any],
        payload: dict[str, Any],
    ) -> MarketReportArtifact:
        """Persist a generated report artifact."""
        artifact = MarketReportArtifact(
            id=uuid4(),
            report_type=report_type,
            geography=geography,
            geo_type=geo_type,
            parameters=parameters,
            payload=payload,
            created_at=datetime.now(UTC),
        )
        return await self.repo.create_generated_report(artifact)

    def _rng_for_seed(self, seed: str) -> random.Random:
        """Create a deterministic RNG for repeatable mock payloads."""
        seed_value = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % (2**32)
        return random.Random(seed_value)

    def _fallback_comps(
        self,
        *,
        rng: random.Random,
        radius_miles: float,
        property_type: PropertyType,
        bedrooms: int | None,
    ) -> list[dict[str, Any]]:
        """Build synthetic comparable rows when the adapter yields no exact matches."""
        comps: list[dict[str, Any]] = []
        for index in range(5):
            list_price = Decimal(str(rng.randint(280000, 620000)))
            sold_price = (list_price * Decimal(str(rng.uniform(0.97, 1.03)))).quantize(
                Decimal("0.01")
            )
            comps.append(
                {
                    "address": f"{120 + index} Meridian Ave",
                    "city": "Atlanta",
                    "state": "GA",
                    "property_type": property_type.value,
                    "bedrooms": bedrooms,
                    "bathrooms": round(rng.uniform(1.5, 3.5), 1),
                    "list_price": str(list_price),
                    "sold_price": str(sold_price),
                    "days_on_market": rng.randint(12, 48),
                    "distance_miles": round(rng.uniform(0.2, radius_miles), 2),
                    "sold_date": (
                        date.today() - timedelta(days=index * 12 + 7)
                    ).isoformat(),
                }
            )
        return comps

    def _heat_index_from_metrics(self, metrics: Any) -> float:
        """Compute a 0-100 market heat score from core metrics."""
        price_momentum = _clip(50 + metrics.yoy_price_change * 200, 0, 100)
        velocity = _clip(100 - metrics.avg_days_on_market, 0, 100)
        inventory_pressure = _clip(100 - metrics.months_of_inventory * 12, 0, 100)
        demand = _clip(
            (metrics.sold_last_30d / max(metrics.active_listings, 1)) * 100,
            0,
            100,
        )
        return (price_momentum + velocity + inventory_pressure + demand) / 4

    def _flatten_for_pdf(self, value: Any, *, prefix: str = "") -> list[str]:
        """Flatten nested data into human-readable PDF lines."""
        lines: list[str] = []

        if isinstance(value, dict):
            if prefix:
                lines.append(prefix)
            for key, item in value.items():
                child_prefix = f"  {key}" if prefix else str(key)
                lines.extend(self._flatten_for_pdf(item, prefix=child_prefix))
            return lines

        if isinstance(value, list):
            if prefix:
                lines.append(prefix)
            for item in value:
                if isinstance(item, (dict, list)):
                    lines.extend(self._flatten_for_pdf(item, prefix="  -"))
                else:
                    lines.append(f"  - {item}")
            return lines

        if prefix:
            lines.append(f"{prefix}: {value}")
        else:
            lines.append(str(value))
        return lines

    def _build_pdf(self, *, title: str, lines: list[str]) -> bytes:
        """Create a simple PDF document from flattened lines."""
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setTitle(title)
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(40, 760, title)
        pdf.setFont("Helvetica", 10)
        text = pdf.beginText(40, 735)
        for line in lines:
            if text.getY() < 45:
                pdf.drawText(text)
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                text = pdf.beginText(40, 760)
            text.textLine(line[:MAX_PDF_LINE_LENGTH])
        pdf.drawText(text)
        pdf.save()
        return buffer.getvalue()
