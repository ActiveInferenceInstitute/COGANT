"""Structured logging with optional structlog integration.

Falls back gracefully to stdlib :mod:`logging` when *structlog* is not
installed.
"""

from __future__ import annotations

import logging
from typing import Any

_STRUCTLOG_AVAILABLE = False
try:
    import structlog  # type: ignore[import-untyped,import-not-found,unused-ignore]

    _STRUCTLOG_AVAILABLE = True
except ImportError:
    pass


def setup_logging(level: str = "INFO", format: str = "json") -> None:
    """Configure the logging subsystem.

    Parameters
    ----------
    level:
        Standard Python log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    format:
        ``"json"`` for machine-readable output, ``"console"`` for
        human-friendly coloured output (structlog only).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    if _STRUCTLOG_AVAILABLE:
        processors: list[Any] = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
        if format == "console":
            processors.append(structlog.dev.ConsoleRenderer())
        else:
            processors.append(structlog.processors.JSONRenderer())

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    logging.basicConfig(level=numeric_level, force=True)


def get_logger(name: str) -> Any:
    """Return a logger for *name*.

    Uses structlog if available, otherwise falls back to
    :func:`logging.getLogger`.
    """
    if _STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    return logging.getLogger(name)
