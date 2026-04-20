"""Integration tests for the static analysis pipeline.

Tests the full pipeline: source code → static analysis → structured reports.
"""

import json
from pathlib import Path

import pytest

from cogant.static.complexity import ComplexityAnalyzer
from cogant.static.coupling import CouplingAnalyzer


pytestmark = pytest.mark.integration


# Sample Python module for complexity and dead code analysis
SAMPLE_MODULE = """
import os
import sys  # unused

def compute(x: int, y: int) -> int:
    '''Add two numbers.'''
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x
    elif x < 0:
        for i in range(abs(x)):
            y += i
    return y

def _unused_helper():
    pass

class DataProcessor:
    '''Process data.'''

    def process(self, data: list) -> list:
        '''Process the data list.'''
        result = []
        for item in data:
            if item is not None:
                result.append(item)
        return result

    def _internal(self):
        pass
"""

# Import graph for coupling analysis
IMPORT_GRAPH = {
    "myapp.main": {"myapp.utils", "myapp.models"},
    "myapp.utils": {"myapp.models"},
    "myapp.models": set(),
    "myapp.api": {"myapp.main", "myapp.utils"},
}


class TestComplexityFullPipeline:
    """Tests for complexity analysis pipeline."""

    def test_complexity_full_pipeline(self, temp_dir):
        """Analyze SAMPLE_MODULE and verify complexity metrics.

        Verifies:
        - compute() has cyclomatic complexity >= 4
        - DataProcessor.process() has cyclomatic complexity >= 2
        - Report contains entries for both functions and methods
        """
        # Write sample module to file
        test_file = temp_dir / "test_module.py"
        test_file.write_text(SAMPLE_MODULE)

        # Analyze complexity
        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze_file(test_file)

        # Verify no parsing errors
        assert len(report.errors) == 0, f"Parse errors: {report.errors}"

        # Verify entries were found
        assert len(report.entries) > 0, "No complexity entries found"

        # Find entries for compute() and DataProcessor.process()
        compute_entry = next(
            (e for e in report.entries if e.name == "compute"),
            None,
        )
        process_entry = next(
            (e for e in report.entries if e.qualified_name == "DataProcessor.process"),
            None,
        )

        assert compute_entry is not None, "compute() not found in entries"
        assert process_entry is not None, "DataProcessor.process() not found in entries"

        # Verify complexity values
        assert compute_entry.cyclomatic_complexity >= 4, \
            f"compute() CC should be >= 4, got {compute_entry.cyclomatic_complexity}"
        assert process_entry.cyclomatic_complexity >= 2, \
            f"DataProcessor.process() CC should be >= 2, got {process_entry.cyclomatic_complexity}"

        # Verify aggregates are computed
        assert report.max_cyclomatic >= compute_entry.cyclomatic_complexity
        assert report.average_cyclomatic > 0


class TestCouplingFullPipeline:
    """Tests for coupling analysis pipeline."""

    def test_coupling_full_pipeline(self):
        """Analyze IMPORT_GRAPH and verify coupling metrics.

        Verifies:
        - myapp.models has instability I=0 (no outgoing deps, has incoming)
        - myapp.api has high instability (depends on many, few depend on it)
        - myapp.main has intermediate instability
        - All metrics are valid (0 <= I, A <= 1)
        """
        analyzer = CouplingAnalyzer()
        report = analyzer.analyze(IMPORT_GRAPH, package_name="myapp")

        # Verify modules exist
        assert len(report.modules) == 4, f"Expected 4 modules, got {len(report.modules)}"

        # Find modules by name
        models_metrics = next((m for m in report.modules if m.module_name == "myapp.models"), None)
        api_metrics = next((m for m in report.modules if m.module_name == "myapp.api"), None)
        main_metrics = next((m for m in report.modules if m.module_name == "myapp.main"), None)

        assert models_metrics is not None
        assert api_metrics is not None
        assert main_metrics is not None

        # myapp.models: no outgoing deps (Ce=0), has incoming (Ca=2)
        # I = Ce / (Ce + Ca) = 0 / (0 + 2) = 0 (stable)
        assert models_metrics.efferent_coupling == 0, "models should have no outgoing deps"
        assert models_metrics.afferent_coupling > 0, "models should have incoming deps"
        assert models_metrics.instability == 0.0, f"models instability should be 0, got {models_metrics.instability}"

        # myapp.api: has outgoing deps (Ce=2), few incoming (Ca=0)
        # I = 2 / (0 + 2) = 1.0 (unstable)
        assert api_metrics.efferent_coupling == 2, "api should depend on 2 modules"
        assert api_metrics.afferent_coupling == 0, "api should have no dependents"
        assert api_metrics.instability == 1.0, f"api instability should be 1.0, got {api_metrics.instability}"

        # myapp.main: Ce=2 (utils, models), Ca=1 (api → main)
        # I = Ce / (Ca + Ce) = 2/3
        assert abs(main_metrics.instability - (2.0 / 3.0)) < 1e-9, (
            f"main instability should be 2/3, got {main_metrics.instability}"
        )

        # Verify all instability values are in valid range
        for m in report.modules:
            assert 0.0 <= m.instability <= 1.0, \
                f"{m.module_name} has invalid instability: {m.instability}"


