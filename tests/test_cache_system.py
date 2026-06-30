from __future__ import annotations

from collections.abc import AsyncIterator
from fnmatch import fnmatch
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from meridian.api.deps import get_redis
from meridian.api.middleware.cache import (
    CacheMetricsMiddleware,
    RateLimitAwarenessMiddleware,
)
from meridian.api.routers.cache_metrics import router as cache_metrics_router
from meridian.cache.helpers import cache_get, cache_set
from meridian.cache.invalidation import invalidate_pattern
from meridian.cache.keys import make_cache_key
from meridian.cache.metrics import cache_metrics


class FakeRedis:
    """Minimal async Redis stub for cache tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.delete_calls = 0

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        """Store value for tests; TTL argument is accepted for API compatibility."""
        self.store[key] = value

    async def delete(self, *keys: str) -> int:
        self.delete_calls += 1
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                deleted += 1
        return deleted

    async def info(self, section: str) -> dict[str, int]:
        assert section == "stats"
        return {"keyspace_hits": 1, "keyspace_misses": 2, "evicted_keys": 0}

    async def scan_iter(self, match: str) -> AsyncIterator[str]:
        for key in list(self.store.keys()):
            if fnmatch(key, match):
                yield key


@pytest.mark.asyncio
async def test_cache_helpers_and_invalidation_work_with_pattern() -> None:
    cache_metrics.hits = 0
    cache_metrics.misses = 0
    cache_metrics.evictions = 0

    redis_client = FakeRedis()

    key_a = make_cache_key(
        "market_reports", "latest", geography="Austin", geo_type="CITY"
    )
    key_b = make_cache_key(
        "market_reports", "latest", geography="Seattle", geo_type="CITY"
    )

    await cache_set(redis_client, key_a, {"value": 1}, ttl_seconds=30)
    await cache_set(redis_client, key_b, {"value": 2}, ttl_seconds=30)

    assert await cache_get(redis_client, key_a) == {"value": 1}

    deleted = await invalidate_pattern(redis_client, "market_reports*")
    assert deleted == 2
    assert cache_metrics.evictions >= 2


@pytest.mark.asyncio
async def test_invalidate_pattern_uses_batched_deletes() -> None:
    redis_client = FakeRedis()
    for index in range(205):
        key = make_cache_key("market_reports", "latest", geography=f"City-{index}")
        await cache_set(redis_client, key, {"value": index}, ttl_seconds=30)

    deleted = await invalidate_pattern(redis_client, "market_reports*")
    assert deleted == 205
    assert redis_client.delete_calls == 3


@pytest.mark.asyncio
async def test_make_cache_key_is_stable_for_same_logical_input() -> None:
    first = make_cache_key("signals", "logs", signal_id="abc", limit=20, geography="TX")
    second = make_cache_key(
        "signals",
        "logs",
        geography="TX",
        limit=20,
        signal_id="abc",
    )
    assert first == second


def test_cache_middleware_and_metrics_endpoint() -> None:
    fake_redis = FakeRedis()
    app = FastAPI()
    app.add_middleware(CacheMetricsMiddleware)
    app.add_middleware(RateLimitAwarenessMiddleware)

    @app.get("/cached")
    async def cached_endpoint() -> JSONResponse:
        return JSONResponse({"ok": True}, headers={"X-Cache": "HIT"})

    app.include_router(cache_metrics_router)
    app.dependency_overrides[get_redis] = lambda: fake_redis

    client = TestClient(app)

    cached_response = client.get("/cached")
    assert cached_response.status_code == 200
    assert cached_response.headers["X-Cache"] == "HIT"
    assert "ETag" in cached_response.headers
    assert "max-age" in cached_response.headers["Cache-Control"]

    metrics_response = client.get("/v1/metrics/cache")
    assert metrics_response.status_code == 200
    body: dict[str, Any] = metrics_response.json()
    assert "cache" in body
    assert "rate_limits" in body
    assert body["redis"]["hits"] == 1
