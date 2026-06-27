from __future__ import annotations

from typing import AsyncGenerator, cast

from fastapi import Request
from redis.asyncio import Redis
from meridian.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields a database session."""
    async for session in get_session():
        yield session


async def get_redis(request: Request) -> Redis:
    """Dependency that yields the application Redis client."""
    return cast(Redis, request.app.state.redis)
