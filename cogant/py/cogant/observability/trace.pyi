from cogant.observability.metrics import MetricsRegistry as MetricsRegistry
from collections.abc import Iterator
from contextlib import contextmanager

@contextmanager
def span(name: str, registry: MetricsRegistry | None = None) -> Iterator[None]: ...
