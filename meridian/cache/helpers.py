from __future__ import annotations

from typing import Any

from redis.asyncio import Redis

from meridian.cache.client import BaseCacheClient
from meridian.settings import get_settings


def _client(redis_client: Redis) -> BaseCacheClient:
    settings = get_settings()
    return BaseCacheClient(
        redis_client,
        prefix=settings.cache_prefix,
        enabled=settings.cache_enabled,
    )


async def cache_get(redis_client: Redis, key: str) -> Any | None:
    """Fetch a value from cache by key."""
    return await _client(redis_client).get_json(key)


async def cache_set(
    redis_client: Redis,
    key: str,
    value: Any,
    ttl_seconds: int,
) -> bool:
    """Store a value in cache with TTL."""
    return await _client(redis_client).set_json(key, value, ttl_seconds)


async def cache_delete_pattern(redis_client: Redis, pattern: str) -> int:
    """Delete cached values by pattern and return number of deleted keys."""
    return await _client(redis_client).delete_pattern(pattern)


def cache_control_header(ttl_seconds: int) -> str:
    """Build a standard Cache-Control header value for public responses."""
    return f"public, max-age={ttl_seconds}"
