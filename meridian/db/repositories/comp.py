from __future__ import annotations

from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.db.models import Comp, CompJob
from meridian.db.models.enums import CompJobStatus


class CompRepository:
    """Repository for comp jobs and comp records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_job_by_id(self, job_id: UUID) -> CompJob | None:
        """Get a comp job by ID."""
        stmt = select(CompJob).where(CompJob.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_job(self, subject_listing_id: UUID) -> CompJob:
        """Create a new comp job record."""
        job = CompJob(
            subject_listing_id=subject_listing_id,
            status=CompJobStatus.PENDING,
            comp_ids=[],
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def update_job_status(
        self,
        job: CompJob,
        status: CompJobStatus,
        *,
        comp_ids: list[UUID] | None = None,
        error: str | None = None,
        commit: bool = True,
        refresh: bool = False,
    ) -> CompJob:
        """Update comp job status and optional metadata."""
        job.status = status
        if comp_ids is not None:
            job.comp_ids = [str(comp_id) for comp_id in comp_ids]
        job.error = error
        job.updated_at = datetime.utcnow()
        job.completed_at = (
            datetime.utcnow()
            if status in {CompJobStatus.SUCCESS, CompJobStatus.FAILED}
            else None
        )
        if commit:
            await self.session.commit()
        if refresh:
            await self.session.refresh(job)
        return job

    async def get_comps_for_job(self, job_id: UUID) -> Sequence[Comp]:
        """Get comps associated with a comp job."""
        stmt = select(Comp).where(Comp.job_id == job_id).order_by(Comp.rank)
        result = await self.session.execute(stmt)
        return result.scalars().all()
