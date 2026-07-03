"""Tests for the new REST API improvement components."""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any

import pytest

from meridian.api.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    MeridianAPIError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
)
from meridian.api.models.errors import ErrorCode, ErrorDetail, ErrorResponse, make_error_response
from meridian.api.models.pagination import PaginatedResponse


# ---------------------------------------------------------------------------
# ErrorResponse model
# ---------------------------------------------------------------------------


class TestErrorResponse:
    def test_minimal_construction(self) -> None:
        err = ErrorResponse(
            error_code=ErrorCode.NOT_FOUND,
            message="Not found",
        )
        assert err.error_code == "NOT_FOUND"
        assert err.message == "Not found"
        assert err.details is None
        assert err.timestamp is not None

    def test_with_details(self) -> None:
        detail = ErrorDetail(field="email", message="Invalid format", code="value_error")
        err = ErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Validation failed",
            details=[detail],
        )
        assert len(err.details) == 1  # type: ignore[arg-type]
        assert err.details[0].field == "email"  # type: ignore[index]

    def test_json_roundtrip(self) -> None:
        err = ErrorResponse(
            error_code="LISTING_NOT_FOUND",
            message="listing missing",
            request_id="req-abc",
            path="/v1/listings/123",
        )
        data = err.model_dump(mode="json")
        assert data["error_code"] == "LISTING_NOT_FOUND"
        assert data["request_id"] == "req-abc"
        assert data["path"] == "/v1/listings/123"
        assert "timestamp" in data


class TestMakeErrorResponse:
    def test_basic(self) -> None:
        payload = make_error_response(ErrorCode.BAD_REQUEST, "bad input")
        assert payload["error_code"] == "BAD_REQUEST"
        assert payload["message"] == "bad input"
        assert payload["details"] is None

    def test_with_details(self) -> None:
        details = [{"field": "zip", "message": "Too short", "code": "min_length"}]
        payload = make_error_response(
            ErrorCode.VALIDATION_ERROR,
            "Validation failed",
            details=details,
        )
        assert len(payload["details"]) == 1
        assert payload["details"][0]["field"] == "zip"

    def test_request_id_and_path(self) -> None:
        payload = make_error_response(
            ErrorCode.INTERNAL_SERVER_ERROR,
            "Oops",
            request_id="x-123",
            path="/v1/something",
        )
        assert payload["request_id"] == "x-123"
        assert payload["path"] == "/v1/something"


# ---------------------------------------------------------------------------
# PaginatedResponse model
# ---------------------------------------------------------------------------


class TestPaginatedResponse:
    def test_basic_page(self) -> None:
        page: PaginatedResponse[dict[str, Any]] = PaginatedResponse(
            items=[{"id": 1}, {"id": 2}],
            next_cursor="abc",
            has_more=True,
        )
        assert len(page.items) == 2
        assert page.next_cursor == "abc"
        assert page.has_more is True
        assert page.total_count is None

    def test_last_page(self) -> None:
        page: PaginatedResponse[str] = PaginatedResponse(
            items=["a"],
            next_cursor=None,
            has_more=False,
            total_count=1,
        )
        assert not page.has_more
        assert page.total_count == 1


# ---------------------------------------------------------------------------
# Custom exception classes
# ---------------------------------------------------------------------------


class TestCustomExceptions:
    def test_not_found_defaults(self) -> None:
        exc = NotFoundError()
        assert exc.status_code == 404
        assert exc.error_code == ErrorCode.NOT_FOUND

    def test_not_found_custom_error_code(self) -> None:
        exc = NotFoundError("Listing gone", error_code=ErrorCode.LISTING_NOT_FOUND)
        assert exc.error_code == ErrorCode.LISTING_NOT_FOUND
        assert exc.message == "Listing gone"

    def test_conflict_error(self) -> None:
        exc = ConflictError("already exists")
        assert exc.status_code == 409
        assert exc.error_code == ErrorCode.CONFLICT

    def test_bad_request_error(self) -> None:
        exc = BadRequestError()
        assert exc.status_code == 400

    def test_unauthorized_error(self) -> None:
        exc = UnauthorizedError()
        assert exc.status_code == 401
        assert exc.error_code == ErrorCode.UNAUTHORIZED

    def test_forbidden_error(self) -> None:
        exc = ForbiddenError()
        assert exc.status_code == 403
        assert exc.error_code == ErrorCode.FORBIDDEN

    def test_rate_limited_error(self) -> None:
        exc = RateLimitedError()
        assert exc.status_code == 429
        assert exc.error_code == ErrorCode.RATE_LIMITED

    def test_is_http_exception(self) -> None:
        from fastapi import HTTPException

        exc = NotFoundError("x")
        assert isinstance(exc, HTTPException)
        assert isinstance(exc, MeridianAPIError)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


