from __future__ import annotations

import asyncio
from uuid import UUID

from celery import Task

from meridian.integrations.celery_app import celery_app
from meridian.comps.engine import CompEngine
from meridian.db.repositories import CompRepository
from meridian.db.models.enums import CompJobStatus
from meridian.db.session import async_session_factory


@celery_app.task(name="meridian.comps.compute_comps", bind=True, max_retries=3)
def compute_comps_task(self: Task, job_id: str, subject_listing_id: str, limit: int = 10) -> None:
    """Compute comps asynchronously for a job."""

    async def work() -> None:
        async with async_session_factory() as session:
            repo = CompRepository(session)
            job_uuid = UUID(job_id)
            job = await repo.get_job_by_id(job_uuid)
            if not job:
                raise ValueError(f"Comp job {job_id} not found")

            await repo.update_job_status(job, CompJobStatus.RUNNING)

            try:
                engine = CompEngine(session)
                comps = await engine.compute_for_subject(UUID(subject_listing_id), job.id, limit=limit)
                comp_ids = [comp.id for comp in comps]
                await repo.update_job_status(job, CompJobStatus.SUCCESS, comp_ids=comp_ids)
            except Exception as exc:
                await repo.update_job_status(job, CompJobStatus.FAILED, error=str(exc))
                raise exc

    return asyncio.run(work())
