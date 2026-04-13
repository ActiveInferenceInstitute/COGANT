"""Lightweight tracing via a ``span()`` context manager.

Records wall-clock elapsed time into a :class:`~cogant.observability.metrics.Histogram`
named ``cogant.span.<name>``.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cogant.observability.metrics import MetricsRegistry


@contextmanager
def span(
    name: str,
    registry: MetricsRegistry | None = None,
) -> Iterator[None]:
    """Time a block and record the elapsed seconds to a histogram.

    Parameters
    ----------
    name:
        Logical operation name.  The histogram will be registered as
        ``cogant.span.<name>``.
    registry:
        Metrics registry to record into.  Falls back to the module-level
        default :data:`cogant.observability.metrics.registry`.
    """
    if registry is None:
        from cogant.observability.metrics import registry as _default

        registry = _default

    hist = registry.histogram(f"cogant.span.{name}")
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        hist.observe(elapsed)
