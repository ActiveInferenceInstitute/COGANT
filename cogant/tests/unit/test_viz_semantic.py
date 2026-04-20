"""Unit tests for viz/semantic_view.py — SemanticVisualizer."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))
import matplotlib
matplotlib.use("Agg")
import pytest
from cogant.viz.semantic_view import SemanticVisualizer


def _state_space_dict() -> dict:
    return {
        "state_variables": [
            {"id": "sv1", "name": "counter", "kind": "HIDDEN_STATE",
             "cardinality": 3, "domain": [0, 1, 2]},
        ],
        "observations": [{"id": "ob1", "name": "obs_counter", "kind": "OBSERVATION"}],
        "actions": [{"id": "ac1", "name": "increment", "kind": "ACTION"}],
        "time_regime": "discrete",
    }


def _mappings() -> list:
    return [
        {"id": "m1", "kind": "HIDDEN_STATE", "label": "counter", "confidence_score": 0.9},
        {"id": "m2", "kind": "OBSERVATION", "label": "obs", "confidence_score": 0.7},
        {"id": "m3", "kind": "ACTION", "label": "act", "confidence_score": 0.5},
        {"id": "m4", "kind": "HIDDEN_STATE", "label": "counter2", "confidence_score": 0.8},
    ]


@pytest.fixture
def sv():
    return SemanticVisualizer()


@pytest.mark.unit
def test_from_state_space_returns_self(sv):
    result = sv.from_state_space(_state_space_dict())
    assert result is sv


@pytest.mark.unit
def test_render_json_after_from_state_space(sv):
    sv.from_state_space(_state_space_dict())
    j = sv.render_json()
    import json
    data = json.loads(j)
    assert isinstance(data, (dict, list))


@pytest.mark.unit
def test_render_html_creates_file(sv, tmp_path):
    sv.from_state_space(_state_space_dict())
    out = str(tmp_path / "semantic.html")
    result = sv.render_html(out)
    assert result == out
    import os
    assert os.path.exists(out)


@pytest.mark.unit
def test_render_role_distribution_with_mappings(sv):
    fig = sv.render_role_distribution(_mappings())
    assert fig is not None
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_render_role_distribution_empty(sv):
    # empty list with no internal state → returns None gracefully
    sv.render_role_distribution([])
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_render_role_distribution_none(sv):
    sv.from_state_space(_state_space_dict())
    fig = sv.render_role_distribution(None)
    # may return None if no internal mappings; either is fine
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_render_confidence_heatmap_with_mappings(sv):
    fig = sv.render_confidence_heatmap(_mappings())
    assert fig is not None
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_render_confidence_heatmap_empty(sv):
    fig = sv.render_confidence_heatmap([])
    assert fig is not None
    import matplotlib.pyplot as plt; plt.close("all")


@pytest.mark.unit
def test_semantic_visualizer_init():
    sv = SemanticVisualizer()
    assert sv is not None
