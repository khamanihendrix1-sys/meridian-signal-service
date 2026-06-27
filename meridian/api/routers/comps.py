from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.api.deps import get_db
from meridian.api.schemas import CompJobResponse, CompRequest, CompResponse
from meridian.db.models.enums import CompJobStatus
from meridian.db.repositories import CompRepository
from meridian.integrations.tasks import compute_comps_task

router = APIRouter(prefix="/v1/comps", tags=["comps"])


@router.post("", response_model=CompJobResponse)
async def create_comp_job(
    request: CompRequest,
    db: AsyncSession = Depends(get_db),
) -> CompJobResponse:
    """Create a comp job and enqueue async computation."""
    repo = CompRepository(db)
    job = await repo.create_job(request.subject_listing_id)
    compute_comps_task.delay(
        str(job.id), str(request.subject_listing_id), request.limit
    )
    return CompJobResponse.from_orm(job)


@router.get("/{job_id}", response_model=CompJobResponse)
async def get_comp_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CompJobResponse:
    """Get comp job status and results."""
    repo = CompRepository(db)
    job = await repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Comp job not found")

    response = CompJobResponse.from_orm(job)
    if job.status == CompJobStatus.SUCCESS:
        comps = await repo.get_comps_for_job(job.id)
        response.comps = [CompResponse.from_orm(comp) for comp in comps]
    return response
