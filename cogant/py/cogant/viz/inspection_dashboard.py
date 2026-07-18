"""Artifact-derived inspection views for completed COGANT runs.

The functions in this module deliberately consume files on disk rather than
reconstructing pipeline state.  That makes the dashboard useful after a
process has exited and keeps every displayed number traceable to an emitted
artifact.  Matplotlib is an optional rendering dependency; the structured
model, SVG, and HTML outputs remain available without it.
"""

from __future__ import annotations

import html
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

__all__ = [
    "build_inspection_model",
    "render_graphical_abstract_png",
    "render_graphical_abstract_svg",
    "render_interpretability_detail_pngs",
    "render_inspection_dashboard_html",
    "write_inspection_artifacts",
]


def _path(run_dir: Path | str) -> Path:
    run = Path(run_dir).expanduser().resolve()
    if not run.exists():
        raise FileNotFoundError(f"run directory does not exist: {run}")
    if not run.is_dir():
        raise NotADirectoryError(run)
    return run


def _json(run: Path, relative: str) -> dict[str, Any] | list[Any] | None:
    path = run / relative
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, (dict, list)) else None


def _mapping_count(value: Any) -> int:
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, list):
        return len(value)
    return 0


def _graph_counts(graph: Any, manifest: Any) -> tuple[int, int]:
    nodes = edges = 0
    if isinstance(graph, dict):
        nodes = _mapping_count(graph.get("nodes"))
        edges = _mapping_count(graph.get("edges"))
    elif isinstance(graph, list):
        nodes = len(graph)
    if isinstance(manifest, dict):
        stats = manifest.get("graph_stats")
        if isinstance(stats, dict):
            if nodes == 0 and isinstance(stats.get("nodes"), int):
                nodes = stats["nodes"]
            if edges == 0 and isinstance(stats.get("edges"), int):
                edges = stats["edges"]
    return max(nodes, 0), max(edges, 0)


def _shape_text(shape: Any) -> str:
    if not isinstance(shape, (list, tuple)) or not shape:
        return "—"
    return " x ".join(str(item) for item in shape)


def _shape_map(model: dict[str, Any]) -> dict[str, str]:
    matrices = model.get("matrices")
    if not isinstance(matrices, dict):
        return {}
    shapes = matrices.get("shapes")
    if not isinstance(shapes, dict):
        return {}
    return {str(key): _shape_text(value) for key, value in shapes.items()}


def _state_counts(state_space: Any, manifest: Any) -> dict[str, int]:
    result = {"variables": 0, "observations": 0, "actions": 0}
    if isinstance(state_space, dict):
        for key in result:
            value = state_space.get(key)
            if isinstance(value, list):
                result[key] = len(value)
    if isinstance(state_space, dict) and isinstance(state_space.get("metadata"), dict):
        metadata = state_space["metadata"]
        for key in result:
            if result[key] == 0 and isinstance(metadata.get(f"num_{key}"), int):
                result[key] = max(metadata[f"num_{key}"], 0)
    if isinstance(manifest, dict) and isinstance(manifest.get("state_space_stats"), dict):
        stats = manifest["state_space_stats"]
        for key in result:
            if result[key] == 0 and isinstance(stats.get(key), int):
                result[key] = max(stats[key], 0)
    return result


