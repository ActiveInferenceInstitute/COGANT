"""Unit tests for static coupling analysis module."""

import pytest
from pathlib import Path

from cogant.static.coupling import (
    CouplingAnalyzer,
    CouplingReport,
    ModuleCouplingMetrics,
)


@pytest.mark.unit
class TestModuleCouplingMetrics:
    """Test ModuleCouplingMetrics dataclass."""

    def test_metrics_creation(self) -> None:
        """Test creating ModuleCouplingMetrics."""
        metrics = ModuleCouplingMetrics(
            module_name="my_module",
            file_path=Path("my_module.py"),
            afferent_coupling=2,
            efferent_coupling=3,
            instability=0.6,
            abstractness=0.0,
            distance_from_main_sequence=0.6,
        )
        assert metrics.module_name == "my_module"
        assert metrics.afferent_coupling == 2
        assert metrics.efferent_coupling == 3
        assert metrics.instability == 0.6

    def test_metrics_with_dependencies(self) -> None:
        """Test metrics with dependency sets."""
        metrics = ModuleCouplingMetrics(
            module_name="mod",
            file_path=Path("mod.py"),
            afferent_coupling=1,
            efferent_coupling=2,
            instability=0.67,
            dependencies={"dep1", "dep2"},
            dependents={"client1"},
        )
        assert len(metrics.dependencies) == 2
        assert len(metrics.dependents) == 1


@pytest.mark.unit
class TestCouplingReport:
    """Test CouplingReport and methods."""

    def test_empty_report(self) -> None:
        """Test creating an empty report."""
        report = CouplingReport(package_name="test_pkg")
        assert report.package_name == "test_pkg"
        assert report.modules == []
        assert report.average_instability == 0.0

    def test_report_with_modules(self) -> None:
        """Test report with multiple modules."""
        modules = [
            ModuleCouplingMetrics(
                module_name="mod_a",
                file_path=Path("a.py"),
                afferent_coupling=0,
                efferent_coupling=2,
                instability=1.0,
            ),
            ModuleCouplingMetrics(
                module_name="mod_b",
                file_path=Path("b.py"),
                afferent_coupling=1,
                efferent_coupling=1,
                instability=0.5,
            ),
        ]
        report = CouplingReport(package_name="test", modules=modules)
        assert len(report.modules) == 2

    def test_get_unstable_modules(self) -> None:
        """Test retrieving unstable modules."""
        modules = [
            ModuleCouplingMetrics(
                module_name="stable",
                file_path=Path("stable.py"),
                efferent_coupling=0,
                afferent_coupling=5,
                instability=0.0,
            ),
            ModuleCouplingMetrics(
                module_name="unstable",
                file_path=Path("unstable.py"),
                efferent_coupling=10,
                afferent_coupling=0,
                instability=1.0,
            ),
        ]
        report = CouplingReport(package_name="test", modules=modules)
        unstable = report.get_unstable_modules(threshold=0.8)
        assert len(unstable) == 1
        assert unstable[0].module_name == "unstable"

    def test_zone_of_pain(self) -> None:
        """Test zone of pain detection (high concrete + high instability)."""
        modules = [
            ModuleCouplingMetrics(
                module_name="pain",
                file_path=Path("pain.py"),
                efferent_coupling=10,
                afferent_coupling=1,
                instability=0.91,
                distance_from_main_sequence=0.5,
                concrete_classes=10,
                abstract_classes=0,
            ),
        ]
        report = CouplingReport(package_name="test", modules=modules)
        pain_zones = report.get_zone_of_pain()
        assert len(pain_zones) == 1

    def test_zone_of_uselessness(self) -> None:
        """Test zone of uselessness detection (high abstract + low use)."""
        modules = [
            ModuleCouplingMetrics(
                module_name="useless",
                file_path=Path("useless.py"),
                efferent_coupling=1,
                afferent_coupling=10,
                instability=0.09,
                distance_from_main_sequence=0.5,
                abstract_classes=10,
                concrete_classes=0,
            ),
        ]
        report = CouplingReport(package_name="test", modules=modules)
        useless_zones = report.get_zone_of_uselessness()
        assert len(useless_zones) == 1


