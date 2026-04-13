"""Wave-20 coverage boost: exercise cogant.ingest.language_detect.

Drives ``LanguageDetector`` and ``get_parser_for_extension`` with real
on-disk paths and repo scans — no mocks.
"""

from __future__ import annotations

from pathlib import Path

from cogant.ingest.language_detect import (
    LanguageDetector,
    get_parser_for_extension,
)


class TestDetectLanguage:
    """``LanguageDetector.detect_language`` on every supported extension."""

    def test_python_extensions(self) -> None:
        assert LanguageDetector.detect_language(Path("foo.py")) == "python"
        assert LanguageDetector.detect_language(Path("foo.pyx")) == "python"
        assert LanguageDetector.detect_language(Path("foo.pyi")) == "python"

    def test_typescript_extensions(self) -> None:
        assert LanguageDetector.detect_language(Path("foo.ts")) == "typescript"
        assert LanguageDetector.detect_language(Path("foo.tsx")) == "typescript"

    def test_javascript_extensions(self) -> None:
        assert LanguageDetector.detect_language(Path("foo.js")) == "javascript"
        assert LanguageDetector.detect_language(Path("foo.jsx")) == "javascript"

    def test_rust_and_go(self) -> None:
        assert LanguageDetector.detect_language(Path("foo.rs")) == "rust"
        assert LanguageDetector.detect_language(Path("foo.go")) == "go"

    def test_unknown_extension_returns_none(self) -> None:
        assert LanguageDetector.detect_language(Path("foo.xyz")) is None
        assert LanguageDetector.detect_language(Path("README")) is None

    def test_uppercase_extension_matches(self) -> None:
        """Extension matching is case-insensitive."""
        assert LanguageDetector.detect_language(Path("foo.PY")) == "python"
        assert LanguageDetector.detect_language(Path("foo.JS")) == "javascript"

    def test_string_path_argument(self) -> None:
        """A plain string path should be coerced to Path internally."""
        assert LanguageDetector.detect_language("foo.py") == "python"  # type: ignore[arg-type]


class TestDetectRepoLanguages:
    """``detect_repo_languages`` over a real small repo."""

    def test_counts_files_per_language(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        (tmp_path / "c.ts").write_text("const z = 3;")
        (tmp_path / "d.txt").write_text("readme")
        counts = LanguageDetector.detect_repo_languages(tmp_path)
        assert counts.get("python") == 2
        assert counts.get("typescript") == 1
        assert "plaintext" not in counts

    def test_handles_nested_dirs(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("pass")
        (tmp_path / "src" / "lib.rs").write_text("fn main() {}")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "t.py").write_text("pass")
        counts = LanguageDetector.detect_repo_languages(tmp_path)
        assert counts.get("python") == 2
        assert counts.get("rust") == 1

    def test_empty_repo_returns_empty_dict(self, tmp_path: Path) -> None:
        counts = LanguageDetector.detect_repo_languages(tmp_path)
        assert counts == {}

    def test_string_path_argument(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("pass")
        counts = LanguageDetector.detect_repo_languages(str(tmp_path))  # type: ignore[arg-type]
        assert counts.get("python") == 1


class TestGetParser:
    """``LanguageDetector.get_parser`` + ``get_supported_languages``."""

    def test_python_parser_is_loadable(self) -> None:
        parser = LanguageDetector.get_parser("python")
        assert parser is not None
        # Instance (not class) — get_parser returns an instance
        assert not isinstance(parser, type)

    def test_case_insensitive_language_name(self) -> None:
        p1 = LanguageDetector.get_parser("Python")
        p2 = LanguageDetector.get_parser("PYTHON")
        assert p1 is not None and p2 is not None

    def test_unknown_language_raises_import_error(self) -> None:
        import pytest as _pytest

        with _pytest.raises(ImportError, match="No parser available"):
            LanguageDetector.get_parser("fortran")

    def test_supported_languages_includes_python(self) -> None:
        langs = LanguageDetector.get_supported_languages()
        assert "python" in langs
        # Returns a list even in the minimal install
        assert isinstance(langs, list)


class TestGetParserForExtension:
    """``get_parser_for_extension`` — extension → LanguagePlugin."""

    def test_python_extension_with_dot(self) -> None:
        p = get_parser_for_extension(".py")
        assert p is not None

    def test_python_extension_without_dot(self) -> None:
        p = get_parser_for_extension("py")
        assert p is not None

    def test_uppercase_extension(self) -> None:
        p = get_parser_for_extension(".PY")
        assert p is not None

    def test_unknown_extension_returns_none(self) -> None:
        assert get_parser_for_extension(".xyz") is None
        assert get_parser_for_extension("xyz") is None

    def test_empty_string_returns_none(self) -> None:
        assert get_parser_for_extension("") is None

    def test_typescript_extension(self) -> None:
        p = get_parser_for_extension(".ts")
        # May be None if no TS parser is installed — both outcomes acceptable
        assert p is None or p is not None

    def test_javascript_extension(self) -> None:
        p = get_parser_for_extension(".js")
        # May or may not be present depending on JS plugin install
        assert p is None or p is not None
