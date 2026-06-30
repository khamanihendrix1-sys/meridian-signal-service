from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from meridian.settings import get_settings


class CacheNamespace:
    """Namespace constants used for cache-key grouping and invalidation."""

    LISTINGS = "listings"
    MARKET_REPORTS = "market_reports"
    SIGNALS = "signals"
    COMPS = "comps"


class CacheStrategy:
    """Cache strategy names used to resolve endpoint TTL policies."""

    LISTINGS_LIST = "listings_list"
    LISTING_DETAIL = "listing_detail"
    MARKET_REPORTS_LIST = "market_reports_list"
    MARKET_REPORT_LATEST = "market_report_latest"
    MARKET_REPORT_DETAIL = "market_report_detail"
    SIGNAL_DEFINITIONS = "signal_definitions"
    SIGNAL_LOGS = "signal_logs"
    COMP_JOB = "comp_job"


def ttl_mapping() -> Mapping[str, int]:
    """Return current cache strategy TTL mapping from settings."""
    settings = get_settings()
    return MappingProxyType(
        {
            CacheStrategy.LISTINGS_LIST: settings.cache_ttl_listings_list,
            CacheStrategy.LISTING_DETAIL: settings.cache_ttl_listing_detail,
            CacheStrategy.MARKET_REPORTS_LIST: settings.cache_ttl_market_reports_list,
            CacheStrategy.MARKET_REPORT_LATEST: settings.cache_ttl_market_report_latest,
            CacheStrategy.MARKET_REPORT_DETAIL: settings.cache_ttl_market_report_detail,
            CacheStrategy.SIGNAL_DEFINITIONS: settings.cache_ttl_signal_definitions,
            CacheStrategy.SIGNAL_LOGS: settings.cache_ttl_signal_logs,
            CacheStrategy.COMP_JOB: settings.cache_ttl_comp_job,
        }
    )


def resolve_ttl(strategy: str, fallback_ttl: int | None = None) -> int:
    """Resolve cache TTL for a strategy with optional fallback."""
    settings = get_settings()
    mapping = ttl_mapping()
    return mapping.get(strategy, fallback_ttl or settings.cache_default_ttl)
