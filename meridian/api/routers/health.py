from __future__ import annotations

from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter()


@router.get("/healthz", summary="Health check")
async def healthz() -> JSONResponse:
    """Return a minimal health response for readiness probes."""
    return JSONResponse({"status": "ok"})


@router.get("/readyz", summary="Readiness check")
async def readyz() -> JSONResponse:
    """Return a readiness response for startup validation."""
    return JSONResponse({"status": "ready"})
