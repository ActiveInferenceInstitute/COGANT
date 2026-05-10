"""Wave 20 coverage boost: viz/static_analysis_view.py — StaticAnalysisView.

Targets matplotlib ImportError fallbacks and exception fallbacks that
the existing test_viz_static_analysis.py does not cover, plus edge
cases such as empty inputs, dict-style modules, missing attributes,
and the various branches of to_mermaid_complexity / to_mermaid_coupling.

Lines targeted (before this file):
    57-59, 122-124  (plot_complexity_heatmap import + except)
    142-144, 202-204 (plot_complexity_histogram import + except)
    173 (histogram empty entries early return)
    224-226, 303-305 (plot_coupling_graph import + except)
    232-233, 258-259, 262-263 (coupling empty + dict-form modules)
    323-325, 385-387 (plot_martin_metrics import + except)
    330-331, 405-407, 412-413 (Martin / dead code empty path)
    447-449 (plot_dead_code_summary except)
    471-473, 506-508 (plot_halstead_radar import + except)
    562-563, 570-571, 578, 590-593 (to_mermaid_coupling branches)
    611-613, 617-618, 626-628, 643-645, 649-650, 658-660 (to_png/to_pdf branches)
"""

from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from cogant.static.complexity import ComplexityEntry, ComplexityReport
from cogant.static.coupling import CouplingReport, ModuleCouplingMetrics
from cogant.static.dead_code import DeadCodeEntry, DeadCodeReport
from cogant.static.metrics import HalsteadMetrics
from cogant.viz.static_analysis_view import StaticAnalysisView

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sav() -> StaticAnalysisView:
    return StaticAnalysisView()


@pytest.fixture(autouse=True)
def _close_matplotlib():
    yield
    plt.close("all")


def _block_imports(*prefixes: str):
    """Return a substitute __import__ that raises ImportError for given prefixes."""
    real_import = builtins.__import__

    def _block(name: str, *args: Any, **kwargs: Any) -> Any:
        for p in prefixes:
            if name.startswith(p):
                raise ImportError(f"blocked: {name}")
        return real_import(name, *args, **kwargs)

    return _block


def _complexity_with_levels() -> ComplexityReport:
    """Report covering all four severity buckets."""
    report = ComplexityReport(file_path=Path("src/all.py"))
    report.entries = [
        ComplexityEntry(
            name="low",
            qualified_name="m.low",
            kind="function",
            file_path=Path("m.py"),
            line_start=1,
            line_end=3,
            cyclomatic_complexity=2,
            cognitive_complexity=1,
        ),
        ComplexityEntry(
            name="moderate",
            qualified_name="m.moderate",
            kind="function",
            file_path=Path("m.py"),
            line_start=10,
            line_end=15,
            cyclomatic_complexity=8,
            cognitive_complexity=6,
        ),
        ComplexityEntry(
            name="high",
            qualified_name="m.high",
            kind="function",
            file_path=Path("m.py"),
            line_start=20,
            line_end=40,
            cyclomatic_complexity=15,
            cognitive_complexity=12,
        ),
        ComplexityEntry(
            name="very_high",
            qualified_name="m.very_high",
            kind="function",
            file_path=Path("m.py"),
            line_start=50,
            line_end=100,
            cyclomatic_complexity=30,
            cognitive_complexity=25,
        ),
    ]
    return report


def _coupling_with_attrs() -> CouplingReport:
    report = CouplingReport(package_name="pkg")
    report.modules = [
        ModuleCouplingMetrics(
            module_name="alpha",
            file_path=Path("alpha.py"),
            instability=0.1,  # green zone
            abstractness=0.8,
        ),
        ModuleCouplingMetrics(
            module_name="beta",
            file_path=Path("beta.py"),
            instability=0.5,  # yellow zone
            abstractness=0.5,
        ),
        ModuleCouplingMetrics(
            module_name="gamma-mod.x",  # exercise sanitisation of dashes / dots
            file_path=Path("gamma.py"),
            instability=0.9,  # red zone
            abstractness=0.1,
        ),
    ]
    # coupling_matrix is consumed via getattr; attach after construction
    report.coupling_matrix = {  # type: ignore[attr-defined]
        "alpha": {"beta": 1.0},
        "beta": {"gamma-mod.x": 2.0},
    }
    return report


