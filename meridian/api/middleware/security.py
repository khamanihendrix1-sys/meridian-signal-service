from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that injects security-oriented HTTP response headers.

    Headers applied
    ---------------
    * ``X-Content-Type-Options: nosniff`` — prevents MIME-type sniffing.
    * ``X-Frame-Options: DENY`` — disallows embedding in iframes.
    * ``X-XSS-Protection: 1; mode=block`` — legacy XSS filter hint for older
      browsers.
    * ``Referrer-Policy: strict-origin-when-cross-origin`` — limits referrer
      leakage.
    * ``Permissions-Policy`` — disables unused browser APIs.
    * ``Strict-Transport-Security`` — instructs browsers to use HTTPS only.
      Only injected when the request scheme is ``https`` so that local HTTP
      development is not broken.
    * ``Cache-Control: no-store`` is *not* set here because individual route
      handlers already manage ``Cache-Control`` for their responses.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )

        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )

        return response
