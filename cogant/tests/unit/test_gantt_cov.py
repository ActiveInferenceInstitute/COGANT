"""Behavioral tests for cogant.viz.gantt.GanttRenderer.

Exercises the dict-based loader, the typed Timeline loader, JSON export,
HTML rendering, critical-path marking, and parallel-group legend
generation. All fixtures are plain Python data — no mocks.
"""

from __future__ import annotations

import json
from pathlib import Path

from cogant.process.timeline import GanttStage, Timeline
from cogant.viz.gantt import GanttRenderer

# ---------------------------- fixtures ----------------------------------- #


def _basic_process_model() -> dict:
    return {
        "stages": [
            {"id": "s1", "name": "Parse", "start": 0, "duration": 2},
            {"id": "s2", "name": "Analyze", "start": 2, "duration": 3},
            {"id": "s3", "name": "Render", "start": 5, "duration": 1},
        ],
        "dependencies": [
            {"from": "s1", "to": "s2", "type": "sequential"},
            {"from": "s2", "to": "s3", "type": "sequential"},
        ],
        "timeline": [],
        "critical_path": ["s1", "s2", "s3"],
        "parallel_groups": [],
    }


# ---------------------------- construction ------------------------------- #


def test_default_renderer_is_empty():
    """Construction yields empty collections."""
    r = GanttRenderer()
    assert r.stages == []
    assert r.dependencies == []
    assert r.timeline == []
    assert r.critical_path == []
    assert r.parallel_groups == []


def test_from_process_model_populates_state_and_returns_self():
    """from_process_model returns self (chainable) and copies all fields."""
    r = GanttRenderer()
    returned = r.from_process_model(_basic_process_model())
    assert returned is r
    assert len(r.stages) == 3
    assert r.critical_path == ["s1", "s2", "s3"]
    assert [d["from"] for d in r.dependencies] == ["s1", "s2"]


def test_from_process_model_defaults_missing_keys_to_empty():
    """Missing keys default to empty lists."""
    r = GanttRenderer().from_process_model({})
    assert r.stages == []
    assert r.dependencies == []
    assert r.critical_path == []
    assert r.parallel_groups == []


# ---------------------------- from_timeline ------------------------------ #


def test_from_timeline_copies_typed_timeline_fields():
    """A typed Timeline is translated into stage/critical/parallel state."""
    timeline = Timeline(
        stages=[
            GanttStage(
                stage_id="t1",
                name="Task 1",
                start_time=0.0,
                duration=2.0,
                dependencies=[],
                criticality=1.0,
            ),
            GanttStage(
                stage_id="t2",
                name="Task 2",
                start_time=2.0,
                duration=3.0,
                dependencies=["t1"],
                criticality=0.5,
            ),
        ],
        total_duration=5.0,
        critical_path=["t1", "t2"],
        parallel_groups=[["t1"]],
    )

    r = GanttRenderer().from_timeline(timeline)

    assert [s["id"] for s in r.stages] == ["t1", "t2"]
    assert r.stages[0]["name"] == "Task 1"
    assert r.stages[0]["duration"] == 2.0
    assert r.critical_path == ["t1", "t2"]
    assert r.parallel_groups == [["t1"]]
    # from_timeline clears dependencies/timeline
    assert r.dependencies == []
    assert r.timeline == []


# ---------------------------- JSON export -------------------------------- #


def test_render_json_round_trips_state():
    """render_json produces valid JSON that matches the loaded state."""
    r = GanttRenderer().from_process_model(_basic_process_model())
    raw = r.render_json()
    payload = json.loads(raw)

    assert set(payload) == {
        "stages",
        "dependencies",
        "timeline",
        "critical_path",
        "parallel_groups",
    }
    assert [s["id"] for s in payload["stages"]] == ["s1", "s2", "s3"]
    assert payload["critical_path"] == ["s1", "s2", "s3"]


def test_render_json_empty_renderer_is_valid_json():
    """Empty renderer produces a well-formed but empty-valued JSON document."""
    payload = json.loads(GanttRenderer().render_json())
    assert payload["stages"] == []
    assert payload["dependencies"] == []


# ---------------------------- HTML rendering ----------------------------- #


def test_render_html_writes_file_with_expected_content(tmp_path: Path):
    """render_html writes a file containing stage names and dependency info."""
    r = GanttRenderer().from_process_model(_basic_process_model())
    out = tmp_path / "gantt.html"

    returned = r.render_html(str(out))

    assert returned == str(out)
    content = out.read_text()
    assert "<html>" in content
    assert "Parse" in content
    assert "Analyze" in content
    assert "Render" in content
    # Dependency block
    assert "s1" in content and "s2" in content
    # Critical-path marker injected on critical stages
    assert "CP" in content or "critical" in content


def test_render_html_with_parallel_groups_emits_legend(tmp_path: Path):
    """Parallel groups produce the Parallel Groups legend section."""
    model = _basic_process_model()
    model["parallel_groups"] = [["s1", "s2"]]
    out = tmp_path / "gantt.html"

    GanttRenderer().from_process_model(model).render_html(str(out))
    content = out.read_text()

    assert "Parallel Groups" in content


def test_render_html_escapes_html_in_stage_names(tmp_path: Path):
    """Stage names containing HTML are properly escaped."""
    model = {
        "stages": [{"id": "s1", "name": "<script>alert(1)</script>", "start": 0, "duration": 1}],
        "dependencies": [],
    }
    out = tmp_path / "escape.html"

    GanttRenderer().from_process_model(model).render_html(str(out))
    content = out.read_text()

    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;" in content


# ---------------------------- empty input -------------------------------- #


def test_render_html_with_no_stages_still_writes_file(tmp_path: Path):
    """Rendering an empty model still produces a valid HTML file."""
    out = tmp_path / "empty.html"
    path = GanttRenderer().render_html(str(out))
    assert Path(path).exists()
    content = out.read_text()
    assert "Process Model" in content
