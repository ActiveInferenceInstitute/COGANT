"""In-process metrics: Counter, Histogram, and a thread-safe MetricsRegistry.

No external dependencies required.  Designed for lightweight telemetry inside
a COGANT pipeline run — *not* a Prometheus exporter.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class Counter:
    """Monotonically increasing counter with optional labels."""

    name: str
    value: int = 0
    labels: dict[str, str] = field(default_factory=dict)

    def inc(self, by: int = 1) -> None:
        """Increment the counter by *by* (default 1)."""
        self.value += by

    def reset(self) -> None:
        """Reset the counter to zero."""
        self.value = 0


@dataclass
class Histogram:
    """Records observations and exposes simple percentile helpers."""

    name: str
    buckets: list[float] = field(
        default_factory=lambda: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    )
    _observations: list[float] = field(default_factory=list)

    def observe(self, value: float) -> None:
        """Record a single observation."""
        self._observations.append(value)

    def mean(self) -> float:
        """Arithmetic mean of observations, or 0.0 if empty."""
        if not self._observations:
            return 0.0
        return sum(self._observations) / len(self._observations)

    def _percentile(self, pct: float) -> float:
        """Return the *pct*-th percentile (0..100), or 0.0 if empty."""
        if not self._observations:
            return 0.0
        s = sorted(self._observations)
        idx = int(len(s) * pct / 100.0)
        idx = min(idx, len(s) - 1)
        return s[idx]

    def p95(self) -> float:
        """95th-percentile latency."""
        return self._percentile(95)

    def p99(self) -> float:
        """99th-percentile latency."""
        return self._percentile(99)

    def count(self) -> int:
        """Number of observations recorded."""
        return len(self._observations)


class MetricsRegistry:
    """Thread-safe registry of named counters and histograms."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}

    def counter(self, name: str, labels: dict | None = None) -> Counter:
        """Return (or create) a :class:`Counter` by *name*."""
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(
                    name=name,
                    labels=labels or {},
                )
            return self._counters[name]

    def histogram(self, name: str) -> Histogram:
        """Return (or create) a :class:`Histogram` by *name*."""
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name=name)
            return self._histograms[name]

    def summary(self) -> dict:
        """Snapshot of all metrics as plain dicts."""
        with self._lock:
            return {
                "counters": {
                    n: {"value": c.value, "labels": c.labels}
                    for n, c in self._counters.items()
                },
                "histograms": {
                    n: {
                        "count": h.count(),
                        "mean": h.mean(),
                        "p95": h.p95(),
                        "p99": h.p99(),
                    }
                    for n, h in self._histograms.items()
                },
            }

    def reset_all(self) -> None:
        """Reset every counter and histogram."""
        with self._lock:
            for c in self._counters.values():
                c.reset()
            for h in self._histograms.values():
                h._observations.clear()


# Module-level default registry
registry: MetricsRegistry = MetricsRegistry()
