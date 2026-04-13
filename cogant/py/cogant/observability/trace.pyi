from collections.abc import Iterator
from contextlib import contextmanager

from cogant.observability.metrics import MetricsRegistry as MetricsRegistry

@contextmanager
def span(name: str, registry: MetricsRegistry | None = None) -> Iterator[None]: ...
