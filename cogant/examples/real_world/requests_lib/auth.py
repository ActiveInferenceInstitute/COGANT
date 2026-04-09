"""Authentication handlers for the requests-style library.

Exercises: small class hierarchy, ``__call__``-based pluggable policies,
and a callable-protocol interface used by :class:`Session`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Callable, Optional

from .models import PreparedRequest

AuthCallable = Callable[[PreparedRequest], PreparedRequest]


class AuthBase:
    """Base interface: a callable that mutates a :class:`PreparedRequest`."""

    def __call__(self, request: PreparedRequest) -> PreparedRequest:
        raise NotImplementedError


class NoAuth(AuthBase):
    """Identity auth — useful as an explicit "no credentials" marker."""

    def __call__(self, request: PreparedRequest) -> PreparedRequest:
        return request


class BasicAuth(AuthBase):
    """HTTP Basic Authentication (RFC 7617)."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

    def __call__(self, request: PreparedRequest) -> PreparedRequest:
        token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        request.headers["Authorization"] = f"Basic {token}"
        return request


class BearerAuth(AuthBase):
    """Bearer token authentication (OAuth 2.0-style)."""

    def __init__(self, token: str) -> None:
        self.token = token

    def __call__(self, request: PreparedRequest) -> PreparedRequest:
        request.headers["Authorization"] = f"Bearer {self.token}"
        return request


class HMACAuth(AuthBase):
    """Signs the request body with HMAC-SHA256 and adds ``X-Signature``."""

    def __init__(self, key_id: str, secret: str) -> None:
        self.key_id = key_id
        self.secret = secret

    def __call__(self, request: PreparedRequest) -> PreparedRequest:
        body = request.body or b""
        if isinstance(body, str):
            body = body.encode()
        sig = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
        request.headers["X-Key-Id"] = self.key_id
        request.headers["X-Signature"] = sig
        return request


class RotatingTokenAuth(AuthBase):
    """Rotates between a pool of tokens round-robin; expiries reset tokens."""

    def __init__(self, tokens: list[str], ttl: float = 60.0) -> None:
        if not tokens:
            raise ValueError("at least one token is required")
        self.tokens = list(tokens)
        self.ttl = ttl
        self._issued_at: dict[str, float] = {t: 0.0 for t in self.tokens}
        self._index = 0

    def _next_token(self) -> str:
        now = time.time()
        for _ in range(len(self.tokens)):
            candidate = self.tokens[self._index]
            self._index = (self._index + 1) % len(self.tokens)
            if now - self._issued_at[candidate] < self.ttl:
                continue
            self._issued_at[candidate] = now
            return candidate
        # All tokens still live; pick the oldest one.
        oldest = min(self._issued_at, key=lambda k: self._issued_at[k])
        self._issued_at[oldest] = now
        return oldest

    def __call__(self, request: PreparedRequest) -> PreparedRequest:
        request.headers["Authorization"] = f"Bearer {self._next_token()}"
        return request


def build_auth(name: str, **kwargs: object) -> Optional[AuthBase]:
    """Factory: resolve a config-friendly name into an auth handler."""
    name_lower = name.lower()
    if name_lower in {"", "none", "noauth"}:
        return NoAuth()
    if name_lower == "basic":
        return BasicAuth(str(kwargs["username"]), str(kwargs["password"]))
    if name_lower == "bearer":
        return BearerAuth(str(kwargs["token"]))
    if name_lower == "hmac":
        return HMACAuth(str(kwargs["key_id"]), str(kwargs["secret"]))
    raise ValueError(f"unknown auth scheme: {name}")
