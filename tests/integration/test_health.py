"""Integration tests for health endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_ready_check(client: AsyncClient):
    """Test the readiness check endpoint."""
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert "checks" in data
