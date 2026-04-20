"""Tests for PipelineVisualizer.render_stage_outputs (previously stub)."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def visualizer():
    from cogant.viz.pipeline_view import PipelineVisualizer
    return PipelineVisualizer()


# ---------------------------------------------------------------------------
# render_stage_outputs
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_render_stage_outputs_with_full_data(visualizer):
    result = visualizer.render_stage_outputs({
        "node_counts": {"ingest": 0, "graph": 42, "translate": 42},
        "edge_counts": {"ingest": 0, "graph": 87, "translate": 87},
        "rule_firings": {"translate": 22},
        "validation_findings": {"validate": 3},
    })
    assert result is not None
    result.clf()
    import matplotlib.pyplot as plt
    plt.close("all")


@pytest.mark.unit
def test_render_stage_outputs_empty_dict(visualizer):
    result = visualizer.render_stage_outputs({})
    assert result is not None
    import matplotlib.pyplot as plt
    plt.close("all")


@pytest.mark.unit
def test_render_stage_outputs_partial_data(visualizer):
    result = visualizer.render_stage_outputs({"node_counts": {"ingest": 10}})
    assert result is not None
    import matplotlib.pyplot as plt
    plt.close("all")


@pytest.mark.unit
def test_render_stage_outputs_findings_as_list(visualizer):
    result = visualizer.render_stage_outputs({
        "validation_findings": ["err1", "err2", "err3"],
    })
    assert result is not None
    import matplotlib.pyplot as plt
    plt.close("all")


@pytest.mark.unit
def test_render_stage_outputs_stage_results_nested(visualizer):
    result = visualizer.render_stage_outputs({
        "stage_results": {
            "graph": {"node_count": 30, "edge_count": 60},
            "translate": {"rule_firings": 18, "node_count": 30},
            "validate": {"findings": ["f1", "f2"]},
        }
    })
    assert result is not None
    import matplotlib.pyplot as plt
    plt.close("all")


@pytest.mark.unit
def test_render_stage_outputs_object_input(visualizer):
    class _Res:
        node_counts = {"ingest": 5, "graph": 20}
        edge_counts = {"graph": 40}
        rule_firings = None
        validation_findings = None
        findings = None
        stage_results = None
        stage_timings = None
        timing = None
        node_count_by_stage = None
        edge_count_by_stage = None

    result = visualizer.render_stage_outputs(_Res())
    assert result is not None
    import matplotlib.pyplot as plt
    plt.close("all")


@pytest.mark.unit
def test_render_stage_outputs_returns_none_on_import_error(visualizer, monkeypatch):
    import builtins
    real_import = builtins.__import__

    def _block(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith("matplotlib"):
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(builtins, "__import__", _block)
        result = visualizer.render_stage_outputs({})

    assert result is None
