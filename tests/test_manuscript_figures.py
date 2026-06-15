from __future__ import annotations

import json
import sys
import zlib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import audit_figure_renderers as afr  # noqa: E402
from manuscript_figures import (  # noqa: E402
    MANUSCRIPT_FIGURES,
    ManuscriptFigure,
    _artifact_summary,
    _render_publication_batch_timeline,
    copy_manuscript_figures,
)


def _write_test_png(path: Path, *, width: int = 1200, height: int = 600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return len(payload).to_bytes(4, "big") + kind + payload + b"\x00\x00\x00\x00"

    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x06\x00\x00\x00"
    )
    rows = []
    for y in range(height):
        row = bytearray(b"\x00")
        for x in range(width):
            row.extend((x % 256, y % 256, (x + y) % 256, 255))
        rows.append(bytes(row))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + chunk(b"IEND", b"")
    )


def test_manuscript_figure_registry_covers_forward_and_roundtrip() -> None:
    roles = {figure.role for figure in MANUSCRIPT_FIGURES}

    assert "forward-code-to-graph" in roles
    assert "forward-graph-to-state-space" in roles
    assert "forward-state-space-to-matrices" in roles
    assert "structural-markov-blanket-partition" in roles
    assert "gnn-to-upstream-generative-model" in roles
    assert "forward-reverse-forward-roundtrip" in roles
    assert "evidence-coverage-review-readiness" in roles
    assert "fixture-graph-size-comparison" in roles
    assert "fixture-node-kind-composition" in roles
    assert "fixture-state-space-output-comparison" in roles
    assert "fixture-api-pipeline-latency" in roles
    assert "cross-target-role-distribution" not in roles
    assert any(figure.key == "gnn_markdown_render" for figure in MANUSCRIPT_FIGURES)
    assert all(figure.destination.endswith(".png") for figure in MANUSCRIPT_FIGURES)


def test_forward_abcd_matrix_figure_uses_flask_real_matrix_artifact() -> None:
    figure = next(item for item in MANUSCRIPT_FIGURES if item.key == "forward_abcd_matrices")

    assert figure.source == "cogant/output/flask_app/connections_matrix.png"
    assert figure.source_artifact == "cogant/output/flask_app/gnn_package/model.gnn.json"
    assert figure.destination == "cogant_forward_abcd_matrices.png"
    assert "Flask" in figure.caption
    assert "inheritance-role" in figure.caption


def test_gnn_markdown_figure_promotes_all_page_mosaic() -> None:
    figure = next(item for item in MANUSCRIPT_FIGURES if item.key == "gnn_markdown_render")

    assert figure.source == "cogant/output/calculator/figures/model_gnn_mosaic.png"
    single_panel_phrase = "first" + " page"
    assert single_panel_phrase not in figure.caption.lower()
    assert "all-page mosaic" in figure.caption


def test_copy_manuscript_figures_writes_manifest(tmp_path: Path) -> None:
    source = tmp_path / "cogant" / "output" / "demo" / "figure.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"fake png bytes")
    figures = (
        ManuscriptFigure(
            key="demo",
            source="cogant/output/demo/figure.png",
            destination="demo.png",
            caption="Demo figure.",
            role="test",
        ),
        ManuscriptFigure(
            key="missing",
            source="cogant/output/demo/missing.png",
            destination="missing.png",
            caption="Missing figure.",
            role="test",
        ),
    )

    manifest_path = copy_manuscript_figures(tmp_path, figures=figures)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert (tmp_path / "output" / "figures" / "demo.png").read_bytes() == b"fake png bytes"
    assert manifest["copied_count"] == 1
    assert manifest["missing_count"] == 1
    assert manifest["figures"][0]["key"] == "demo"
    assert manifest["figures"][0]["panels"][0]["key"] == "demo"
    assert manifest["missing"][0]["key"] == "missing"

    sidecar = json.loads((tmp_path / "output" / "figures" / "demo.figure.json").read_text())
    assert sidecar["panels"][0]["key"] == "demo"
    assert sidecar["panels"][0]["displayed_counts"]["panels"] == 1


