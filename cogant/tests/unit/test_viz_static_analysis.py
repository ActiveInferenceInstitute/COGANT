"""Unit tests for viz/static_analysis_view.py — StaticAnalysisView."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))
import matplotlib
matplotlib.use("Agg")
import pytest
from pathlib import Path
from cogant.viz.static_analysis_view import StaticAnalysisView
from cogant.static.complexity import ComplexityReport, ComplexityEntry
from cogant.static.coupling import CouplingReport, ModuleCouplingMetrics
from cogant.static.dead_code import DeadCodeReport, DeadCodeEntry
from cogant.static.metrics import HalsteadMetrics


def _complexity_report() -> ComplexityReport:
    report = ComplexityReport(file_path=Path("src/mod.py"))
    report.entries = [
        ComplexityEntry(name="func_a", qualified_name="mod.func_a", kind="function",
                        file_path=Path("src/mod.py"), line_start=1, line_end=5,
                        cyclomatic_complexity=3, cognitive_complexity=2),
        ComplexityEntry(name="func_b", qualified_name="mod.func_b", kind="function",
                        file_path=Path("src/mod.py"), line_start=10, line_end=30,
                        cyclomatic_complexity=12, cognitive_complexity=15),
    ]
    return report


def _empty_complexity() -> ComplexityReport:
    return ComplexityReport(file_path=Path("empty.py"))


def _coupling_report() -> CouplingReport:
    report = CouplingReport(package_name="mypkg")
    report.modules = [
        ModuleCouplingMetrics(module_name="mod_a", file_path=Path("mod_a.py"),
                              afferent_coupling=3, efferent_coupling=2, instability=0.4),
        ModuleCouplingMetrics(module_name="mod_b", file_path=Path("mod_b.py"),
                              afferent_coupling=1, efferent_coupling=5, instability=0.83),
    ]
    return report


def _dead_code_report() -> DeadCodeReport:
    report = DeadCodeReport(file_path=Path("src/dead.py"))
    report.entries = [
        DeadCodeEntry(symbol_name="unused_func", file_path=Path("src/dead.py"),
                      line_num=5, kind="UNUSED_FUNCTION"),
        DeadCodeEntry(symbol_name="UNUSED_VAR", file_path=Path("src/dead.py"),
                      line_num=12, kind="UNUSED_VARIABLE"),
    ]
    return report


def _halstead() -> HalsteadMetrics:
    return HalsteadMetrics(
        unique_operators=10, unique_operands=20,
        total_operators=30, total_operands=40,
        vocabulary=30, length=70,
        volume=210.0, difficulty=7.5, effort=1575.0,
    )


@pytest.fixture
def sav():
    return StaticAnalysisView()


@pytest.mark.unit
def test_init():
    assert StaticAnalysisView() is not None


@pytest.mark.unit
def test_plot_complexity_heatmap_basic(sav):
    fig = sav.plot_complexity_heatmap(_complexity_report())
    assert fig is not None
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_complexity_heatmap_empty(sav):
    sav.plot_complexity_heatmap(_empty_complexity())
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_complexity_histogram_basic(sav):
    fig = sav.plot_complexity_histogram(_complexity_report())
    assert fig is not None
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_complexity_histogram_empty(sav):
    sav.plot_complexity_histogram(_empty_complexity())
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_coupling_graph_basic(sav):
    sav.plot_coupling_graph(_coupling_report())
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_martin_metrics_basic(sav):
    sav.plot_martin_metrics(_coupling_report())
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_dead_code_summary_basic(sav):
    sav.plot_dead_code_summary(_dead_code_report())
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_plot_halstead_radar_basic(sav):
    sav.plot_halstead_radar(_halstead())
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_to_mermaid_complexity_returns_str(sav):
    result = sav.to_mermaid_complexity(_complexity_report())
    assert isinstance(result, str) and len(result) > 0


@pytest.mark.unit
def test_to_mermaid_complexity_empty(sav):
    assert isinstance(sav.to_mermaid_complexity(_empty_complexity()), str)


@pytest.mark.unit
def test_to_mermaid_coupling_returns_str(sav):
    assert isinstance(sav.to_mermaid_coupling(_coupling_report()), str)


@pytest.mark.unit
def test_to_png_round_trip(sav, tmp_path):
    import matplotlib.pyplot as plt
    fig, _ = plt.subplots()
    out = sav.to_png(fig, str(tmp_path / "sa.png"))
    assert isinstance(out, str)
    plt.close("all")


@pytest.mark.unit
def test_to_pdf_round_trip(sav, tmp_path):
    import matplotlib.pyplot as plt
    fig, _ = plt.subplots()
    out = sav.to_pdf(fig, str(tmp_path / "sa.pdf"))
    assert isinstance(out, str)
    plt.close("all")
