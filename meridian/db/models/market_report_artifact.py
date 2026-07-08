from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from meridian.db.base import Base
from meridian.db.models.enums import GeoType


class MarketReportArtifact(Base):
    """Persisted generated market report payload for export and history."""

    __tablename__ = "market_report_artifacts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    geography: Mapped[str | None] = mapped_column(String(128), nullable=True)
    geo_type: Mapped[GeoType | None] = mapped_column(Enum(GeoType), nullable=True)
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
