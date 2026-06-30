from __future__ import annotations

from collections.abc import Iterable

from redis.asyncio import Redis

from meridian.cache.helpers import cache_delete_pattern
from meridian.cache.metrics import cache_metrics
from meridian.cache.strategies import CacheNamespace


async def invalidate_pattern(redis_client: Redis, pattern: str) -> int:
    """Invalidate cache keys matching a pattern and track eviction metrics."""
    deleted = await cache_delete_pattern(redis_client, pattern)
    cache_metrics.record_evictions(deleted)
    return deleted


async def invalidate_namespaces(redis_client: Redis, namespaces: Iterable[str]) -> int:
    """Invalidate all keys under one or more cache namespaces."""
    deleted = 0
    for namespace in namespaces:
        deleted += await invalidate_pattern(redis_client, f"{namespace}*")
    return deleted


async def invalidate_market_reports_cache(redis_client: Redis) -> int:
    """Invalidate all market report cache entries."""
    return await invalidate_namespaces(redis_client, [CacheNamespace.MARKET_REPORTS])


async def invalidate_signals_cache(redis_client: Redis) -> int:
    """Invalidate all signal cache entries."""
    return await invalidate_namespaces(redis_client, [CacheNamespace.SIGNALS])


async def invalidate_comps_cache(redis_client: Redis) -> int:
    """Invalidate all comps cache entries."""
    return await invalidate_namespaces(redis_client, [CacheNamespace.COMPS])
