"""Transport adapters for the requests-style library.

Exercises: an abstract base class, a polymorphic ``send`` interface,
and a chain-of-responsibility style mount table keyed on URL scheme.
"""

from __future__ import annotations

import logging

from .models import (
    ConnectionError as TransportConnectionError,
)
from .models import (
    PreparedRequest,
    Response,
    Timeout,
)

logger = logging.getLogger(__name__)


class BaseAdapter:
    """Base transport adapter interface."""

    def send(
        self,
        request: PreparedRequest,
        *,
        stream: bool = False,
        timeout: float | None = None,
        verify: bool = True,
    ) -> Response:
        raise NotImplementedError("subclasses must implement send()")

    def close(self) -> None:
        """Release any resources held by the adapter."""


class HTTPAdapter(BaseAdapter):
    """Default HTTP transport adapter.

    In a real library this would wrap a connection pool and urllib3. Here
    we emulate those semantics with an in-memory route table so the
    fixture exercises realistic control flow without any real I/O.
    """

    def __init__(self, pool_connections: int = 10, pool_maxsize: int = 10) -> None:
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self._routes: dict[str, Response] = {}
        self._closed = False

    def register(self, url: str, response: Response) -> None:
        self._routes[url] = response

    def send(
        self,
        request: PreparedRequest,
        *,
        stream: bool = False,
        timeout: float | None = None,
        verify: bool = True,
    ) -> Response:
        if self._closed:
            raise TransportConnectionError("adapter is closed")
        if timeout is not None and timeout <= 0:
            raise Timeout("non-positive timeout")
        canned = self._routes.get(request.url)
        if canned is None:
            raise TransportConnectionError(f"no route for {request.url}")
        canned.request = request
        return canned

    def close(self) -> None:
        self._closed = True
        self._routes.clear()


class MockAdapter(BaseAdapter):
    """A recording adapter used in tests to capture outgoing requests."""

    def __init__(self) -> None:
        self.sent: list[PreparedRequest] = []
        self.response_status: int = 200

    def send(
        self,
        request: PreparedRequest,
        *,
        stream: bool = False,
        timeout: float | None = None,
        verify: bool = True,
    ) -> Response:
        self.sent.append(request)
        return Response(
            status_code=self.response_status,
            url=request.url,
            request=request,
        )


class MountTable:
    """Resolves a URL prefix to an adapter, longest-prefix first."""

    def __init__(self) -> None:
        self._mounts: dict[str, BaseAdapter] = {}

    def mount(self, prefix: str, adapter: BaseAdapter) -> None:
        self._mounts[prefix] = adapter

    def resolve(self, url: str) -> BaseAdapter:
        candidates = [
            (prefix, adapter) for prefix, adapter in self._mounts.items() if url.startswith(prefix)
        ]
        if not candidates:
            raise TransportConnectionError(f"no adapter mounted for {url}")
        candidates.sort(key=lambda item: len(item[0]), reverse=True)
        return candidates[0][1]

    def close_all(self) -> None:
        for adapter in self._mounts.values():
            try:
                adapter.close()
            except Exception:  # noqa: BLE001
                logger.exception("error while closing adapter")
        self._mounts.clear()
