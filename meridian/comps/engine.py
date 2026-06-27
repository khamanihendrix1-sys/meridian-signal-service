from __future__ import annotations

from datetime import datetime
from typing import Sequence
from uuid import UUID, uuid4

from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.comps.scoring import CompScore, haversine_distance, score_comparable
from meridian.db.models import Comp, Listing
from meridian.db.repositories import CompRepository, ListingRepository
from meridian.hooks import (
    COMP_COMPUTE_COMPLETE,
    COMP_COMPUTE_FAILED,
    COMP_COMPUTE_START,
    trigger_hook,
)


class CompEngine:
    """Compute comparable sale matches for a subject listing."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.listing_repo = ListingRepository(session)
        self.comp_repo = CompRepository(session)

    async def compute_for_subject(
        self,
        subject_listing_id: UUID,
        job_id: UUID,
        limit: int = 10,
    ) -> Sequence[Comp]:
        """Compute comps for a subject listing and persist results."""
        await trigger_hook(
            COMP_COMPUTE_START,
            subject_listing_id=subject_listing_id,
            job_id=job_id,
            limit=limit,
        )

        try:
            subject = await self.listing_repo.get_by_id(subject_listing_id)
            if not subject:
                raise ValueError(f"Subject listing {subject_listing_id} not found")

            if not subject.geom:
                raise ValueError("Subject listing must include geographic coordinates")

            subject_point = to_shape(subject.geom)
            subject_lat = subject_point.y
            subject_lon = subject_point.x
            candidate_listings = await self.listing_repo.search_nearby(
                lat=subject_lat,
                lon=subject_lon,
                radius_miles=10.0,
                limit=limit * 5,
            )

            candidates = [
                listing
                for listing in candidate_listings
                if listing.id != subject_listing_id
                and listing.status == "SOLD"
                and listing.sold_price is not None
            ]

            scored_candidates: list[tuple[Listing, CompScore, int]] = []
            for listing in candidates:
                if (
                    not listing.geom
                    or not listing.sold_date
                    or listing.sold_price is None
                ):
                    continue

                candidate_point = to_shape(listing.geom)
                distance = haversine_distance(
                    subject_lat, subject_lon, candidate_point.y, candidate_point.x
                )
                days_delta = (datetime.utcnow().date() - listing.sold_date).days
                score = score_comparable(
                    subject_price=subject.list_price,
                    subject_sqft=subject.living_sqft,
                    subject_beds=subject.beds,
                    subject_baths=subject.baths,
                    candidate_price=listing.sold_price,
                    candidate_sqft=listing.living_sqft,
                    candidate_beds=listing.beds,
                    candidate_baths=listing.baths,
                    distance_miles=distance,
                    sold_date_delta_days=days_delta,
                )
                scored_candidates.append((listing, score, days_delta))

            scored_candidates.sort(
                key=lambda item: item[1].raw_similarity, reverse=True
            )
            selected = scored_candidates[:limit]

            persisted: list[Comp] = []
            rank = 1
            for listing, score, days_delta in selected:
                comp = Comp(
                    id=uuid4(),
                    job_id=job_id,
                    subject_listing_id=subject_listing_id,
                    comp_listing_id=listing.id,
                    distance_miles=score.distance_miles,
                    sold_date_delta_days=days_delta,
                    raw_similarity=score.raw_similarity,
                    adjustments=score.adjustments,
                    adjusted_price=score.adjusted_price,
                    rank=rank,
                    created_at=datetime.utcnow(),
                )
                self.session.add(comp)
                persisted.append(comp)
                rank += 1

            if not persisted:
                await trigger_hook(
                    COMP_COMPUTE_FAILED,
                    job_id=job_id,
                    subject_listing_id=subject_listing_id,
                    error="No valid comparables found",
                )
                return persisted

            await self.session.commit()
            for comp in persisted:
                await self.session.refresh(comp)

            await trigger_hook(
                COMP_COMPUTE_COMPLETE,
                job_id=job_id,
                subject_listing_id=subject_listing_id,
                comp_ids=[comp.id for comp in persisted],
                count=len(persisted),
            )

            return persisted
        except Exception as exc:
            await trigger_hook(
                COMP_COMPUTE_FAILED,
                job_id=job_id,
                subject_listing_id=subject_listing_id,
                error=str(exc),
            )
            raise

    async def compute_for_subject_sync(
        self, subject_listing_id: UUID, job_id: UUID, limit: int = 10
    ) -> Sequence[Comp]:
        """Synchronous wrapper for compute_for_subject to be used in Celery tasks."""
        return await self.compute_for_subject(subject_listing_id, job_id, limit)