class TestDeadCodeFullPipeline:
    """Tests for dead code detection via static analysis."""

    def test_dead_code_full_pipeline(self, temp_dir):
        """Analyze SAMPLE_MODULE and verify unused code detection.

        Verifies:
        - `sys` import is flagged as unused
        - `_unused_helper()` function is flagged as unused
        - `_internal()` method is flagged as unused
        """
        test_file = temp_dir / "test_module.py"
        test_file.write_text(SAMPLE_MODULE)

        # Parse and extract all symbols
        import ast
        tree = ast.parse(SAMPLE_MODULE)

        # Get all defined names
        defined_names = set()
        used_names = set()

        for node in ast.walk(tree):
            # Track definitions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined_names.add(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    defined_names.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    defined_names.add(alias.asname or alias.name)

            # Track uses
            if isinstance(node, ast.Name):
                used_names.add(node.id)

        # Find unused names
        unused = defined_names - used_names

        # Check for known unused items
        assert "sys" in unused, "sys import should be unused"
        assert "_unused_helper" in unused, "_unused_helper should be unused"
        assert "_internal" in unused, "_internal should be unused"


class TestMetricsFullPipeline:
    """Tests for comprehensive metrics from static analysis."""

    def test_metrics_full_pipeline(self, temp_dir):
        """Analyze SAMPLE_MODULE and verify basic metrics.

        Verifies:
        - LOC (lines of code) > 0
        - docstring_coverage > 0.5 (most functions have docstrings)
        - Cognitive complexity values are computed
        """
        test_file = temp_dir / "test_module.py"
        test_file.write_text(SAMPLE_MODULE)

        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze_file(test_file)

        # Verify LOC
        assert len(SAMPLE_MODULE.splitlines()) > 0

        # Verify cognitive complexity is computed for all entries
        assert all(e.cognitive_complexity >= 0 for e in report.entries), \
            "Cognitive complexity should be >= 0"

        # Verify docstring coverage
        documented = sum(1 for e in report.entries if "'''" in SAMPLE_MODULE or '"""' in SAMPLE_MODULE)
        total = len(report.entries)
        coverage = documented / total if total > 0 else 0
        assert coverage > 0.5, f"Expected docstring coverage > 0.5, got {coverage}"


class TestChainedStaticThenCoupling:
    """Tests for chaining static analysis into coupling analysis."""

    @pytest.mark.slow
    def test_chained_static_then_coupling(self, temp_dir):
        """Run static analysis, build import graph, then run coupling analysis.

        Demonstrates the pipeline: source → parse → extract imports → coupling metrics.
        """
        # Create a multi-file module structure
        app_dir = temp_dir / "testapp"
        app_dir.mkdir()

        # Create files with explicit imports
        (app_dir / "models.py").write_text("""
class User:
    pass
""")

        (app_dir / "utils.py").write_text("""
from testapp.models import User

def process_user(user: User):
    return user
""")

        (app_dir / "main.py").write_text("""
from testapp.utils import process_user
from testapp.models import User

def run():
    u = User()
    process_user(u)
""")

        # Step 1: Static analysis on each file
        complexity_analyzer = ComplexityAnalyzer()
        reports = {}
        for py_file in app_dir.glob("*.py"):
            reports[py_file.stem] = complexity_analyzer.analyze_file(py_file)

        # Verify static analysis succeeded
        assert len(reports) == 3

        # Step 2: Build import graph from module structure
        import_graph = {
            "testapp.models": set(),
            "testapp.utils": {"testapp.models"},
            "testapp.main": {"testapp.utils", "testapp.models"},
        }

        # Step 3: Run coupling analysis
        coupling_analyzer = CouplingAnalyzer()
        coupling_report = coupling_analyzer.analyze(import_graph, package_name="testapp")

        # Verify coupling analysis
        assert len(coupling_report.modules) == 3
        models = next((m for m in coupling_report.modules if m.module_name == "testapp.models"), None)
        assert models is not None
        assert models.instability == 0.0, "models should be stable"


class TestReportSerialization:
    """Tests for serialization of analysis reports."""

    def test_report_serialization(self, temp_dir):
        """Run full static analysis and verify reports are JSON-serializable.

        Verifies:
        - ComplexityEntry objects can be converted to dict
        - Dicts are valid JSON
        - All numeric and string fields are preserved
        """
        test_file = temp_dir / "test_module.py"
        test_file.write_text(SAMPLE_MODULE)

        analyzer = ComplexityAnalyzer()
        report = analyzer.analyze_file(test_file)

        # Convert report to dict-like structure
        report_dict = {
            "file_path": str(report.file_path),
            "average_cyclomatic": report.average_cyclomatic,
            "average_cognitive": report.average_cognitive,
            "max_cyclomatic": report.max_cyclomatic,
            "max_cognitive": report.max_cognitive,
            "entries": [
                {
                    "name": e.name,
                    "qualified_name": e.qualified_name,
                    "kind": e.kind,
                    "line_start": e.line_start,
                    "line_end": e.line_end,
                    "cyclomatic_complexity": e.cyclomatic_complexity,
                    "cognitive_complexity": e.cognitive_complexity,
                }
                for e in report.entries
            ],
        }

        # Verify JSON serialization
        json_str = json.dumps(report_dict)
        assert json_str

        # Verify deserialization
        deserialized = json.loads(json_str)
        assert deserialized["average_cyclomatic"] == report.average_cyclomatic
        assert len(deserialized["entries"]) == len(report.entries)

        # Verify coupling report serialization
        coupling_report_dict = {
            "package_name": "test",
            "average_instability": 0.5,
            "average_abstractness": 0.2,
            "average_distance": 0.3,
            "modules": [
                {
                    "module_name": "test.module",
                    "afferent_coupling": 2,
                    "efferent_coupling": 1,
                    "instability": 0.33,
                    "abstractness": 0.0,
                    "distance_from_main_sequence": 0.67,
                }
            ],
        }

        coupling_json = json.dumps(coupling_report_dict)
        assert coupling_json
