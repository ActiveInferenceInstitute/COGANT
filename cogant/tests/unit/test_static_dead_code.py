"""Unit tests for dead code detection module."""

from pathlib import Path

import pytest

from cogant.static.dead_code import (
    DeadCodeAnalyzer,
    DeadCodeEntry,
    DeadCodeReport,
)


@pytest.mark.unit
class TestDeadCodeEntry:
    """Test DeadCodeEntry dataclass."""

    def test_entry_creation(self) -> None:
        """Test creating a DeadCodeEntry."""
        entry = DeadCodeEntry(
            symbol_name="unused_import",
            file_path=Path("test.py"),
            line_num=1,
            kind="UNUSED_IMPORT",
            confidence=0.95,
        )
        assert entry.symbol_name == "unused_import"
        assert entry.kind == "UNUSED_IMPORT"
        assert entry.confidence == 0.95

    def test_entry_confidence_bounds(self) -> None:
        """Test confidence is in valid range [0.0, 1.0]."""
        entry = DeadCodeEntry(
            symbol_name="test",
            file_path=Path("test.py"),
            line_num=1,
            kind="UNUSED_FUNCTION",
            confidence=0.8,
        )
        assert 0.0 <= entry.confidence <= 1.0


@pytest.mark.unit
class TestDeadCodeReport:
    """Test DeadCodeReport and methods."""

    def test_empty_report(self) -> None:
        """Test creating an empty report."""
        report = DeadCodeReport(file_path=Path("test.py"))
        assert report.file_path == Path("test.py")
        assert report.entries == []
        assert report.unused_imports == 0
        assert report.errors == []

    def test_report_with_entries(self) -> None:
        """Test report with multiple entries."""
        entries = [
            DeadCodeEntry(
                symbol_name="os",
                file_path=Path("test.py"),
                line_num=1,
                kind="UNUSED_IMPORT",
                confidence=0.95,
            ),
            DeadCodeEntry(
                symbol_name="_helper",
                file_path=Path("test.py"),
                line_num=5,
                kind="UNUSED_FUNCTION",
                confidence=0.8,
            ),
        ]
        report = DeadCodeReport(
            file_path=Path("test.py"),
            entries=entries,
            unused_imports=1,
            unused_functions=1,
        )
        assert len(report.entries) == 2
        assert report.unused_imports == 1
        assert report.unused_functions == 1

    def test_get_certain_entries(self) -> None:
        """Test filtering entries by high confidence."""
        entries = [
            DeadCodeEntry(
                symbol_name="a",
                file_path=Path("test.py"),
                line_num=1,
                kind="UNUSED_IMPORT",
                confidence=0.95,
            ),
            DeadCodeEntry(
                symbol_name="b",
                file_path=Path("test.py"),
                line_num=2,
                kind="UNUSED_FUNCTION",
                confidence=0.7,
            ),
        ]
        report = DeadCodeReport(file_path=Path("test.py"), entries=entries)
        certain = report.get_certain_entries()
        assert len(certain) == 1
        assert certain[0].symbol_name == "a"


@pytest.mark.unit
class TestDeadCodeAnalyzer:
    """Test DeadCodeAnalyzer."""

    def test_analyzer_creation(self) -> None:
        """Test creating a DeadCodeAnalyzer."""
        analyzer = DeadCodeAnalyzer()
        assert analyzer is not None

    def test_analyze_empty_source(self) -> None:
        """Test analyzing empty source code."""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze("", Path("empty.py"))
        assert report.file_path == Path("empty.py")
        assert report.entries == []
        assert report.errors == []

    def test_detect_unused_import(self) -> None:
        """Test detection of unused import."""
        source = """
import os
print("hello")
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert report.unused_imports == 1
        assert len(report.entries) == 1
        assert report.entries[0].symbol_name == "os"
        assert report.entries[0].kind == "UNUSED_IMPORT"

    def test_detect_used_import(self) -> None:
        """Test that used imports are NOT flagged."""
        source = """
import os
path = os.path.join("a", "b")
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert report.unused_imports == 0
        assert len(report.entries) == 0

    def test_detect_unused_import_from(self) -> None:
        """Test detection of unused 'from X import Y' statement."""
        source = """
from pathlib import Path
print("test")
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert report.unused_imports == 1
        assert report.entries[0].symbol_name == "Path"

    def test_unused_import_with_alias(self) -> None:
        """Test unused import with alias."""
        source = """
