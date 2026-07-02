from __future__ import annotations

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from meridian.api.models.errors import ErrorCode, make_error_response

# ---------------------------------------------------------------------------
# Custom exception classes
# ---------------------------------------------------------------------------


class MeridianAPIError(HTTPException):
    """Base class for all Meridian API errors.

    Subclasses must set ``error_code`` and can override ``status_code``.
    """

    error_code: str = ErrorCode.INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        if error_code is not None:
            self.error_code = error_code
        self.message = message


class NotFoundError(MeridianAPIError):
    """Raised when a requested resource cannot be found (HTTP 404)."""

    error_code = ErrorCode.NOT_FOUND

    def __init__(
        self, message: str = "Resource not found", *, error_code: str | None = None
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=error_code or self.error_code,
        )


class ConflictError(MeridianAPIError):
    """Raised when an operation conflicts with current state (HTTP 409)."""

    error_code = ErrorCode.CONFLICT

    def __init__(
        self, message: str = "Resource conflict", *, error_code: str | None = None
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_409_CONFLICT,
            error_code=error_code or self.error_code,
        )


class BadRequestError(MeridianAPIError):
    """Raised when the client submits an invalid request (HTTP 400)."""

    error_code = ErrorCode.BAD_REQUEST

    def __init__(
        self, message: str = "Bad request", *, error_code: str | None = None
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code or self.error_code,
        )


class UnauthorizedError(MeridianAPIError):
    """Raised when authentication is missing or invalid (HTTP 401)."""

    error_code = ErrorCode.UNAUTHORIZED

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=self.error_code,
        )


class ForbiddenError(MeridianAPIError):
    """Raised when the caller lacks permission for the requested action (HTTP 403)."""

    error_code = ErrorCode.FORBIDDEN

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(
            message, status_code=status.HTTP_403_FORBIDDEN, error_code=self.error_code
        )


class RateLimitedError(MeridianAPIError):
    """Raised when the client has exceeded the allowed request rate (HTTP 429)."""

    error_code = ErrorCode.RATE_LIMITED

    def __init__(self, message: str = "Too many requests — please retry later") -> None:
        super().__init__(
            message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=self.error_code,
        )


class IdempotencyConflictError(MeridianAPIError):
    """Raised when an idempotency key collides with a previous, non-identical request (HTTP 409)."""

    error_code = ErrorCode.IDEMPOTENCY_CONFLICT

    def __init__(
        self,
        message: str = "Idempotency key already used with different request parameters",
    ) -> None:
        super().__init__(
            message, status_code=status.HTTP_409_CONFLICT, error_code=self.error_code
        )


# ---------------------------------------------------------------------------
# Exception handlers (to be registered on the FastAPI app)
# ---------------------------------------------------------------------------


def _request_id(request: Request) -> str | None:
    return request.headers.get("X-Request-ID") or request.headers.get(
        "X-Correlation-ID"
    )


async def meridian_api_error_handler(
    request: Request, exc: MeridianAPIError
) -> JSONResponse:
    """Handler for all :class:`MeridianAPIError` subclasses."""
    return JSONResponse(
        status_code=exc.status_code,
        content=make_error_response(
            exc.error_code,
            exc.message,
            request_id=_request_id(request),
            path=str(request.url.path),
        ),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler that converts plain :class:`~fastapi.HTTPException` into the
    standardized error envelope."""
    error_code = (
        ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.BAD_REQUEST
    )
    if exc.status_code == 401:
        error_code = ErrorCode.UNAUTHORIZED
    elif exc.status_code == 403:
        error_code = ErrorCode.FORBIDDEN
    elif exc.status_code == 409:
        error_code = ErrorCode.CONFLICT
    elif exc.status_code == 429:
        error_code = ErrorCode.RATE_LIMITED
    elif exc.status_code >= 500:
        error_code = ErrorCode.INTERNAL_SERVER_ERROR

    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=make_error_response(
            error_code,
            detail,
            request_id=_request_id(request),
            path=str(request.url.path),
        ),
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handler that converts Pydantic :class:`~fastapi.exceptions.RequestValidationError`
    into the standardized error envelope."""
    details = []
    for error in exc.errors():
        loc = error.get("loc", ())
        field = ".".join(str(part) for part in loc if part != "body") or None
        details.append({"field": field, "message": error["msg"], "code": error["type"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=make_error_response(
            ErrorCode.VALIDATION_ERROR,
            "Request validation failed",
            details=details,
            request_id=_request_id(request),
            path=str(request.url.path),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected server errors."""
    import logging

    logging.getLogger(__name__).exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=make_error_response(
            ErrorCode.INTERNAL_SERVER_ERROR,
            "An unexpected error occurred",
            request_id=_request_id(request),
            path=str(request.url.path),
        ),
    )
