"""ASGI middleware for loopback-only HTTP hardening."""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def _host_allowed(host: str) -> bool:
    if not host:
        return True
    if _host_is_loopback(host):
        return True
    if host == "testserver" and os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    return False


def _host_is_loopback(host: str) -> bool:
    host = (host or "").strip().lower()
    if not host:
        return False
    if host in {"127.0.0.1", "localhost", "[::1]", "::1"}:
        return True
    bare = host.split("%", 1)[0]
    if bare.startswith("[") and bare.endswith("]"):
        bare = bare[1:-1]
    try:
        return ipaddress.ip_address(bare).is_loopback
    except ValueError:
        return False


def _parse_host_header(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    if value.startswith("["):
        end = value.find("]")
        if end != -1:
            return value[1:end]
    if ":" in value and value.count(":") == 1:
        host, _port = value.rsplit(":", 1)
        if host.replace(".", "").isdigit():
            return host
    return value.split(":", 1)[0]


class LoopbackHostMiddleware(BaseHTTPMiddleware):
    """Reject non-loopback Host headers (DNS rebinding mitigation)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        host_hdr = request.headers.get("host", "")
        host = _parse_host_header(host_hdr)
        if host and not _host_allowed(host):
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "message": "Forbidden Host header (Construct-Zero is loopback-only)",
                        "type": "invalid_request_error",
                        "code": "cz_forbidden_host",
                    }
                },
            )

        origin = request.headers.get("origin", "").strip()
        if origin:
            parsed = urlparse(origin)
            if parsed.hostname and not _host_is_loopback(parsed.hostname):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "message": "Cross-origin browser requests are not allowed",
                            "type": "invalid_request_error",
                            "code": "cz_forbidden_origin",
                        }
                    },
                )

        return await call_next(request)
