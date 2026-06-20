from __future__ import annotations

from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from meridian.hooks import DB_SESSION_CLOSED, DB_SESSION_OPENED, trigger_hook
from meridian.settings import settings


def create_engine() -> AsyncEngine:
    """Create the SQLAlchemy async engine for the application."""
    return create_async_engine(
        settings.database_url,
        echo=False,
    )


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return cached SQLAlchemy async engine."""
    return create_engine()


@lru_cache(maxsize=1)
def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return cached async session factory."""
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async_session_factory = get_async_session_factory()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async generator that yields a DB session and emits lifecycle hooks."""
    async with get_async_session_factory()() as session:
        await trigger_hook(DB_SESSION_OPENED, session=session)
        try:
            yield session
        finally:
            await trigger_hook(DB_SESSION_CLOSED, session=session)
