from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends

from meridian.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields a database session."""
    async for session in get_session():
        yield session