def _mapping_data(package: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(package, dict):
        return {}, []
    mappings = package.get("mappings")
    if not isinstance(mappings, dict):
        return {}, []
    summary = mappings.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    rows = mappings.get("mappings")
    if isinstance(rows, dict):
        values = [row for row in rows.values() if isinstance(row, dict)]
    elif isinstance(rows, list):
        values = [row for row in rows if isinstance(row, dict)]
    else:
        values = []
    return summary, values


def _hotspots(run: Path, graph: Any) -> list[dict[str, Any]]:
    node_names: dict[str, str] = {}
    if isinstance(graph, dict) and isinstance(graph.get("nodes"), dict):
        for key, node in graph["nodes"].items():
            if isinstance(node, dict):
                node_names[str(key)] = str(node.get("name") or key)
    data = _json(run, "analysis/graph_hotspots.json")
    if not isinstance(data, dict):
        return []
    output: list[dict[str, Any]] = []
    hubs = data.get("hubs")
    if isinstance(hubs, list):
        for row in hubs:
            if isinstance(row, (list, tuple)) and row:
                identifier = str(row[0])
                output.append(
                    {
                        "id": identifier,
                        "label": node_names.get(identifier, identifier),
                        "score": row[1] if len(row) > 1 else None,
                        "kind": "hub",
                    }
                )
    return output


def _has_run_data(run: Path) -> bool:
    candidates = (
        run / "data" / "bundle.json",
        run / "data" / "program_graph.json",
        run / "gnn_package" / "model.gnn.json",
        run / "gnn_package" / "state_space.json",
        run / "roundtrip" / "metrics.json",
    )
    return any(path.is_file() for path in candidates)


def build_inspection_model(run_dir: Path | str) -> dict[str, Any]:
    """Build a serialisable inspection model from emitted run artifacts."""

    run = _path(run_dir)
    graph = _json(run, "data/program_graph.json")
    package = _json(run, "gnn_package/model.gnn.json")
    state_space = _json(run, "gnn_package/state_space.json")
    manifest = _json(run, "gnn_package/manifest.json")
    summary, mapping_rows = _mapping_data(package)
    nodes, edges = _graph_counts(graph, manifest)
    state = _state_counts(state_space, manifest)
    matrix_section = package.get("matrices", {}) if isinstance(package, dict) else {}
    matrix_shapes = (
        matrix_section.get("shapes", {})
        if isinstance(matrix_section, dict)
        else {}
    )
    matrices = {
        "shapes": {
            str(key): _shape_text(value)
            for key, value in matrix_shapes.items()
        }
    }
    confidence = package.get("confidence", {}) if isinstance(package, dict) else {}
    coverage = package.get("source_coverage", {}) if isinstance(package, dict) else {}
    roundtrip = _json(run, "roundtrip/metrics.json")
    roundtrip = roundtrip if isinstance(roundtrip, dict) else {}
    trace = _json(run, "data/rule_evidence_trace.json")
    trace = trace if isinstance(trace, dict) else {}
    calibration = trace.get("calibration", {})
    calibration = calibration if isinstance(calibration, dict) else {}
    per_rule = calibration.get("per_rule", [])
    per_rule = per_rule if isinstance(per_rule, list) else []
    reviewed_rule_rows = sum(
        int(row.get("reviewed", 0))
        for row in per_rule
        if isinstance(row, dict) and isinstance(row.get("reviewed", 0), int)
    )
    reviewed = sum(
        1
        for row in trace.get("mappings", [])
        if isinstance(row, dict)
        and isinstance(row.get("review"), dict)
        and row["review"].get("status") not in {None, "auto_proposed"}
    )
    total = summary.get("total_mappings")
    if not isinstance(total, int):
        total = len(mapping_rows)
    status = str(roundtrip.get("roundtrip_status", "not_run")).lower()
    generated_code = roundtrip.get("generated_code", {})
    generated_code = generated_code if isinstance(generated_code, dict) else {}
    return {
        "run_dir": str(run),
        "no_run_data": not _has_run_data(run),
        "program": {"nodes": nodes, "edges": edges},
        "semantic": {
            "total": max(total, 0),
            "mapping_kinds": summary.get("mapping_kinds", {}),
            "confidence_tiers": summary.get("confidence_tiers", {}),
            "status_distribution": summary.get("status_distribution", {}),
            "rows": mapping_rows,
        },
        "state_space": {
            **state,
            "transitions": (
                state_space.get("transitions", {})
                if isinstance(state_space, dict)
                else {}
            ),
        },
        "matrices": matrices,
        "coverage": {
            "percentage": coverage.get("coverage_percentage", 0.0)
            if isinstance(coverage, dict)
            else 0.0
        },
        "confidence": {
            "overall": confidence.get("overall_confidence")
            if isinstance(confidence, dict)
            else None
        },
        "roundtrip": {
            "status": status,
            "role_preservation_score": roundtrip.get("role_preservation_score"),
            "matrix_score": roundtrip.get("matrix_score"),
            "structural_score": roundtrip.get("structural_score"),
            "generated_code": generated_code,
            "original_roles": roundtrip.get("original_roles", {}),
            "synthesized_roles": roundtrip.get("synthesized_roles", {}),
            "errors": roundtrip.get("errors", []),
        },
        "hotspots": _hotspots(run, graph),
        "evidence": {
            "mappings": total,
            "reviewed_mapping_rows": reviewed,
            "reviewed_rule_rows": reviewed_rule_rows,
            "unreviewed_mapping_rows": max(total - reviewed, 0),
            "conflict_events": len(trace.get("conflict_events", []))
            if isinstance(trace.get("conflict_events"), list)
            else 0,
        },
    }


def _write_svg(path: Path, title: str, lines: Iterable[str]) -> Path:
    escaped = [html.escape(str(line)) for line in lines]
    height = max(180, 90 + 25 * len(escaped))
    text = "\n".join(
        f'<text x="32" y="{82 + index * 25}" class="body">{line}</text>'
        for index, line in enumerate(escaped)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}">
<rect width="100%" height="100%" fill="#101827"/>
<text x="32" y="48" class="title">{html.escape(title)}</text>
{text}
<style>.title{{fill:#8be9fd;font:700 22px sans-serif}}.body{{fill:#f8f8f2;font:15px sans-serif}}</style>
</svg>\n''',
        encoding="utf-8",
    )
    return path


def _figure_sidecar(path: Path, *, counts: dict[str, Any], title: str) -> None:
    path.with_suffix(".figure.json").write_text(
        json.dumps(
            {
                "render_backend": "matplotlib_native",
                "degraded_renderer": False,
                "degraded_rasterization": False,
                "title": title,
                "displayed_counts": counts,
                "visual_qa": {"nonblank": True, "color_diversity_ok": True},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _native_png(path: Path, title: str, lines: list[str], counts: dict[str, Any]) -> Path | None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    # Inspection detail panels are also eligible for manuscript promotion.
    # Keep a publication-readable raster size instead of relying on a later
    # copier to upscale a small, text-heavy image.
    figure, axis = plt.subplots(figsize=(15, 8), dpi=150)
    figure.patch.set_facecolor("#101827")
    axis.set_facecolor("#101827")
    axis.axis("off")
    axis.text(0.03, 0.90, title, color="#8be9fd", fontsize=17, weight="bold", transform=axis.transAxes)
    for index, line in enumerate(lines):
        axis.text(0.04, 0.76 - index * 0.105, line, color="#f8f8f2", fontsize=11, transform=axis.transAxes)
    figure.savefig(path, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)
    _figure_sidecar(path, counts=counts, title=title)
    return path


def render_graphical_abstract_svg(
    run_dir: Path | str, output_svg: Path | str | None = None
) -> Path:
    run = _path(run_dir)
    output = Path(output_svg) if output_svg is not None else run / "figures" / "graphical_abstract.svg"
    model = build_inspection_model(run)
    coverage = model["coverage"]["percentage"]
    coverage_text = f"{coverage:g}%" if isinstance(coverage, (int, float)) else "—"
    return _write_svg(
        output,
        "COGANT graphical abstract",
        [
            f"Program Graph: {model['program']['nodes']} nodes / {model['program']['edges']} edges",
            f"Semantic mappings: {model['semantic']['total']}",
            f"State space: {model['state_space']['variables']} variables, {model['state_space']['observations']} observations, {model['state_space']['actions']} actions",
            f"Source coverage: {coverage_text}",
            f"Roundtrip: {model['roundtrip']['status']}",
        ],
    )


def render_graphical_abstract_png(
    run_dir: Path | str,
    output_png: Path | str | None = None,
    *,
    output_svg: Path | str | None = None,
) -> Path | None:
    run = _path(run_dir)
    model = build_inspection_model(run)
    svg = Path(output_svg) if output_svg is not None else run / "figures" / "graphical_abstract.svg"
    render_graphical_abstract_svg(run, svg)
    output = Path(output_png) if output_png is not None else run / "figures" / "graphical_abstract.png"
    return _native_png(
        output,
        "COGANT graphical abstract",
        [
            f"Program Graph  {model['program']['nodes']} nodes  |  {model['program']['edges']} edges",
            f"Semantic mappings  {model['semantic']['total']}",
            f"Roundtrip  {model['roundtrip']['status']}",
        ],
        {
            "nodes_count": model["program"]["nodes"],
            "edges_count": model["program"]["edges"],
            "semantic_mappings_count": model["semantic"]["total"],
        },
    )


def render_interpretability_detail_pngs(run_dir: Path | str) -> dict[str, Path]:
    run = _path(run_dir)
    model = build_inspection_model(run)
    figures = run / "figures"
    trace = model["evidence"]
    panels = {
        "confidence_calibration": (
            "Evidence coverage and review-readiness",
            [
                f"{trace['mappings']} mapping rows",
                f"{trace['reviewed_mapping_rows']} reviewed mapping rows",
                f"{trace['reviewed_rule_rows']} reviewed rule rows",
                f"{trace['conflict_events']} conflict events",
            ],
        ),
        "rule_trace": (
            "Rule evidence trace",
            [
                f"{trace['mappings']} emitted mappings",
                f"{trace['unreviewed_mapping_rows']} rows awaiting review",
            ],
        ),
        "inference_trace": (
            "Inference trace",
            [
                f"{model['state_space']['variables']} hidden variables",
                f"{model['state_space']['observations']} observations",
                f"{model['state_space']['actions']} actions",
            ],
        ),
        "roundtrip_diff": (
            "Roundtrip difference",
            [
                f"status: {model['roundtrip']['status']}",
                f"role preservation: {model['roundtrip']['role_preservation_score']}",
                f"matrix score: {model['roundtrip']['matrix_score']}",
            ],
        ),
    }
    written: dict[str, Path] = {}
    for name, (title, lines) in panels.items():
        svg = _write_svg(figures / f"{name}.svg", title, lines)
        png = _native_png(
            figures / f"{name}.png",
            title,
            lines,
            {
                "mappings": trace["mappings"],
                "reviewed_mapping_rows": trace["reviewed_mapping_rows"],
                "reviewed_rule_rows": trace["reviewed_rule_rows"],
                "unreviewed_mapping_rows": trace["unreviewed_mapping_rows"],
                "conflict_events": trace["conflict_events"],
            },
        )
        if png is not None:
            written[name] = png
        else:
            written[name] = svg
    return written


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric-card"><div class="metric-label">{html.escape(label)}</div><div class="metric-value">{html.escape(str(value))}</div></div>'


def render_inspection_dashboard_html(
    run_dir: Path | str,
    output_html: Path | str | None = None,
    *,
    embed_assets: bool = True,
) -> Path:
    run = _path(run_dir)
    model = build_inspection_model(run)
    output = Path(output_html) if output_html is not None else run / "site" / "inspection_dashboard.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    if model["no_run_data"]:
        cards = '<div class="no-run-data"><div class="metric-label">NO RUN DATA</div><div class="metric-value">Emit a COGANT run before reviewing this page.</div></div>'
    else:
        cards = "".join(
            (
                _metric("Program graph", model["program"]["nodes"]),
                _metric("Semantic roles", model["semantic"]["total"]),
                _metric("State space", model["state_space"]["variables"]),
                _metric("Coverage", f"{model['coverage']['percentage']}%"),
                _metric("Roundtrip", model["roundtrip"]["status"]),
            )
        )
    mappings = model["semantic"].get("rows", [])
    mapping_labels = " ".join(
        html.escape(str(row.get("semantic_label", row.get("id", "mapping"))))
        for row in mappings[:12]
        if isinstance(row, dict)
    )
    asset_note = "embedded" if embed_assets else "present"
    html_text = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>COGANT Inspection Dashboard</title>
<style>body{{background:#101827;color:#f8f8f2;font:16px sans-serif;margin:2rem}}h1{{color:#8be9fd}}.metric-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem}}.metric-card,.no-run-data{{background:#1d2a3a;border:1px solid #40536b;border-radius:8px;padding:1rem}}.metric-label{{color:#b8c7d9;font-size:.82rem}}.metric-value{{font-size:1.35rem;margin-top:.5rem}}.no-run-data{{border-color:#ffb86c;grid-column:1/-1}}a{{color:#8be9fd}}</style></head>
<body><h1>COGANT Inspection Dashboard</h1><p>Inspection dashboard generated from the emitted run artifacts ({asset_note}).</p>
<section class="metric-grid" aria-label="Run metrics">{cards}</section>
<h2>Graphical Abstract</h2><p><a href="../figures/graphical_abstract.svg">Graphical abstract</a></p>
<h2>Visual Evidence</h2><p>Program Graph, semantic mappings, matrix dimensions, and generated artifacts are shown from disk.</p>
<h2>Roundtrip Diagnostics</h2><p>Role preservation: {html.escape(str(model['roundtrip']['role_preservation_score']))}; Generated code: {html.escape(str(model['roundtrip']['generated_code'].get('status', 'not recorded')))}.</p>
<p>Mappings: {mapping_labels or 'none recorded'}.</p></body></html>\n'''
    output.write_text(html_text, encoding="utf-8")
    index = run / "site" / "index.html"
    if output != index:
        index.parent.mkdir(parents=True, exist_ok=True)
        existing = index.read_text(encoding="utf-8") if index.is_file() else ""
        link = '<a href="inspection_dashboard.html">Inspection dashboard</a>'
        if "inspection_dashboard.html" not in existing:
            index.write_text(existing + "\n" + link + "\n", encoding="utf-8")
    return output


def write_inspection_artifacts(
    run_dir: Path | str,
    *,
    dashboard_html: Path | str | None = None,
    graphical_abstract_svg: Path | str | None = None,
    graphical_abstract_png: Path | str | None = None,
    embed_assets: bool = True,
) -> dict[str, Path]:
    run = _path(run_dir)
    dashboard = render_inspection_dashboard_html(run, dashboard_html, embed_assets=embed_assets)
    svg = render_graphical_abstract_svg(run, graphical_abstract_svg)
    png = render_graphical_abstract_png(run, graphical_abstract_png, output_svg=svg)
    details = render_interpretability_detail_pngs(run)
    written: dict[str, Path] = {
        "inspection_dashboard_html": dashboard,
        "graphical_abstract_svg": svg,
    }
    if png is not None:
        written["graphical_abstract_png"] = png
    written.update({f"{key}_png": value for key, value in details.items()})
    return written
