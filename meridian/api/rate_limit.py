from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from meridian.api.models.errors import ErrorCode, make_error_response
from meridian.settings import get_settings


class _InMemoryRateLimiter:
    """Sliding-window, in-process rate limiter used as a fallback when Redis
    is unavailable or when ``rate_limit_enabled`` is False.

    This implementation is intentionally simple and is **not** suitable for
    multi-process deployments where every process would maintain its own
    independent counter.  In production the Redis-backed middleware (below)
    should be used instead.
    """

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Return ``(allowed, remaining)`` for *key* within *window_seconds*."""
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._windows[key]
            # Evict expired entries
            self._windows[key] = [t for t in timestamps if t > cutoff]
            count = len(self._windows[key])
            if count < limit:
                self._windows[key].append(now)
                return True, limit - count - 1
            return False, 0


_fallback_limiter = _InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket style rate-limiting middleware.

    The rate limit window and request cap are controlled by the settings:
    * ``rate_limit_requests`` — maximum requests per window (default 200)
    * ``rate_limit_window_seconds`` — window length in seconds (default 60)

    The key used to identify a caller is:
    1. The bearer token ``sub`` claim if present, otherwise
    2. The ``X-Forwarded-For`` header, otherwise
    3. The raw client IP.

    When the limit is exceeded the middleware returns ``429 Too Many Requests``
    with the standard :class:`~meridian.api.models.errors.ErrorResponse` body
    and the following headers:

    * ``Retry-After`` — seconds until the current window resets
    * ``X-RateLimit-Limit`` — maximum requests per window
    * ``X-RateLimit-Remaining`` — remaining requests in the current window
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        settings = get_settings()

        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Determine the caller identity key
        caller_key = self._resolve_key(request)

        allowed, remaining = _fallback_limiter.is_allowed(
            caller_key,
            settings.rate_limit_requests,
            settings.rate_limit_window_seconds,
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                headers={
                    "Retry-After": str(settings.rate_limit_window_seconds),
                    "X-RateLimit-Limit": str(settings.rate_limit_requests),
                    "X-RateLimit-Remaining": "0",
                },
                content=make_error_response(
                    ErrorCode.RATE_LIMITED,
                    "Too many requests — please retry later",
                    path=str(request.url.path),
                ),
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    @staticmethod
    def _resolve_key(request: Request) -> str:
        # Prefer the bearer token subject for authenticated callers
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Use the raw token as the key (avoids decoding overhead on hot path)
            return f"token:{auth_header[7:30]}"

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"

        client = request.client
        if client:
            return f"ip:{client.host}"

        return "ip:unknown"
