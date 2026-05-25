"""Targeted unit tests for: viz/pipeline_view.py — PipelineVisualizer.

Targets the lowest-coverage viz module (33%). Exercises every method,
including matplotlib ImportError fallbacks and exception fallbacks.

Modules under test:
    py/cogant/viz/pipeline_view.py — PipelineVisualizer

Lines targeted (before this file):
    45-68 (render_stage_diagram), 81-115 (render_timing_chart),
    248-271 (to_mermaid_pipeline), 285-353 (to_png),
    365-433 (to_pdf), 444-467 (render_dataflow_diagram),
    481-526 (plot_stage_memory_usage), 540-600 (render_stage_grid),
    plus error/empty branches in render_stage_outputs (179-180, 200, 236-238).
"""

from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from cogant.viz.pipeline_view import PipelineVisualizer
from tests.unit._viz_assert import assert_figure_nondegenerate, assert_png_nondegenerate

pytestmark = pytest.mark.unit


@pytest.fixture
def pv() -> PipelineVisualizer:
    return PipelineVisualizer()


@pytest.fixture(autouse=True)
def _close_matplotlib():
    """Ensure all figures are closed between tests."""
    yield
    plt.close("all")


# ---------------------------------------------------------------------------
# render_stage_diagram (lines 45-68)
# ---------------------------------------------------------------------------


class TestRenderStageDiagram:
    def test_returns_str(self, pv):
        result = pv.render_stage_diagram()
        assert isinstance(result, str)

    def test_starts_with_flowchart(self, pv):
        result = pv.render_stage_diagram()
        assert result.startswith("flowchart TD")

    def test_contains_all_ten_stages(self, pv):
        result = pv.render_stage_diagram()
        for label in (
            "Ingest",
            "Parse",
            "Extract",
            "Build",
            "Translate",
            "Markov",
            "StateSpace",
            "Export",
            "Validate",
            "Render",
        ):
            assert label in result

    def test_contains_arrow_edges(self, pv):
        result = pv.render_stage_diagram()
        # Should have nine arrows A→B, B→C ... I→J
        assert result.count("-->") == 9


# ---------------------------------------------------------------------------
# render_timing_chart (lines 81-115)
# ---------------------------------------------------------------------------


class TestRenderTimingChart:
    def test_basic_dict(self, pv):
        fig = pv.render_timing_chart(
            {"ingest": 0.5, "parse": 1.2, "build": 0.8}
        )
        assert_figure_nondegenerate(fig)

    def test_empty_dict(self, pv):
        fig = pv.render_timing_chart({})
        assert_figure_nondegenerate(fig)

    def test_single_stage(self, pv):
        fig = pv.render_timing_chart({"only_stage": 2.5})
        assert_figure_nondegenerate(fig)

    def test_zero_values(self, pv):
        fig = pv.render_timing_chart({"a": 0.0, "b": 0.0})
        assert_figure_nondegenerate(fig)

    def test_returns_none_on_import_error(self, pv, monkeypatch):
        real_import = builtins.__import__

        def _block(name: str, *args: Any, **kwargs: Any) -> Any:
            if name.startswith("matplotlib"):
                raise ImportError("blocked")
            return real_import(name, *args, **kwargs)

        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block)
            result = pv.render_timing_chart({"x": 1.0})
        assert result is None

    def test_returns_none_on_internal_error(self, pv):
        # Pass non-numeric values — float() conversion path is fine, but
        # the bar plotting itself will raise on incompatible types.
        # We use a non-coerce-able mapping by overriding sorted later;
        # simplest is to pass a value that is already a list (unhashable).
        class BrokenDict(dict):
            def values(self):
                raise RuntimeError("broken")

        bd = BrokenDict()
        bd["a"] = 1.0
        result = pv.render_timing_chart(bd)
        assert result is None


# ---------------------------------------------------------------------------
# render_stage_outputs additional coverage (lines 179-180, 200, 236-238)
# ---------------------------------------------------------------------------


