from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from shapely.geometry import Point
from sqlalchemy import JSON, Date, DateTime, Enum, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from meridian.db.base import Base
from meridian.db.models.enums import ListingStatus, PropertyType


class Listing(Base):
    """A property record ingested from a market adapter."""

    __tablename__ = "listings"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    mls_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    address: Mapped[str] = mapped_column(String(256), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    city: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zip: Mapped[str] = mapped_column(String(5), nullable=False)
    zip4: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    county: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    geom: Mapped[Optional[Point]] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    property_type: Mapped[PropertyType] = mapped_column(Enum(PropertyType), nullable=False)
    beds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    baths: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    living_sqft: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lot_sqft: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    list_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    sold_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    list_date: Mapped[date] = mapped_column(Date, nullable=False)
    sold_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[ListingStatus] = mapped_column(Enum(ListingStatus), nullable=False)
    days_on_market: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    photos: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    raw: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
