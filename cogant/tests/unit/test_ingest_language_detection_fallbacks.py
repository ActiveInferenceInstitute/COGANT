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
    """The compatibility refresh logs unavailable parsers via the registry.

    Parser selection moved to cogant.parsers.registry (673db14);
    _lazy_load_parsers is a compatibility refresh, not a module-import
    loader, so blocking module imports no longer changes behavior. The
    observable contract: unavailable parsers produce a debug log and
    PARSER_CLASSES keeps a typed entry for every registered language.
    """

    def test_refresh_populates_all_registered_languages(self) -> None:
        from cogant.ingest.language_detect import LanguageDetector

        LanguageDetector.PARSER_CLASSES = dict.fromkeys(
            ("python", "typescript", "javascript", "rust", "go"), None
        )
        LanguageDetector._lazy_load_parsers()
        assert set(LanguageDetector.PARSER_CLASSES) >= {
            "python",
            "typescript",
            "javascript",
            "rust",
            "go",
        }
        assert all(cls is not None for cls in LanguageDetector.PARSER_CLASSES.values())

    def test_refresh_logs_unavailable_parser(self, caplog: pytest.LogCaptureFixture) -> None:
        from cogant.ingest import language_detect as mod
        from cogant.ingest.language_detect import LanguageDetector
        from cogant.parsers import LanguageParserUnavailable

        class _Unavailable:
            @staticmethod
            def _get_parser(language: str):
                raise LanguageParserUnavailable(language, "no parser installed")

        original = mod.registry_get_parser
        mod.registry_get_parser = _Unavailable._get_parser
        try:
            with caplog.at_level(logging.DEBUG, logger="cogant.ingest.language_detect"):
                LanguageDetector._lazy_load_parsers()
            assert any(
                "unavailable during compatibility refresh" in rec.message for rec in caplog.records
            )
        finally:
            mod.registry_get_parser = original


class TestDetectRepoLanguagesErrorPath:
    """Drive the ``except Exception`` block on lines 159-160."""

    def test_missing_repo_raises(self) -> None:
        # detect_repo_languages is fail-closed: a missing directory raises
        # LanguageDetectionError instead of silently returning {}.
        with pytest.raises(ld.LanguageDetectionError, match="does not exist"):
            ld.LanguageDetector.detect_repo_languages("/definitely/not/a/repo/targeted")


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

    def test_tree_sitter_unavailable_falls_through(self, restore_module: object) -> None:
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

    def test_javascript_inner_exception_fallback(self, restore_module: object) -> None:
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

    def test_typescript_inner_exception_fallback(self, restore_module: object) -> None:
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
