from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from meridian.db.base import Base
from meridian.db.models.enums import CompJobStatus


class CompJob(Base):
    """Async comparable job tracking record."""

    __tablename__ = "comp_jobs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    subject_listing_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[CompJobStatus] = mapped_column(Enum(CompJobStatus), nullable=False, default=CompJobStatus.PENDING)
    comp_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    comps: Mapped[list["Comp"]] = relationship("Comp", back_populates="job")
