"""Adapters package for market data sources."""

from meridian.adapters.base import (
    Capability,
    MarketAdapter,
    RawListing,
    RawMarketMetrics,
)
from meridian.adapters.mock import MockAdapter
from meridian.adapters.registry import AdapterRegistry

__all__ = [
    "Capability",
    "MarketAdapter",
    "RawListing",
    "RawMarketMetrics",
    "MockAdapter",
    "AdapterRegistry",
]

# Global registry instance
registry = AdapterRegistry()
registry.register(MockAdapter())