def test_copy_manuscript_figures_writes_template_figure_registry(tmp_path: Path) -> None:
    source = tmp_path / "cogant" / "output" / "demo" / "figure.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"fake png bytes")
    manuscript_dir = tmp_path / "manuscript"
    manuscript_dir.mkdir()
    (manuscript_dir / "01_body.md").write_text(
        "![Demo figure.](../figures/demo.png){#fig:demo-figure width=80%}\n",
        encoding="utf-8",
    )
    figures = (
        ManuscriptFigure(
            key="demo",
            source="cogant/output/demo/figure.png",
            destination="demo.png",
            caption="Demo figure.",
            role="test",
            renderer="test.renderer",
        ),
    )

    copy_manuscript_figures(tmp_path, figures=figures)

    registry = json.loads(
        (tmp_path / "output" / "figures" / "figure_registry.json").read_text(
            encoding="utf-8"
        )
    )
    assert registry["figures"] == [
        {
            "caption": "Demo figure.",
            "filename": "demo.png",
            "generated_by": "test.renderer",
            "key": "demo",
            "label": "fig:demo-figure",
            "role": "test",
            "sha256": registry["figures"][0]["sha256"],
            "source_artifact": "",
        }
    ]


def test_copy_manuscript_figures_strict_fails_on_missing(tmp_path: Path) -> None:
    figures = (
        ManuscriptFigure(
            key="missing",
            source="cogant/output/demo/missing.png",
            destination="missing.png",
            caption="Missing figure.",
            role="test",
        ),
    )

    with pytest.raises(FileNotFoundError, match="missing"):
        copy_manuscript_figures(tmp_path, figures=figures, strict=True)


