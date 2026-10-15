from pathlib import Path

import pytest

from cogant.ingest.language_detect import LanguageDetectionError, LanguageDetector
from cogant.parsers import LanguageParserUnavailable, get_parser_for_extension


@pytest.mark.parametrize("extension", ["py", ".py", ".PY", ".js", ".jsx", ".ts", ".rs", ".go"])
def test_registered_extension_returns_parser(extension: str) -> None:
    parser = get_parser_for_extension(extension)
    assert callable(parser.parse)


@pytest.mark.parametrize("extension", [".unknownlang", "unknownlang", "", ".txt"])
def test_unknown_extension_raises(extension: str) -> None:
    with pytest.raises(LanguageParserUnavailable):
        get_parser_for_extension(extension)


def test_detect_repository_counts_real_files(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("x = 1\n")
    (tmp_path / "main.js").write_text("const x = 1;\n")
    (tmp_path / "README.md").write_text("example\n")
    assert LanguageDetector.detect_repo_languages(tmp_path) == {"python": 1, "javascript": 1}


def test_missing_repository_raises(tmp_path: Path) -> None:
    with pytest.raises(LanguageDetectionError, match="does not exist"):
        LanguageDetector.detect_repo_languages(tmp_path / "missing")


def test_registry_parser_extracts_real_python_symbols(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("def increment(x):\n    return x + 1\n")
    parser = get_parser_for_extension(source.suffix)
    symbols = parser.extract_symbols(parser.parse(source.read_text()))
    assert any(symbol["name"] == "increment" for symbol in symbols)
