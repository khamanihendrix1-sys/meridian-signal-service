from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from starlette.middleware import Middleware

from meridian.api.exceptions import (
    MeridianAPIError,
    http_exception_handler,
    meridian_api_error_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from meridian.api.middleware.cache import (
    CacheMetricsMiddleware,
    RateLimitAwarenessMiddleware,
)
from meridian.api.middleware.security import SecurityHeadersMiddleware
from meridian.api.rate_limit import RateLimitMiddleware
from meridian.cache.warming import warm_critical_cache
from meridian.db.session import get_async_session_factory
from meridian.observability.logging import configure_structlog
from meridian.settings import Settings, get_settings

logger = logging.getLogger(__name__)


def _build_middleware(settings: Settings) -> list[Any]:
    """Build the ordered middleware stack from current settings."""
    cors_allow_origins = settings.cors_origins_list
    cors_allow_credentials = settings.cors_allow_credentials

    cors_middleware: Any = Middleware(
        CORSMiddleware,
        allow_origins=cors_allow_origins,
        allow_credentials=cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "Idempotency-Key",
            "X-Request-ID",
        ],
        expose_headers=[
            "X-Cache",
            "X-Next-Cursor",
            "Cache-Control",
            "ETag",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "Retry-After",
        ],
    )

    return [
        Middleware(SecurityHeadersMiddleware),
        Middleware(RateLimitMiddleware),
        Middleware(CacheMetricsMiddleware),
        Middleware(RateLimitAwarenessMiddleware),
        cors_middleware,
    ]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_structlog(settings)
    app.state.redis = Redis.from_url(settings.redis_url)
    logger.info("Application startup event")
    warmed_keys = await warm_critical_cache(
        app.state.redis,
        get_async_session_factory(),
    )
    logger.info("Cache warmup completed", extra={"warmed_keys": warmed_keys})
    try:
        yield
    finally:
        await app.state.redis.close()
        logger.info("Application shutdown event")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    from meridian.api.routers.comps import router as comps_router
    from meridian.api.routers.health import router as health_router
    from meridian.api.routers.listings import router as listings_router
    from meridian.api.routers.cache_metrics import router as cache_metrics_router
    from meridian.api.routers.market_reports import router as market_reports_router
    from meridian.api.routers.signals import router as signals_router

    settings = get_settings()
    middleware = _build_middleware(settings)

    app = FastAPI(
        title="Meridian Signal Service",
        version="0.1.0",
        description=(
            "Backend API for Meridian Signals® and Meridian Data®. "
            "Provides listings, market reports, signals, and comparable-property analysis."
        ),
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url=None,
        middleware=middleware,
        lifespan=lifespan,
    )
    app.include_router(health_router, prefix="", tags=["health"])
    app.include_router(cache_metrics_router)
    app.include_router(listings_router)
    app.include_router(market_reports_router)
    app.include_router(signals_router)
    app.include_router(comps_router)

    # Register exception handlers — most specific first
    app.add_exception_handler(MeridianAPIError, meridian_api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    return app


app = create_app()


def run() -> None:
    """Run the API using Uvicorn."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "meridian.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
    )
