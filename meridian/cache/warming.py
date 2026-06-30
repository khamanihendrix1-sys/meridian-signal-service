from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from redis.asyncio import Redis

from meridian.api.schemas import SignalDefinitionResponse
from meridian.cache.helpers import cache_set
from meridian.cache.keys import make_cache_key
from meridian.cache.strategies import CacheNamespace, CacheStrategy, resolve_ttl
from meridian.db.models import SignalDefinition
from meridian.settings import get_settings


async def warm_critical_cache(
    redis_client: Redis,
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Warm critical cache keys at startup when enabled in settings."""
    settings = get_settings()
    if not settings.cache_enabled or not settings.cache_warm_on_startup:
        return 0

    async with session_factory() as session:
        result = await session.execute(select(SignalDefinition))
        definitions = result.scalars().all()

    key = make_cache_key(CacheNamespace.SIGNALS, "definitions")
    payload = [
        SignalDefinitionResponse.model_validate(item).model_dump(mode="json")
        for item in definitions
    ]
    await cache_set(
        redis_client,
        key,
        payload,
        resolve_ttl(CacheStrategy.SIGNAL_DEFINITIONS),
    )
    return 1
