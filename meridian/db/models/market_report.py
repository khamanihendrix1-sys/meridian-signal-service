from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Date, DateTime, Enum, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from meridian.db.base import Base
from meridian.db.models.enums import GeoType


class MarketReport(Base):
    """Point-in-time market summary for a defined geography."""

    __tablename__ = "market_reports"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    geography: Mapped[str] = mapped_column(String(128), nullable=False)
    geo_type: Mapped[GeoType] = mapped_column(Enum(GeoType), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    median_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    mean_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    active_listings: Mapped[int] = mapped_column(Integer, nullable=False)
    sold_last_30d: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_days_on_market: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    months_of_inventory: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    absorption_rate: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    yoy_price_change: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    mom_price_change: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    list_to_sold_ratio: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    raw_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
