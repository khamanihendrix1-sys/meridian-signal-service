from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from starlette.middleware import Middleware
from starlette.responses import JSONResponse

from meridian.observability.logging import configure_structlog
from meridian.settings import get_settings

logger = logging.getLogger(__name__)

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    ),
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_structlog(settings)
    app.state.redis = Redis.from_url(settings.redis_url)
    logger.info("Application startup event")
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
    from meridian.api.routers.market_reports import router as market_reports_router
    from meridian.api.routers.signals import router as signals_router

    app = FastAPI(
        title="Meridian Signal Service",
        version="0.1.0",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url=None,
        middleware=middleware,
        lifespan=lifespan,
    )
    app.include_router(health_router, prefix="", tags=["health"])
    app.include_router(listings_router)
    app.include_router(market_reports_router)
    app.include_router(signals_router)
    app.include_router(comps_router)

    @app.exception_handler(Exception)
    async def internal_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

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
