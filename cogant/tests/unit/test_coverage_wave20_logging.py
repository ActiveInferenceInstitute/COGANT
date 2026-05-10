"""Wave-20 coverage tests for cogant.observability.logging.

Targets uncovered branches in setup_logging() — specifically the
structlog ``format="console"`` and ``format="json"`` paths plus the
structlog get_logger() branch. No mocks: real structlog calls; the
import-fallback branch is exercised by direct ImportError simulation
through reload semantics on a copy of the module.
"""

from __future__ import annotations

import importlib
import logging
import sys

import pytest


def test_setup_logging_console_format_configures_structlog():
    """setup_logging(format='console') runs the ConsoleRenderer branch."""
    import cogant.observability.logging as log_mod

    log_mod.setup_logging(level="DEBUG", format="console")
    # Logger from structlog should be returned
    logger = log_mod.get_logger("wave20.console")
    assert logger is not None


def test_setup_logging_json_format_configures_structlog():
    """setup_logging(format='json') runs the JSONRenderer branch."""
    import cogant.observability.logging as log_mod

    log_mod.setup_logging(level="WARNING", format="json")
    logger = log_mod.get_logger("wave20.json")
    assert logger is not None


def test_setup_logging_unknown_format_falls_into_json_branch():
    """Any non-'console' format defaults to JSON renderer."""
    import cogant.observability.logging as log_mod

    log_mod.setup_logging(level="ERROR", format="something-else")
    # Should not raise and should still return a logger
    assert log_mod.get_logger("wave20.unknown") is not None


def test_setup_logging_unknown_level_defaults_to_info():
    """Unknown log levels fall back to INFO via getattr default."""
    import cogant.observability.logging as log_mod

    # Bogus level name; getattr falls back to logging.INFO
    log_mod.setup_logging(level="NOT_A_REAL_LEVEL", format="json")
    assert logging.getLogger().level == logging.INFO


def test_get_logger_returns_logger_with_name():
    """get_logger threads the name through to the underlying lib."""
    from cogant.observability.logging import get_logger

    logger = get_logger("wave20.named")
    assert logger is not None
    # Either structlog BoundLogger or stdlib Logger — both have ``info``
    assert callable(getattr(logger, "info", None))


def test_setup_logging_lowercase_level_string():
    """Level strings are case-insensitive (uppercased internally)."""
    import cogant.observability.logging as log_mod

    log_mod.setup_logging(level="debug", format="json")
    assert logging.getLogger().level == logging.DEBUG


def test_logging_module_fallback_branch_when_structlog_missing(monkeypatch):
    """Reloading the module with structlog hidden hits the ImportError branch.

    Even when structlog is genuinely available, this test forces the
    ImportError path by setting ``sys.modules['structlog'] = None``,
    which causes Python's import machinery to raise ImportError on
    subsequent imports. After the test we restore the original module
    so downstream tests see the original behavior.
    """
    # Block structlog import for a fresh module reload
    real_structlog = sys.modules.pop("structlog", None)
    monkeypatch.setitem(sys.modules, "structlog", None)
    try:
        # Force a fresh import that hits the ImportError branch
        if "cogant.observability.logging" in sys.modules:
            del sys.modules["cogant.observability.logging"]
        fallback_mod = importlib.import_module("cogant.observability.logging")
        assert fallback_mod._STRUCTLOG_AVAILABLE is False

        # Both functions should still work via stdlib fallback
        fallback_mod.setup_logging(level="INFO", format="json")
        logger = fallback_mod.get_logger("wave20.fallback")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "wave20.fallback"
    finally:
        # Restore environment so other tests see normal structlog branch
        if "cogant.observability.logging" in sys.modules:
            del sys.modules["cogant.observability.logging"]
        if real_structlog is not None:
            sys.modules["structlog"] = real_structlog
        importlib.import_module("cogant.observability.logging")


def test_setup_logging_console_then_json_reconfigures():
    """Re-calling setup_logging swaps renderers without raising."""
    import cogant.observability.logging as log_mod

    log_mod.setup_logging(level="INFO", format="console")
    log_mod.setup_logging(level="INFO", format="json")
    log_mod.setup_logging(level="INFO", format="console")


def test_setup_logging_invalid_format_does_not_raise():
    """Empty format string falls into the JSON branch (not 'console')."""
    import cogant.observability.logging as log_mod

    log_mod.setup_logging(level="INFO", format="")


@pytest.mark.parametrize(
    "level",
    ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
)
def test_setup_logging_each_standard_level(level: str):
    """All standard levels should map cleanly through getattr."""
    import cogant.observability.logging as log_mod

    log_mod.setup_logging(level=level, format="json")
    expected = getattr(logging, level)
    assert logging.getLogger().level == expected
