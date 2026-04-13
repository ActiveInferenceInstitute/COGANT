"""Unit tests for static complexity analysis module."""

import pytest
from pathlib import Path

from cogant.static.complexity import (
    ComplexityAnalyzer,
    ComplexityEntry,
    ComplexityReport,
    ComplexityVisitor,
)


@pytest.mark.unit
class TestComplexityEntry:
    """Test ComplexityEntry dataclass."""

    def test_complexity_entry_creation(self) -> None:
        """Test creating a ComplexityEntry with all fields."""
        entry = ComplexityEntry(
            name="test_func",
            qualified_name="module.test_func",
            kind="function",
            file_path=Path("test.py"),
            line_start=10,
            line_end=20,
            cyclomatic_complexity=3,
            cognitive_complexity=5,
        )
        assert entry.name == "test_func"
        assert entry.cyclomatic_complexity == 3
        assert entry.cognitive_complexity == 5
        assert entry.kind == "function"

    def test_complexity_entry_with_metadata(self) -> None:
        """Test ComplexityEntry with custom metadata."""
        entry = ComplexityEntry(
            name="test_func",
            qualified_name="module.test_func",
            kind="function",
            file_path=Path("test.py"),
            line_start=10,
            line_end=20,
            cyclomatic_complexity=2,
            cognitive_complexity=3,
            metadata={"source": "ast", "analyzed_at": "2026-04-13"},
        )
        assert entry.metadata["source"] == "ast"


@pytest.mark.unit
class TestComplexityReport:
    """Test ComplexityReport dataclass and methods."""

    def test_empty_report_creation(self) -> None:
        """Test creating an empty ComplexityReport."""
        report = ComplexityReport(file_path=Path("test.py"))
        assert report.file_path == Path("test.py")
        assert report.entries == []
        assert report.average_cyclomatic == 0.0
        assert report.average_cognitive == 0.0

    def test_report_with_entries(self) -> None:
        """Test report with populated entries."""
        entries = [
            ComplexityEntry(
                name="func1",
                qualified_name="func1",
                kind="function",
                file_path=Path("test.py"),
                line_start=1,
                line_end=5,
                cyclomatic_complexity=2,
                cognitive_complexity=3,
            ),
            ComplexityEntry(
                name="func2",
                qualified_name="func2",
                kind="function",
                file_path=Path("test.py"),
                line_start=6,
                line_end=15,
                cyclomatic_complexity=4,
                cognitive_complexity=6,
            ),
        ]
        report = ComplexityReport(
            file_path=Path("test.py"),
            entries=entries,
            average_cyclomatic=3.0,
            average_cognitive=4.5,
            max_cyclomatic=4,
            max_cognitive=6,
        )
        assert len(report.entries) == 2
        assert report.average_cyclomatic == 3.0
        assert report.max_cyclomatic == 4

    def test_get_hotspots_empty(self) -> None:
        """Test get_hotspots on empty report."""
        report = ComplexityReport(file_path=Path("test.py"))
        hotspots = report.get_hotspots(threshold=5)
        assert hotspots == []

    def test_get_hotspots_with_threshold(self) -> None:
        """Test get_hotspots filters by threshold correctly."""
        entries = [
            ComplexityEntry(
                name="simple",
                qualified_name="simple",
                kind="function",
                file_path=Path("test.py"),
                line_start=1,
                line_end=3,
                cyclomatic_complexity=2,
                cognitive_complexity=2,
            ),
            ComplexityEntry(
                name="complex",
                qualified_name="complex",
                kind="function",
                file_path=Path("test.py"),
                line_start=4,
                line_end=20,
                cyclomatic_complexity=12,
                cognitive_complexity=15,
            ),
        ]
        report = ComplexityReport(file_path=Path("test.py"), entries=entries)
        hotspots = report.get_hotspots(threshold=5)
        assert len(hotspots) == 1
        assert hotspots[0].name == "complex"

    def test_get_hotspots_ordered_by_complexity(self) -> None:
        """Test get_hotspots returns entries sorted by complexity (highest first)."""
        entries = [
            ComplexityEntry(
                name="func1",
                qualified_name="func1",
                kind="function",
                file_path=Path("test.py"),
                line_start=1,
                line_end=5,
                cyclomatic_complexity=10,
                cognitive_complexity=12,
            ),
            ComplexityEntry(
                name="func2",
                qualified_name="func2",
                kind="function",
                file_path=Path("test.py"),
                line_start=6,
                line_end=15,
                cyclomatic_complexity=15,
                cognitive_complexity=18,
            ),
            ComplexityEntry(
                name="func3",
                qualified_name="func3",
                kind="function",
                file_path=Path("test.py"),
                line_start=16,
                line_end=20,
                cyclomatic_complexity=12,
                cognitive_complexity=14,
            ),
        ]
        report = ComplexityReport(file_path=Path("test.py"), entries=entries)
        hotspots = report.get_hotspots(threshold=9)
        assert len(hotspots) == 3
        assert hotspots[0].cyclomatic_complexity == 15
        assert hotspots[1].cyclomatic_complexity == 12
        assert hotspots[2].cyclomatic_complexity == 10


