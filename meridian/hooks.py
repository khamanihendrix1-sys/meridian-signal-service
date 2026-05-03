from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List

HookCallback = Callable[..., Any] | Callable[..., Awaitable[Any]]
HookRegistry = Dict[str, List[HookCallback]]

_registry: HookRegistry = defaultdict(list)

APP_STARTUP = "app.startup"
APP_SHUTDOWN = "app.shutdown"
DB_SESSION_OPENED = "db.session.opened"
DB_SESSION_CLOSED = "db.session.closed"
MARKET_REPORT_REFRESH_START = "market_report.refresh.start"
MARKET_REPORT_REFRESH_COMPLETE = "market_report.refresh.complete"
COMP_COMPUTE_START = "comp.compute.start"
COMP_COMPUTE_COMPLETE = "comp.compute.complete"
COMP_COMPUTE_FAILED = "comp.compute.failed"
SIGNAL_RUN_START = "signal.run.start"
SIGNAL_RUN_COMPLETE = "signal.run.complete"


def register_hook(event: str, callback: HookCallback) -> None:
    """Register a callback for a named lifecycle event."""
    _registry[event].append(callback)


async def trigger_hook(event: str, **payload: Any) -> None:
    """Invoke all callbacks registered for an event."""
    callbacks = _registry.get(event, [])
    for callback in callbacks:
        result = callback(**payload)
        if asyncio.iscoroutine(result):
            await result
