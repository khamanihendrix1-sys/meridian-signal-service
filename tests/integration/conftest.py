"""Fixtures for API integration tests."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from meridian.db.base import Base
from meridian.db.session import get_session
from meridian.main import create_app
from meridian.settings import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create a new event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_engine():
    """Create an in-memory test database."""
    # Use SQLite for testing with async support
    test_database_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_factory = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with overridden dependencies."""
    app = create_app()

    # Override the session dependency
    async def override_get_session():
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def sample_listing(test_session: AsyncSession):
    """Create a sample listing for testing."""
    from meridian.db.models import Listing
    from uuid import uuid4

    listing = Listing(
        id=uuid4(),
        mls_id="MLS123456",
        address="123 Main St",
        city="Atlanta",
        state="GA",
        zip_code="30301",
        beds=3,
        baths=2.0,
        living_sqft=2000,
        lot_sqft=7500,
        list_price=450000,
        list_date="2026-05-01",
        status="ACTIVE",
        geom=None,  # Will need to set if testing geo queries
    )
    test_session.add(listing)
    await test_session.commit()
    await test_session.refresh(listing)
    return listing


@pytest.fixture
async def sample_market_report(test_session: AsyncSession):
    """Create a sample market report for testing."""
    from meridian.db.models import MarketReport
    from meridian.db.models.enums import GeoType
    from uuid import uuid4
    from datetime import date, datetime

    report = MarketReport(
        id=uuid4(),
        geography="Atlanta-GA",
        geo_type=GeoType.CITY,
        report_date=date.today(),
        median_price=425000,
        mean_price=450000,
        active_listings=1250,
        sold_last_30d=180,
        avg_days_on_market=45,
        months_of_inventory=6.5,
        absorption_rate=0.72,
        yoy_price_change=3.2,
        mom_price_change=1.1,
        list_to_sold_ratio=0.95,
        raw_metrics={},
        created_at=datetime.utcnow(),
    )
    test_session.add(report)
    await test_session.commit()
    await test_session.refresh(report)
    return report