class TestJWTHelpers:
    def test_create_and_decode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import meridian.settings

        meridian.settings.get_settings.cache_clear()
        monkeypatch.setenv("JWT_SIGNING_KEY", "test-secret-key-for-unit-test")
        meridian.settings.get_settings.cache_clear()

        from meridian.api.auth import create_access_token, decode_access_token

        token = create_access_token("user-42", roles=["analyst"])
        payload = decode_access_token(token)
        assert payload["sub"] == "user-42"
        assert "analyst" in payload["roles"]

    def test_expired_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import meridian.settings

        meridian.settings.get_settings.cache_clear()
        monkeypatch.setenv("JWT_SIGNING_KEY", "test-secret-key-for-unit-test")
        meridian.settings.get_settings.cache_clear()

        from meridian.api.auth import create_access_token, decode_access_token
        from meridian.api.exceptions import UnauthorizedError

        token = create_access_token("u", expires_delta=timedelta(seconds=-1))
        with pytest.raises(UnauthorizedError):
            decode_access_token(token)

    def test_invalid_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import meridian.settings

        meridian.settings.get_settings.cache_clear()
        monkeypatch.setenv("JWT_SIGNING_KEY", "test-secret-key-for-unit-test")
        meridian.settings.get_settings.cache_clear()

        from meridian.api.auth import decode_access_token
        from meridian.api.exceptions import UnauthorizedError

        with pytest.raises(UnauthorizedError):
            decode_access_token("not.a.valid.token")


# ---------------------------------------------------------------------------
# Settings: CORS origins list
# ---------------------------------------------------------------------------


class TestSettingsCorsOrigins:
    def test_wildcard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import meridian.settings

        meridian.settings.get_settings.cache_clear()
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
        meridian.settings.get_settings.cache_clear()
        s = meridian.settings.get_settings()
        assert s.cors_origins_list == ["*"]
        meridian.settings.get_settings.cache_clear()

    def test_multiple_origins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import meridian.settings

        meridian.settings.get_settings.cache_clear()
        monkeypatch.setenv(
            "CORS_ALLOWED_ORIGINS",
            "https://app.example.com, https://admin.example.com",
        )
        meridian.settings.get_settings.cache_clear()
        s = meridian.settings.get_settings()
        assert s.cors_origins_list == [
            "https://app.example.com",
            "https://admin.example.com",
        ]
        meridian.settings.get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class TestInMemoryRateLimiter:
    def test_allows_within_limit(self) -> None:
        from meridian.api.rate_limit import _InMemoryRateLimiter

        limiter = _InMemoryRateLimiter()
        allowed, remaining = limiter.is_allowed("key1", limit=3, window_seconds=60)
        assert allowed is True
        assert remaining == 2

    def test_blocks_when_limit_exceeded(self) -> None:
        from meridian.api.rate_limit import _InMemoryRateLimiter

        limiter = _InMemoryRateLimiter()
        for _ in range(3):
            limiter.is_allowed("key2", limit=3, window_seconds=60)

        allowed, remaining = limiter.is_allowed("key2", limit=3, window_seconds=60)
        assert allowed is False
        assert remaining == 0

    def test_independent_keys(self) -> None:
        from meridian.api.rate_limit import _InMemoryRateLimiter

        limiter = _InMemoryRateLimiter()
        for _ in range(3):
            limiter.is_allowed("keyA", limit=3, window_seconds=60)

        # Different key should still be allowed
        allowed, _ = limiter.is_allowed("keyB", limit=3, window_seconds=60)
        assert allowed is True
