"""Language detection and installable parser loading."""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from cogant.parsers import LanguageParserUnavailable
from cogant.parsers import get_parser as registry_get_parser
from cogant.parsers.languages.go import GoLanguageParser
from cogant.parsers.languages.python import PythonLanguageParser
from cogant.parsers.languages.rust import RustLanguageParser
from cogant.parsers.languages.typescript import TypeScriptLanguageParser
from cogant.plugins.base import LanguagePlugin

logger = logging.getLogger(__name__)


class LanguageDetectionError(RuntimeError):
    """Raised when a repository cannot be inspected safely."""


class LanguageDetector:
    """Detect programming languages and instantiate concrete parsers."""

    EXTENSION_MAP: dict[str, str] = {
        ".py": "python",
        ".pyx": "python",
        ".pyi": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".rs": "rust",
        ".go": "go",
    }

    # Compatibility-only view retained for callers that inspected the old
    # class map. Actual selection goes through the capability-aware registry.
    PARSER_CLASSES: dict[str, type[LanguagePlugin]] = {
        "python": PythonLanguageParser,
        "typescript": TypeScriptLanguageParser,
        "javascript": TypeScriptLanguageParser,
        "rust": RustLanguageParser,
        "go": GoLanguageParser,
    }

    @classmethod
    def _lazy_load_parsers(cls) -> None:
        """Refresh the legacy parser-class view through the canonical registry.

        The old implementation imported parser modules on demand and exposed
        a mutable ``PARSER_CLASSES`` table.  Parser selection now belongs to
        :mod:`cogant.parsers.registry`; this compatibility hook keeps callers
        that explicitly triggered the old refresh operation working without
        reviving the deleted duplicate module tree.
        """
        for language in sorted(set(cls.EXTENSION_MAP.values())):
            try:
                parser = registry_get_parser(language)
            except LanguageParserUnavailable as exc:
                logger.debug("Parser %s unavailable during compatibility refresh: %s", language, exc)
                continue
            cls.PARSER_CLASSES[language] = type(parser)

    @staticmethod
    def detect_language(file_path: Path | str) -> str | None:
        """Return the normalized language name for a file extension."""

        return LanguageDetector.EXTENSION_MAP.get(Path(file_path).suffix.lower())

    @staticmethod
    def detect_repo_languages(repo_path: Path | str) -> dict[str, int]:
        """Count supported source files below a repository directory."""

        root = Path(repo_path).expanduser().resolve()
        if not root.is_dir():
            raise LanguageDetectionError(f"Repository directory does not exist: {root}")

        language_counts: dict[str, int] = defaultdict(int)
        for file_path in root.rglob("*"):
            if file_path.is_file():
                language = LanguageDetector.detect_language(file_path)
                if language is not None:
                    language_counts[language] += 1
        return dict(language_counts)

    @classmethod
    def get_parser(cls, language: str) -> LanguagePlugin:
        """Return a parser instance or raise an actionable capability error."""

        try:
            return registry_get_parser(language)
        except LanguageParserUnavailable:
            raise

    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """Return every language with a concrete shipped parser."""

        from cogant.parsers import supported_languages

        return list(supported_languages())


def get_parser_for_extension(ext: str) -> LanguagePlugin | None:
    """Return the parser owning ``ext`` through the canonical registry.

    This ingest-level function is a deprecated compatibility adapter: an
    unknown extension returns ``None`` for legacy callers.  The canonical
    ``cogant.parsers.get_parser_for_extension`` API remains strict and raises
    :class:`LanguageParserUnavailable`, so new ingestion and evidence paths
    cannot silently discard unsupported files.
    """

    normalized = ext.lower()
    if not normalized.startswith("."):
        normalized = f".{normalized}"
    language = LanguageDetector.EXTENSION_MAP.get(normalized)
    if language is None:
        logger.debug("No shipped parser owns extension %s", normalized)
        return None
    try:
        return LanguageDetector.get_parser(language)
    except Exception as exc:  # noqa: BLE001 - legacy adapter preserves None contract
        logger.debug("Parser unavailable for extension %s: %s", normalized, exc)
        return None


__all__ = ["LanguageDetectionError", "LanguageDetector", "get_parser_for_extension"]
