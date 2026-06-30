from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis

from meridian.cache.metrics import cache_metrics

logger = logging.getLogger(__name__)


class BaseCacheClient:
    """Redis-backed cache client used by API caching utilities."""

    def __init__(
        self, redis_client: Redis, *, prefix: str, enabled: bool = True
    ) -> None:
        self.redis = redis_client
        self.prefix = prefix
        self.enabled = enabled

    def namespaced_key(self, key: str) -> str:
        """Build fully namespaced key used in Redis."""
        return f"{self.prefix}:{key}"

    async def get_json(self, key: str) -> Any | None:
        """Get a JSON value from Redis cache."""
        if not self.enabled:
            return None

        try:
            raw = await self.redis.get(self.namespaced_key(key))
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            cache_metrics.record_error()
            logger.exception("Failed to decode JSON from cache", extra={"key": key})
            return None
        except Exception:
            cache_metrics.record_error()
            logger.exception("Failed to retrieve value from Redis", extra={"key": key})
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> bool:
        """Set a JSON value in Redis cache with TTL."""
        if not self.enabled:
            return False

        try:
            payload = json.dumps(value, separators=(",", ":"), default=str)
            await self.redis.set(self.namespaced_key(key), payload, ex=ttl_seconds)
            return True
        except Exception:
            cache_metrics.record_error()
            logger.exception("Failed to write cached payload", extra={"key": key})
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching a namespaced pattern and return deleted count."""
        if not self.enabled:
            return 0

        namespaced_pattern = self.namespaced_key(pattern)
        deleted = 0
        try:
            async for key in self.redis.scan_iter(match=namespaced_pattern):
                deleted += await self.redis.delete(key)
            return deleted
        except Exception:
            cache_metrics.record_error()
            logger.exception(
                "Failed to delete cache keys",
                extra={"pattern": namespaced_pattern},
            )
            return deleted
