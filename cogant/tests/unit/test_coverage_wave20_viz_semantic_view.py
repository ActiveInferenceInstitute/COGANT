"""Wave 20 coverage boost: viz/semantic_view.py — SemanticVisualizer.

Targets the remaining uncovered lines in semantic_view.py (84% → ~100%):
    95-98       to_dict(): __dict__ branch and bare-string fallback
    304-306     render_role_distribution import error
    350-352     render_role_distribution internal exception
    372-374     render_confidence_heatmap import error
    390/392/394/396  kind-routing branches in render_confidence_heatmap
    422-424     "no confidence values" branch
    447-449     render_confidence_heatmap internal exception
"""

from __future__ import annotations

import builtins
import json
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from cogant.viz.semantic_view import SemanticVisualizer

pytestmark = pytest.mark.unit


@pytest.fixture
def sv() -> SemanticVisualizer:
    return SemanticVisualizer()


@pytest.fixture(autouse=True)
def _close_matplotlib():
    yield
    plt.close("all")


def _block_imports(*prefixes: str):
    real_import = builtins.__import__

    def _block(name: str, *args: Any, **kwargs: Any) -> Any:
        for p in prefixes:
            if name.startswith(p):
                raise ImportError(f"blocked: {name}")
        return real_import(name, *args, **kwargs)

    return _block


# ---------------------------------------------------------------------------
# from_state_space + render_json basic
# ---------------------------------------------------------------------------


class TestFromStateSpaceAndJson:
    def test_from_state_space_returns_self(self, sv):
        out = sv.from_state_space({"states": [], "observations": []})
        assert out is sv

    def test_from_state_space_loads_all_lists(self, sv):
        sv.from_state_space(
            {
                "states": [{"name": "s1"}],
                "observations": [{"name": "o1"}],
                "actions": [{"name": "a1"}],
                "policies": [{"name": "p1"}],
                "transitions": [{"from": "s1", "to": "s1"}],
            }
        )
        assert sv.states and sv.observations and sv.actions
        assert sv.policies and sv.transitions

    def test_render_json_empty(self, sv):
        s = sv.render_json()
        data = json.loads(s)
        assert data == {
            "states": [],
            "observations": [],
            "actions": [],
            "policies": [],
            "transitions": [],
        }

    def test_render_json_round_trip(self, sv):
        sv.from_state_space({"states": [{"name": "s1"}]})
        data = json.loads(sv.render_json())
        assert data["states"][0]["name"] == "s1"


# ---------------------------------------------------------------------------
# _generate_html via render_html: dict / object / scalar branches
# ---------------------------------------------------------------------------


class TestGenerateHtml:
    def test_dict_items(self, sv, tmp_path):
        sv.from_state_space(
            {
                "states": [{"name": "S1", "description": "first", "type": "discrete"}],
                "observations": [{"name": "O1", "description": "obs", "source": "sensor"}],
                "actions": [{"name": "A1", "description": "act", "target": "actuator"}],
                "policies": [{"name": "P1", "rule": "if x then y", "confidence": 0.9}],
            }
        )
        out = str(tmp_path / "html_dict.html")
        sv.render_html(out)
        with open(out) as f:
            html = f.read()
        assert "S1" in html and "first" in html and "discrete" in html
        assert "O1" in html and "sensor" in html
        assert "A1" in html and "actuator" in html
        assert "P1" in html and "if x then y" in html
        assert "0.90" in html  # formatted confidence

    def test_object_items_via_dunder_dict(self, sv, tmp_path):
        """to_dict() falls through to ``vars(item)`` for objects with __dict__."""

        class _S:
            def __init__(self, name: str, desc: str, type_: str):
                self.name = name
                self.description = desc
                self.type = type_

        sv.states = [_S("OB1", "object-based state", "kind_x")]
        out = str(tmp_path / "html_objs.html")
        sv.render_html(out)
        with open(out) as f:
            html = f.read()
        assert "OB1" in html
        assert "object-based state" in html
        assert "kind_x" in html

    def test_scalar_items_fallback(self, sv, tmp_path):
        """Items that are neither dict nor have __dict__ fall back to {'name': str(item), ...}.

        Use a tuple — its __dict__ is missing, so the bare-string branch executes.
        """
        # Use objects without __dict__ (slots) to force the str() fallback.

        class _NoDict:
            __slots__ = ()

            def __str__(self) -> str:
                return "scalar_item_x"

        sv.states = [_NoDict()]
        out = str(tmp_path / "html_scalar.html")
        sv.render_html(out)
        with open(out) as f:
            html = f.read()
        assert "scalar_item_x" in html


