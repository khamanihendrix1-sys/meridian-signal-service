from __future__ import annotations

import hashlib
from time import perf_counter

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from meridian.cache.metrics import cache_metrics
from meridian.cache.rate_limit import rate_limit_monitor
from meridian.settings import get_settings


class CacheMetricsMiddleware(BaseHTTPMiddleware):
    """Track cache behavior and inject cache visibility headers."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start = perf_counter()
        response = await call_next(request)
        elapsed_ms = (perf_counter() - start) * 1000

        cache_metrics.record_request_time(elapsed_ms)

        cache_status = response.headers.get("X-Cache") or "BYPASS"
        response.headers["X-Cache"] = cache_status

        if cache_status == "HIT":
            cache_metrics.record_hit()
        elif cache_status == "MISS":
            cache_metrics.record_miss()

        if request.method == "GET":
            settings = get_settings()
            response.headers.setdefault(
                "Cache-Control",
                f"public, max-age={settings.cache_default_ttl}",
            )
            self._set_etag(response)

        return response

    @staticmethod
    def _set_etag(response: Response) -> None:
        if "ETag" in response.headers:
            return
        body = getattr(response, "body", b"")
        if not isinstance(body, (bytes, bytearray)):
            return
        digest = hashlib.sha256(body).hexdigest()[:16]
        response.headers["ETag"] = f'W/"{digest}"'


class RateLimitAwarenessMiddleware(BaseHTTPMiddleware):
    """Capture upstream rate-limit headers for observability endpoints."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        rate_limit_monitor.update_from_headers(
            response.headers,
            source=str(request.url.path),
        )
        return response
