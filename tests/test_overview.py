"""Tests for the dashboard overview endpoint building blocks."""

from __future__ import annotations

from datetime import datetime, timezone

from meridian.api.routers.overview import _build_listing_counts
from meridian.api.schemas.overview import (
    ListingCounts,
    OverviewResponse,
    SignalCounts,
)
from meridian.cache.strategies import CacheStrategy, resolve_ttl


class TestBuildListingCounts:
    def test_maps_statuses_and_totals(self) -> None:
        counts = _build_listing_counts(
            {"ACTIVE": 5, "SOLD": 3, "PENDING": 2, "EXPIRED": 1, "WITHDRAWN": 4}
        )
        assert counts.total == 15
        assert counts.active == 5
        assert counts.sold == 3
        assert counts.pending == 2
        assert counts.expired == 1
        assert counts.withdrawn == 4
        assert counts.by_status["ACTIVE"] == 5

    def test_missing_statuses_default_to_zero(self) -> None:
        counts = _build_listing_counts({"ACTIVE": 2})
        assert counts.total == 2
        assert counts.active == 2
        assert counts.sold == 0
        assert counts.pending == 0

    def test_empty_counts(self) -> None:
        counts = _build_listing_counts({})
        assert counts.total == 0
        assert counts.by_status == {}


class TestOverviewResponse:
    def test_json_roundtrip(self) -> None:
        response = OverviewResponse(
            geography="Austin",
            geo_type="CITY",
            generated_at=datetime.now(timezone.utc),
            listings=ListingCounts(total=10, active=6, sold=4),
            signals=SignalCounts(total_evaluations=20, fired=5, definitions=2),
        )
        data = response.model_dump(mode="json")
        assert data["geography"] == "Austin"
        assert data["geo_type"] == "CITY"
        assert data["listings"]["total"] == 10
        assert data["signals"]["fired"] == 5
        assert data["latest_market_report"] is None
        assert data["recent_signals"] == []

        # Ensure the serialized payload validates back into the model (cache path).
        restored = OverviewResponse.model_validate(data)
        assert restored.listings.active == 6


class TestOverviewCacheStrategy:
    def test_overview_ttl_resolves(self) -> None:
        ttl = resolve_ttl(CacheStrategy.OVERVIEW)
        assert isinstance(ttl, int)
        assert ttl > 0