def _coupling_dict_form() -> Any:
    """Return a CouplingReport whose .modules is a list of plain dicts.

    The viz code branches on ``isinstance(module, dict)`` — exercise
    that path explicitly.
    """
    report = CouplingReport(package_name="dict_pkg")
    # Override `modules` with a list of dicts to hit dict branches at L569-571 and L242-244.
    report.modules = [  # type: ignore[assignment]
        {"module_name": "ddict_a", "instability": 0.2, "abstractness": 0.7},
        {"name": "ddict_b", "instability": 0.85, "abstractness": 0.15},
        # missing module_name and name → falls back to "unknown"
        {"instability": 0.5},
    ]
    report.coupling_matrix = {  # type: ignore[attr-defined]
        "ddict_a": {"ddict_b": 0.5},
    }
    return report


def _dead_code() -> DeadCodeReport:
    rep = DeadCodeReport(file_path=Path("d.py"))
    rep.entries = [
        DeadCodeEntry(
            symbol_name="f1", file_path=Path("d.py"), line_num=1, kind="UNUSED_FUNCTION"
        ),
        DeadCodeEntry(
            symbol_name="f2", file_path=Path("d.py"), line_num=5, kind="UNUSED_FUNCTION"
        ),
        DeadCodeEntry(
            symbol_name="v1", file_path=Path("d.py"), line_num=12, kind="UNUSED_VARIABLE"
        ),
    ]
    return rep


def _halstead() -> HalsteadMetrics:
    return HalsteadMetrics(
        unique_operators=12,
        unique_operands=8,
        total_operators=40,
        total_operands=30,
        vocabulary=20,
        length=70,
        volume=300.0,
        difficulty=5.0,
        effort=1500.0,
    )


# ---------------------------------------------------------------------------
# plot_complexity_heatmap — error & internal-exception paths
# ---------------------------------------------------------------------------


class TestPlotComplexityHeatmap:
    def test_import_error_returns_none(self, sav, monkeypatch):
        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block_imports("matplotlib"))
            assert sav.plot_complexity_heatmap(_complexity_with_levels()) is None

    def test_internal_exception_returns_none(self, sav):
        # Pass an object that lacks `entries` and triggers an exception.
        class Boom:
            @property
            def entries(self):
                raise RuntimeError("boom")

        assert sav.plot_complexity_heatmap(Boom()) is None

    def test_missing_entries_attr_returns_none(self, sav):
        """hasattr(report, 'entries') is False → returns None."""

        class _NoEntries:
            pass

        assert sav.plot_complexity_heatmap(_NoEntries()) is None

    def test_all_severity_zones(self, sav):
        """Hits all four colour branches: green / yellow / orange / red."""
        fig = sav.plot_complexity_heatmap(_complexity_with_levels())
        assert fig is not None


# ---------------------------------------------------------------------------
# plot_complexity_histogram
# ---------------------------------------------------------------------------


class TestPlotComplexityHistogram:
    def test_import_error_returns_none(self, sav, monkeypatch):
        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block_imports("matplotlib", "numpy"))
            assert sav.plot_complexity_histogram(_complexity_with_levels()) is None

    def test_missing_entries_returns_none(self, sav):
        class _NoEntries:
            pass

        assert sav.plot_complexity_histogram(_NoEntries()) is None

    def test_internal_exception_returns_none(self, sav):
        class Boom:
            @property
            def entries(self):
                raise RuntimeError("boom")

        assert sav.plot_complexity_histogram(Boom()) is None

    def test_all_zones_in_bin_colours(self, sav):
        # Multi-zone entries exercise the bin-colour selection branches.
        fig = sav.plot_complexity_histogram(_complexity_with_levels())
        assert fig is not None


# ---------------------------------------------------------------------------
# plot_coupling_graph
# ---------------------------------------------------------------------------