def test_copy_manuscript_figures_strict_rejects_degraded_graphical_abstract(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cogant" / "output" / "demo" / "figures" / "graphical_abstract.png"
    _write_test_png(source, width=1600, height=800)
    source_artifact = tmp_path / "cogant" / "output" / "demo" / "data" / "program_graph.json"
    source_artifact.parent.mkdir(parents=True, exist_ok=True)
    source_artifact.write_text('{"nodes": [], "edges": []}\n', encoding="utf-8")
    source.with_suffix(".figure.json").write_text(
        json.dumps(
            {
                "render_backend": "svg_degraded",
                "degraded_renderer": True,
                "renderer": "cogant.viz.inspection_dashboard.render_graphical_abstract_png",
                "displayed_counts": {"nodes_count": 1, "edges_count": 1},
                "panel_metadata": {"panel": "graphical_abstract"},
                "panels": [{"key": "graphical_abstract"}],
                "known_limitations": "renderer unavailable placeholder.",
            }
        ),
        encoding="utf-8",
    )
    figures = (
        ManuscriptFigure(
            key="graphical_abstract",
            source="cogant/output/demo/figures/graphical_abstract.png",
            destination="graphical_abstract.png",
            caption="Graphical abstract.",
            role="code-gnn-code-graphical-abstract",
            source_artifact="cogant/output/demo/data/program_graph.json",
            renderer="cogant.viz.inspection_dashboard.render_graphical_abstract_png",
            method_note="Native renderer.",
            reading_guide="Read left to right.",
            limitations="Overview only.",
            alt_text="Graphical abstract.",
            min_width_px=1400,
            min_height_px=600,
            require_manuscript_reference=False,
        ),
    )

    with pytest.raises(ValueError, match="degraded_renderer"):
        copy_manuscript_figures(tmp_path, figures=figures, strict=True)


def test_copy_manuscript_figures_strict_accepts_native_graphical_abstract(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cogant" / "output" / "demo" / "figures" / "graphical_abstract.png"
    _write_test_png(source, width=1600, height=800)
    source_artifact = tmp_path / "cogant" / "output" / "demo" / "data" / "program_graph.json"
    source_artifact.parent.mkdir(parents=True, exist_ok=True)
    source_artifact.write_text('{"nodes": [{"id": "n"}], "edges": []}\n', encoding="utf-8")
    source.with_suffix(".figure.json").write_text(
        json.dumps(
            {
                "render_backend": "matplotlib_native",
                "degraded_renderer": False,
                "degraded_rasterization": False,
                "renderer": "cogant.viz.inspection_dashboard.render_graphical_abstract_png",
                "displayed_counts": {"nodes_count": 1, "edges_count": 0},
                "panel_metadata": {"panel": "graphical_abstract"},
                "panels": [{"key": "graphical_abstract"}],
            }
        ),
        encoding="utf-8",
    )
    figures = (
        ManuscriptFigure(
            key="graphical_abstract",
            source="cogant/output/demo/figures/graphical_abstract.png",
            destination="graphical_abstract.png",
            caption="Graphical abstract.",
            role="code-gnn-code-graphical-abstract",
            source_artifact="cogant/output/demo/data/program_graph.json",
            renderer="cogant.viz.inspection_dashboard.render_graphical_abstract_png",
            method_note="Native renderer.",
            reading_guide="Read left to right.",
            limitations="Overview only.",
            alt_text="Graphical abstract.",
            min_width_px=1400,
            min_height_px=600,
            require_manuscript_reference=False,
        ),
    )

    copy_manuscript_figures(tmp_path, figures=figures, strict=True)

    sidecar = json.loads(
        (tmp_path / "output" / "figures" / "graphical_abstract.figure.json").read_text()
    )
    assert sidecar["render_backend"] == "matplotlib_native"
    assert sidecar["degraded_renderer"] is False
    assert sidecar["displayed_counts"]["nodes_count"] == 1


def test_copy_manuscript_figures_strict_rejects_non_native_detail_panel(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cogant" / "output" / "demo" / "figures" / "rule_trace.png"
    _write_test_png(source, width=1600, height=800)
    source_artifact = tmp_path / "cogant" / "output" / "demo" / "rule_evidence_trace.json"
    source_artifact.parent.mkdir(parents=True, exist_ok=True)
    source_artifact.write_text('{"mappings": [{"id": "m1"}]}\n', encoding="utf-8")
    source.with_suffix(".figure.json").write_text(
        json.dumps(
            {
                "renderer": "cogant.viz.inspection_dashboard.render_interpretability_detail_pngs",
                "displayed_counts": {"mappings": 1, "rules": 1, "conflict_events": 0},
                "panel_metadata": {"panel": "rule_trace"},
                "panels": [{"key": "rule_trace"}],
            }
        ),
        encoding="utf-8",
    )
    figures = (
        ManuscriptFigure(
            key="rule_evidence_trace",
            source="cogant/output/demo/figures/rule_trace.png",
            destination="rule_trace.png",
            caption="Rule evidence trace.",
            role="rule-evidence-human-review-trace",
            source_artifact="cogant/output/demo/rule_evidence_trace.json",
            renderer="cogant.viz.inspection_dashboard native rule trace renderer",
            method_note="Rule trace method.",
            reading_guide="Read rule bars.",
            limitations="Trace only.",
            alt_text="Rule trace.",
            min_width_px=1400,
            min_height_px=650,
            require_manuscript_reference=False,
        ),
    )

    with pytest.raises(ValueError, match="render_backend_matplotlib_native"):
        copy_manuscript_figures(tmp_path, figures=figures, strict=True)


def test_copy_manuscript_figures_strict_rejects_tall_timeline(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cogant" / "output" / "dashboard" / "run_gantt.png"
    _write_test_png(source, width=1600, height=1600)
    source_artifact = tmp_path / "cogant" / "output" / "run_manifest.json"
    source_artifact.parent.mkdir(parents=True, exist_ok=True)
    source_artifact.write_text('{"targets": []}\n', encoding="utf-8")
    source.with_suffix(".figure.json").write_text(
        json.dumps(
            {
                "selected_target_id": "calculator",
                "selected_target_command_count": 13,
                "batch_target_count": 24,
                "batch_command_count": 315,
                "displayed_counts": {"targets_count": 24, "stages": 13},
                "panel_metadata": {"panel": "roundtrip_batch_gantt"},
                "panels": [{"key": "roundtrip_batch_gantt"}],
            }
        ),
        encoding="utf-8",
    )
    figures = (
        ManuscriptFigure(
            key="roundtrip_batch_gantt",
            source="cogant/output/dashboard/run_gantt.png",
            destination="run_gantt.png",
            caption="Calculator timeline.",
            role="forward-reverse-forward-roundtrip",
            source_artifact="cogant/output/run_manifest.json",
            renderer="tools.manuscript_figures._render_publication_batch_timeline",
            method_note="Timeline method.",
            reading_guide="Read top to bottom.",
            limitations="Single run.",
            alt_text="Timeline.",
            min_width_px=1400,
            min_height_px=700,
            require_manuscript_reference=False,
            evidence_requirements=("targets_count", "stages"),
        ),
    )

    with pytest.raises(ValueError, match="height_gt_1400"):
        copy_manuscript_figures(tmp_path, figures=figures, strict=True)


def test_publication_batch_timeline_selects_calculator_and_bounds_height(
    tmp_path: Path,
) -> None:
    pytest.importorskip("matplotlib")
    manifest = tmp_path / "cogant" / "output" / "run_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "targets": [
                    {
                        "id": "calculator",
                        "commands": [
                            {"step": "translate:calculator", "wall_time_s": 1.0},
                            {"step": "validate:calculator", "wall_time_s": 0.5},
                            {"step": "roundtrip:calculator", "wall_time_s": 0.75},
                        ],
                    },
                    {
                        "id": "other",
                        "commands": [
                            {"step": "translate:other", "wall_time_s": 2.0},
                            {"step": "validate:other", "wall_time_s": 1.0},
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    output = _render_publication_batch_timeline(tmp_path)

    assert output is not None
    sidecar = json.loads(output.with_suffix(".figure.json").read_text(encoding="utf-8"))
    assert sidecar["selected_target_id"] == "calculator"
    assert sidecar["selected_target_command_count"] == 3
    assert sidecar["batch_target_count"] == 2
    assert sidecar["batch_command_count"] == 5
    assert sidecar["displayed_counts"]["stages"] == 3
    data = output.read_bytes()
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    assert width >= 1400
    assert height <= 1400
    assert width / height >= 1.6


def test_copy_manuscript_figures_strict_fails_on_uncited_registered_figure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cogant" / "output" / "demo" / "figure.png"
    _write_test_png(source)
    manuscript = tmp_path / "manuscript"
    manuscript.mkdir()
    (manuscript / "00_demo.md").write_text("No inserted figures here.\n", encoding="utf-8")
    figures = (
        ManuscriptFigure(
            key="demo",
            source="cogant/output/demo/figure.png",
            destination="demo.png",
            caption="Demo figure.",
            role="test",
            source_artifact="cogant/output/demo/figure.png",
            renderer="test renderer",
            method_note="Test method.",
            reading_guide="Test reading order.",
            limitations="Test limitation.",
            alt_text="Demo figure.",
        ),
    )

    with pytest.raises(ValueError, match="registered-but-uncited"):
        copy_manuscript_figures(tmp_path, figures=figures, strict=True)


def test_copy_manuscript_figures_strict_fails_on_inserted_unregistered_figure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cogant" / "output" / "demo" / "figure.png"
    _write_test_png(source)
    manuscript = tmp_path / "manuscript"
    manuscript.mkdir()
    (manuscript / "00_demo.md").write_text(
        "![Unregistered](../figures/not_registered.png)\n",
        encoding="utf-8",
    )
    figures = (
        ManuscriptFigure(
            key="demo",
            source="cogant/output/demo/figure.png",
            destination="demo.png",
            caption="Demo figure.",
            role="test",
            source_artifact="cogant/output/demo/figure.png",
            renderer="test renderer",
            method_note="Test method.",
            reading_guide="Test reading order.",
            limitations="Test limitation.",
            alt_text="Demo figure.",
            require_manuscript_reference=False,
        ),
    )

    with pytest.raises(ValueError, match="inserted-but-unregistered"):
        copy_manuscript_figures(tmp_path, figures=figures, strict=True)


def test_copy_manuscript_figures_strict_fails_on_angle_bracket_unregistered_figure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cogant" / "output" / "demo" / "figure.png"
    _write_test_png(source)
    manuscript = tmp_path / "manuscript"
    manuscript.mkdir()
    (manuscript / "00_demo.md").write_text(
        "![Unregistered](<../figures/not_registered.png>)\n",
        encoding="utf-8",
    )
    figures = (
        ManuscriptFigure(
            key="demo",
            source="cogant/output/demo/figure.png",
            destination="demo.png",
            caption="Demo figure.",
            role="test",
            source_artifact="cogant/output/demo/figure.png",
            renderer="test renderer",
            method_note="Test method.",
            reading_guide="Test reading order.",
            limitations="Test limitation.",
            alt_text="Demo figure.",
            require_manuscript_reference=False,
        ),
    )

    with pytest.raises(ValueError, match="inserted-but-unregistered"):
        copy_manuscript_figures(tmp_path, figures=figures, strict=True)


def test_copy_manuscript_figures_strict_requires_real_matrix_sidecar(tmp_path: Path) -> None:
    source = tmp_path / "cogant" / "output" / "demo" / "connections_matrix.png"
    _write_test_png(source)
    source.with_suffix(".figure.json").write_text(
        json.dumps(
            {
                "renderer": "cogant.viz.png.render_connections_matrix_png",
                "displayed_counts": {"matrices": 4},
                "panel_metadata": {
                    "panels": [
                        {"key": "A", "shape": [1, 1]},
                        {"key": "B", "shape": [1, 1]},
                        {"key": "C", "shape": [1, 1]},
                        {"key": "D", "shape": [1, 1]},
                    ]
                },
                "matrix_values_from_artifact": False,
                "fallback_panels": ["A", "B", "C", "D"],
                "matrix_source_artifact": None,
                "source_artifact_digest": "digest",
                "source_matrix_shapes": {"A": [1, 1], "B": [1, 1, 1], "C": [1], "D": [1]},
                "matrix_reducers": {"B": {"method": "max_over_actions"}},
            }
        ),
        encoding="utf-8",
    )
    model = tmp_path / "cogant" / "output" / "demo" / "gnn_package" / "model.gnn.json"
    model.parent.mkdir(parents=True)
    model.write_text(
        json.dumps(
            {
                "matrices": {
                    "A": [[1.0]],
                    "B": [[[1.0]]],
                    "C": [0.0],
                    "D": [1.0],
                }
            }
        ),
        encoding="utf-8",
    )
    figures = (
        ManuscriptFigure(
            key="forward_abcd_matrices",
            source="cogant/output/demo/connections_matrix.png",
            destination="demo_abcd.png",
            caption="A/B/C/D matrix panel.",
            role="forward-state-space-to-matrices",
            source_artifact="cogant/output/demo/gnn_package/model.gnn.json",
            renderer="cogant.viz.png.render_connections_matrix_png",
            method_note="Matrix method.",
            reading_guide="Matrix guide.",
            limitations="Matrix limitation.",
            alt_text="Matrix panel.",
            require_manuscript_reference=False,
        ),
    )

    with pytest.raises(ValueError, match="matrix_values_from_artifact"):
        copy_manuscript_figures(tmp_path, figures=figures, strict=True)


def test_copy_manuscript_figures_strict_fails_on_matrix_dimension_mismatch(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cogant" / "output" / "demo" / "connections_matrix.png"
    _write_test_png(source)
    source.with_suffix(".figure.json").write_text(
        json.dumps(
            {
                "renderer": "cogant.viz.png.render_connections_matrix_png",
                "displayed_counts": {"matrices": 4},
                "panel_metadata": {
                    "panels": [
                        {"key": "A", "shape": [1, 1]},
                        {"key": "B", "shape": [1, 1]},
                        {"key": "C", "shape": [1, 1]},
                        {"key": "D", "shape": [1, 1]},
                    ]
                },
                "matrix_values_from_artifact": True,
                "matrix_validation_errors": [],
                "fallback_panels": [],
                "degraded_panels": [],
                "matrix_source_artifact": "output/demo/gnn_package/model.gnn.json",
                "source_artifact_digest": "source-digest",
                "source_matrix_shapes": {"A": [1, 1], "B": [1, 1, 1], "C": [1], "D": [1]},
                "display_matrix_shapes": {
                    "A": [1, 1],
                    "B": [1, 1],
                    "C": [1, 1],
                    "D": [1, 1],
                },
                "matrix_reducers": {
                    "B": {
                        "method": "max_over_actions",
                        "axis": 2,
                        "source_action_count": 1,
                    }
                },
                "source_matrix_diagnostics": {
                    "A": {"distinct_values": 1},
                    "B": {"distinct_values": 1},
                    "C": {"distinct_values": 1},
                    "D": {"distinct_values": 1},
                },
                "panel_diagnostics": {
                    "A": {"nonzero_fraction": 1.0},
                    "B": {"nonzero_fraction": 1.0},
                    "C": {"nonzero_fraction": 0.0},
                    "D": {"nonzero_fraction": 1.0},
                },
                "matrix_dimensions": {"hidden_states": 1, "observations": 1, "actions": 1},
                "state_space_counts": {"hidden_states": 2, "observations": 1, "actions": 1},
                "dimension_alignment": {
                    "hidden_states_match": False,
                    "observations_match": True,
                    "actions_match": True,
                },
                "strict_real_matrices": True,
            }
        ),
        encoding="utf-8",
    )
    model = tmp_path / "cogant" / "output" / "demo" / "gnn_package" / "model.gnn.json"
    model.parent.mkdir(parents=True)
    model.write_text(
        json.dumps(
            {
                "matrices": {
                    "A": [[1.0]],
                    "B": [[[1.0]]],
                    "C": [0.0],
                    "D": [1.0],
                }
            }
        ),
        encoding="utf-8",
    )
    figures = (
        ManuscriptFigure(
            key="forward_abcd_matrices",
            source="cogant/output/demo/connections_matrix.png",
            destination="demo_abcd.png",
            caption="A/B/C/D matrix panel.",
            role="forward-state-space-to-matrices",
            source_artifact="cogant/output/demo/gnn_package/model.gnn.json",
            renderer="cogant.viz.png.render_connections_matrix_png",
            method_note="Matrix method.",
            reading_guide="Matrix guide.",
            limitations="Matrix limitation.",
            alt_text="Matrix panel.",
            require_manuscript_reference=False,
        ),
    )

    with pytest.raises(ValueError, match="dimension_alignment.hidden_states_match"):
        copy_manuscript_figures(tmp_path, figures=figures, strict=True)


def test_copy_manuscript_figures_promotes_matrix_diagnostics(tmp_path: Path) -> None:
    source = tmp_path / "cogant" / "output" / "demo" / "connections_matrix.png"
    _write_test_png(source)
    source.with_suffix(".figure.json").write_text(
        json.dumps(
            {
                "renderer": "cogant.viz.png.render_connections_matrix_png",
                "displayed_counts": {
                    "matrices": 4,
                    "hidden_states": 1,
                    "observations": 1,
                    "actions": 1,
                },
                "panel_metadata": {
                    "panels": [
                        {"key": "A", "shape": [1, 1]},
                        {"key": "B", "shape": [1, 1]},
                        {"key": "C", "shape": [1, 1]},
                        {"key": "D", "shape": [1, 1]},
                    ]
                },
                "matrix_values_from_artifact": True,
                "matrix_validation_errors": [],
                "fallback_panels": [],
                "degraded_panels": [],
                "matrix_source_artifact": "output/demo/gnn_package/model.gnn.json",
                "source_artifact_digest": "source-digest",
                "source_matrix_shapes": {"A": [1, 1], "B": [1, 1, 1], "C": [1], "D": [1]},
                "display_matrix_shapes": {
                    "A": [1, 1],
                    "B": [1, 1],
                    "C": [1, 1],
                    "D": [1, 1],
                },
                "matrix_reducers": {
                    "B": {
                        "method": "max_over_actions",
                        "axis": 2,
                        "source_action_count": 1,
                    }
                },
                "source_matrix_diagnostics": {
                    "A": {"distinct_values": 1},
                    "B": {"distinct_values": 1},
                    "C": {"distinct_values": 1},
                    "D": {"distinct_values": 1},
                },
                "panel_diagnostics": {
                    "A": {"nonzero_fraction": 1.0},
                    "B": {"nonzero_fraction": 1.0},
                    "C": {"nonzero_fraction": 0.0},
                    "D": {"nonzero_fraction": 1.0},
                },
                "matrix_dimensions": {"hidden_states": 1, "observations": 1, "actions": 1},
                "state_space_counts": {"hidden_states": 1, "observations": 1, "actions": 1},
                "axis_labels": {
                    "hidden_states": ["Service - Hidden State"],
                    "observations": ["event - Observation"],
                    "actions": ["act - Action"],
                },
                "state_label_groups": [
                    {
                        "key": "program_service_state_variables",
                        "label": "program/service state variables",
                        "indices": "0",
                        "count": 1,
                    }
                ],
                "matrix_interpretation_notes": {
                    "A": "Likelihood columns are non-uniform when extracted evidence is non-uniform.",
                    "B": "Displayed panel is the max-over-actions transition summary.",
                    "C": "The zero preference vector is exported.",
                    "D": "The prior vector is exported structural evidence.",
                },
                "dimension_alignment": {
                    "hidden_states_match": True,
                    "observations_match": True,
                    "actions_match": True,
                },
                "strict_real_matrices": True,
            }
        ),
        encoding="utf-8",
    )
    model = tmp_path / "cogant" / "output" / "demo" / "gnn_package" / "model.gnn.json"
    model.parent.mkdir(parents=True)
    model.write_text(
        json.dumps(
            {
                "matrices": {
                    "A": [[1.0]],
                    "B": [[[1.0]]],
                    "C": [0.0],
                    "D": [1.0],
                }
            }
        ),
        encoding="utf-8",
    )
    figures = (
        ManuscriptFigure(
            key="forward_abcd_matrices",
            source="cogant/output/demo/connections_matrix.png",
            destination="demo_abcd.png",
            caption="A/B/C/D matrix panel.",
            role="forward-state-space-to-matrices",
            source_artifact="cogant/output/demo/gnn_package/model.gnn.json",
            renderer="cogant.viz.png.render_connections_matrix_png",
            method_note="Matrix method.",
            reading_guide="Matrix guide.",
            limitations="Matrix limitation.",
            alt_text="Matrix panel.",
            require_manuscript_reference=False,
        ),
    )

    copy_manuscript_figures(tmp_path, figures=figures, strict=True)

    sidecar = json.loads((tmp_path / "output" / "figures" / "demo_abcd.figure.json").read_text())
    assert sidecar["matrix_values_from_artifact"] is True
    assert sidecar["matrix_validation_errors"] == []
    assert sidecar["matrix_source_path"] == "cogant/output/demo/gnn_package/model.gnn.json"
    assert sidecar["matrix_source_digest"]
    assert sidecar["source_matrix_shapes"]["B"] == [1, 1, 1]
    assert sidecar["b_reducer"]["method"] == "max_over_actions"
    assert sidecar["source_matrix_diagnostics"]["A"]["distinct_values"] == 1
    assert sidecar["panel_diagnostics"]["B"]["nonzero_fraction"] == 1.0
    assert sidecar["fallback_panels"] == []
    assert sidecar["degraded_panels"] == []
    assert sidecar["image_width_px"] == 1200
    assert sidecar["image_height_px"] == 600


def test_artifact_summary_extracts_fixture_metrics_counts(tmp_path: Path) -> None:
    metrics = tmp_path / "cogant" / "evaluation" / "figures" / "metrics.json"
    metrics.parent.mkdir(parents=True)
    metrics.write_text(
        json.dumps(
            {
                "calculator": {
                    "nodes": 12,
                    "edges": 25,
                    "mappings_total": 11,
                    "state_variables": 1,
                    "observations": 3,
                    "actions": 6,
                    "transitions": 6,
                    "elapsed_s": 3.87,
                    "group": "control_positive",
                    "nodes_by_kind": {"MODULE": 1, "CLASS": 1, "METHOD": 10},
                },
                "flask_app": {
                    "nodes": 98,
                    "edges": 154,
                    "mappings_total": 72,
                    "state_variables": 14,
                    "observations": 22,
                    "actions": 31,
                    "transitions": 31,
                    "elapsed_s": 5.67,
                    "group": "real_world",
                    "nodes_by_kind": {"MODULE": 6, "CLASS": 25, "METHOD": 57, "FUNCTION": 10},
                },
            }
        ),
        encoding="utf-8",
    )

    summary = _artifact_summary(metrics, tmp_path)

    assert summary is not None
    assert summary["fixture_count"] == 2
    assert summary["fixture_group_count"] == 2
    assert summary["node_kind_count"] == 4
    assert summary["total_nodes"] == 110
    assert summary["total_edges"] == 179
    assert summary["total_mappings"] == 83
    assert summary["total_state_variables"] == 15
    assert summary["total_observations"] == 25
    assert summary["total_actions"] == 37
    assert summary["total_elapsed_s"] == 9.54


def test_artifact_summary_extracts_gnn_bundle_counts_without_fixture_heuristics(
    tmp_path: Path,
) -> None:
    model = tmp_path / "cogant" / "output" / "demo" / "gnn_package" / "model.gnn.json"
    model.parent.mkdir(parents=True)
    model.write_text(
        json.dumps(
            {
                "model_id": "demo",
                "schema_name": "Demo",
                "state_space": {
                    "variables": [{"id": "s0"}, {"id": "s1"}],
                    "observations": [{"id": "o0"}, {"id": "o1"}, {"id": "o2"}],
                    "actions": [{"id": "a0"}],
                    "transitions": [{"id": "t0"}],
                    "likelihoods": [{"id": "l0"}],
                    "preferences": [],
                },
                "matrices": {
                    "A": [[0.5, 0.5], [0.5, 0.5], [0.0, 0.0]],
                    "B": [[[1.0]], [[1.0]]],
                    "C": [0.0, 0.0, 0.0],
                    "D": [0.5, 0.5],
                    "dimensions": {"n_states": 2, "n_obs": 3, "n_actions": 1},
                    "shapes": {"A": [3, 2], "B": [2, 2, 1], "C": [3], "D": [2]},
                },
                "mappings": {"mappings": [{"id": "m0"}]},
                "ontology_mapping": {"mappings": [{"id": "o0"}]},
                "program_graph": {"nodes": [{"id": "n0"}], "edges": [{"id": "e0"}]},
            }
        ),
        encoding="utf-8",
    )

    summary = _artifact_summary(model, tmp_path)

    assert summary is not None
    assert summary["bundle_kind"] == "gnn_model"
    assert "fixture_count" not in summary
    assert summary["total_state_variables"] == 2
    assert summary["total_observations"] == 3
    assert summary["total_actions"] == 1
    assert summary["mappings_count"] == 1
    assert summary["program_nodes_count"] == 1


def test_registry_renderer_paths_resolve() -> None:
    """Every dotted ``renderer`` path in the registry must import to a callable.

    Guards the silent-provenance-lie failure mode where a renderer is refactored
    into a new module (e.g. ``cogant.viz.png_export`` -> ``cogant.viz.png``) but
    the registry metadata still points at the dead path. Free-text descriptions
    (with spaces) are skipped by design.
    """
    errors = afr.audit()
    assert errors == [], "out-of-sync/unresolvable renderer paths in registry:\n" + "\n".join(errors)


def test_renderer_audit_is_not_vacuous() -> None:
    """The audit must actually fail on a bad path (else green is meaningless)."""
    # A dotted path that looks importable but cannot resolve.
    assert afr.looks_like_import_path("cogant.viz.png.render_does_not_exist_png")
    with pytest.raises((AttributeError, ModuleNotFoundError, ValueError)):
        afr.resolve_renderer("cogant.viz.png.render_does_not_exist_png")
    with pytest.raises((AttributeError, ModuleNotFoundError, ValueError)):
        afr.resolve_renderer("cogant.viz.png_export.render_program_graph_png")
    # Free-text descriptions are correctly treated as non-paths (and skipped).
    assert not afr.looks_like_import_path("upstream GNN visualization pipeline")
    assert not afr.looks_like_import_path("cogant.viz.inspection_dashboard roundtrip renderer")


def test_caption_encoding_constants_hold() -> None:
    """Every locked caption-encoding constant must still exist in its renderer.

    This is the layer that defends caption<->encoding drift (a color/marker change
    silently making a caption lie) — the failure the path-resolution layer cannot
    catch. Non-vacuous: a fabricated constant is provably absent, so a real
    renderer color change (vanished substring) would fail the same check.
    """
    assert afr.audit_encodings() == []
    state_space = (
        afr._REPO_ROOT / "cogant" / "py" / "cogant" / "viz" / "png" / "state_space.py"
    ).read_text(encoding="utf-8")
    assert '"#0072B2"' in state_space  # the real "hidden state = blue" constant
    assert '"#deadbe"' not in state_space  # a fabricated color would fail the gate


def test_gantt_diamond_marker_check_is_ast_draw_path_bound() -> None:
    """The gantt diamond assertion must bind to a real scatter draw call, not a
    bare substring (so a marker surviving only on a legend handle cannot pass it).
    Non-vacuous: a legend-only diamond is rejected; a scatter diamond is accepted.
    """
    import ast

    assert afr._gantt_diamond_marker_errors() == []  # the real renderer passes
    # Legend handle alone (Line2D marker="D") must NOT satisfy the draw-path check.
    legend_only = ast.parse('Line2D([0], [0], marker="D", label="gate")\n')
    assert not afr._has_scatter_with_diamond(legend_only)
    # An actual scatter draw call with a diamond does satisfy it.
    real_scatter = ast.parse('ax.scatter(x, y, marker="D", color="#172033")\n')
    assert afr._has_scatter_with_diamond(real_scatter)
    # gate-stage set predicate is grounded and non-vacuous.
    assert afr._has_gate_stage_set(ast.parse('gate_stages = {"validate", "roundtrip"}\n'))
    assert not afr._has_gate_stage_set(ast.parse('gate_stages = {"validate"}\n'))


def test_module_name_collector_sees_conditionally_defined_symbols() -> None:
    """The AST name collector must see symbols guarded by try/except or if — the
    optional-dependency pattern a renderer could be refactored into — so the gate
    does not spuriously fail a valid path (Forge cross-vendor finding)."""
    import ast

    tree = ast.parse(
        "try:\n"
        "    from somewhere import render_x_png\n"
        "except ImportError:\n"
        "    def render_x_png():\n        return None\n"
        "if True:\n"
        "    render_y_png = render_x_png\n"
        "class C:\n"
        "    def method_not_a_module_attr(self):\n        return 1\n"
    )
    names = afr._module_level_names(tree)
    assert "render_x_png" in names  # try-body import
    assert "render_y_png" in names  # if-guarded assignment
    assert "C" in names
    assert "method_not_a_module_attr" not in names  # class methods are not module attrs
