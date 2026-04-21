"""Unit tests for viz/gantt.py — GanttRenderer."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../py"))
import pytest

from cogant.viz.gantt import GanttRenderer


def _process_model() -> dict:
    return {
        "name": "test_pipeline",
        "stages": [
            {"id": "s1", "name": "ingest", "elapsed_s": 0.1, "status": "done"},
            {"id": "s2", "name": "graph", "elapsed_s": 0.5, "status": "done"},
        ],
        "transitions": [{"from": "s1", "to": "s2"}],
    }


@pytest.mark.unit
def test_from_process_model_returns_self():
    gr = GanttRenderer()
    result = gr.from_process_model(_process_model())
    assert result is gr


@pytest.mark.unit
def test_render_json_after_process_model():
    gr = GanttRenderer()
    gr.from_process_model(_process_model())
    j = gr.render_json()
    import json

    data = json.loads(j)
    assert isinstance(data, (dict, list))


@pytest.mark.unit
def test_render_html_creates_file(tmp_path):
    gr = GanttRenderer()
    gr.from_process_model(_process_model())
    out = str(tmp_path / "gantt.html")
    result = gr.render_html(out)
    assert result == out
    import os

    assert os.path.exists(out)


@pytest.mark.unit
def test_render_html_content_not_empty(tmp_path):
    gr = GanttRenderer()
    gr.from_process_model(_process_model())
    out = str(tmp_path / "gantt2.html")
    gr.render_html(out)
    content = open(out).read()
    assert len(content) > 0


@pytest.mark.unit
def test_render_json_empty_model():
    gr = GanttRenderer()
    gr.from_process_model({"name": "empty", "stages": [], "transitions": []})
    j = gr.render_json()
    assert j  # non-empty string


@pytest.mark.unit
def test_from_process_model_many_stages():
    gr = GanttRenderer()
    stages = [{"id": f"s{i}", "name": f"stage{i}", "elapsed_s": float(i) * 0.1} for i in range(10)]
    gr.from_process_model({"name": "big", "stages": stages, "transitions": []})
    j = gr.render_json()
    assert j


@pytest.mark.unit
def test_renderer_init_creates_instance():
    gr = GanttRenderer()
    assert gr is not None
