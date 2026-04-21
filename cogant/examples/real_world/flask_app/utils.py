"""Utility helpers for the Flask-style app.

Exercises: pure functions, generator-based streaming, a lightweight
decorator library, and a classic "retry with backoff" pattern.
"""

from __future__ import annotations

import functools
import itertools
import json
import logging
import time
from collections.abc import Callable, Iterable, Iterator
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def slugify(value: str) -> str:
    """Normalise ``value`` into an ASCII slug usable in URLs."""
    cleaned = []
    for char in value.lower():
        if char.isalnum():
            cleaned.append(char)
        elif char in {" ", "-", "_"}:
            cleaned.append("-")
    result = "".join(cleaned)
    while "--" in result:
        result = result.replace("--", "-")
    return result.strip("-")


def paginate(items: list[Any], *, page: int, per_page: int) -> dict[str, Any]:
    """Return a standard paginated envelope around ``items``."""
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 1
    start = (page - 1) * per_page
    end = start + per_page
    total = len(items)
    pages = max(1, (total + per_page - 1) // per_page)
    return {
        "items": items[start:end],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }


def chunked(iterable: Iterable[Any], size: int) -> Iterator[list[Any]]:
    """Yield successive ``size``-sized lists from ``iterable``."""
    if size < 1:
        raise ValueError("size must be >= 1")
    it = iter(iterable)
    while True:
        batch = list(itertools.islice(it, size))
        if not batch:
            break
        yield batch


def jsonify(data: Any, *, sort_keys: bool = True, indent: int | None = None) -> str:
    """Serialise ``data`` to JSON, preferring str over bytes."""
    try:
        return json.dumps(data, sort_keys=sort_keys, indent=indent, default=str)
    except (TypeError, ValueError) as exc:
        logger.warning("jsonify failed: %s", exc)
        return json.dumps({"error": "serialization_failed", "detail": str(exc)})


def retry(
    *,
    attempts: int = 3,
    initial_backoff: float = 0.1,
    max_backoff: float = 2.0,
    exceptions: tuple[type, ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator: retry the wrapped callable on transient failures."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            last_error: BaseException | None = None
            backoff = initial_backoff
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # noqa: PERF203
                    last_error = exc
                    logger.info(
                        "retry %s attempt %d/%d failed: %s",
                        func.__name__,
                        attempt,
                        attempts,
                        exc,
                    )
                    if attempt == attempts:
                        break
                    time.sleep(min(backoff, max_backoff))
                    backoff *= 2
            assert last_error is not None
            raise last_error

        return wrapped  # type: ignore[return-value]

    return decorator


def timed(func: F) -> F:
    """Decorator: log how long the wrapped callable takes to run."""

    @functools.wraps(func)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            logger.debug("%s took %.4fs", func.__name__, elapsed)

    return wrapped  # type: ignore[return-value]


def merge_dicts(*dicts: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge ``dicts`` left-to-right, preferring later values."""
    out: dict[str, Any] = {}
    for d in dicts:
        for key, value in d.items():
            if isinstance(value, dict) and isinstance(out.get(key), dict):
                out[key] = merge_dicts(out[key], value)
            else:
                out[key] = value
    return out
