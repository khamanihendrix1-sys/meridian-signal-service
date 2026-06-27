from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from meridian.db.base import Base
from meridian.db.models.enums import GeoType, SignalCategory


class SignalDefinition(Base):
    """Declarative signal definition baked into the signal engine."""

    __tablename__ = "signal_definitions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[SignalCategory] = mapped_column(Enum(SignalCategory), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    refresh_frequency: Mapped[str] = mapped_column(String(64), nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    logs: Mapped[list["SignalLog"]] = relationship("SignalLog", back_populates="signal")


class SignalLog(Base):
    """A computed signal result recorded for a geography."""

    __tablename__ = "signal_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    signal_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("signal_definitions.id", ondelete="CASCADE"), nullable=False)
    geography: Mapped[str] = mapped_column(String(128), nullable=False)
    geo_type: Mapped[GeoType] = mapped_column(Enum(GeoType), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    computed_output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    fired: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    signal: Mapped[SignalDefinition] = relationship("SignalDefinition", back_populates="logs")
