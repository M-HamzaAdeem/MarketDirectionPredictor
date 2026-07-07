"""Response security headers applied to every HTTP request — CSP, frame/
sniff protections, a strict referrer policy, and HSTS — per
.claude/rules/security.md. Doesn't touch the /ws WebSocket handshake; these
are browser-document protections and the app has no server-rendered HTML
of its own to protect other than FastAPI's built-in /docs and /redoc pages.

The CSP explicitly allow-lists the CDN that FastAPI's bundled Swagger UI
(/docs) loads its JS/CSS from — a bare `default-src 'self'` would silently
break the interactive API docs rather than just tightening security.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response

_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "img-src 'self' data: fastapi.tiangolo.com; "
    "script-src 'self' cdn.jsdelivr.net; "
    "style-src 'self' cdn.jsdelivr.net 'unsafe-inline'; "
    "frame-ancestors 'none'"
)

_SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": _CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # Inert (and harmless) over plain HTTP local dev — only ever honored by
    # a browser that saw this header over a real HTTPS connection.
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}


async def add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers.update(_SECURITY_HEADERS)
    return response