@pytest.mark.unit
class TestComplexityAnalyzer:
    """Test ComplexityAnalyzer."""

    def test_analyzer_creation(self) -> None:
        """Test creating a ComplexityAnalyzer."""
        analyzer = ComplexityAnalyzer()
        assert analyzer is not None

    def test_analyze_empty_source(self) -> None:
        """Test analyzing empty source code."""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze("", Path("empty.py"))
        assert report.file_path == Path("empty.py")
        assert report.entries == []
        assert report.errors == []

    def test_analyze_simple_function(self) -> None:
        """Test analyzing a simple function with no branches."""
        source = """
def add(a, b):
    return a + b
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.entries) == 1
        assert report.entries[0].name == "add"
        assert report.entries[0].cyclomatic_complexity == 1
        assert report.entries[0].kind == "function"

    def test_analyze_function_with_if(self) -> None:
        """Test analyzing a function with if statement."""
        source = """
def check_positive(x):
    if x > 0:
        return True
    return False
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.entries) == 1
        assert report.entries[0].cyclomatic_complexity == 2

    def test_analyze_function_with_if_and_for(self) -> None:
        """Test analyzing a function with if and for loops."""
        source = """
def process(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item)
    return result
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.entries) == 1
        # Base 1 + if + for = 3
        assert report.entries[0].cyclomatic_complexity == 3

    def test_analyze_nested_complexity(self) -> None:
        """Test that cognitive complexity penalizes nesting more than flat conditions."""
        source = """
def flat(x):
    if x > 0:
        pass
    if x > 5:
        pass
    if x > 10:
        pass
"""
        source_nested = """
def nested(x):
    if x > 0:
        if x > 5:
            if x > 10:
                pass
"""
        analyzer = ComplexityAnalyzer()
        report_flat = analyzer.analyze(source, Path("test.py"))
        report_nested = analyzer.analyze(source_nested, Path("test.py"))

        flat_cog = report_flat.entries[0].cognitive_complexity
        nested_cog = report_nested.entries[0].cognitive_complexity

        # Nested should have higher cognitive complexity due to depth penalty
        assert nested_cog > flat_cog

    def test_analyze_class_with_methods(self) -> None:
        """Test analyzing a class with multiple methods."""
        source = """
class Calculator:
    def add(self, a, b):
        return a + b

    def divide(self, a, b):
        if b == 0:
            raise ValueError("Division by zero")
        return a / b
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.entries) == 2
        assert report.entries[0].kind == "method"
        assert report.entries[0].qualified_name == "Calculator.add"
        assert report.entries[1].qualified_name == "Calculator.divide"
        assert report.entries[1].cyclomatic_complexity == 2

    def test_analyze_syntax_error(self) -> None:
        """Test analyzing invalid Python syntax."""
        source = "def broken(\n  invalid"
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.errors) == 1
        assert "Syntax error" in report.errors[0]
        assert report.entries == []

    def test_analyze_with_boolean_operators(self) -> None:
        """Test complexity calculation with boolean operators."""
        source = """
def check(a, b, c):
    return a and b and c
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.entries) == 1
        # Base 1 + 2 additional "and" operators
        assert report.entries[0].cyclomatic_complexity == 3

    def test_analyze_with_try_except(self) -> None:
        """Test complexity with try/except blocks."""
        source = """
def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.entries) == 1
        # Base 1 + try + except handler
        assert report.entries[0].cyclomatic_complexity == 3

    def test_analyze_file(self, tmp_path: Path) -> None:
        """Test analyzing a file from disk."""
        test_file = tmp_path / "test_module.py"
        test_file.write_text("""
def simple():
    return 42

def complex_func(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                pass
""")
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze_file(test_file)
        assert report.file_path == test_file
        assert len(report.entries) == 2
        assert report.entries[0].name == "simple"
        assert report.entries[1].name == "complex_func"

    def test_analyze_aggregates(self) -> None:
        """Test that aggregates (average, max) are computed correctly."""
        source = """
def func1():
    if True:
        pass

def func2():
    if True:
        if True:
            pass
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert report.average_cyclomatic == 2.5  # (2 + 3) / 2
        assert report.max_cyclomatic == 3
        assert report.average_cognitive > 0
        assert report.max_cognitive > report.average_cognitive

    def test_analyze_async_function(self) -> None:
        """Test analyzing async functions."""
        source = """
async def fetch_data(url):
    if url:
        return "data"
    return None
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.entries) == 1
        assert report.entries[0].name == "fetch_data"
        assert report.entries[0].cyclomatic_complexity == 2

    def test_analyze_nested_functions(self) -> None:
        """Test analyzing nested function definitions."""
        source = """
def outer():
    def inner():
        if True:
            pass
    return inner
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.entries) == 2
        assert report.entries[0].name == "outer"
        assert report.entries[1].name == "inner"

    def test_analyze_ternary_operator(self) -> None:
        """Test complexity with ternary conditional expression."""
        source = """
def get_value(x):
    return x if x > 0 else -x
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.entries) == 1
        # Base 1 + ternary (IfExp)
        assert report.entries[0].cyclomatic_complexity == 2

    def test_analyze_while_loop(self) -> None:
        """Test complexity with while loops."""
        source = """
def countdown(n):
    while n > 0:
        n -= 1
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.entries) == 1
        assert report.entries[0].cyclomatic_complexity == 2

    def test_analyze_for_loop_with_else(self) -> None:
        """Test complexity with for-else construct."""
        source = """
def search(items, target):
    for item in items:
        if item == target:
            return item
    else:
        return None
"""
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze(source, Path("test.py"))
        assert len(report.entries) == 1
        # Base 1 + for + if = 3
        assert report.entries[0].cyclomatic_complexity == 3