@pytest.mark.unit
class TestCouplingAnalyzer:
    """Test CouplingAnalyzer."""

    def test_analyzer_creation(self) -> None:
        """Test creating a CouplingAnalyzer."""
        analyzer = CouplingAnalyzer()
        assert analyzer is not None

    def test_analyze_empty_graph(self) -> None:
        """Test analyzing an empty dependency graph."""
        analyzer = CouplingAnalyzer()
        report = analyzer.analyze({})
        assert report.modules == []
        assert report.average_instability == 0.0

    def test_analyze_simple_graph(self) -> None:
        """Test basic import graph analysis."""
        # Graph: A -> B, C -> B, C -> D (D is isolated)
        import_graph = {
            "A": {"B"},
            "B": set(),
            "C": {"B", "D"},
            "D": set(),
        }

        analyzer = CouplingAnalyzer()
        report = analyzer.analyze(import_graph, package_name="test")

        # B should have Ca=2 (A, C depend on it), Ce=0
        b_metrics = next((m for m in report.modules if m.module_name == "B"), None)
        assert b_metrics is not None
        assert b_metrics.afferent_coupling == 2
        assert b_metrics.efferent_coupling == 0
        assert b_metrics.instability == 0.0  # Ce/(Ca+Ce) = 0/2

        # A should have Ca=0, Ce=1 (depends on B)
        a_metrics = next((m for m in report.modules if m.module_name == "A"), None)
        assert a_metrics is not None
        assert a_metrics.afferent_coupling == 0
        assert a_metrics.efferent_coupling == 1
        assert a_metrics.instability == 1.0  # Ce/(Ca+Ce) = 1/1

    def test_instability_calculation(self) -> None:
        """Test instability formula I = Ce / (Ca + Ce)."""
        # Module with equal coupling should have I = 0.5
        import_graph = {
            "M": {"Dep1", "Dep2"},  # Ce = 2
            "Dep1": set(),
            "Dep2": set(),
            "Client1": {"M"},  # Ca += 1
            "Client2": {"M"},  # Ca += 1
        }

        analyzer = CouplingAnalyzer()
        report = analyzer.analyze(import_graph, package_name="test")

        m_metrics = next((m for m in report.modules if m.module_name == "M"), None)
        assert m_metrics is not None
        assert m_metrics.afferent_coupling == 2
        assert m_metrics.efferent_coupling == 2
        assert abs(m_metrics.instability - 0.5) < 0.001

    def test_isolated_module_instability(self) -> None:
        """Test instability for isolated module (no dependencies)."""
        import_graph = {
            "IsolatedModule": set(),
        }

        analyzer = CouplingAnalyzer()
        report = analyzer.analyze(import_graph)

        iso_metrics = report.modules[0]
        assert iso_metrics.module_name == "IsolatedModule"
        assert iso_metrics.afferent_coupling == 0
        assert iso_metrics.efferent_coupling == 0
        assert iso_metrics.instability == 0.0

    def test_distance_from_main_sequence(self) -> None:
        """Test distance calculation D = |A + I - 1|."""
        # D = 0 when A + I = 1 (on main sequence)
        # D = 1 when A + I = 0 or A + I = 2
        import_graph = {
            "M": {"Dep"},  # I = 1.0
            "Dep": set(),
        }
        abstract_classes = {"M": 1}  # A = 1.0
        concrete_classes = {"M": 0, "Dep": 1}

        analyzer = CouplingAnalyzer()
        report = analyzer.analyze(
            import_graph,
            abstract_classes=abstract_classes,
            concrete_classes=concrete_classes,
        )

        m_metrics = next((m for m in report.modules if m.module_name == "M"), None)
        assert m_metrics is not None
        # A = 1, I = 1, D = |1 + 1 - 1| = 1
        assert abs(m_metrics.abstractness - 1.0) < 0.001
        assert abs(m_metrics.distance_from_main_sequence - 1.0) < 0.001

    def test_abstractness_calculation(self) -> None:
        """Test abstractness A = abstract_classes / total_classes."""
        import_graph = {
            "M": set(),
        }
        abstract_classes = {"M": 3}
        concrete_classes = {"M": 7}

        analyzer = CouplingAnalyzer()
        report = analyzer.analyze(
            import_graph,
            abstract_classes=abstract_classes,
            concrete_classes=concrete_classes,
        )

        m_metrics = report.modules[0]
        assert abs(m_metrics.abstractness - 0.3) < 0.001

    def test_complex_dependency_graph(self) -> None:
        """Test a more complex dependency graph with cycles."""
        import_graph = {
            "A": {"B"},
            "B": {"C"},
            "C": {"A"},  # Creates cycle
            "D": {"A", "B"},
        }

        analyzer = CouplingAnalyzer()
        report = analyzer.analyze(import_graph)

        assert len(report.modules) == 4
        assert report.average_instability >= 0.0
        assert report.average_instability <= 1.0

    def test_aggregates_computed(self) -> None:
        """Test that aggregates are computed correctly."""
        import_graph = {
            "A": {"B"},  # I = 1.0
            "B": {"A"},  # I = 1.0
            "C": set(),  # I = 0.0
        }

        analyzer = CouplingAnalyzer()
        report = analyzer.analyze(import_graph)

        # Average should be (1.0 + 1.0 + 0.0) / 3 = 0.667
        assert abs(report.average_instability - 0.667) < 0.01
        assert report.average_abstractness == 0.0
        assert report.average_distance >= 0.0

    def test_abstract_and_concrete_classes_with_no_dependencies(self) -> None:
        """Test modules with class counts but no dependencies."""
        import_graph = {
            "M": set(),
        }
        abstract_classes = {"M": 5}
        concrete_classes = {"M": 5}

        analyzer = CouplingAnalyzer()
        report = analyzer.analyze(
            import_graph,
            abstract_classes=abstract_classes,
            concrete_classes=concrete_classes,
        )

        m_metrics = report.modules[0]
        assert abs(m_metrics.abstractness - 0.5) < 0.001
        # D = |0.5 + 0.0 - 1| = 0.5
        assert abs(m_metrics.distance_from_main_sequence - 0.5) < 0.001

    def test_modules_set_in_report(self) -> None:
        """Test that all modules appear in report (even if no explicit entry)."""
        import_graph = {
            "A": {"B"},
            "B": {"C"},
            "C": set(),
        }

        analyzer = CouplingAnalyzer()
        report = analyzer.analyze(import_graph)

        module_names = {m.module_name for m in report.modules}
        assert module_names == {"A", "B", "C"}

    def test_dependencies_and_dependents_sets(self) -> None:
        """Test that dependencies and dependents are correctly tracked."""
        import_graph = {
            "A": {"B", "C"},
            "B": {"C"},
            "C": set(),
        }

        analyzer = CouplingAnalyzer()
        report = analyzer.analyze(import_graph)

        a_metrics = next((m for m in report.modules if m.module_name == "A"), None)
        c_metrics = next((m for m in report.modules if m.module_name == "C"), None)

        assert a_metrics is not None
        assert a_metrics.dependencies == {"B", "C"}

        assert c_metrics is not None
        assert c_metrics.dependents == {"A", "B"}

    def test_multiple_abstract_concrete_counts(self) -> None:
        """Test with multiple modules having varying class counts."""
        import_graph = {
            "Interface": {"Impl1", "Impl2"},
            "Impl1": set(),
            "Impl2": set(),
        }
        abstract_classes = {
            "Interface": 5,
            "Impl1": 0,
            "Impl2": 0,
        }
        concrete_classes = {
            "Interface": 0,
            "Impl1": 10,
            "Impl2": 8,
        }

        analyzer = CouplingAnalyzer()
        report = analyzer.analyze(
            import_graph,
            abstract_classes=abstract_classes,
            concrete_classes=concrete_classes,
        )

        interface = next((m for m in report.modules if m.module_name == "Interface"), None)
        impl1 = next((m for m in report.modules if m.module_name == "Impl1"), None)

        assert interface is not None
        assert abs(interface.abstractness - 1.0) < 0.001

        assert impl1 is not None
        assert abs(impl1.abstractness - 0.0) < 0.001
