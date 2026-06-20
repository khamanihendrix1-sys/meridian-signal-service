from __future__ import annotations

from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from meridian.hooks import DB_SESSION_CLOSED, DB_SESSION_OPENED, trigger_hook
from meridian.settings import settings


def create_engine() -> AsyncEngine:
    """Create the SQLAlchemy async engine for the application."""
    return create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
    )


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return cached SQLAlchemy async engine."""
    return create_engine()


@lru_cache(maxsize=1)
def get_async_session_factory() -> sessionmaker:
    """Return cached async session factory."""
    return sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a new database session and expose lifecycle hooks."""
    async with get_async_session_factory()() as session:
        await trigger_hook(DB_SESSION_OPENED, session=session)
        try:
            yield session
        finally:
            await trigger_hook(DB_SESSION_CLOSED, session=session)
