from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """A single structured error detail."""

    field: str | None = Field(
        None, description="The field that caused the error, if applicable"
    )
    message: str = Field(..., description="Human-readable description of the error")
    code: str | None = Field(None, description="Machine-readable sub-error code")


class ErrorResponse(BaseModel):
    """Standardized error response returned for all API errors."""

    error_code: str = Field(
        ...,
        description="Machine-readable error code (e.g. LISTING_NOT_FOUND)",
        examples=["LISTING_NOT_FOUND"],
    )
    message: str = Field(
        ...,
        description="Human-readable summary of the error",
        examples=["The requested listing was not found"],
    )
    details: list[ErrorDetail] | None = Field(
        None,
        description="Optional structured details for multi-field validation errors",
    )
    request_id: str | None = Field(
        None,
        description="Trace/request identifier for support lookups",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the error occurred",
    )
    path: str | None = Field(None, description="Request path that produced the error")

    model_config = {
        "json_schema_extra": {
            "example": {
                "error_code": "LISTING_NOT_FOUND",
                "message": "The requested listing was not found",
                "details": None,
                "request_id": "req-abc123",
                "timestamp": "2026-07-02T10:00:00Z",
                "path": "/v1/listings/00000000-0000-0000-0000-000000000001",
            }
        }
    }


# ---------------------------------------------------------------------------
# Well-known error codes used across the service
# ---------------------------------------------------------------------------


class ErrorCode:
    """Namespace of well-known error code constants."""

    # Generic
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMITED = "RATE_LIMITED"
    BAD_REQUEST = "BAD_REQUEST"

    # Listings
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    INVALID_LISTING_FILTERS = "INVALID_LISTING_FILTERS"

    # Market reports
    MARKET_REPORT_NOT_FOUND = "MARKET_REPORT_NOT_FOUND"
    MARKET_REPORT_REFRESH_FAILED = "MARKET_REPORT_REFRESH_FAILED"
    INVALID_GEO_TYPE = "INVALID_GEO_TYPE"

    # Signals
    SIGNAL_NOT_FOUND = "SIGNAL_NOT_FOUND"
    SIGNAL_EVALUATION_FAILED = "SIGNAL_EVALUATION_FAILED"

    # Comps
    COMP_JOB_NOT_FOUND = "COMP_JOB_NOT_FOUND"
    COMP_JOB_DUPLICATE = "COMP_JOB_DUPLICATE"

    # Auth
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # Idempotency
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"


def make_error_response(
    error_code: str,
    message: str,
    *,
    details: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    """Build a serializable error response payload."""
    parsed_details: list[ErrorDetail] | None = None
    if details:
        parsed_details = [ErrorDetail(**d) for d in details]
    return ErrorResponse(
        error_code=error_code,
        message=message,
        details=parsed_details,
        request_id=request_id,
        path=path,
    ).model_dump(mode="json")