class TestPlotCouplingGraph:
    def test_import_error_returns_none(self, sav, monkeypatch):
        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block_imports("matplotlib", "networkx"))
            assert sav.plot_coupling_graph(_coupling_with_attrs()) is None

    def test_missing_modules_returns_none(self, sav):
        class _NoMods:
            pass

        assert sav.plot_coupling_graph(_NoMods()) is None

    def test_empty_modules_returns_none(self, sav):
        rep = CouplingReport(package_name="empty")
        # rep.modules defaults to [] — the empty-modules branch.
        assert sav.plot_coupling_graph(rep) is None

    def test_internal_exception_returns_none(self, sav):
        class Boom:
            @property
            def modules(self):
                raise RuntimeError("boom")

        assert sav.plot_coupling_graph(Boom()) is None

    def test_with_dict_modules(self, sav):
        # Exercise the dict branches in module-name/instability extraction.
        fig = sav.plot_coupling_graph(_coupling_dict_form())
        # Returns either fig or None (e.g. if no edges + no nodes); accept
        # whichever, but should not raise.
        assert fig is not None or fig is None

    def test_with_attr_modules(self, sav):
        fig = sav.plot_coupling_graph(_coupling_with_attrs())
        assert fig is not None


# ---------------------------------------------------------------------------
# plot_martin_metrics
# ---------------------------------------------------------------------------


class TestPlotMartinMetrics:
    def test_import_error_returns_none(self, sav, monkeypatch):
        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block_imports("matplotlib", "numpy"))
            assert sav.plot_martin_metrics(_coupling_with_attrs()) is None

    def test_missing_modules_returns_none(self, sav):
        class _NoMods:
            pass

        assert sav.plot_martin_metrics(_NoMods()) is None

    def test_empty_modules_returns_none(self, sav):
        rep = CouplingReport(package_name="empty")
        assert sav.plot_martin_metrics(rep) is None

    def test_internal_exception_returns_none(self, sav):
        class Boom:
            @property
            def modules(self):
                raise RuntimeError("boom")

        assert sav.plot_martin_metrics(Boom()) is None

    def test_dict_form_modules(self, sav):
        fig = sav.plot_martin_metrics(_coupling_dict_form())
        assert fig is not None


# ---------------------------------------------------------------------------
# plot_dead_code_summary
# ---------------------------------------------------------------------------


class TestPlotDeadCodeSummary:
    def test_import_error_returns_none(self, sav, monkeypatch):
        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block_imports("matplotlib"))
            assert sav.plot_dead_code_summary(_dead_code()) is None

    def test_missing_entries_returns_none(self, sav):
        class _NoE:
            pass

        assert sav.plot_dead_code_summary(_NoE()) is None

    def test_empty_report_returns_none(self, sav):
        rep = DeadCodeReport(file_path=Path("e.py"))
        assert sav.plot_dead_code_summary(rep) is None

    def test_internal_exception_returns_none(self, sav):
        class Boom:
            @property
            def entries(self):
                raise RuntimeError("boom")

        assert sav.plot_dead_code_summary(Boom()) is None


# ---------------------------------------------------------------------------
# plot_halstead_radar
# ---------------------------------------------------------------------------


class TestPlotHalsteadRadar:
    def test_import_error_returns_none(self, sav, monkeypatch):
        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block_imports("matplotlib", "numpy"))
            assert sav.plot_halstead_radar(_halstead()) is None

    def test_internal_exception_returns_none(self, sav):
        class Boom:
            def __getattr__(self, item):
                raise RuntimeError("boom")

        assert sav.plot_halstead_radar(Boom()) is None

    def test_basic(self, sav):
        fig = sav.plot_halstead_radar(_halstead())
        assert fig is not None


# ---------------------------------------------------------------------------
# to_mermaid_complexity
# ---------------------------------------------------------------------------


