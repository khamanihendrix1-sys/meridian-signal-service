from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from time import time
from typing import Any


@dataclass
class WebhookSimulator:
    """Lightweight webhook simulator used by performance tests."""

    _counter: count[int] = field(default_factory=lambda: count(1))

    def create_signal_webhook_payload(self) -> dict[str, Any]:
        """Create a deterministic signal webhook payload."""
        event_id = next(self._counter)
        return {
            "eventType": "signal.created",
            "eventId": f"evt-{event_id}",
            "occurredAt": time(),
            "payload": {
                "listingId": f"listing-{event_id}",
                "signalId": f"signal-{event_id}",
                "score": float(event_id % 100) / 100,
            },
        }

    def simulate_webhook_processing(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Simulate basic webhook normalization."""
        inner_payload = payload["payload"]
        return {
            "event_type": payload["eventType"],
            "event_id": payload["eventId"],
            "listing_id": inner_payload["listingId"],
            "signal_id": inner_payload["signalId"],
            "score": inner_payload["score"],
        }
