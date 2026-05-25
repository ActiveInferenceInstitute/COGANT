"""Tests for artifact-first COGANT inspection dashboards."""

from __future__ import annotations

import json
from pathlib import Path

from cogant.viz.inspection_dashboard import (
    build_inspection_model,
    render_graphical_abstract_svg,
    render_inspection_dashboard_html,
    render_interpretability_detail_pngs,
    write_inspection_artifacts,
)

_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
    b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_run_fixture(run_dir: Path) -> None:
    _write_json(
        run_dir / "data" / "program_graph.json",
        {
            "nodes": {
                "module": {"id": "module", "kind": "module", "name": "calculator"},
                "class": {"id": "class", "kind": "class", "name": "Calculator"},
                "method": {"id": "method", "kind": "method", "name": "input_digit"},
            },
            "edges": {
                "e1": {"id": "e1", "source_id": "module", "target_id": "class", "kind": "contains"},
                "e2": {"id": "e2", "source_id": "class", "target_id": "method", "kind": "contains"},
            },
        },
    )
    _write_json(
        run_dir / "gnn_package" / "model.gnn.json",
        {
            "mappings": {
                "summary": {
                    "total_mappings": 2,
                    "mapping_kinds": {"hidden_state": 1, "action": 1},
                    "confidence_tiers": {"static_only": 2},
                    "status_distribution": {"auto_proposed": 2},
                },
                "mappings": {
                    "m1": {
                        "id": "m1",
                        "kind": "hidden_state",
                        "semantic_label": "Calculator - Hidden State",
                        "confidence_score": 0.72,
                        "status": "auto_proposed",
                    },
                    "m2": {
                        "id": "m2",
                        "kind": "action",
                        "semantic_label": "input_digit - Action",
                        "confidence_score": 0.63,
                        "status": "auto_proposed",
                    },
                },
            },
            "matrices": {
                "shapes": {"A": [1, 1], "B": [1, 1, 1], "C": [1], "D": [1]},
                "dimensions": {"n_states": 1, "n_obs": 1, "n_actions": 1},
            },
            "confidence": {"overall_confidence": 0.5},
            "source_coverage": {"coverage_percentage": 100.0},
            "validation_notes": {"validation_status": "valid", "last_validated": "2026-05-13"},
        },
    )
    _write_json(
        run_dir / "gnn_package" / "state_space.json",
        {
            "variables": [{"id": "v1"}],
            "observations": [{"id": "o1"}],
            "actions": [{"id": "a1"}],
            "transitions": {"transition_count": 1, "time_regime": "synchronous"},
            "metadata": {"num_variables": 1, "num_observations": 1, "num_actions": 1},
        },
    )
    _write_json(
        run_dir / "gnn_package" / "markov_blanket.json",
        {
            "stats": {
                "internal_count": 1,
                "sensory_count": 1,
                "active_count": 0,
                "external_count": 1,
            },
            "roles": {
                "internal": [{"id": "method"}],
                "sensory": [{"id": "class"}],
                "active": [],
                "external": [{"id": "module"}],
            },
        },
    )
    _write_json(
        run_dir / "gnn_package" / "manifest.json",
        {
            "timestamp": "2026-05-13T12:00:00Z",
            "graph_stats": {"nodes": 3, "edges": 2},
            "state_space_stats": {"variables": 1, "observations": 1, "actions": 1},
        },
    )
    _write_json(
        run_dir / "analysis" / "graph_hotspots.json",
        {"hubs": [["class", 2]], "bottlenecks": [["class", 0.75]]},
    )
    _write_json(
        run_dir / "data" / "rule_evidence_trace.json",
        {
            "schema_version": "1.0",
            "generated_at": "2026-05-13T12:00:00Z",
            "mapping_count": 2,
            "rule_summary": {"action": 1, "mutating_subsystem": 1},
            "kind_summary": {"ACTION": 1, "HIDDEN_STATE": 1},
            "confidence_tier_summary": {"static_only": 2},
            "mappings": [
                {
                    "id": "m1",
                    "rule_id": "mutating_subsystem",
                    "confidence_score": 0.72,
                    "confidence_tier": "static_only",
                    "final_mapping_status": "proposed",
                    "review": {"status": "auto_proposed"},
                },
                {
                    "id": "m2",
                    "rule_id": "action",
                    "confidence_score": 0.63,
                    "confidence_tier": "static_only",
                    "final_mapping_status": "proposed",
                    "review": {"status": "auto_proposed"},
                },
            ],
            "conflict_events": [{"id": "c1", "status": "resolved"}],
            "calibration": {
                "per_rule": [
                    {
                        "rule_id": "action",
                        "total": 1,
                        "reviewed": 0,
                        "precision_proxy": None,
                        "review_coverage": 0.0,
                    },
                    {
                        "rule_id": "mutating_subsystem",
                        "total": 1,
                        "reviewed": 0,
                        "precision_proxy": None,
                        "review_coverage": 0.0,
                    },
                ]
            },
        },
    )
    (run_dir / "reports").mkdir(parents=True, exist_ok=True)
    (run_dir / "reports" / "run_summary.md").write_text("# summary\n", encoding="utf-8")
    (run_dir / "roundtrip" / "forward").mkdir(parents=True, exist_ok=True)
    (run_dir / "roundtrip" / "forward" / "model.gnn.md").write_text(
        "# model\n", encoding="utf-8"
    )
    (run_dir / "roundtrip" / "reverse" / "calculator").mkdir(parents=True, exist_ok=True)
    (run_dir / "roundtrip" / "reverse" / "calculator" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    _write_json(
        run_dir / "roundtrip" / "metrics.json",
        {
            "schema_version": "2.0",
            "generated_at": "2026-05-13T12:00:00Z",
            "roundtrip_status": "STRUCTURALLY_ISOMORPHIC",
            "role_preservation_score": 1.0,
            "role_preserved": True,
            "structurally_isomorphic": True,
            "matrix_score": 0.5,
            "structural_score": 1.0,
            "role_confusion": [
                {"role": "ACTION", "original": 1, "synthesized": 1, "delta": 0},
                {"role": "HIDDEN_STATE", "original": 1, "synthesized": 1, "delta": 0},
            ],
            "graph_edit_distance": {"missing": 0, "extra": 0, "distance": 0, "normalized": 0.0},
            "generated_code": {
                "status": "passed",
                "compile_status": "passed",
                "test_status": "passed",
            },
            "original_roles": {"HIDDEN_STATE": 1, "ACTION": 1},
            "synthesized_roles": {"HIDDEN_STATE": 1, "ACTION": 1},
            "shape_match": {"n_states": True, "n_obs": True},
            "package_path": str(run_dir / "roundtrip" / "reverse" / "calculator"),
            "errors": [],
            "threshold": 0.5,
        },
    )
    (run_dir / "site").mkdir(parents=True, exist_ok=True)
    (run_dir / "site" / "index.html").write_text(
        "<html><body><nav><ul><li><a href=\"index.html\">Overview</a></li></ul></nav></body></html>",
        encoding="utf-8",
    )
    (run_dir / "figures").mkdir(parents=True, exist_ok=True)
    (run_dir / "figures" / "program_graph.png").write_bytes(_PNG_1X1)


def test_build_inspection_model_summarizes_run_artifacts(tmp_path):
    _write_run_fixture(tmp_path)

    model = build_inspection_model(tmp_path)

    assert model["program"]["nodes"] == 3
    assert model["program"]["edges"] == 2
    assert model["semantic"]["total"] == 2
    assert model["state_space"]["actions"] == 1
    assert model["matrices"]["shapes"]["B"] == "1 x 1 x 1"
    assert model["roundtrip"]["status"] == "structurally_isomorphic"
    assert model["roundtrip"]["role_preservation_score"] == 1.0
    assert model["roundtrip"]["generated_code"]["status"] == "passed"
    assert model["roundtrip"]["original_roles"]["ACTION"] == 1
    assert model["hotspots"][0]["label"] == "Calculator"


def test_render_graphical_abstract_svg_writes_visual_chain(tmp_path):
    _write_run_fixture(tmp_path)

    svg = render_graphical_abstract_svg(tmp_path)

    text = svg.read_text(encoding="utf-8")
    assert "COGANT graphical abstract" in text
    assert "Program Graph" in text
    assert "Roundtrip" in text
    assert "100%" in text


def test_render_inspection_dashboard_html_writes_embedded_dashboard(tmp_path):
    _write_run_fixture(tmp_path)

    html = render_inspection_dashboard_html(tmp_path, embed_assets=False)

    text = html.read_text(encoding="utf-8")
    assert "COGANT Inspection Dashboard" in text
    assert "Graphical Abstract" in text
    assert "Visual Evidence" in text
    assert "Roundtrip Diagnostics" in text
    assert "Role preservation" in text
    assert "Generated code" in text
    assert "Calculator - Hidden State" in text
    assert "Inspection dashboard" in text
    assert "present" in text
    assert "inspection_dashboard.html" in (tmp_path / "site" / "index.html").read_text(
        encoding="utf-8"
    )


def test_write_inspection_artifacts_returns_dashboard_and_abstract(tmp_path):
    _write_run_fixture(tmp_path)

    written = write_inspection_artifacts(tmp_path, embed_assets=False)

    assert written["inspection_dashboard_html"].is_file()
    assert written["graphical_abstract_svg"].is_file()
    assert set(written).issuperset({"inspection_dashboard_html", "graphical_abstract_svg"})


def test_render_detail_pngs_records_evidence_coverage_counts(tmp_path):
    _write_run_fixture(tmp_path)

    written = render_interpretability_detail_pngs(tmp_path)

    assert written["confidence_calibration"].is_file()
    svg_text = (tmp_path / "figures" / "confidence_calibration.svg").read_text(
        encoding="utf-8"
    )
    assert "Evidence coverage and review-readiness" in svg_text
    assert "0 reviewed mapping rows" in svg_text
    sidecar = json.loads(
        (tmp_path / "figures" / "confidence_calibration.figure.json").read_text(
            encoding="utf-8"
        )
    )
    assert sidecar["displayed_counts"]["mappings"] == 2
    assert sidecar["displayed_counts"]["reviewed_mapping_rows"] == 0
    assert sidecar["displayed_counts"]["unreviewed_mapping_rows"] == 2
    assert sidecar["displayed_counts"]["conflict_events"] == 1
