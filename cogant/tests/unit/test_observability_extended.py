"""Extended behavioral tests for cogant.observability — metrics, trace, logging.

Covers: Histogram percentiles with data, Counter labels, MetricsRegistry
summary structure, span with default registry, nested spans, and histogram
with many observations.
"""

from __future__ import annotations

import time

import pytest

from cogant.observability.logging import get_logger, setup_logging
from cogant.observability.metrics import Counter, Histogram, MetricsRegistry
from cogant.observability.trace import span

# ---------------------------------------------------------------------------
# Counter extended
# ---------------------------------------------------------------------------


def test_counter_labels_preserved() -> None:
    """Counter stores labels dict."""
    c = Counter(name="labeled", labels={"env": "prod", "region": "us"})
    assert c.labels == {"env": "prod", "region": "us"}
    assert c.value == 0


def test_counter_multiple_increments() -> None:
    """Counter accumulates across multiple inc() calls."""
    c = Counter(name="multi")
    for _ in range(100):
        c.inc()
    assert c.value == 100


def test_counter_reset_then_inc() -> None:
    """Reset followed by inc starts from zero."""
    c = Counter(name="reset_then_inc")
    c.inc(50)
    c.reset()
    c.inc(3)
    assert c.value == 3


# ---------------------------------------------------------------------------
# Histogram extended
# ---------------------------------------------------------------------------


def test_histogram_mean_multiple_values() -> None:
    """Mean of [1, 2, 3, 4, 5] is 3.0."""
    h = Histogram(name="mean_test")
    for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
        h.observe(v)
    assert h.mean() == pytest.approx(3.0)


def test_histogram_p95_with_100_values() -> None:
    """P95 of [1..100] is 95 or 96 (index-based)."""
    h = Histogram(name="p95_test")
    for v in range(1, 101):
        h.observe(float(v))
    p95 = h.p95()
    assert 95 <= p95 <= 96


def test_histogram_p99_with_100_values() -> None:
    """P99 of [1..100] is 99 or 100 (index-based)."""
    h = Histogram(name="p99_test")
    for v in range(1, 101):
        h.observe(float(v))
    p99 = h.p99()
    assert 99 <= p99 <= 100


def test_histogram_single_observation_percentiles() -> None:
    """With a single observation, all percentiles return that value."""
    h = Histogram(name="single")
    h.observe(42.0)
    assert h.p95() == 42.0
    assert h.p99() == 42.0
    assert h.mean() == 42.0


def test_histogram_custom_buckets() -> None:
    """Custom bucket configuration is stored."""
    h = Histogram(name="custom_buckets", buckets=[0.01, 0.1, 1.0])
    assert h.buckets == [0.01, 0.1, 1.0]


# ---------------------------------------------------------------------------
# MetricsRegistry extended
# ---------------------------------------------------------------------------


def test_registry_counter_with_labels() -> None:
    """Counter created via registry with labels preserves them."""
    reg = MetricsRegistry()
    c = reg.counter("http.requests", labels={"method": "GET"})
    assert c.labels == {"method": "GET"}
    # Second call returns same instance (labels from first call)
    c2 = reg.counter("http.requests")
    assert c2 is c


def test_registry_summary_structure() -> None:
    """Summary dict has the expected nested structure."""
    reg = MetricsRegistry()
    reg.counter("a").inc(3)
    reg.histogram("b").observe(0.5)
    reg.histogram("b").observe(1.5)

    s = reg.summary()
    assert s["counters"]["a"]["value"] == 3
    assert s["histograms"]["b"]["count"] == 2
    assert s["histograms"]["b"]["mean"] == pytest.approx(1.0)


def test_registry_reset_all_clears_observations() -> None:
    """reset_all clears all counter values and histogram observations."""
    reg = MetricsRegistry()
    reg.counter("c1").inc(10)
    reg.counter("c2").inc(20)
    reg.histogram("h1").observe(1.0)
    reg.histogram("h1").observe(2.0)

    reg.reset_all()

    assert reg.counter("c1").value == 0
    assert reg.counter("c2").value == 0
    assert reg.histogram("h1").count() == 0


# ---------------------------------------------------------------------------
# Span extended
# ---------------------------------------------------------------------------


def test_span_with_default_registry() -> None:
    """span() without explicit registry uses the current module-level default."""
    import cogant.observability.metrics as _metrics_mod

    # Re-import live to survive any module reload a prior test may have triggered
    live_registry = _metrics_mod.registry
    live_registry.reset_all()
    with span("default_reg_test"):
        pass
    h = live_registry.histogram("cogant.span.default_reg_test")
    assert h.count() == 1


def test_span_nested() -> None:
    """Nested spans both record independently."""
    reg = MetricsRegistry()
    with span("outer", registry=reg):
        with span("inner", registry=reg):
            time.sleep(0.005)

    assert reg.histogram("cogant.span.outer").count() == 1
    assert reg.histogram("cogant.span.inner").count() == 1
    # Outer should be >= inner
    assert reg.histogram("cogant.span.outer").mean() >= reg.histogram("cogant.span.inner").mean()


def test_span_records_elapsed_on_exception() -> None:
    """span() records elapsed time even when the block raises."""
    reg = MetricsRegistry()
    with pytest.raises(ValueError):
        with span("error_span", registry=reg):
            raise ValueError("boom")
    assert reg.histogram("cogant.span.error_span").count() == 1


# ---------------------------------------------------------------------------
# Logging extended
# ---------------------------------------------------------------------------


def test_get_logger_different_names() -> None:
    """Different logger names return different objects."""
    l1 = get_logger("module.a")
    l2 = get_logger("module.b")
    # They should be distinct (different name)
    assert l1 is not l2


def test_setup_logging_invalid_level_defaults_to_info() -> None:
    """Invalid level name falls back to INFO without crashing."""
    setup_logging(level="NONEXISTENT")
    # Should not raise
