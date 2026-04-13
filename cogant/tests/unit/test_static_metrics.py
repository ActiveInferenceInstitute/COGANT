"""Unit tests for static metrics module."""

import pytest
import math
from pathlib import Path

from cogant.static.metrics import (
    CodeMetrics,
    HalsteadMetrics,
    MetricsAnalyzer,
    HalsteadVisitor,
)


@pytest.mark.unit
class TestCodeMetrics:
    """Test CodeMetrics dataclass."""

    def test_creation(self) -> None:
        """Test creating CodeMetrics."""
        metrics = CodeMetrics(
            lines_of_code=100,
            logical_lines=50,
            comment_lines=10,
            blank_lines=20,
            docstring_coverage=0.8,
            public_symbols=10,
            documented_symbols=8,
        )
        assert metrics.lines_of_code == 100
        assert metrics.docstring_coverage == 0.8

    def test_zero_metrics(self) -> None:
        """Test zero-valued metrics."""
        metrics = CodeMetrics(
            lines_of_code=0,
            logical_lines=0,
            comment_lines=0,
            blank_lines=0,
            docstring_coverage=0.0,
            public_symbols=0,
            documented_symbols=0,
        )
        assert metrics.lines_of_code == 0
        assert metrics.docstring_coverage == 0.0


@pytest.mark.unit
class TestHalsteadMetrics:
    """Test HalsteadMetrics dataclass and computation."""

    def test_halstead_creation(self) -> None:
        """Test creating HalsteadMetrics."""
        metrics = HalsteadMetrics(
            unique_operators=5,
            unique_operands=10,
            total_operators=20,
            total_operands=30,
            vocabulary=15,
            length=50,
            volume=200.0,
            difficulty=5.0,
            effort=1000.0,
        )
        assert metrics.unique_operators == 5
        assert metrics.effort == 1000.0

    def test_halstead_compute_simple_assignment(self) -> None:
        """Test Halstead metrics on simple assignment."""
        source = "x = 1"
        metrics = HalsteadMetrics.compute(source)
        # Assignment operator + name + constant
        assert metrics.unique_operators > 0
        assert metrics.unique_operands > 0
        assert metrics.total_operators > 0
        assert metrics.total_operands > 0

    def test_halstead_compute_empty_source(self) -> None:
        """Test Halstead on empty source."""
        metrics = HalsteadMetrics.compute("")
        assert metrics.unique_operators == 0
        assert metrics.unique_operands == 0
        assert metrics.volume == 0.0

    def test_halstead_vocabulary_calculation(self) -> None:
        """Test vocabulary n = n1 + n2."""
        source = "x = a + b"
        metrics = HalsteadMetrics.compute(source)
        assert metrics.vocabulary == metrics.unique_operators + metrics.unique_operands

    def test_halstead_length_calculation(self) -> None:
        """Test length N = N1 + N2."""
        source = "x = a + b"
        metrics = HalsteadMetrics.compute(source)
        assert metrics.length == metrics.total_operators + metrics.total_operands

    def test_halstead_volume_formula(self) -> None:
        """Test volume V = N * log2(n)."""
        source = "x = a + b"
        metrics = HalsteadMetrics.compute(source)
        if metrics.vocabulary > 0:
            expected_volume = metrics.length * math.log2(metrics.vocabulary)
            assert abs(metrics.volume - expected_volume) < 0.001

    def test_halstead_difficulty_formula(self) -> None:
        """Test difficulty D = (n1/2) * (N2/n2)."""
        source = "x = a + b"
        metrics = HalsteadMetrics.compute(source)
        if metrics.unique_operands > 0:
            expected_difficulty = (metrics.unique_operators / 2.0) * (
                metrics.total_operands / metrics.unique_operands
            )
            assert abs(metrics.difficulty - expected_difficulty) < 0.001

    def test_halstead_effort_formula(self) -> None:
        """Test effort E = D * V."""
        source = "x = a + b"
        metrics = HalsteadMetrics.compute(source)
        expected_effort = metrics.difficulty * metrics.volume
        assert abs(metrics.effort - expected_effort) < 0.001

    def test_halstead_syntax_error(self) -> None:
        """Test Halstead on syntax error."""
        metrics = HalsteadMetrics.compute("x = (invalid")
        assert metrics.unique_operators == 0
        assert metrics.unique_operands == 0

    def test_halstead_zero_vocabulary_edge_case(self) -> None:
        """Test when vocabulary is zero."""
        metrics = HalsteadMetrics(
            unique_operators=0,
            unique_operands=0,
            total_operators=0,
            total_operands=0,
            vocabulary=0,
            length=0,
            volume=0.0,
            difficulty=0.0,
            effort=0.0,
        )
        assert metrics.volume == 0.0

    def test_halstead_with_operators_only(self) -> None:
        """Test Halstead with comparison operators."""
        source = "if x > 5 and y < 10: pass"
        metrics = HalsteadMetrics.compute(source)
        assert metrics.unique_operators > 0


