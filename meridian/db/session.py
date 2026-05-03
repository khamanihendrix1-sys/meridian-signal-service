from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncEngine, AsyncSession, create_async_engine
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


engine = create_engine()
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """Yield a new database session and expose lifecycle hooks."""
    async with async_session_factory() as session:
        await trigger_hook(DB_SESSION_OPENED, session=session)
        try:
            yield session
        finally:
            await trigger_hook(DB_SESSION_CLOSED, session=session)
