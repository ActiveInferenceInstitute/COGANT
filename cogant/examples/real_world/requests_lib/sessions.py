"""Session: a stateful HTTP client in the requests-library style.

Exercises: stateful object with cookie jar, adapter mount table,
auth hook wiring, context-manager protocol, and a request-preparation
pipeline (prepare -> auth -> middleware -> send -> response hooks).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .adapters import BaseAdapter, HTTPAdapter, MountTable
from .auth import AuthBase, NoAuth
from .models import (
    CaseInsensitiveDict,
    PreparedRequest,
    Request,
    Response,
    Timeout,
)

logger = logging.getLogger(__name__)


class CookieJar:
    """A trivial cookie jar keyed on (domain, name)."""

    def __init__(self) -> None:
        self._cookies: Dict[str, Dict[str, str]] = {}

    def set(self, domain: str, name: str, value: str) -> None:
        self._cookies.setdefault(domain, {})[name] = value

    def get(self, domain: str, name: str) -> Optional[str]:
        return self._cookies.get(domain, {}).get(name)

    def for_url(self, url: str) -> Dict[str, str]:
        domain = _domain_of(url)
        return dict(self._cookies.get(domain, {}))

    def clear(self) -> None:
        self._cookies.clear()


def _domain_of(url: str) -> str:
    if "://" in url:
        host = url.split("://", 1)[1]
    else:
        host = url
    if "/" in host:
        host = host.split("/", 1)[0]
    return host.split(":", 1)[0]


class Session:
    """Stateful HTTP client orchestrating adapters, auth, and hooks."""

    def __init__(self) -> None:
        self.headers: CaseInsensitiveDict = CaseInsensitiveDict(
            {
                "User-Agent": "cogant-requests-fixture/1.0",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
        )
        self.auth: AuthBase = NoAuth()
        self.cookies = CookieJar()
        self.adapters = MountTable()
        self.adapters.mount("http://", HTTPAdapter())
        self.adapters.mount("https://", HTTPAdapter())
        self.hooks: Dict[str, List[Any]] = {"response": []}
        self.max_redirects: int = 30
        self.verify: bool = True

    # ------------------------------------------------------------------
    # Context manager protocol
    # ------------------------------------------------------------------

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def close(self) -> None:
        self.adapters.close_all()
        self.cookies.clear()

    # ------------------------------------------------------------------
    # Mount / hook helpers
    # ------------------------------------------------------------------

    def mount(self, prefix: str, adapter: BaseAdapter) -> None:
        self.adapters.mount(prefix, adapter)

    def register_hook(self, event: str, hook: Any) -> None:
        self.hooks.setdefault(event, []).append(hook)

    # ------------------------------------------------------------------
    # High-level verbs
    # ------------------------------------------------------------------

    def get(self, url: str, **kwargs: Any) -> Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> Response:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Response:
        return self.request("DELETE", url, **kwargs)

    def head(self, url: str, **kwargs: Any) -> Response:
        return self.request("HEAD", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> Response:
        return self.request("PATCH", url, **kwargs)

    # ------------------------------------------------------------------
    # Core request pipeline
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        data: Any = None,
        json: Any = None,
        timeout: Optional[float] = None,
        auth: Optional[AuthBase] = None,
    ) -> Response:
        merged_headers: Dict[str, str] = dict(self.headers)
        if headers:
            merged_headers.update(headers)
        req = Request(
            method=method,
            url=url,
            headers=merged_headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
        )
        prepared = req.prepare()

        # Attach session cookies.
        cookie_string = "; ".join(
            f"{name}={value}" for name, value in self.cookies.for_url(url).items()
        )
        if cookie_string:
            prepared.headers["Cookie"] = cookie_string

        # Apply auth (per-call overrides session-level auth).
        active_auth = auth or self.auth
        prepared = active_auth(prepared)

        adapter = self.adapters.resolve(url)
        if timeout is not None and timeout <= 0:
            raise Timeout("non-positive timeout")

        response = adapter.send(
            prepared,
            timeout=timeout,
            verify=self.verify,
        )

        for hook in self.hooks.get("response", []):
            try:
                result = hook(response)
                if isinstance(result, Response):
                    response = result
            except Exception:  # noqa: BLE001
                logger.exception("response hook failed")

        return response