# ---------------------------------------------------------------------------
# render_role_distribution
# ---------------------------------------------------------------------------


class TestRenderRoleDistribution:
    def test_import_error_returns_none(self, sv, monkeypatch):
        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block_imports("matplotlib"))
            assert sv.render_role_distribution([{"kind": "hidden_state"}]) is None

    def test_internal_exception_returns_none(self, sv):
        """Override list.get to blow up inside the role-counting loop."""

        class BoomMapping:
            def get(self, key, default=None):
                raise RuntimeError("boom")

        # Pass a list whose elements will explode on .get()
        result = sv.render_role_distribution([BoomMapping()])
        assert result is None

    def test_with_internal_state_no_mappings(self, sv):
        """Use internal state path (mappings=None) and verify dict counts."""
        sv.from_state_space(
            {
                "states": [{"name": "s1"}, {"name": "s2"}],
                "observations": [{"name": "o1"}],
                "actions": [],
                "policies": [{"name": "p1"}],
            }
        )
        fig = sv.render_role_distribution(None)
        assert fig is not None

    def test_all_zero_returns_none(self, sv):
        """When all role counts are zero the function bails out early."""
        # No internal data, no mappings → all four buckets are 0.
        assert sv.render_role_distribution() is None


# ---------------------------------------------------------------------------
# render_confidence_heatmap
# ---------------------------------------------------------------------------


class TestRenderConfidenceHeatmap:
    def test_import_error_returns_none(self, sv, monkeypatch):
        with monkeypatch.context() as m:
            m.setattr(builtins, "__import__", _block_imports("matplotlib", "numpy"))
            result = sv.render_confidence_heatmap([{"kind": "hidden_state"}])
        assert result is None

    def test_all_kind_branches(self, sv):
        """Mappings with each recognised kind exercise lines 390/392/394/396."""
        mappings = [
            {"kind": "hidden_state", "confidence": 0.55},
            {"kind": "observation", "confidence": 0.9},
            {"kind": "action", "confidence": 0.1},
            {"kind": "policy", "confidence": 0.7},
            # 'unknown' kind — none of the branches match.
            {"kind": "unknown", "confidence": 0.5},
        ]
        fig = sv.render_confidence_heatmap(mappings)
        assert fig is not None

    def test_internal_exception_returns_none(self, sv):
        class BoomMapping:
            def get(self, key, default=None):
                raise RuntimeError("boom")

        result = sv.render_confidence_heatmap([BoomMapping()])
        assert result is None

    def test_internal_state_path(self, sv):
        """When mappings is None, derive placeholder confidences from internal state."""
        sv.from_state_space(
            {
                "states": [{"name": "s1"}, {"name": "s2"}],
                "observations": [{"name": "o1"}],
                "actions": [{"name": "a1"}],
                "policies": [{"name": "p1"}],
            }
        )
        fig = sv.render_confidence_heatmap(None)
        assert fig is not None

    def test_empty_no_state_no_mappings(self, sv):
        """No internal state, no mappings → confidences all empty, but heatmap
        still rendered with zero rows (zeros)."""
        fig = sv.render_confidence_heatmap(None)
        assert fig is not None  # zero-array heatmap still produces a figure


# ---------------------------------------------------------------------------
# render_html basic round-trip (state attribute)
# ---------------------------------------------------------------------------


class TestRenderHtmlReturn:
    def test_render_html_returns_path(self, sv, tmp_path):
        out = str(tmp_path / "view.html")
        result = sv.render_html(out)
        assert result == out


# ---------------------------------------------------------------------------
# Constructor sanity
# ---------------------------------------------------------------------------


class TestInit:
    def test_init_empty(self):
        sv = SemanticVisualizer()
        assert sv.states == []
        assert sv.observations == []
        assert sv.actions == []
        assert sv.policies == []
        assert sv.transitions == []