@pytest.mark.unit
class TestMetricsAnalyzer:
    """Test MetricsAnalyzer."""

    def test_analyzer_creation(self) -> None:
        """Test creating a MetricsAnalyzer."""
        analyzer = MetricsAnalyzer()
        assert analyzer is not None

    def test_compute_empty_source(self) -> None:
        """Test computing metrics on empty source."""
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute("")
        assert metrics.lines_of_code == 0
        assert metrics.blank_lines == 0
        assert metrics.comment_lines == 0

    def test_compute_loc_count(self) -> None:
        """Test lines of code counting."""
        source = """
def add(a, b):
    return a + b

print("test")
"""
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute(source)
        assert metrics.lines_of_code > 0

    def test_compute_blank_lines(self) -> None:
        """Test blank line counting."""
        source = """x = 1

y = 2

z = 3"""
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute(source)
        assert metrics.blank_lines == 2

    def test_compute_comment_lines(self) -> None:
        """Test comment line counting."""
        source = """
# This is a comment
x = 1
# Another comment
y = 2
"""
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute(source)
        assert metrics.comment_lines == 2

    def test_compute_docstring_coverage_100_percent(self) -> None:
        """Test docstring coverage when all public symbols documented."""
        source = '''
def func1():
    """This is documented."""
    return 1

def func2():
    """This is also documented."""
    return 2

class MyClass:
    """Documented class."""
    pass
'''
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute(source)
        assert metrics.public_symbols == 3
        assert metrics.documented_symbols == 3
        assert metrics.docstring_coverage == 1.0

    def test_compute_docstring_coverage_partial(self) -> None:
        """Test docstring coverage with some undocumented symbols."""
        source = '''
def func1():
    """Documented."""
    return 1

def func2():
    return 2

class MyClass:
    """Documented."""
    pass
'''
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute(source)
        assert metrics.public_symbols == 3
        assert metrics.documented_symbols == 2
        assert abs(metrics.docstring_coverage - 2.0 / 3.0) < 0.001

    def test_compute_docstring_coverage_zero(self) -> None:
        """Test docstring coverage when no symbols documented."""
        source = """
def func1():
    return 1

def func2():
    return 2
"""
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute(source)
        assert metrics.public_symbols == 2
        assert metrics.documented_symbols == 0
        assert metrics.docstring_coverage == 0.0

    def test_compute_private_symbols_ignored(self) -> None:
        """Test that private symbols are not counted."""
        source = """
def public():
    '''Documented.'''
    pass

def _private():
    '''Also documented.'''
    pass

class Public:
    '''Documented.'''
    pass

class _Private:
    '''Also documented.'''
    pass
"""
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute(source)
        assert metrics.public_symbols == 2  # Only public, not _private
        assert metrics.documented_symbols == 2

    def test_compute_logical_lines(self) -> None:
        """Test logical lines counting."""
        source = """
x = 1
y = 2
if x > 0:
    z = 3
"""
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute(source)
        assert metrics.logical_lines > 0

    def test_halstead_method(self) -> None:
        """Test the halstead() method."""
        source = "x = a + b"
        analyzer = MetricsAnalyzer()
        halstead = analyzer.halstead(source)
        assert isinstance(halstead, HalsteadMetrics)
        assert halstead.vocabulary > 0

    def test_analyze_file(self, tmp_path: Path) -> None:
        """Test analyzing a file from disk."""
        test_file = tmp_path / "test_module.py"
        test_file.write_text("""
def add(a, b):
    '''Add two numbers.'''
    return a + b

def _private():
    return 1

class Calculator:
    '''A calculator class.'''
    pass
""")
        analyzer = MetricsAnalyzer()
        code_metrics, halstead_metrics = analyzer.analyze_file(test_file)

        assert code_metrics.public_symbols == 2  # add, Calculator
        assert code_metrics.documented_symbols == 2
        assert code_metrics.docstring_coverage == 1.0
        assert halstead_metrics.vocabulary > 0

    def test_analyze_file_not_found(self, tmp_path: Path) -> None:
        """Test analyze_file with nonexistent file."""
        analyzer = MetricsAnalyzer()
        code_metrics, halstead_metrics = analyzer.analyze_file(
            tmp_path / "nonexistent.py"
        )
        assert code_metrics.lines_of_code == 0
        assert halstead_metrics.vocabulary == 0

    def test_compute_with_syntax_error(self) -> None:
        """Test compute with invalid syntax."""
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute("x = (invalid")
        assert metrics.lines_of_code > 0  # LOC still counted
        assert metrics.logical_lines == 0  # AST parsing failed
        assert metrics.docstring_coverage == 0.0

    def test_mixed_comments_and_code(self) -> None:
        """Test with mixed comments, code, and blank lines."""
        source = """
# Header comment
def func():
    # Function body comment
    x = 1
    y = 2

# End comment
"""
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute(source)
        assert metrics.comment_lines == 3
        assert metrics.blank_lines == 1
        assert metrics.lines_of_code >= 2

    def test_compute_async_functions(self) -> None:
        """Test counting async functions."""
        source = """
async def async_func1():
    '''Documented async.'''
    pass

async def async_func2():
    pass
"""
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute(source)
        assert metrics.public_symbols == 2
        assert metrics.documented_symbols == 1

    def test_public_class_with_private_methods(self) -> None:
        """Test class counts without counting private methods."""
        source = """
class PublicClass:
    '''Documented.'''
    def public_method(self):
        '''Documented method.'''
        pass

    def _private_method(self):
        pass
"""
        analyzer = MetricsAnalyzer()
        metrics = analyzer.compute(source)
        # Only the public class is counted, not the methods
        assert metrics.public_symbols == 1
        assert metrics.documented_symbols == 1
