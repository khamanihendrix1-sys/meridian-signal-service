from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from meridian.db.base import Base


class Comp(Base):
    """A comparable sale scored against a subject listing."""

    __tablename__ = "comps"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    subject_listing_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    comp_listing_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("comp_jobs.id", ondelete="CASCADE"), nullable=False)
    distance_miles: Mapped[float] = mapped_column(Float, nullable=False)
    sold_date_delta_days: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_similarity: Mapped[float] = mapped_column(Float, nullable=False)
    adjustments: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    adjusted_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    subject_listing = relationship("Listing", foreign_keys=[subject_listing_id])
    comp_listing = relationship("Listing", foreign_keys=[comp_listing_id])
    job = relationship("CompJob", back_populates="comps")
