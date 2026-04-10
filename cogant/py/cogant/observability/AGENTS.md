# Agents — py/cogant/observability

## Owner

Runtime Lead

## Responsibilities

Structured logging (`get_logger`, `setup_logging` with optional structlog), in-process metrics (`Counter`, `Histogram`, `MetricsRegistry`, module `registry`). Span helpers live in `trace.py` for modules that import them explicitly.

## Coordination

Cross-cutting: ingest, pipeline, server, and CLI should use `get_logger` rather than ad hoc prints. Metrics integrate with dashboards and health checks where enabled.

## Files

- `logging.py` — `setup_logging`, `get_logger`.
- `metrics.py` — counters, histograms, `MetricsRegistry`.
- `trace.py` — span/trace helpers (see module for public names).
- `__init__.py` — public exports.
