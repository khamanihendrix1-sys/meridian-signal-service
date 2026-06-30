from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from meridian.api.deps import get_redis
from meridian.cache.metrics import cache_metrics
from meridian.cache.rate_limit import rate_limit_monitor

router = APIRouter(prefix="/v1/metrics", tags=["metrics"])


@router.get("/cache")
async def get_cache_metrics(redis_client: Redis = Depends(get_redis)) -> Mapping[str, Any]:
    """Return cache and rate-limit metrics for operational monitoring."""
    redis_stats: Mapping[str, Any]
    try:
        redis_stats = await redis_client.info("stats")
    except Exception:
        redis_stats = {}

    return {
        "cache": cache_metrics.snapshot(),
        "rate_limits": rate_limit_monitor.snapshot(),
        "redis": {
            "hits": redis_stats.get("keyspace_hits", 0),
            "misses": redis_stats.get("keyspace_misses", 0),
            "evicted_keys": redis_stats.get("evicted_keys", 0),
        },
    }
