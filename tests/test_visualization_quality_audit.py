from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from visualization_quality_audit import (  # noqa: E402
    build_visualization_quality_audit,
    write_json,
    write_markdown,
    write_png_matrix,
)


def _figure_record(
    key: str,
    *,
    width: int = 1600,
    height: int = 900,
    render_backend: str | None = None,
    degraded_renderer: bool | None = None,
) -> dict[str, object]:
    destination = f"output/figures/{key}.png"
    sidecar = f"output/figures/{key}.figure.json"
    return {
        "key": key,
        "destination": destination,
        "destination_figure_sidecar": sidecar,
        "destination_figure_sidecar_exists": True,
        "dimensions_px": {"width": width, "height": height},
        "min_width_px": 1000,
        "min_height_px": 500,
        "source_artifact": f"cogant/output/{key}/data.json",
        "source_artifact_digest": "abc123",
        "render_backend": render_backend,
        "degraded_renderer": degraded_renderer,
        "visual_qa": {
            "nonblank": True,
            "color_diversity_ok": True,
            "min_dimension_ok": True,
        },
    }


def _write_manifest(tmp_path: Path, figures: list[dict[str, object]]) -> Path:
    for figure in figures:
        sidecar = tmp_path / str(figure["destination_figure_sidecar"])
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(json.dumps({"key": figure["key"]}), encoding="utf-8")
    manifest = tmp_path / "output" / "figures" / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"figures": figures}), encoding="utf-8")
    return manifest


def test_visualization_quality_audit_passes_native_graphical_abstract(tmp_path: Path) -> None:
    manifest = _write_manifest(
        tmp_path,
        [
            _figure_record(
                "graphical_abstract",
                render_backend="matplotlib_native",
                degraded_renderer=False,
            )
        ],
    )

    report = build_visualization_quality_audit(manifest, root=tmp_path)

    assert report["summary"]["failed"] == 0
    assert report["figures"][0]["checks"]["publication"] is True


def test_visualization_quality_audit_rejects_degraded_graphical_abstract(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(
        tmp_path,
        [
            _figure_record(
                "graphical_abstract",
                render_backend="svg_degraded",
                degraded_renderer=True,
            )
        ],
    )

    report = build_visualization_quality_audit(manifest, root=tmp_path)

    assert report["summary"]["failed"] == 1
    issues = report["figures"][0]["issues"]
    assert "degraded renderer metadata is present" in issues
    assert "graphical abstract is not native matplotlib PNG" in issues


def test_visualization_quality_audit_rejects_tall_timeline(tmp_path: Path) -> None:
    manifest = _write_manifest(
        tmp_path,
        [_figure_record("roundtrip_batch_gantt", width=900, height=1800)],
    )

    report = build_visualization_quality_audit(manifest, root=tmp_path)

    assert report["summary"]["failed"] == 1
    assert "timeline dimensions are not publication readable" in report["figures"][0]["issues"]


def test_visualization_quality_audit_requires_native_detail_panels(tmp_path: Path) -> None:
    manifest = _write_manifest(
        tmp_path,
        [_figure_record("rule_evidence_trace", render_backend=None, degraded_renderer=None)],
    )

    report = build_visualization_quality_audit(manifest, root=tmp_path)

    assert report["summary"]["failed"] == 1
    assert "publication detail panel is not native matplotlib PNG" in report["figures"][0]["issues"]


def test_visualization_quality_audit_writes_review_artifacts(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, [_figure_record("demo")])
    report = build_visualization_quality_audit(manifest, root=tmp_path)

    json_path = write_json(report, tmp_path / "audit.json")
    md_path = write_markdown(report, tmp_path / "audit.md")

    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["passed"] == 1
    assert "| demo | pass | 1600 x 900 |" in md_path.read_text(encoding="utf-8")


def test_visualization_quality_audit_writes_png_matrix(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    manifest = _write_manifest(tmp_path, [_figure_record("demo")])
    report = build_visualization_quality_audit(manifest, root=tmp_path)

    png_path = write_png_matrix(report, tmp_path / "audit.png")

    assert png_path is not None
    assert png_path.is_file()