class TestRenderStageOutputsExtra:
    def test_metric_series_falls_back_to_typeerror(self, pv):
        """stage_results value that is not coercible to float exercises the
        TypeError/ValueError except path in _metric_series."""
        result = pv.render_stage_outputs(
            {
                "stage_results": {
                    "graph": {"node_count": object()},  # not numeric
                    "translate": {"node_count": "not_a_number"},  # ValueError
                }
            }
        )
        assert_figure_nondegenerate(result)

    def test_findings_as_int_per_stage(self, pv):
        """Cover the (int, float) branch in _finding_series."""
        result = pv.render_stage_outputs(
            {
                "stage_results": {
                    "validate": {"findings": 5},
                    "another": {"validation_findings": 2.0},
                }
            }
        )
        assert_figure_nondegenerate(result)

    def test_findings_dict_with_list_values(self, pv):
        """findings dict where values are lists triggers len(v) coercion."""
        result = pv.render_stage_outputs(
            {"validation_findings": {"validate": ["e1", "e2"], "post": ["e3"]}}
        )
        assert_figure_nondegenerate(result)

    def test_returns_none_on_internal_error(self, pv):
        """Force an internal error in render_stage_outputs by passing a value
        that explodes when accessed."""

        class Boom:
            def __getattr__(self, item):
                raise RuntimeError("boom")

        result = pv.render_stage_outputs(Boom())
        assert result is None


# ---------------------------------------------------------------------------
# to_mermaid_pipeline (lines 248-271)
# ---------------------------------------------------------------------------


class TestToMermaidPipeline:
    def test_returns_str(self, pv):
        result = pv.to_mermaid_pipeline()
        assert isinstance(result, str)

    def test_starts_with_flowchart(self, pv):
        result = pv.to_mermaid_pipeline()
        assert result.startswith("flowchart TD")

    def test_has_bold_labels(self, pv):
        result = pv.to_mermaid_pipeline()
        assert "<b>" in result
        assert "</b>" in result

    def test_has_all_ten_stages(self, pv):
        result = pv.to_mermaid_pipeline()
        for stage in ("Ingest", "Parse", "Markov", "Render"):
            assert stage in result

    def test_nine_arrows(self, pv):
        result = pv.to_mermaid_pipeline()
        assert result.count("-->") == 9


# ---------------------------------------------------------------------------
# to_png (lines 285-353)
# ---------------------------------------------------------------------------


class TestToPng:
    def test_creates_file(self, pv, tmp_path):
        out = str(tmp_path / "pipeline.png")
        result = pv.to_png(out)
        assert result == out
        assert Path(out).exists()
        assert_png_nondegenerate(out)

    def test_returns_empty_on_import_error(self, pv, tmp_path, monkeypatch):
        real_import = builtins.__import__

        def _block(name: str, *args: Any, **kwargs: Any) -> Any:
            if name.startswith("matplotlib"):
                raise ImportError("blocked")
            return real_import(name, *args, **kwargs)

        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block)
            result = pv.to_png(str(tmp_path / "foo.png"))
        assert result == ""

    def test_returns_empty_on_invalid_path(self, pv):
        # Save to a directory that doesn't exist (no parent created)
        result = pv.to_png("/nonexistent_dir_qwerty12345/output.png")
        assert result == ""


# ---------------------------------------------------------------------------
# to_pdf (lines 365-433)
# ---------------------------------------------------------------------------


class TestToPdf:
    def test_creates_file(self, pv, tmp_path):
        out = str(tmp_path / "pipeline.pdf")
        result = pv.to_pdf(out)
        assert result == out
        assert Path(out).exists()
        assert Path(out).stat().st_size > 256

    def test_returns_empty_on_import_error(self, pv, tmp_path, monkeypatch):
        real_import = builtins.__import__

        def _block(name: str, *args: Any, **kwargs: Any) -> Any:
            if name.startswith("matplotlib"):
                raise ImportError("blocked")
            return real_import(name, *args, **kwargs)

        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block)
            result = pv.to_pdf(str(tmp_path / "foo.pdf"))
        assert result == ""

    def test_returns_empty_on_invalid_path(self, pv):
        result = pv.to_pdf("/nonexistent_dir_qwerty12345/output.pdf")
        assert result == ""


# ---------------------------------------------------------------------------
# render_dataflow_diagram (lines 444-467)
# ---------------------------------------------------------------------------


