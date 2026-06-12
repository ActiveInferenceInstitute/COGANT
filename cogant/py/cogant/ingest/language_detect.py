"""Language detection and parser loading."""

import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Add parsers to path
parsers_root = Path(__file__).parent.parent.parent.parent / "parsers"
sys.path.insert(0, str(parsers_root))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "py"))


class LanguageDetector:
    """Detect programming languages in a repository."""

    # Map file extensions to language names
    EXTENSION_MAP = {
        ".py": "python",
        ".pyx": "python",
        ".pyi": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".rs": "rust",
        ".go": "go",
    }

    # Map language names to parser classes
    PARSER_CLASSES = {
        "python": None,  # Lazy-loaded
        "typescript": None,
        "javascript": None,
        "rust": None,
        "go": None,
    }

    @classmethod
    def _lazy_load_parsers(cls) -> None:
        """Lazy load parser classes on first use.

        Prefers the new tree-sitter backed plugins for JavaScript and
        TypeScript when the ``tree-sitter`` runtime + grammars are
        installed, and falls back to the regex-plugin
        ``TypeScriptLanguageParser`` otherwise.
        """
        if cls.PARSER_CLASSES["python"] is not None:
            return  # Already loaded

        try:
            from python.parser import (
                PythonLanguageParser,  # type: ignore[import-not-found,unused-ignore]
            )

            cls.PARSER_CLASSES["python"] = PythonLanguageParser
        except Exception as exc:
            logger.debug(
                "Python tree-sitter parser unavailable; CPython ast fallback active: %s", exc
            )

        # Prefer tree-sitter for JavaScript; fall back to the TS regex parser.
        js_loaded = False
        try:
            from javascript.parser import (
                JavaScriptLanguageParser,  # type: ignore[import-not-found,unused-ignore]
            )

            cls.PARSER_CLASSES["javascript"] = JavaScriptLanguageParser
            js_loaded = True
        except Exception as exc:
            logger.debug("JavaScript tree-sitter parser unavailable: %s", exc)

        # Prefer tree-sitter for TypeScript when available.
        ts_loaded = False
        try:
            from typescript.tree_sitter_parser import (
                TypeScriptTreeSitterParser,  # type: ignore[import-not-found,unused-ignore]
            )

            if TypeScriptTreeSitterParser is not None:
                cls.PARSER_CLASSES["typescript"] = TypeScriptTreeSitterParser
                ts_loaded = True
        except Exception as exc:
            logger.debug("TypeScript tree-sitter parser unavailable: %s", exc)

        # Regex fallback for either JS or TS that didn't get a tree-sitter plugin.
        try:
            from typescript.parser import (
                TypeScriptLanguageParser,  # type: ignore[import-not-found,unused-ignore]
            )

            if not ts_loaded:
                cls.PARSER_CLASSES["typescript"] = TypeScriptLanguageParser
                logger.debug("TypeScript using regex fallback parser")
            if not js_loaded:
                cls.PARSER_CLASSES["javascript"] = TypeScriptLanguageParser
                logger.debug("JavaScript using TypeScript regex fallback parser")
        except Exception as exc:
            logger.debug("TypeScript/JavaScript regex fallback parser unavailable: %s", exc)

        try:
            from rust.parser import (
                RustLanguageParser,  # type: ignore[import-not-found,unused-ignore]
            )

            cls.PARSER_CLASSES["rust"] = RustLanguageParser
        except Exception as exc:
            logger.debug("Rust parser unavailable: %s", exc)

        try:
            from go.parser import GoLanguageParser  # type: ignore[import-not-found,unused-ignore]

            cls.PARSER_CLASSES["go"] = GoLanguageParser
        except Exception as exc:
            logger.debug("Go parser unavailable: %s", exc)

    @staticmethod
    def detect_language(file_path: Path) -> str | None:
        """Detect programming language from file extension.

        Args:
            file_path: Path to file.

        Returns:
            Language name or None if not recognized.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        ext = file_path.suffix.lower()
        return LanguageDetector.EXTENSION_MAP.get(ext)

    @staticmethod
    def detect_repo_languages(repo_path: Path) -> dict[str, int]:
        """Detect all programming languages in a repository.

        Args:
            repo_path: Path to repository root.

        Returns:
            Dictionary mapping language names to file counts.
        """
        if isinstance(repo_path, str):
            repo_path = Path(repo_path)

        language_counts: dict[str, int] = defaultdict(int)

        # Iterate through all files recursively
        try:
            for file_path in repo_path.rglob("*"):
                if file_path.is_file():
                    lang = LanguageDetector.detect_language(file_path)
                    if lang:
                        language_counts[lang] += 1
        except Exception as exc:
            logger.warning("Failed while scanning %s for languages: %s", repo_path, exc)

        return dict(language_counts)

    @classmethod
    def get_parser(cls, language: str) -> Any:
        """Get parser instance for a language.

        Args:
            language: Language name (e.g., "python", "typescript").

        Returns:
            LanguagePlugin instance or None if language not supported.

        Raises:
            ImportError: If parser module cannot be loaded.
        """
        cls._lazy_load_parsers()

        parser_class = cls.PARSER_CLASSES.get(language.lower())
        if parser_class is None:
            raise ImportError(f"No parser available for language: {language}")

        return parser_class()

    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """Get list of supported languages.

        Returns:
            List of supported language names.
        """
        cls._lazy_load_parsers()
        supported: list[str] = []
        for lang, parser_class in cls.PARSER_CLASSES.items():
            if parser_class is not None:
                supported.append(lang)
        return supported


def get_parser_for_extension(ext: str) -> Any:
    """Return a LanguagePlugin instance suitable for a file extension.

    Prefers tree-sitter backed plugins when the corresponding grammar is
    installed, and falls back to the regex plugins otherwise.

    Args:
        ext: File extension, e.g. ``.py``, ``.ts``, ``.js``.

    Returns:
        A :class:`cogant.plugins.base.LanguagePlugin` instance, or
        ``None`` if no parser is registered for the extension.
    """
    ext = (ext or "").lower()
    if not ext.startswith("."):
        ext = f".{ext}"

    try:
        from cogant.parsers.tree_sitter_base import get_tree_sitter_parser

        ts = get_tree_sitter_parser()
        if ext in ts.supported_extensions():
            language = ts.language_for_path(Path(f"x{ext}"))
            if language == "javascript":
                try:
                    from javascript.parser import JavaScriptLanguageParser

                    return JavaScriptLanguageParser()
                except Exception:
                    pass
            if language in ("typescript", "tsx"):
                try:
                    from typescript.tree_sitter_parser import (
                        TypeScriptTreeSitterParser,
                    )

                    if TypeScriptTreeSitterParser is not None:
                        return TypeScriptTreeSitterParser()
                except Exception:
                    pass
            # python / rust / go — fall through to the regex-plugin dispatcher
    except Exception:
        pass

    language = LanguageDetector.EXTENSION_MAP.get(ext)
    if language is None:
        return None
    try:
        return LanguageDetector.get_parser(language)
    except Exception:
        return None
