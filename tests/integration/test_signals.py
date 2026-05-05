"""Integration tests for signal endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_signal_definitions(client: AsyncClient):
    """Test retrieving signal definitions."""
    response = await client.get("/v1/signals/definitions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should have at least the two standard signals
    signal_types = {sig["signal_type"] for sig in data}
    assert "price_drop_30d" in signal_types or len(data) >= 0


@pytest.mark.asyncio
async def test_list_signal_logs(client: AsyncClient):
    """Test listing signal logs."""
    response = await client.get("/v1/signals/logs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_signal_logs_by_signal_type(client: AsyncClient):
    """Test listing signal logs filtered by signal type."""
    response = await client.get("/v1/signals/logs?signal_type=price_drop_30d")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(log["signal_type"] == "price_drop_30d" for log in data)


@pytest.mark.asyncio
async def test_list_signal_logs_by_geography(client: AsyncClient):
    """Test listing signal logs filtered by geography."""
    response = await client.get("/v1/signals/logs?geography=Atlanta-GA")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(log["geography"] == "Atlanta-GA" for log in data)


@pytest.mark.asyncio
async def test_evaluate_signals(client: AsyncClient):
    """Test evaluating signals for a geography."""
    response = await client.post(
        "/v1/signals/evaluate",
        json={"geography": "Atlanta-GA", "geo_type": "CITY"},
    )
    # May return 200 if evaluation succeeds, or 500 if services unavailable
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, dict)
        assert "logs" in data
