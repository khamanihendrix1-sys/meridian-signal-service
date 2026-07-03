from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from meridian.api.exceptions import ForbiddenError, UnauthorizedError
from meridian.settings import get_settings

_bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

ALGORITHM = "HS256"
DEFAULT_TOKEN_TTL_MINUTES = 60


def create_access_token(
    subject: str,
    roles: list[str] | None = None,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Parameters
    ----------
    subject:
        Typically the user ID or API key identifier.
    roles:
        Optional list of role strings included in the ``roles`` claim.
    expires_delta:
        How long the token should be valid for.  Defaults to
        :data:`DEFAULT_TOKEN_TTL_MINUTES`.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    ttl = expires_delta or timedelta(minutes=DEFAULT_TOKEN_TTL_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "roles": roles or [],
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, settings.jwt_signing_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Raises
    ------
    UnauthorizedError
        If the token is missing, malformed, or has an invalid signature.
    UnauthorizedError
        If the token has expired.
    """
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_signing_key, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired") from None
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid authentication token") from None


# ---------------------------------------------------------------------------
# FastAPI dependency helpers
# ---------------------------------------------------------------------------


async def get_optional_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any] | None:
    """Return the decoded JWT payload, or ``None`` if no token was supplied.

    This dependency does *not* enforce authentication — use
    :func:`get_current_token` for that.
    """
    if credentials is None:
        return None
    return decode_access_token(credentials.credentials)


async def get_current_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """Return the decoded JWT payload for the authenticated caller.

    Raises :class:`~meridian.api.exceptions.UnauthorizedError` when no valid
    bearer token is present.
    """
    if credentials is None:
        raise UnauthorizedError()
    return decode_access_token(credentials.credentials)


def require_roles(*required_roles: str) -> Any:
    """Return a FastAPI dependency that enforces role-based access control.

    Usage::

        @router.get("/admin-only", dependencies=[Depends(require_roles("admin"))])
        async def admin_endpoint(): ...

    Parameters
    ----------
    *required_roles:
        One or more role strings.  The caller must hold **all** of them.
    """

    async def _check(
        token: dict[str, Any] = Depends(get_current_token),
    ) -> dict[str, Any]:
        token_roles: list[str] = token.get("roles") or []
        missing = [r for r in required_roles if r not in token_roles]
        if missing:
            raise ForbiddenError(f"Missing required role(s): {', '.join(missing)}")
        return token

    return Depends(_check)


# ---------------------------------------------------------------------------
# Idempotency key support
# ---------------------------------------------------------------------------


async def get_idempotency_key(
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> str | None:
    """Extract the optional ``Idempotency-Key`` request header."""
    return idempotency_key