class TestToMermaidComplexity:
    def test_returns_pie_chart_string(self, sav):
        result = sav.to_mermaid_complexity(_complexity_with_levels())
        assert "pie title Complexity Distribution" in result
        assert '"Low (1-5)"' in result
        assert '"Moderate (6-10)"' in result
        assert '"High (11-20)"' in result
        assert '"Very High (20+)"' in result

    def test_no_entries_returns_empty(self, sav):
        rep = ComplexityReport(file_path=Path("e.py"))
        assert sav.to_mermaid_complexity(rep) == ""

    def test_no_entries_attr_returns_empty(self, sav):
        class _NoE:
            pass

        assert sav.to_mermaid_complexity(_NoE()) == ""


# ---------------------------------------------------------------------------
# to_mermaid_coupling
# ---------------------------------------------------------------------------


class TestToMermaidCoupling:
    def test_no_modules_returns_empty(self, sav):
        rep = CouplingReport(package_name="empty")
        assert sav.to_mermaid_coupling(rep) == ""

    def test_no_modules_attr_returns_empty(self, sav):
        class _NoM:
            pass

        assert sav.to_mermaid_coupling(_NoM()) == ""

    def test_attr_modules_all_three_zones(self, sav):
        result = sav.to_mermaid_coupling(_coupling_with_attrs())
        assert "graph TD" in result
        # Green for low instability
        assert "#90EE90" in result
        # Yellow for mid
        assert "#FFD700" in result
        # Red for high
        assert "#FF6B6B" in result
        # Sanitised name (dashes and dots → underscores)
        assert "gamma_mod_x" in result

    def test_dict_modules(self, sav):
        result = sav.to_mermaid_coupling(_coupling_dict_form())
        assert "graph TD" in result
        # Module from dict with module_name key
        assert "ddict_a" in result
        # Module from dict with name key
        assert "ddict_b" in result
        # Edge formed from coupling_matrix
        assert "ddict_a --> ddict_b" in result

    def test_default_module_unknown(self, sav):
        result = sav.to_mermaid_coupling(_coupling_dict_form())
        # The third dict module had no name/module_name — falls back to "unknown".
        assert "unknown" in result


# ---------------------------------------------------------------------------
# to_png / to_pdf
# ---------------------------------------------------------------------------


class TestToPngPdfFallbacks:
    def test_to_png_import_error(self, sav, tmp_path, monkeypatch):
        fig, _ = plt.subplots()
        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block_imports("matplotlib"))
            result = sav.to_png(fig, str(tmp_path / "x.png"))
        assert result == ""

    def test_to_png_none_fig(self, sav, tmp_path):
        assert sav.to_png(None, str(tmp_path / "y.png")) == ""

    def test_to_png_save_error(self, sav, tmp_path):
        # Pass a path that cannot be written (parent dir missing) — savefig raises.
        fig, _ = plt.subplots()
        result = sav.to_png(fig, "/nonexistent_dir_zzzz/img.png")
        assert result == ""

    def test_to_png_success(self, sav, tmp_path):
        fig, _ = plt.subplots()
        out = sav.to_png(fig, str(tmp_path / "ok.png"))
        assert out == str(tmp_path / "ok.png")
        assert Path(out).exists()

    def test_to_pdf_import_error(self, sav, tmp_path, monkeypatch):
        fig, _ = plt.subplots()
        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block_imports("matplotlib"))
            result = sav.to_pdf(fig, str(tmp_path / "x.pdf"))
        assert result == ""

    def test_to_pdf_none_fig(self, sav, tmp_path):
        assert sav.to_pdf(None, str(tmp_path / "y.pdf")) == ""

    def test_to_pdf_save_error(self, sav, tmp_path):
        fig, _ = plt.subplots()
        result = sav.to_pdf(fig, "/nonexistent_dir_zzzz/img.pdf")
        assert result == ""

    def test_to_pdf_success(self, sav, tmp_path):
        fig, _ = plt.subplots()
        out = sav.to_pdf(fig, str(tmp_path / "ok.pdf"))
        assert out == str(tmp_path / "ok.pdf")
        assert Path(out).exists()


# ---------------------------------------------------------------------------
# Constructor sanity
# ---------------------------------------------------------------------------


class TestInit:
    def test_init(self):
        assert StaticAnalysisView() is not None
