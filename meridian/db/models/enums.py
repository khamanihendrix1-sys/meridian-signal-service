from __future__ import annotations

from enum import StrEnum


class PropertyType(StrEnum):
    """Property type identifiers used consistently across the domain."""
    SFR = "SFR"
    CONDO = "CONDO"
    TOWNHOUSE = "TOWNHOUSE"
    MULTIFAMILY = "MULTIFAMILY"
    LAND = "LAND"


class ListingStatus(StrEnum):
    """Valid listing lifecycle states."""
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    SOLD = "SOLD"
    EXPIRED = "EXPIRED"
    WITHDRAWN = "WITHDRAWN"


class GeoType(StrEnum):
    """Geography type identifiers for spatial reports and signals."""
    METRO = "METRO"
    ZIP = "ZIP"
    COUNTY = "COUNTY"
    NEIGHBORHOOD = "NEIGHBORHOOD"
    CITY = "CITY"


class SignalCategory(StrEnum):
    """Signal categories for grouping signal definitions."""
    PRICE = "PRICE"
    INVENTORY = "INVENTORY"
    VELOCITY = "VELOCITY"
    ABSORPTION = "ABSORPTION"


class CompJobStatus(StrEnum):
    """Status values for comp jobs."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