import numpy as np
x = 5
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert report.unused_imports == 1
        assert report.entries[0].symbol_name == "np"

    def test_dunder_imports_not_flagged(self) -> None:
        """Test that dunder-prefixed imports are not flagged."""
        source = """
import os as _os
print("hello")
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        # _os starts with underscore, should not be flagged
        assert report.unused_imports == 0

    def test_detect_unused_private_function(self) -> None:
        """Test detection of unused private function."""
        source = """
def _helper():
    return 42

def main():
    return 1
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert report.unused_functions == 1
        assert report.entries[0].symbol_name == "_helper"
        assert report.entries[0].kind == "UNUSED_FUNCTION"

    def test_detect_used_private_function(self) -> None:
        """Test that used private functions are NOT flagged."""
        source = """
def _helper():
    return 42

def main():
    return _helper()
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert report.unused_functions == 0

    def test_public_functions_not_flagged(self) -> None:
        """Test that public functions are not flagged as unused."""
        source = """
def public_func():
    return 42
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        # Public functions can be called from outside, so not flagged
        assert report.unused_functions == 0

    def test_detect_unused_private_variable(self) -> None:
        """Test detection of unused private variable."""
        source = """
_unused_var = 42
print("hello")
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert report.unused_variables == 1
        assert report.entries[0].symbol_name == "_unused_var"
        assert report.entries[0].kind == "UNUSED_VARIABLE"

    def test_detect_used_private_variable(self) -> None:
        """Test that used private variables are NOT flagged."""
        source = """
_used_var = 42
x = _used_var + 1
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert report.unused_variables == 0

    def test_confidence_scores(self) -> None:
        """Test that confidence scores are appropriate for different kinds."""
        source = """
import unused_module
def _unused_func():
    pass
_unused_var = 1
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))

        import_entry = next((e for e in report.entries if e.kind == "UNUSED_IMPORT"), None)
        func_entry = next((e for e in report.entries if e.kind == "UNUSED_FUNCTION"), None)
        var_entry = next((e for e in report.entries if e.kind == "UNUSED_VARIABLE"), None)

        # Imports have highest confidence
        assert import_entry is not None
        assert import_entry.confidence > 0.9

        # Functions have medium confidence
        assert func_entry is not None
        assert 0.7 <= func_entry.confidence < 0.9

        # Variables have lower confidence
        assert var_entry is not None
        assert var_entry.confidence < func_entry.confidence

    def test_syntax_error_handling(self) -> None:
        """Test handling of syntax errors."""
        source = "import os\nthis is invalid python"
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.errors) == 1
        assert "Syntax error" in report.errors[0]

    def test_analyze_file(self, tmp_path: Path) -> None:
        """Test analyzing a file from disk."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
import sys
import os
print(sys.version)
""")
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze_file(test_file)
        assert report.file_path == test_file
        assert report.unused_imports == 1
        assert report.entries[0].symbol_name == "os"

    def test_multiple_unused_imports(self) -> None:
        """Test detection of multiple unused imports."""
        source = """
import os
import sys
import json
x = 1
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert report.unused_imports == 3
        assert len(report.entries) == 3

    def test_mixed_used_and_unused(self) -> None:
        """Test mixed scenario with some used and some unused."""
        source = """
import os
import sys
import json

print(os.name)
x = sys.version
# json is unused
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert report.unused_imports == 1
        assert report.entries[0].symbol_name == "json"

    def test_async_function_detection(self) -> None:
        """Test detection of unused async functions."""
        source = """
async def _unused_async():
    return 42

async def used_async():
    return await _unused_async()
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        # _unused_async is used, so shouldn't be flagged
        assert report.unused_functions == 0

    def test_class_scope_functions(self) -> None:
        """Test that class methods are tracked separately."""
        source = """
class MyClass:
    def _private_method(self):
        return 42

    def public_method(self):
        return 1
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        # Private method not called, should be flagged
        assert report.unused_functions == 1
        assert report.entries[0].symbol_name == "_private_method"

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test handling of missing file."""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze_file(tmp_path / "nonexistent.py")
        assert len(report.errors) == 1
        assert "Failed to read file" in report.errors[0]

    def test_from_import_multiple(self) -> None:
        """Test from import with multiple names."""
        source = """
from os.path import join, exists
print(join("a", "b"))
"""
        analyzer = DeadCodeAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert report.unused_imports == 1
        assert report.entries[0].symbol_name == "exists"