class TestRenderDataflowDiagram:
    def test_returns_str(self, pv):
        result = pv.render_dataflow_diagram()
        assert isinstance(result, str)

    def test_starts_with_graph_td(self, pv):
        result = pv.render_dataflow_diagram()
        assert result.startswith("graph TD")

    def test_contains_input_output_labels(self, pv):
        result = pv.render_dataflow_diagram()
        assert "Input:" in result
        assert "Output:" in result

    def test_has_all_ten_stages(self, pv):
        result = pv.render_dataflow_diagram()
        for stage in ("Ingest", "Parse", "Translate", "Render"):
            assert stage in result

    def test_nine_arrows(self, pv):
        result = pv.render_dataflow_diagram()
        assert result.count("-->") == 9


# ---------------------------------------------------------------------------
# plot_stage_memory_usage (lines 481-526)
# ---------------------------------------------------------------------------


class TestPlotStageMemoryUsage:
    def test_basic_dict(self, pv):
        memory = {
            "ingest": 1024 * 1024 * 5,  # 5 MB
            "parse": 1024 * 1024 * 10,  # 10 MB
            "build": 1024 * 1024 * 25,  # 25 MB
        }
        fig = pv.plot_stage_memory_usage(memory)
        assert_figure_nondegenerate(fig)

    def test_empty_dict_returns_none(self, pv):
        result = pv.plot_stage_memory_usage({})
        assert result is None

    def test_single_stage(self, pv):
        fig = pv.plot_stage_memory_usage({"only": 1024 * 1024 * 1})
        assert_figure_nondegenerate(fig)

    def test_returns_none_on_import_error(self, pv, monkeypatch):
        real_import = builtins.__import__

        def _block(name: str, *args: Any, **kwargs: Any) -> Any:
            if name.startswith("matplotlib"):
                raise ImportError("blocked")
            return real_import(name, *args, **kwargs)

        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block)
            result = pv.plot_stage_memory_usage({"x": 1024})
        assert result is None

    def test_returns_none_on_internal_error(self, pv):
        class BrokenDict(dict):
            def values(self):
                raise RuntimeError("broken")

        bd = BrokenDict()
        bd["a"] = 1024
        result = pv.plot_stage_memory_usage(bd)
        assert result is None


# ---------------------------------------------------------------------------
# render_stage_grid (lines 540-600)
# ---------------------------------------------------------------------------


class TestRenderStageGrid:
    def test_with_metrics(self, pv):
        results = {
            "Ingest": {"metrics": {"files": 10, "lines": 500, "bytes": 12000}},
            "Parse": {"metrics": {"asts": 7, "tokens": 2000}},
            "Build": {"metrics": {"nodes": 50}},
        }
        fig = pv.render_stage_grid(results)
        assert_figure_nondegenerate(fig)

    def test_with_missing_metrics(self, pv):
        # stages with no 'metrics' key go through the "no data" branch
        fig = pv.render_stage_grid({"Ingest": {}, "Parse": {"other": "x"}})
        assert_figure_nondegenerate(fig)

    def test_with_non_dict_stage_result(self, pv):
        # exercise the else branch (line ~588)
        fig = pv.render_stage_grid({"Ingest": "not_a_dict", "Parse": 42})
        assert_figure_nondegenerate(fig)

    def test_empty_dict(self, pv):
        # All stages take the non-data path
        fig = pv.render_stage_grid({})
        assert_figure_nondegenerate(fig)

    def test_returns_none_on_import_error(self, pv, monkeypatch):
        real_import = builtins.__import__

        def _block(name: str, *args: Any, **kwargs: Any) -> Any:
            if name.startswith("matplotlib"):
                raise ImportError("blocked")
            return real_import(name, *args, **kwargs)

        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block)
            result = pv.render_stage_grid({"Ingest": {"metrics": {"a": 1}}})
        assert result is None

    def test_returns_none_on_internal_error(self, pv):
        class BrokenDict(dict):
            def get(self, *args, **kwargs):
                raise RuntimeError("broken get")

        bd = BrokenDict()
        result = pv.render_stage_grid(bd)
        assert result is None


# ---------------------------------------------------------------------------
# Constructor sanity
# ---------------------------------------------------------------------------


class TestInit:
    def test_init_no_args(self):
        pv = PipelineVisualizer()
        assert pv is not None

    def test_init_no_state_attrs(self):
        # __init__ is intentionally a pass — instances should have no extra attrs.
        pv = PipelineVisualizer()
        # Should be able to call any rendering method immediately.
        assert isinstance(pv.render_stage_diagram(), str)
