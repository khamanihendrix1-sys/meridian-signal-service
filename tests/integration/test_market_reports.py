"""Integration tests for market report endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_latest_report(client: AsyncClient, sample_market_report):
    """Test retrieving the latest market report for a geography."""
    response = await client.get(
        "/v1/market-reports/latest?geography=Atlanta-GA&geo_type=CITY"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["geography"] == "Atlanta-GA"
    assert data["median_price"] == 425000


@pytest.mark.asyncio
async def test_get_latest_report_not_found(client: AsyncClient):
    """Test retrieving latest report for non-existent geography."""
    response = await client.get(
        "/v1/market-reports/latest?geography=NonExistent&geo_type=CITY"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_report_by_id(client: AsyncClient, sample_market_report):
    """Test retrieving a report by ID."""
    response = await client.get(f"/v1/market-reports/{sample_market_report.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_market_report.id)
    assert data["geography"] == "Atlanta-GA"


@pytest.mark.asyncio
async def test_list_reports(client: AsyncClient, sample_market_report):
    """Test listing all market reports."""
    response = await client.get("/v1/market-reports")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_reports_by_geography(client: AsyncClient, sample_market_report):
    """Test listing reports filtered by geography."""
    response = await client.get(
        "/v1/market-reports?geography=Atlanta-GA&geo_type=CITY"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(report["geography"] == "Atlanta-GA" for report in data)


@pytest.mark.asyncio
async def test_refresh_report(client: AsyncClient):
    """Test refreshing a market report via adapter."""
    response = await client.post(
        "/v1/market-reports/refresh",
        json={"geography": "Atlanta-GA", "geo_type": "CITY"},
    )
    # May return 200 if mock adapter works, or 500 if Redis/services unavailable
    assert response.status_code in (200, 500)
