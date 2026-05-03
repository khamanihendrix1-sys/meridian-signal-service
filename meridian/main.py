from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from meridian.api.routers.health import router as health_router
from meridian.hooks import APP_SHUTDOWN, APP_STARTUP, trigger_hook
from meridian.api.routers.listings import router as listings_router
from meridian.api.routers.market_reports import router as market_reports_router
from meridian.api.routers.signals import router as signals_router
from meridian.api.routers.comps import router as comps_router
from meridian.settings import Settings
from meridian.observability.logging import configure_structlog

settings = Settings()
configure_structlog(settings)
logger = logging.getLogger(__name__)

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    ),
]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Meridian Signal Service",
        version="0.1.0",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url=None,
    )

    app.include_router(health_router, prefix="", tags=["health"])
    app.include_router(listings_router)
    app.include_router(market_reports_router)
    app.include_router(signals_router)
    app.include_router(comps_router)

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("Application startup event")
        await trigger_hook(APP_STARTUP)

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("Application shutdown event")
        await trigger_hook(APP_SHUTDOWN)

    @app.exception_handler(Exception)
    async def internal_exception_handler(request, exc):
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

    uvicorn.run(
        "meridian.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
    )
