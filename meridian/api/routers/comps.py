from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.auth import get_current_token, get_idempotency_key
from meridian.api.deps import get_db, get_redis
from meridian.api.exceptions import NotFoundError
from meridian.api.models.errors import ErrorCode, ErrorResponse
from meridian.api.schemas import CompJobResponse, CompRequest, CompResponse
from meridian.cache.helpers import cache_control_header, cache_get, cache_set
from meridian.cache.invalidation import invalidate_comps_cache
from meridian.cache.keys import make_cache_key
from meridian.cache.strategies import CacheNamespace, CacheStrategy, resolve_ttl
from meridian.db.models.enums import CompJobStatus
from meridian.db.repositories import CompRepository
from meridian.integrations.tasks import compute_comps_task

router = APIRouter(prefix="/v1/comps", tags=["comps"])

_error_responses: dict[int | str, dict[str, Any]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token",
    },
    404: {"model": ErrorResponse, "description": "Comp job not found"},
    409: {
        "model": ErrorResponse,
        "description": "Idempotency key conflict or duplicate job",
    },
    422: {"model": ErrorResponse, "description": "Request validation error"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
}


@router.post(
    "",
    response_model=CompJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create comp job",
    description=(
        "Submit a comparable-property analysis job for the given listing. "
        "The job is queued for asynchronous processing and this endpoint returns "
        "``202 Accepted`` immediately. Poll ``GET /v1/comps/{job_id}`` to check "
        "progress.\n\n"
        "Supply an ``Idempotency-Key`` header to safely retry this request without "
        "creating duplicate jobs."
    ),
    responses={
        202: {"description": "Comp job accepted and enqueued"},
        **_error_responses,
    },
)
async def create_comp_job(
    request: CompRequest,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> CompJobResponse:
    """Create a comp job and enqueue async computation."""
    repo = CompRepository(db)

    # Idempotency: when the same key is replayed, return the existing job with
    # 200 OK rather than 202 Accepted so that the caller can distinguish a
    # fresh submission from a replayed one.
    if idempotency_key:
        idempotency_cache_key = make_cache_key(
            CacheNamespace.COMPS,
            "idempotency",
            key=idempotency_key,
        )
        cached_job_id = await cache_get(redis_client, idempotency_cache_key)
        if isinstance(cached_job_id, str):
            existing_job = await repo.get_job_by_id(UUID(cached_job_id))
            if existing_job:
                http_response.status_code = status.HTTP_200_OK
                return CompJobResponse.from_orm(existing_job)

    job = await repo.create_job(request.subject_listing_id)
    compute_comps_task.delay(
        str(job.id), str(request.subject_listing_id), request.limit
    )

    if idempotency_key:
        idempotency_cache_key = make_cache_key(
            CacheNamespace.COMPS,
            "idempotency",
            key=idempotency_key,
        )
        await cache_set(redis_client, idempotency_cache_key, str(job.id), 86400)

    await invalidate_comps_cache(redis_client)
    return CompJobResponse.from_orm(job)


@router.get(
    "/{job_id}",
    response_model=CompJobResponse,
    summary="Get comp job status",
    description=(
        "Poll the status and results of a comparable-property analysis job. "
        "When the job ``status`` is ``SUCCESS`` the ``comps`` list is populated "
        "with the ranked comparable properties."
    ),
    responses={
        200: {"description": "Comp job status and results"},
        **_error_responses,
    },
)
async def get_comp_job(
    job_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _token: dict[str, Any] = Depends(get_current_token),
) -> CompJobResponse:
    """Get comp job status and results."""
    ttl = resolve_ttl(CacheStrategy.COMP_JOB)
    cache_key = make_cache_key(CacheNamespace.COMPS, "job", job_id=job_id)
    cached = await cache_get(redis_client, cache_key)
    if isinstance(cached, dict):
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = cache_control_header(ttl)
        return CompJobResponse.model_validate(cached)

    repo = CompRepository(db)
    job = await repo.get_job_by_id(job_id)
    if not job:
        raise NotFoundError(
            "Comp job not found", error_code=ErrorCode.COMP_JOB_NOT_FOUND
        )

    comp_job_response = CompJobResponse.from_orm(job)
    if job.status == CompJobStatus.SUCCESS:
        comps = await repo.get_comps_for_job(job.id)
        comp_job_response.comps = [CompResponse.from_orm(comp) for comp in comps]
    await cache_set(
        redis_client,
        cache_key,
        comp_job_response.model_dump(mode="json"),
        ttl,
    )
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return comp_job_response
