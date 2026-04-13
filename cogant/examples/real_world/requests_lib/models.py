"""HTTP request/response models for a requests-style library.

Exercises: dataclass fields, frozen vs mutable objects, custom
__repr__, and a lightweight header container.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple, Union


class CaseInsensitiveDict(Mapping[str, str]):
    """A headers container that hashes keys case-insensitively."""

    def __init__(self, initial: Optional[Mapping[str, str]] = None) -> None:
        self._store: Dict[str, Tuple[str, str]] = {}
        if initial:
            for key, value in initial.items():
                self[key] = value  # type: ignore[index]

    def __setitem__(self, key: str, value: str) -> None:
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key: str) -> str:
        return self._store[key.lower()][1]

    def __delitem__(self, key: str) -> None:
        del self._store[key.lower()]

    def __iter__(self) -> Iterator[str]:
        return (original for original, _ in self._store.values())

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return key.lower() in self._store

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._store.get(key.lower())
        return entry[1] if entry is not None else default

    def update(self, other: Mapping[str, str]) -> None:
        for key, value in other.items():
            self[key] = value  # type: ignore[index]

    def items(self) -> Iterable[Tuple[str, str]]:
        return [(original, value) for original, value in self._store.values()]

    def copy(self) -> "CaseInsensitiveDict":
        new = CaseInsensitiveDict()
        new._store = dict(self._store)
        return new


@dataclass
class PreparedRequest:
    """A finalised, ready-to-send HTTP request."""

    method: str
    url: str
    headers: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)
    body: Optional[Union[str, bytes]] = None
    hooks: Dict[str, List[Any]] = field(default_factory=dict)

    def register_hook(self, event: str, hook: Any) -> None:
        self.hooks.setdefault(event, []).append(hook)

    def deregister_hook(self, event: str, hook: Any) -> bool:
        hooks = self.hooks.get(event, [])
        try:
            hooks.remove(hook)
            return True
        except ValueError:
            return False


@dataclass
class Request:
    """A user-facing, not-yet-prepared HTTP request."""

    method: str
    url: str
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, str]] = None
    data: Optional[Union[str, bytes, Dict[str, Any]]] = None
    json: Optional[Any] = None
    timeout: Optional[float] = None

    def prepare(self) -> PreparedRequest:
        prepared = PreparedRequest(
            method=self.method.upper(),
            url=_apply_params(self.url, self.params or {}),
            headers=CaseInsensitiveDict(self.headers or {}),
        )
        if self.json is not None:
            import json as _json

            prepared.headers["Content-Type"] = "application/json"
            prepared.body = _json.dumps(self.json)
        elif isinstance(self.data, (bytes, str)):
            prepared.body = self.data
        elif isinstance(self.data, dict):
            prepared.headers.setdefault(
                "Content-Type", "application/x-www-form-urlencoded"
            )
            prepared.body = _urlencode(self.data)
        return prepared


@dataclass
class Response:
    """An HTTP response observation."""

    status_code: int
    headers: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)
    content: bytes = b""
    url: str = ""
    encoding: Optional[str] = None
    history: List["Response"] = field(default_factory=list)
    request: Optional[PreparedRequest] = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    @property
    def text(self) -> str:
        if not self.content:
            return ""
        enc = self.encoding or "utf-8"
        try:
            return self.content.decode(enc)
        except UnicodeDecodeError:
            return self.content.decode(enc, errors="replace")

    def json(self) -> Any:
        import json as _json

        return _json.loads(self.text)

    def raise_for_status(self) -> None:
        if 400 <= self.status_code < 600:
            raise HTTPError(f"{self.status_code} error for url: {self.url}")


class RequestException(Exception):
    """Base class for all requests-style errors."""


class HTTPError(RequestException):
    """Raised when :meth:`Response.raise_for_status` is called on a 4xx/5xx."""


class ConnectionError(RequestException):  # noqa: A001 - shadow stdlib intentionally
    """Raised when the underlying transport could not connect."""


class Timeout(RequestException):
    """Raised when a request exceeds its configured timeout."""


def _apply_params(url: str, params: Dict[str, str]) -> str:
    if not params:
        return url
    sep = "&" if "?" in url else "?"
    return url + sep + _urlencode(params)


def _urlencode(data: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key, value in data.items():
        parts.append(f"{key}={value}")
    return "&".join(parts)
