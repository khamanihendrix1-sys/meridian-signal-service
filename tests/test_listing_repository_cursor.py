from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from meridian.db.repositories.listing import ListingRepository


class _FakeScalars:
    def __init__(self, items: list[SimpleNamespace]) -> None:
        self._items = items

    def all(self) -> list[SimpleNamespace]:
        return self._items


class _FakeResult:
    def __init__(self, items: list[SimpleNamespace]) -> None:
        self._items = items

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._items)


class _FakeSession:
    def __init__(self, items: list[SimpleNamespace]) -> None:
        self._items = items
        self.stmt: object | None = None

    async def execute(self, stmt: object) -> _FakeResult:
        self.stmt = stmt
        return _FakeResult(self._items)


@pytest.mark.asyncio
async def test_search_listings_uses_keyset_pagination() -> None:
    now = datetime.utcnow()
    rows = [
        SimpleNamespace(created_at=now, id=uuid4()),
        SimpleNamespace(created_at=now - timedelta(seconds=1), id=uuid4()),
        SimpleNamespace(created_at=now - timedelta(seconds=2), id=uuid4()),
    ]
    session = _FakeSession(rows)
    repo = ListingRepository(session)  # type: ignore[arg-type]

    page, next_cursor = await repo.search_listings(limit=2)

    assert len(page) == 2
    assert next_cursor is not None
    cursor_created_at, cursor_id = repo._decode_cursor(next_cursor)
    assert cursor_created_at == page[-1].created_at
    assert cursor_id == page[-1].id
    assert session.stmt is not None
    assert "OFFSET" not in str(session.stmt)


def test_invalid_cursor_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid cursor"):
        ListingRepository._decode_cursor("not-a-valid-cursor")
