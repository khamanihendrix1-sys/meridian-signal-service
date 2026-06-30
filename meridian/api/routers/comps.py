from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.deps import get_db, get_redis
from meridian.api.schemas import CompJobResponse, CompRequest, CompResponse
from meridian.cache.helpers import cache_control_header, cache_get, cache_set
from meridian.cache.invalidation import invalidate_comps_cache
from meridian.cache.keys import make_cache_key
from meridian.cache.strategies import CacheNamespace, CacheStrategy, resolve_ttl
from meridian.db.models.enums import CompJobStatus
from meridian.db.repositories import CompRepository
from meridian.integrations.tasks import compute_comps_task

router = APIRouter(prefix="/v1/comps", tags=["comps"])


@router.post("", response_model=CompJobResponse)
async def create_comp_job(
    request: CompRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> CompJobResponse:
    """Create a comp job and enqueue async computation."""
    repo = CompRepository(db)
    job = await repo.create_job(request.subject_listing_id)
    compute_comps_task.delay(
        str(job.id), str(request.subject_listing_id), request.limit
    )
    await invalidate_comps_cache(redis_client)
    return CompJobResponse.from_orm(job)


@router.get("/{job_id}", response_model=CompJobResponse)
async def get_comp_job(
    job_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
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
        raise HTTPException(status_code=404, detail="Comp job not found")

    payload = CompJobResponse.from_orm(job)
    if job.status == CompJobStatus.SUCCESS:
        comps = await repo.get_comps_for_job(job.id)
        payload.comps = [CompResponse.from_orm(comp) for comp in comps]
    await cache_set(redis_client, cache_key, payload.model_dump(mode="json"), ttl)
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = cache_control_header(ttl)
    return payload
