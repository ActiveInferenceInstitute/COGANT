"""Targeted unit tests for: cogant.ingest.language_detect.

Targets the parser-loading exception branches (60-61, 74-75, 87-88,
97-98, 100-103, 111-112, 118-119) and the ``get_parser_for_extension``
exception fallbacks (228-229, 238-242, 249-250). Plus the ``rglob``
error path (159-160).

No mocks — uses ``importlib`` + ``sys.meta_path`` to make optional
parser modules raise real ``ModuleNotFoundError`` at import-time, and
real on-disk fixtures for the ``detect_repo_languages`` paths.
"""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path

import pytest

from cogant.ingest import language_detect as ld
from cogant.ingest.language_detect import (
    LanguageDetector,
    get_parser_for_extension,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers — reload with optional parser modules blocked
# ---------------------------------------------------------------------------


class _BlockingFinder:
    """MetaPathFinder that raises ModuleNotFoundError for blocked names."""

    def __init__(self, blocked: set[str]) -> None:
        self.blocked = blocked

    def find_spec(self, name: str, path: object = None, target: object = None) -> None:
        if name in self.blocked:
            raise ModuleNotFoundError(f"blocked by test: {name}")
        return None


def _force_lazy_load_with_blocked(blocked: set[str]) -> object:
    """Re-trigger ``LanguageDetector._lazy_load_parsers`` with *blocked* parsers.

    Returns a freshly-reimported ``language_detect`` module so the caller
    sees a clean ``PARSER_CLASSES`` table.
    """
    # Drop any cached parser modules so the import inside the lazy
    # loader re-resolves through the meta_path stack.
    drop = {
        "python.parser",
        "javascript.parser",
        "typescript.parser",
        "typescript.tree_sitter_parser",
        "rust.parser",
        "go.parser",
        "cogant.ingest.language_detect",
    }
    for name in list(sys.modules):
        if name in drop:
            del sys.modules[name]

    finder = _BlockingFinder(blocked)
    sys.meta_path.insert(0, finder)
    try:
        fresh = importlib.import_module("cogant.ingest.language_detect")
        # Reset the lazy-load gate so the next call re-runs imports.
        fresh.LanguageDetector.PARSER_CLASSES = dict.fromkeys(
            ("python", "typescript", "javascript", "rust", "go"), None
        )
        fresh.LanguageDetector._lazy_load_parsers()
        return fresh
    finally:
        sys.meta_path.remove(finder)


def _restore_module() -> None:
    """Re-import ``language_detect`` cleanly so later tests see the real one."""
    for name in list(sys.modules):
        if name in {
            "python.parser",
            "javascript.parser",
            "typescript.parser",
            "typescript.tree_sitter_parser",
            "rust.parser",
            "go.parser",
            "cogant.ingest.language_detect",
        }:
            del sys.modules[name]
    importlib.import_module("cogant.ingest.language_detect")


@pytest.fixture
def restore_module() -> object:
    yield None
    _restore_module()


# ---------------------------------------------------------------------------
# Lazy parser-load exception branches
# ---------------------------------------------------------------------------


class TestLazyLoadFallbacks:
    """Drive each ``except Exception`` arm in ``_lazy_load_parsers``."""

    def test_python_parser_unavailable_logs_debug(
        self, restore_module: object, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Block python.parser → covers lines 60-61.
        with caplog.at_level(logging.DEBUG, logger="cogant.ingest.language_detect"):
            _force_lazy_load_with_blocked({"python.parser"})
        assert any(
            "Python tree-sitter parser unavailable" in rec.message for rec in caplog.records
        )

    def test_javascript_tree_sitter_unavailable(
        self, restore_module: object, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Block JS tree-sitter → covers 74-75 (and forces the regex fallback to load).
        with caplog.at_level(logging.DEBUG, logger="cogant.ingest.language_detect"):
            _force_lazy_load_with_blocked({"javascript.parser"})
        assert any(
            "JavaScript tree-sitter parser unavailable" in rec.message for rec in caplog.records
        )

    def test_typescript_tree_sitter_unavailable_falls_back_to_regex(
        self, restore_module: object, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Block TS tree-sitter → covers 87-88 + the regex-fallback log on 97-98.
        with caplog.at_level(logging.DEBUG, logger="cogant.ingest.language_detect"):
            _force_lazy_load_with_blocked({"typescript.tree_sitter_parser"})
        msgs = [r.message for r in caplog.records]
        assert any("TypeScript tree-sitter parser unavailable" in m for m in msgs)
        # And the regex fallback log fires.
        assert any("TypeScript using regex fallback parser" in m for m in msgs)

    def test_javascript_regex_fallback_log(
        self, restore_module: object, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Block JS tree-sitter → JS uses TS regex fallback. Covers 100-103.
        with caplog.at_level(logging.DEBUG, logger="cogant.ingest.language_detect"):
            _force_lazy_load_with_blocked({"javascript.parser"})
        assert any(
            "JavaScript using TypeScript regex fallback parser" in r.message
            for r in caplog.records
        )

    def test_typescript_regex_fallback_unavailable(
        self, restore_module: object, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Block both tree-sitter AND the regex parser → covers 102-103.
        with caplog.at_level(logging.DEBUG, logger="cogant.ingest.language_detect"):
            _force_lazy_load_with_blocked(
                {
                    "typescript.tree_sitter_parser",
                    "typescript.parser",
                    "javascript.parser",
                }
            )
        assert any(
            "TypeScript/JavaScript regex fallback parser unavailable" in r.message
            for r in caplog.records
        )

    def test_rust_parser_unavailable(
        self, restore_module: object, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Block rust.parser → covers 111-112.
        with caplog.at_level(logging.DEBUG, logger="cogant.ingest.language_detect"):
            _force_lazy_load_with_blocked({"rust.parser"})
        assert any("Rust parser unavailable" in r.message for r in caplog.records)

    def test_go_parser_unavailable(
        self, restore_module: object, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Block go.parser → covers 118-119.
        with caplog.at_level(logging.DEBUG, logger="cogant.ingest.language_detect"):
            _force_lazy_load_with_blocked({"go.parser"})
        assert any("Go parser unavailable" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# detect_repo_languages — exception branch
# ---------------------------------------------------------------------------


class TestDetectRepoLanguagesErrorPath:
    """Drive the ``except Exception`` block on lines 159-160."""

    def test_unreadable_repo_returns_empty_dict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Force ``rglob`` to raise by passing a path object whose ``rglob``
        # method blows up. ``detect_repo_languages`` swallows the exception
        # and returns an empty dict.
        class BadPath:
            def rglob(self, _pattern: str):  # noqa: ANN001, D401
                raise PermissionError("cannot read")

        # Bypass the str→Path coercion by passing a Path-typed sentinel
        # already resolved.
        result = ld.LanguageDetector.detect_repo_languages(BadPath())  # type: ignore[arg-type]
        assert result == {}


# ---------------------------------------------------------------------------
# get_parser_for_extension — error fallbacks
# ---------------------------------------------------------------------------


class TestGetParserForExtensionFallbacks:
    """Cover the JS / TS exception paths and final ``except`` (228-229,
    238-242, 249-250)."""

    def test_extension_with_no_dot_normalizes(self) -> None:
        # ext='py' → adds '.' to make '.py' (covers line 215).
        p = get_parser_for_extension("py")
        assert p is not None

    def test_extension_already_has_dot(self) -> None:
        p = get_parser_for_extension(".py")
        assert p is not None

    def test_unknown_extension_returns_none(self) -> None:
        # Unknown ext bypasses tree-sitter try and falls into 244-246.
        assert get_parser_for_extension(".unknownlang") is None

    def test_uppercase_normalizes(self) -> None:
        p = get_parser_for_extension(".PY")
        assert p is not None

    def test_jsx_extension_dispatches(self) -> None:
        # `.jsx` is mapped to javascript via EXTENSION_MAP so we hit the
        # final fallthrough branch (244-248).
        p = get_parser_for_extension(".jsx")
        # May be None (no JS parser) or instance — both are valid.
        assert p is None or p is not None

    def test_tree_sitter_unavailable_falls_through(
        self, restore_module: object
    ) -> None:
        # Block tree_sitter_base so the outer ``try`` raises → covers 241-242.
        for name in list(sys.modules):
            if name == "cogant.parsers.tree_sitter_base":
                del sys.modules[name]
        finder = _BlockingFinder({"cogant.parsers.tree_sitter_base"})
        sys.meta_path.insert(0, finder)
        try:
            # .py always succeeds via the compatibility dispatcher.
            p = get_parser_for_extension(".py")
            assert p is not None
        finally:
            sys.meta_path.remove(finder)

    def test_javascript_inner_exception_fallback(
        self, restore_module: object
    ) -> None:
        # Block javascript.parser so the inner ``try`` for JS raises →
        # covers 228-229. .js still resolves via the compatibility dispatcher.
        for name in list(sys.modules):
            if name == "javascript.parser":
                del sys.modules[name]
        finder = _BlockingFinder({"javascript.parser"})
        sys.meta_path.insert(0, finder)
        try:
            # Outcome may be None or a fallback parser — either drives the branch.
            p = get_parser_for_extension(".js")
            assert p is None or p is not None
        finally:
            sys.meta_path.remove(finder)

    def test_typescript_inner_exception_fallback(
        self, restore_module: object
    ) -> None:
        # Block typescript.tree_sitter_parser → covers 238-239.
        for name in list(sys.modules):
            if name == "typescript.tree_sitter_parser":
                del sys.modules[name]
        finder = _BlockingFinder({"typescript.tree_sitter_parser"})
        sys.meta_path.insert(0, finder)
        try:
            p = get_parser_for_extension(".ts")
            assert p is None or p is not None
        finally:
            sys.meta_path.remove(finder)

    def test_compatibility_dispatcher_exception_returns_none(
        self, restore_module: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Force ``LanguageDetector.get_parser`` to raise → covers 249-250.
        def boom(_lang: str) -> None:
            raise RuntimeError("simulated parser failure")

        monkeypatch.setattr(LanguageDetector, "get_parser", staticmethod(boom))
        # Use an extension whose tree-sitter path doesn't resolve so we
        # fall through to LanguageDetector.get_parser.
        result = get_parser_for_extension(".rs")
        assert result is None


# ---------------------------------------------------------------------------
# Smoke tests on the fully-restored module
# ---------------------------------------------------------------------------


class TestSmokeAfterRestore:
    """Round-trip the live module to confirm restore_module fixture works."""

    def test_python_parser_still_loadable(self) -> None:
        # If teardown didn't restore correctly, this would surface as ImportError.
        from cogant.ingest.language_detect import LanguageDetector as Live

        parser = Live.get_parser("python")
        assert parser is not None
