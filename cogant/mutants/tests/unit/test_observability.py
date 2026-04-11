"""Tests for cogant.observability — structured logging + in-process metrics."""

from __future__ import annotations

import time

import pytest

# ---------------------------------------------------------------------------
# Counter
# ---------------------------------------------------------------------------

def test_counter_starts_at_zero():
    from cogant.observability.metrics import Counter
    c = Counter(name="test.counter")
    assert c.value == 0


def test_counter_inc_by_default():
    from cogant.observability.metrics import Counter
    c = Counter(name="test.counter")
    c.inc()
    assert c.value == 1


def test_counter_inc_by_n():
    from cogant.observability.metrics import Counter
    c = Counter(name="test.counter")
    c.inc(5)
    assert c.value == 5
    c.inc(3)
    assert c.value == 8


def test_counter_reset():
    from cogant.observability.metrics import Counter
    c = Counter(name="test.counter")
    c.inc(10)
    c.reset()
    assert c.value == 0


# ---------------------------------------------------------------------------
# Histogram
# ---------------------------------------------------------------------------

def test_histogram_observe_count():
    from cogant.observability.metrics import Histogram
    h = Histogram(name="test.hist")
    h.observe(0.1)
    h.observe(0.2)
    h.observe(0.3)
    assert h.count() == 3


def test_histogram_mean_single_observation():
    from cogant.observability.metrics import Histogram
    h = Histogram(name="test.hist")
    h.observe(4.0)
    assert h.mean() == pytest.approx(4.0)


def test_histogram_p95_empty_returns_zero():
    from cogant.observability.metrics import Histogram
    h = Histogram(name="test.hist")
    assert h.p95() == 0.0
    assert h.p99() == 0.0
    assert h.mean() == 0.0


# ---------------------------------------------------------------------------
# MetricsRegistry
# ---------------------------------------------------------------------------

def test_metrics_registry_counter_returns_same_instance():
    from cogant.observability.metrics import MetricsRegistry
    reg = MetricsRegistry()
    c1 = reg.counter("req.total")
    c2 = reg.counter("req.total")
    assert c1 is c2


def test_metrics_registry_histogram_returns_same_instance():
    from cogant.observability.metrics import MetricsRegistry
    reg = MetricsRegistry()
    h1 = reg.histogram("latency")
    h2 = reg.histogram("latency")
    assert h1 is h2


def test_metrics_registry_summary_has_keys():
    from cogant.observability.metrics import MetricsRegistry
    reg = MetricsRegistry()
    reg.counter("a").inc()
    reg.histogram("b").observe(1.0)
    s = reg.summary()
    assert "counters" in s
    assert "histograms" in s
    assert "a" in s["counters"]
    assert "b" in s["histograms"]


def test_metrics_registry_reset_all():
    from cogant.observability.metrics import MetricsRegistry
    reg = MetricsRegistry()
    reg.counter("x").inc(5)
    reg.histogram("y").observe(1.0)
    reg.reset_all()
    assert reg.counter("x").value == 0
    assert reg.histogram("y").count() == 0


# ---------------------------------------------------------------------------
# Module-level registry
# ---------------------------------------------------------------------------

def test_module_level_registry_exists():
    from cogant.observability.metrics import MetricsRegistry, registry
    assert isinstance(registry, MetricsRegistry)


# ---------------------------------------------------------------------------
# span() context manager
# ---------------------------------------------------------------------------

def test_span_context_manager_records_histogram():
    from cogant.observability.metrics import MetricsRegistry
    from cogant.observability.trace import span
    reg = MetricsRegistry()
    with span("test_op", registry=reg):
        time.sleep(0.01)
    h = reg.histogram("cogant.span.test_op")
    assert h.count() == 1
    assert h.mean() > 0.0


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def test_get_logger_returns_something():
    from cogant.observability.logging import get_logger
    logger = get_logger("test")
    assert logger is not None


def test_setup_logging_does_not_raise():
    from cogant.observability.logging import setup_logging
    setup_logging(level="DEBUG", format="console")
    setup_logging(level="INFO", format="json")


# ---------------------------------------------------------------------------
# Package-level exports
# ---------------------------------------------------------------------------

def test_package_exports():
    from cogant.observability import (
        get_logger,
        setup_logging,
    )
    assert callable(get_logger)
    assert callable(setup_logging)
