"""Unit tests for viz/diff_view.py — DiffVisualizer."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))
import pytest

from cogant.viz.diff_view import DiffVisualizer


def _bundle_a() -> dict:
    return {
        "target": "pkg_a",
        "stage_results": {
            "ingest": {"node_count": 10, "edge_count": 15},
            "translate": {"rule_firings": 8, "hidden_states": 3},
        },
        "errors": [],
        "score": 0.85,
    }


def _bundle_b() -> dict:
    return {
        "target": "pkg_a",
        "stage_results": {
            "ingest": {"node_count": 12, "edge_count": 17},
            "translate": {"rule_firings": 9, "hidden_states": 4},
        },
        "errors": [],
        "score": 0.90,
    }


@pytest.fixture
def dv():
    return DiffVisualizer(_bundle_a(), _bundle_b())


@pytest.mark.unit
def test_init_creates_instance():
    dv = DiffVisualizer(_bundle_a(), _bundle_b())
    assert dv is not None


@pytest.mark.unit
def test_init_identical_bundles():
    b = _bundle_a()
    dv = DiffVisualizer(b, b)
    assert dv is not None


@pytest.mark.unit
def test_init_empty_bundles():
    dv = DiffVisualizer({}, {})
    assert dv is not None


@pytest.mark.unit
def test_render_json_returns_valid_json(dv):
    import json

    j = dv.render_json()
    assert isinstance(j, str)
    data = json.loads(j)
    assert isinstance(data, (dict, list))


@pytest.mark.unit
def test_render_json_empty():
    dv = DiffVisualizer({}, {})
    import json

    j = dv.render_json()
    assert isinstance(j, str)
    json.loads(j)


@pytest.mark.unit
def test_render_html_creates_file(dv, tmp_path):
    out = str(tmp_path / "diff.html")
    result = dv.render_html(out)
    assert result == out
    import os

    assert os.path.exists(out)


@pytest.mark.unit
def test_render_html_content_not_empty(dv, tmp_path):
    out = str(tmp_path / "diff2.html")
    dv.render_html(out)
    content = open(out).read()
    assert len(content) > 0
