"""Utility helpers for the requests-style library.

Exercises: pure functions, URL parsing, and a small status-code helper
registry (classic requests-library shape).
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, urlunparse


STATUS_CODES: Dict[int, str] = {
    200: "ok",
    201: "created",
    202: "accepted",
    204: "no_content",
    301: "moved_permanently",
    302: "found",
    304: "not_modified",
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    418: "im_a_teapot",
    429: "too_many_requests",
    500: "internal_server_error",
    502: "bad_gateway",
    503: "service_unavailable",
    504: "gateway_timeout",
}


def status_text(code: int) -> str:
    """Return a short snake_case label for a status code."""
    return STATUS_CODES.get(code, "unknown")


def is_success(code: int) -> bool:
    return 200 <= code < 300


def is_redirect(code: int) -> bool:
    return code in {301, 302, 303, 307, 308}


def is_client_error(code: int) -> bool:
    return 400 <= code < 500


def is_server_error(code: int) -> bool:
    return 500 <= code < 600


def parse_url(url: str) -> Tuple[str, str, str, Optional[int]]:
    """Return ``(scheme, host, path, port)`` for ``url``."""
    parsed = urlparse(url)
    return parsed.scheme, parsed.hostname or "", parsed.path or "/", parsed.port


def rebuild_url(scheme: str, host: str, path: str, port: Optional[int] = None) -> str:
    """Recombine a URL from its parts."""
    netloc = host if port is None else f"{host}:{port}"
    return urlunparse((scheme, netloc, path, "", "", ""))


def default_headers(user_agent: str) -> Dict[str, str]:
    """Return the default header set used by a fresh session."""
    return {
        "User-Agent": user_agent,
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }


def resolve_redirect(base_url: str, location: str) -> str:
    """Resolve a ``Location`` header against the originating URL."""
    if location.startswith(("http://", "https://")):
        return location
    scheme, host, _, port = parse_url(base_url)
    if location.startswith("/"):
        return rebuild_url(scheme, host, location, port)
    return rebuild_url(scheme, host, "/" + location, port)
