from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Mapping


@dataclass
class RateLimitState:
    """Latest observed upstream rate-limit state."""

    limit: int | None = None
    remaining: int | None = None
    reset_epoch: int | None = None
    used: int | None = None
    last_observed_at: datetime | None = None
    source: str | None = None


class RateLimitMonitor:
    """Stores and exposes latest upstream rate-limit telemetry."""

    def __init__(self) -> None:
        self._state = RateLimitState()

    @staticmethod
    def _parse_int(value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def update_from_headers(
        self,
        headers: Mapping[str, str],
        *,
        source: str,
    ) -> None:
        """Update tracked rate-limit state from response headers."""
        normalized = {key.lower(): value for key, value in headers.items()}
        self._state.limit = self._parse_int(normalized.get("x-ratelimit-limit"))
        self._state.remaining = self._parse_int(normalized.get("x-ratelimit-remaining"))
        self._state.reset_epoch = self._parse_int(normalized.get("x-ratelimit-reset"))
        self._state.used = self._parse_int(normalized.get("x-ratelimit-used"))
        self._state.last_observed_at = datetime.now(UTC)
        self._state.source = source

    def snapshot(self) -> dict[str, str | int | None]:
        """Return a serializable snapshot of tracked rate-limit state."""
        return {
            "limit": self._state.limit,
            "remaining": self._state.remaining,
            "reset_epoch": self._state.reset_epoch,
            "used": self._state.used,
            "source": self._state.source,
            "last_observed_at": (
                self._state.last_observed_at.isoformat()
                if self._state.last_observed_at
                else None
            ),
        }


rate_limit_monitor = RateLimitMonitor()
