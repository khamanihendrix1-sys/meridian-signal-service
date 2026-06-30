from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CacheMetrics:
    """In-memory cache metrics tracker for API cache visibility."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    errors: int = 0
    requests: int = 0
    total_request_time_ms: float = 0.0
    last_request_time_ms: float = 0.0

    def record_hit(self) -> None:
        """Record a cache hit event."""
        self.hits += 1

    def record_miss(self) -> None:
        """Record a cache miss event."""
        self.misses += 1

    def record_evictions(self, count: int = 1) -> None:
        """Record one or more cache evictions."""
        self.evictions += max(count, 0)

    def record_error(self) -> None:
        """Record a cache operation error."""
        self.errors += 1

    def record_request_time(self, duration_ms: float) -> None:
        """Record request latency used for cache observability."""
        self.requests += 1
        self.last_request_time_ms = duration_ms
        self.total_request_time_ms += duration_ms

    @property
    def hit_rate(self) -> float:
        """Return cache hit rate across all cache lookups."""
        lookups = self.hits + self.misses
        return (self.hits / lookups) if lookups else 0.0

    @property
    def average_request_time_ms(self) -> float:
        """Return average request latency across observed requests."""
        return (self.total_request_time_ms / self.requests) if self.requests else 0.0

    def snapshot(self) -> dict[str, float | int]:
        """Return a serializable snapshot of cache metrics."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "errors": self.errors,
            "requests": self.requests,
            "hit_rate": self.hit_rate,
            "last_request_time_ms": self.last_request_time_ms,
            "average_request_time_ms": self.average_request_time_ms,
        }


cache_metrics = CacheMetrics()
