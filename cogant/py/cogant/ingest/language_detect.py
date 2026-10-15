"""Language detection and installable parser loading."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from cogant.parsers import get_parser as registry_get_parser
from cogant.plugins.base import LanguagePlugin


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

        return registry_get_parser(language)

    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """Return every language with a concrete shipped parser."""

        from cogant.parsers import supported_languages

        return list(supported_languages())


__all__ = ["LanguageDetectionError", "LanguageDetector"]
