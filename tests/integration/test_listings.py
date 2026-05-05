"""Integration tests for listings endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_listing(client: AsyncClient, sample_listing):
    """Test retrieving a listing by ID."""
    response = await client.get(f"/v1/listings/{sample_listing.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_listing.id)
    assert data["address"] == "123 Main St"
    assert data["beds"] == 3


@pytest.mark.asyncio
async def test_get_listing_not_found(client: AsyncClient):
    """Test retrieving a non-existent listing."""
    response = await client.get("/v1/listings/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_listings(client: AsyncClient, sample_listing):
    """Test listing all listings."""
    response = await client.get("/v1/listings")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(listing["id"] == str(sample_listing.id) for listing in data)


@pytest.mark.asyncio
async def test_list_listings_with_filters(client: AsyncClient, sample_listing):
    """Test listing with city filter."""
    response = await client.get("/v1/listings?city=Atlanta")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(listing["city"] == "Atlanta" for listing in data)


@pytest.mark.asyncio
async def test_list_listings_with_price_filter(client: AsyncClient, sample_listing):
    """Test listing with price range filter."""
    response = await client.get("/v1/listings?min_price=400000&max_price=500000")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(
        400000 <= listing["list_price"] <= 500000
        for listing in data
        if listing.get("list_price")
    )
