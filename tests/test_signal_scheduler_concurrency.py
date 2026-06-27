from __future__ import annotations

import asyncio

import pytest

from meridian.signals import scheduler as scheduler_module


class _DummyRedis:
    async def close(self) -> None:
        return None


class _DummySessionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


@pytest.mark.asyncio
async def test_signal_scheduler_runs_geographies_with_concurrency_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        scheduler_module.Redis,
        "from_url",
        lambda _url: _DummyRedis(),
    )
    monkeypatch.setattr(
        scheduler_module,
        "async_session_factory",
        lambda: _DummySessionContext(),
    )

    active = 0
    max_active = 0

    class _FakeEngine:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def run_all_signals(self, geography: str, geo_type: str) -> list[object]:
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1
            return [object()]

    monkeypatch.setattr(scheduler_module, "PersistentSignalEngine", _FakeEngine)

    scheduler = scheduler_module.SignalScheduler()
    scheduler.max_concurrency = 2

    await scheduler._run_signals_job()

    assert max_active > 1
    assert max_active <= scheduler.max_concurrency
