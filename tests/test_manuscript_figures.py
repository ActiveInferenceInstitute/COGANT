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

from manuscript_figures import (  # noqa: E402
    MANUSCRIPT_FIGURES,
    ManuscriptFigure,
    _artifact_summary,
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
