"""Canonical language parser registry.

The registry is deliberately explicit: a language is either backed by a
concrete parser or reported as unavailable with a reason.  Import failures
are never converted into an empty parser list.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cogant.plugins.base import LanguagePlugin


class LanguageParserUnavailable(ImportError, RuntimeError):
    """Raised when a requested language has no usable parser.

    ``ImportError`` is retained as a compatibility base for callers of the
    pre-registry parser loader.  The concrete exception still carries the
    structured ``language`` and ``reason`` fields needed by the canonical
    capability-aware API.
    """

    def __init__(self, language: str, reason: str) -> None:
        self.language = language
        self.reason = reason
        super().__init__(f"No parser available for {language!r}: {reason}")


@dataclass(frozen=True)
class ParserCapability:
    """Description of a registered parser capability."""

    language: str
    extensions: tuple[str, ...]
    implementation: str
    optional_dependency: str | None = None
    fallback_implementation: str | None = None


@dataclass(frozen=True)
class _ParserSpec:
    capability: ParserCapability
    factory: Callable[[], LanguagePlugin]


def _specs() -> tuple[_ParserSpec, ...]:
    from cogant.parsers.languages.go import GoLanguageParser
    from cogant.parsers.languages.javascript import JavaScriptLanguageParser
    from cogant.parsers.languages.python import PythonLanguageParser
    from cogant.parsers.languages.rust import RustLanguageParser
    from cogant.parsers.languages.typescript import (
        TypeScriptLanguageParser,
        TypeScriptTreeSitterParser,
    )

    def tree_sitter_or_fallback(
        language: str,
        preferred: Callable[[], LanguagePlugin],
        fallback: Callable[[], LanguagePlugin],
    ) -> Callable[[], LanguagePlugin]:
        """Choose a grammar-backed parser only when its grammar is loaded."""

        def factory() -> LanguagePlugin:
            try:
                from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

                if language in get_tree_sitter_parser().available_languages():
                    return preferred()
            except Exception:
                # Optional grammar loading must never make the compatibility
                # parser unavailable on a minimal installation.
                pass
            return fallback()

        return factory

    return (
        _ParserSpec(
            ParserCapability("python", (".py", ".pyi", ".pyx"), "cpython-ast"),
            PythonLanguageParser,
        ),
        _ParserSpec(
            ParserCapability(
                "javascript",
                (".js", ".jsx", ".mjs", ".cjs"),
                "tree-sitter-preferred",
                optional_dependency="cogant[multilang]",
                fallback_implementation="regex-structural",
            ),
            tree_sitter_or_fallback("javascript", JavaScriptLanguageParser, TypeScriptLanguageParser),
        ),
        _ParserSpec(
            ParserCapability(
                "typescript",
                (".ts", ".tsx"),
                "tree-sitter-preferred",
                optional_dependency="cogant[multilang]",
                fallback_implementation="regex-structural",
            ),
            tree_sitter_or_fallback("typescript", TypeScriptTreeSitterParser, TypeScriptLanguageParser),
        ),
        _ParserSpec(
            ParserCapability("rust", (".rs",), "regex-structural"),
            RustLanguageParser,
        ),
        _ParserSpec(
            ParserCapability("go", (".go",), "regex-structural"),
            GoLanguageParser,
        ),
    )


def parser_capabilities() -> dict[str, ParserCapability]:
    """Return all concrete parser capabilities keyed by language."""

    return {spec.capability.language: spec.capability for spec in _specs()}


def parser_capability_report() -> dict[str, dict[str, object]]:
    """Return active parser modes and explicit degradation reasons.

    Static capabilities describe the installable contract; this report also
    probes optional tree-sitter grammars so exported evidence can distinguish
    grammar-backed parsing from the deterministic structural fallback.
    """
    capabilities = parser_capabilities()
    try:
        from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

        available = set(get_tree_sitter_parser().available_languages())
        probe_error: str | None = None
    except Exception as exc:  # pragma: no cover - optional dependency boundary
        available = set()
        probe_error = f"{type(exc).__name__}: {exc}"

    report: dict[str, dict[str, object]] = {}
    for language, capability in sorted(capabilities.items()):
        grammar_backed = (
            capability.fallback_implementation is not None
            and language in available
        )
        active = capability.implementation if grammar_backed else (
            capability.fallback_implementation or capability.implementation
        )
        degraded = capability.fallback_implementation is not None and not grammar_backed
        report[language] = {
            "language": language,
            "extensions": list(capability.extensions),
            "declared_implementation": capability.implementation,
            "active_implementation": active,
            "fallback_implementation": capability.fallback_implementation,
            "optional_dependency": capability.optional_dependency,
            "grammar_available": grammar_backed,
            "degraded": degraded,
            "reason": (
                "optional grammar unavailable"
                if degraded and probe_error is None
                else probe_error
                if degraded
                else None
            ),
        }
    return report


def supported_languages() -> tuple[str, ...]:
    """Return the sorted installable language identifiers."""

    return tuple(sorted(parser_capabilities()))


def get_parser(language: str) -> LanguagePlugin:
    """Instantiate the concrete parser for ``language``.

    ``LanguageParserUnavailable`` includes the requested language and the
    supported set, so CLI/API callers can expose an actionable error.
    """

    normalized = language.strip().lower()
    for spec in _specs():
        if normalized == spec.capability.language:
            return spec.factory()
    available = ", ".join(sorted(parser_capabilities()))
    raise LanguageParserUnavailable(normalized, f"supported languages are: {available}")


def get_parser_for_extension(extension: str) -> LanguagePlugin:
    """Instantiate the parser that owns ``extension``."""

    normalized = extension.lower()
    if not normalized.startswith("."):
        normalized = f".{normalized}"
    for capability in parser_capabilities().values():
        if normalized in capability.extensions:
            return get_parser(capability.language)
    raise LanguageParserUnavailable(normalized, "no parser owns this extension")


__all__ = [
    "LanguageParserUnavailable",
    "ParserCapability",
    "get_parser",
    "get_parser_for_extension",
    "parser_capability_report",
    "parser_capabilities",
    "supported_languages",
]
