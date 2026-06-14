"""Figure metadata, sidecar, and strict-publication validation helpers."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from manuscript_figure_registry import ManuscriptFigure

from figures.common import _as_float, _as_int, _int_dict, _string_values
from figures.constants import _DEGRADED_RENDER_MARKERS
from figures.png import _sha256_file


def _fixture_metrics_summary(data: dict[str, object]) -> dict[str, object] | None:
    """Summarize ``evaluation/figures/metrics.json`` style fixture metrics."""

    fixture_rows = [value for value in data.values() if isinstance(value, dict)]
    if not fixture_rows:
        return None
    if not any(
        {"nodes", "edges", "mappings_total", "state_variables", "elapsed_s"} & set(row)
        for row in fixture_rows
    ):
        return None

    node_kinds: set[str] = set()
    groups: set[str] = set()
    for row in fixture_rows:
        raw_node_kinds = row.get("nodes_by_kind")
        if isinstance(raw_node_kinds, dict):
            node_kinds.update(str(key) for key in raw_node_kinds)
        raw_group = row.get("group")
        if raw_group:
            groups.add(str(raw_group))

    return {
        "fixture_count": len(fixture_rows),
        "fixture_names": sorted(str(key) for key, value in data.items() if isinstance(value, dict)),
        "fixture_group_count": len(groups),
        "fixture_groups": sorted(groups),
        "node_kind_count": len(node_kinds),
        "node_kinds": sorted(node_kinds),
        "total_nodes": sum(_as_int(row.get("nodes")) for row in fixture_rows),
        "total_edges": sum(_as_int(row.get("edges")) for row in fixture_rows),
        "total_mappings": sum(_as_int(row.get("mappings_total")) for row in fixture_rows),
        "total_state_variables": sum(_as_int(row.get("state_variables")) for row in fixture_rows),
        "total_observations": sum(_as_int(row.get("observations")) for row in fixture_rows),
        "total_actions": sum(_as_int(row.get("actions")) for row in fixture_rows),
        "total_transitions": sum(_as_int(row.get("transitions")) for row in fixture_rows),
        "total_elapsed_s": round(sum(_as_float(row.get("elapsed_s")) for row in fixture_rows), 3),
    }


def _count_nested(container: object, key: str) -> int:
    if not isinstance(container, dict):
        return 0
    value = container.get(key)
    if isinstance(value, (list, dict)):
        return len(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _gnn_bundle_summary(data: dict[str, object]) -> dict[str, object] | None:
    """Summarize an exported ``model.gnn.json`` bundle without fixture heuristics."""
    matrices = data.get("matrices")
    state_space = data.get("state_space")
    if not isinstance(matrices, dict) or not isinstance(state_space, dict):
        return None

    dimensions = matrices.get("dimensions") if isinstance(matrices.get("dimensions"), dict) else {}
    shapes = matrices.get("shapes") if isinstance(matrices.get("shapes"), dict) else {}
    mappings = data.get("mappings")
    ontology = data.get("ontology_mapping")
    graph = data.get("program_graph")
    summary: dict[str, object] = {
        "bundle_kind": "gnn_model",
        "model_id": str(data.get("model_id") or ""),
        "schema_name": str(data.get("schema_name") or ""),
        "matrices_count": len([key for key in ("A", "B", "C", "D") if key in matrices]),
        "matrix_dimensions": dict(dimensions),
        "matrix_shapes": dict(shapes),
        "variables_count": _count_nested(state_space, "variables"),
        "observations_count": _count_nested(state_space, "observations"),
        "actions_count": _count_nested(state_space, "actions"),
        "transitions_count": _count_nested(state_space, "transitions"),
        "likelihoods_count": _count_nested(state_space, "likelihoods"),
        "preferences_count": _count_nested(state_space, "preferences"),
        "mappings_count": _count_nested(mappings, "mappings"),
        "ontology_mappings_count": _count_nested(ontology, "mappings"),
        "program_nodes_count": _count_nested(graph, "nodes"),
        "program_edges_count": _count_nested(graph, "edges"),
    }
    if isinstance(dimensions, dict):
        summary["total_state_variables"] = _as_int(dimensions.get("n_states"))
        summary["total_observations"] = _as_int(dimensions.get("n_obs"))
        summary["total_actions"] = _as_int(dimensions.get("n_actions"))
    return summary


def _artifact_summary(path: Path | None, root: Path) -> dict[str, object] | None:
    if path is None or not path.is_file():
        return None
    summary: dict[str, object] = {
        "path": str(path.relative_to(root)),
        "sha256": _sha256_file(path),
    }
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            summary["kind"] = "json"
            if isinstance(data, dict):
                summary["top_level_keys"] = sorted(data.keys())[:40]
                gnn_summary = _gnn_bundle_summary(data)
                if gnn_summary:
                    summary.update(gnn_summary)
                else:
                    fixture_summary = _fixture_metrics_summary(data)
                    if fixture_summary:
                        summary.update(fixture_summary)
                for key in (
                    "nodes",
                    "edges",
                    "semantic_mappings",
                    "mappings",
                    "matrices",
                    "variables",
                    "observations",
                    "actions",
                    "transitions",
                    "likelihoods",
                    "preferences",
                    "targets",
                ):
                    value = data.get(key)
                    if isinstance(value, (list, dict)):
                        summary.setdefault(f"{key}_count", len(value))
                if isinstance(data.get("targets"), list):
                    targets = [row for row in data["targets"] if isinstance(row, dict)]
                    role_totals: dict[str, int] = {}
                    parser_statuses: set[str] = set()
                    roundtrip_statuses: set[str] = set()
                    visual_artifacts = 0
                    total_nodes = 0
                    total_edges = 0
                    total_mappings = 0
                    validation_score_count = 0
                    complete_evidence_target_count = 0
                    for target in targets:
                        node_count = _as_int(target.get("node_count"))
                        edge_count = _as_int(target.get("edge_count"))
                        mapping_count = _as_int(target.get("mapping_count"))
                        total_nodes += node_count
                        total_edges += edge_count
                        total_mappings += mapping_count
                        score = target.get("score")
                        has_score = isinstance(score, int | float) and not isinstance(score, bool)
                        if has_score:
                            validation_score_count += 1
                        target_roles = _int_dict(target.get("role_distribution"))
                        for role, count in target_roles.items():
                            role_totals[role] = role_totals.get(role, 0) + count
                        parser_statuses.add(str(target.get("parser_status") or "unknown"))
                        roundtrip_status = str(target.get("roundtrip_status") or "not_present")
                        roundtrip_statuses.add(roundtrip_status)
                        raw_visual = target.get("visual_artifact_count")
                        visual_count = 0
                        if isinstance(raw_visual, int | float) and not isinstance(raw_visual, bool):
                            visual_count = int(raw_visual)
                            visual_artifacts += visual_count
                        if (
                            node_count > 0
                            and edge_count > 0
                            and mapping_count > 0
                            and target_roles
                            and has_score
                            and bool(roundtrip_status)
                            and visual_count > 0
                        ):
                            complete_evidence_target_count += 1
                    summary["target_count"] = len(targets)
                    summary["total_nodes"] = total_nodes
                    summary["total_edges"] = total_edges
                    summary["total_mappings"] = total_mappings
                    summary["validation_score_count"] = validation_score_count
                    summary["role_kind_count"] = len(role_totals)
                    summary["role_total_count"] = sum(role_totals.values())
                    summary["parser_status_kind_count"] = len(parser_statuses)
                    summary["roundtrip_status_kind_count"] = len(roundtrip_statuses)
                    summary["visual_artifact_total_count"] = visual_artifacts
                    summary["complete_evidence_target_count"] = complete_evidence_target_count
            elif isinstance(data, list):
                summary["kind"] = "json-list"
                summary["top_level_list_count"] = len(data)
            return summary
        text = path.read_text(encoding="utf-8")
        summary.update(
            {
                "kind": "text",
                "line_count": text.count("\n") + 1,
                "byte_count": path.stat().st_size,
            }
        )
    except (OSError, UnicodeDecodeError, ValueError):
        summary["kind"] = "binary"
        summary["byte_count"] = path.stat().st_size
    return summary


def _source_artifact_recency_issues(path: Path | None, root: Path) -> list[dict[str, object]]:
    """Return newer divergent siblings for ``cogant/output/<target>/data/*`` artifacts."""
    if path is None or not path.is_file():
        return []
    try:
        rel = path.relative_to(root)
    except ValueError:
        return []
    parts = rel.parts
    if len(parts) < 5 or parts[0] != "cogant" or parts[1] != "output" or parts[3] != "data":
        return []
    run_dir = root / Path(*parts[:3])
    source_digest = _sha256_file(path)
    findings: list[dict[str, object]] = []
    for candidate in (run_dir / path.name, run_dir / "gnn_package" / path.name):
        if not candidate.is_file() or candidate == path:
            continue
        if candidate.stat().st_mtime_ns <= path.stat().st_mtime_ns:
            continue
        candidate_digest = _sha256_file(candidate)
        if candidate_digest == source_digest:
            continue
        findings.append(
            {
                "source_artifact": str(rel),
                "newer_sibling": str(candidate.relative_to(root)),
                "source_sha256": source_digest,
                "newer_sibling_sha256": candidate_digest,
            }
        )
    return findings


def _package_version(root: Path) -> str:
    pyproject = root / "cogant" / "pyproject.toml"
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    for line in text.splitlines():
        if line.strip().startswith("version"):
            _, _, value = line.partition("=")
            return value.strip().strip('"').strip("'") or "unknown"
    return "unknown"


def _source_metadata(record: dict[str, object]) -> dict[str, object]:
    value = record.get("source_figure_metadata")
    return value if isinstance(value, dict) else {}


def _displayed_counts(record: dict[str, object]) -> dict[str, object]:
    figure_key = str(record.get("key") or "")
    source_metadata = _source_metadata(record)
    for key in ("displayed_counts", "counts"):
        value = source_metadata.get(key)
        if isinstance(value, dict) and value:
            counts = dict(value)
            summary = record.get("source_artifact_summary")
            if (
                figure_key == "rule_evidence_trace"
                and isinstance(summary, dict)
                and isinstance(summary.get("mappings_count"), int)
            ):
                counts["mappings"] = max(
                    int(counts.get("mappings") or 0), summary["mappings_count"]
                )
            return counts

    summary = record.get("source_artifact_summary")
    counts: dict[str, object] = {}
    if isinstance(summary, dict):
        if figure_key in {"forward_state_space_factor", "forward_abcd_matrices"}:
            for key in (
                "variables_count",
                "observations_count",
                "actions_count",
                "transitions_count",
                "likelihoods_count",
                "preferences_count",
            ):
                if key in summary:
                    counts[key] = summary[key]
            if figure_key == "forward_abcd_matrices":
                counts["matrices"] = 4
        elif figure_key == "batch_role_distribution":
            for key in (
                "target_count",
                "role_kind_count",
                "role_total_count",
                "parser_status_kind_count",
                "roundtrip_status_kind_count",
                "visual_artifact_total_count",
            ):
                if key in summary:
                    counts[key] = summary[key]
        for key, value in summary.items():
            if (
                key.endswith("_count")
                or key.startswith("total_")
                or key in {"top_level_list_count", "line_count"}
            ):
                counts[key] = value
    if counts:
        return counts

    return {"panels": 1}


def _panel_metadata(figure: ManuscriptFigure, record: dict[str, object]) -> dict[str, object]:
    source_metadata = _source_metadata(record)
    value = source_metadata.get("panel_metadata")
    if isinstance(value, dict) and value:
        return dict(value)
    return {
        "panels": [
            {
                "key": figure.key,
                "role": figure.role,
                "displayed_counts": record.get("displayed_counts") or {"panels": 1},
            }
        ]
    }


def _panels(record: dict[str, object]) -> list[dict[str, object]]:
    source_metadata = _source_metadata(record)
    value = source_metadata.get("panels")
    if isinstance(value, list) and value:
        return [dict(item) for item in value if isinstance(item, dict)]
    panel_metadata = record.get("panel_metadata")
    if isinstance(panel_metadata, dict):
        nested = panel_metadata.get("panels")
        if isinstance(nested, list) and nested:
            return [dict(item) for item in nested if isinstance(item, dict)]
        panel = panel_metadata.get("panel")
        if panel:
            return [
                {
                    "key": str(panel),
                    "displayed_counts": record.get("displayed_counts") or {"panels": 1},
                    "reading_order": panel_metadata.get("reading_order"),
                }
            ]
    return [
        {
            "key": str(record.get("key") or record.get("role") or "figure"),
            "displayed_counts": record.get("displayed_counts") or {"panels": 1},
        }
    ]


def _layout_method(record: dict[str, object]) -> str:
    source_metadata = _source_metadata(record)
    value = source_metadata.get("layout_method") or source_metadata.get("layout")
    if value:
        return str(value)
    renderer = str(record.get("renderer") or "")
    if "dashboard" in renderer or "inspection_dashboard" in renderer:
        return "dashboard evidence panel"
    if "batch_dashboard" in renderer:
        return "batch dashboard chart layout"
    if "upstream" in renderer.lower():
        return "upstream renderer layout"
    return "registered package renderer layout"


def _layout_seed(record: dict[str, object]) -> int | None:
    source_metadata = _source_metadata(record)
    value = source_metadata.get("layout_seed")
    return value if isinstance(value, int) else None


def _caption_reference_findings(caption: str) -> list[str]:
    findings: list[str] = []
    if re.search(r"@(sec|tbl|eq|fig):[A-Za-z0-9_-]+", caption):
        findings.append("caption.unresolved_crossref")
    if re.search(
        r"\b(Table|Figure)\s+\d+[A-Za-z]?(?:\.\d+)?\s*[:—-]\s*\1\s+\d+",
        caption,
        re.IGNORECASE,
    ):
        findings.append("caption.duplicate_number")
    if re.search(r"\\(?:eq)?ref\{[^}]+\}", caption):
        findings.append("caption.raw_latex_ref")
    return findings


def _publication_dimension_findings(record: dict[str, object]) -> list[str]:
    dims = record.get("dimensions_px")
    if not isinstance(dims, dict):
        return ["dimensions_px"]
    width = _as_int(dims.get("width"))
    height = _as_int(dims.get("height"))
    min_width = _as_int(record.get("min_width_px"), 1000)
    min_height = _as_int(record.get("min_height_px"), 500)
    findings: list[str] = []
    if width < min_width:
        findings.append(f"visual_qa.width_lt_{min_width}")
    if height < min_height:
        findings.append(f"visual_qa.height_lt_{min_height}")
    if record.get("key") == "roundtrip_batch_gantt":
        if height > 1400:
            findings.append("visual_qa.height_gt_1400")
        aspect_ratio = (width / height) if height else 0.0
        if aspect_ratio < 1.6:
            findings.append("visual_qa.aspect_ratio_lt_1_6")
    return findings


def _degraded_render_findings(record: dict[str, object]) -> list[str]:
    source_metadata = _source_metadata(record)
    findings: list[str] = []
    figure_key = str(record.get("key") or "")
    backend = str(source_metadata.get("render_backend") or record.get("render_backend") or "")
    backend_lower = backend.lower()
    if record.get("key") == "graphical_abstract" and backend != "matplotlib_native":
        findings.append("source_figure_metadata.render_backend_matplotlib_native")
    if figure_key in {
        "roundtrip_visual_diff",
        "rule_evidence_trace",
        "confidence_calibration",
        "inference_trace",
    } and backend != "matplotlib_native":
        findings.append("source_figure_metadata.render_backend_matplotlib_native")
    if (
        source_metadata.get("degraded_renderer") is True
        or source_metadata.get("degraded_rasterization") is True
        or "degraded" in backend_lower
    ):
        findings.append("visual_qa.degraded_renderer")
    text_blob = "\n".join(_string_values(record)).lower()
    if any(marker in text_blob for marker in _DEGRADED_RENDER_MARKERS):
        findings.append("visual_qa.degraded_renderer_notice")
    return sorted(set(findings))


def _evidence_requirement_findings(record: dict[str, object]) -> list[str]:
    counts = record.get("displayed_counts")
    if not isinstance(counts, dict):
        return ["displayed_counts"]
    requirements = record.get("evidence_requirements")
    if not isinstance(requirements, (list, tuple)):
        return []
    findings: list[str] = []
    for key in requirements:
        text_key = str(key)
        if text_key not in counts:
            findings.append(f"displayed_counts.{text_key}")
            continue
        value = counts.get(text_key)
        if not text_key.startswith("reviewed_") and _as_int(value) <= 0:
            findings.append(f"displayed_counts.{text_key}_nonzero")
    if record.get("key") == "confidence_calibration":
        role = str(record.get("role") or "")
        caption = str(record.get("caption") or "").lower()
        if "calibration" in role or (
            "calibration" in caption and "not" not in caption and "review-readiness" not in caption
        ):
            findings.append("caption_role.overclaims_calibration")
        if "reviewed_mapping_rows" not in counts or "reviewed_rule_rows" not in counts:
            findings.append("displayed_counts.reviewed_rows")
    return findings


def _matrix_provenance_findings(record: dict[str, object]) -> list[str]:
    if record.get("key") != "forward_abcd_matrices":
        return []
    source_metadata = _source_metadata(record)
    findings: list[str] = []

    def _alignment_findings(prefix: str, value: object) -> list[str]:
        if not isinstance(value, dict) or not value:
            return [prefix]
        missing_or_false: list[str] = []
        for key in ("hidden_states_match", "observations_match", "actions_match"):
            if value.get(key) is not True:
                missing_or_false.append(f"{prefix}.{key}")
        return missing_or_false

    if source_metadata.get("matrix_values_from_artifact") is not True:
        findings.append("source_figure_metadata.matrix_values_from_artifact")
    matrix_validation_errors = source_metadata.get("matrix_validation_errors")
    if matrix_validation_errors not in ([], ()):
        findings.append("source_figure_metadata.matrix_validation_errors_empty")
    fallback_panels = source_metadata.get("fallback_panels")
    if fallback_panels not in ([], ()):
        findings.append("source_figure_metadata.fallback_panels_empty")
    if not source_metadata.get("matrix_source_artifact"):
        findings.append("source_figure_metadata.matrix_source_artifact")
    if not source_metadata.get("source_artifact_digest"):
        findings.append("source_figure_metadata.matrix_source_digest")
    source_shapes = source_metadata.get("source_matrix_shapes")
    if not isinstance(source_shapes, dict):
        findings.append("source_figure_metadata.source_matrix_shapes")
    else:
        for key in ("A", "B", "C", "D"):
            if not isinstance(source_shapes.get(key), list) or not source_shapes.get(key):
                findings.append(f"source_figure_metadata.source_matrix_shapes.{key}")
    reducers = source_metadata.get("matrix_reducers")
    if not isinstance(reducers, dict):
        findings.append("source_figure_metadata.matrix_reducers")
    else:
        reducer_b = reducers.get("B")
        if not isinstance(reducer_b, dict) or reducer_b.get("method") != "max_over_actions":
            findings.append("source_figure_metadata.matrix_reducers.B")
    findings.extend(
        _alignment_findings(
            "source_figure_metadata.dimension_alignment",
            source_metadata.get("dimension_alignment"),
        )
    )
    label_groups = source_metadata.get("state_label_groups")
    if not isinstance(label_groups, list) or not label_groups:
        findings.append("source_figure_metadata.state_label_groups")
    interpretation_notes = source_metadata.get("matrix_interpretation_notes")
    if not isinstance(interpretation_notes, dict):
        findings.append("source_figure_metadata.matrix_interpretation_notes")
    else:
        for key in ("A", "B", "C", "D"):
            if not interpretation_notes.get(key):
                findings.append(f"source_figure_metadata.matrix_interpretation_notes.{key}")
    degraded_panels = record.get("degraded_panels")
    if degraded_panels not in ([], ()):
        findings.append("degraded_panels_empty")
    if not record.get("matrix_source_path"):
        findings.append("matrix_source_path")
    if not record.get("matrix_source_digest"):
        findings.append("matrix_source_digest")
    b_reducer = record.get("b_reducer")
    if not isinstance(b_reducer, dict) or b_reducer.get("method") != "max_over_actions":
        findings.append("b_reducer")
    for key in (
        "source_matrix_diagnostics",
        "panel_diagnostics",
        "matrix_dimensions",
        "state_space_counts",
    ):
        value = record.get(key)
        if not isinstance(value, dict) or not value:
            findings.append(key)
    findings.extend(_alignment_findings("dimension_alignment", record.get("dimension_alignment")))
    for key in ("source_matrix_diagnostics", "panel_diagnostics"):
        value = record.get(key)
        if isinstance(value, dict):
            for panel in ("A", "B", "C", "D"):
                if not isinstance(value.get(panel), dict) or not value.get(panel):
                    findings.append(f"{key}.{panel}")
    return findings


def _metadata_missing(record: dict[str, object]) -> list[str]:
    required = (
        "caption",
        "role",
        "source_artifact",
        "renderer",
        "method_note",
        "reading_guide",
        "limitations",
        "known_limitations",
        "alt_text",
        "sha256",
        "data_digest_sha256",
        "source_artifact_digest",
        "renderer_version",
        "layout_method",
        "displayed_counts",
        "panel_metadata",
        "panels",
    )
    missing = [key for key in required if not record.get(key)]
    if not record.get("source_artifact_exists"):
        missing.append("source_artifact_exists")
    dims = record.get("dimensions_px")
    if not isinstance(dims, dict) or not dims.get("width") or not dims.get("height"):
        missing.append("dimensions_px")
    qa = record.get("visual_qa")
    if not isinstance(qa, dict):
        missing.append("visual_qa")
    else:
        if qa.get("nonblank") is False:
            missing.append("visual_qa.nonblank")
        if qa.get("min_dimension_ok") is False:
            missing.append("visual_qa.min_dimension_ok")
        if qa.get("color_diversity_ok") is False:
            missing.append("visual_qa.color_diversity_ok")
    missing.extend(_publication_dimension_findings(record))
    missing.extend(_degraded_render_findings(record))
    missing.extend(_evidence_requirement_findings(record))
    missing.extend(_matrix_provenance_findings(record))
    missing.extend(_caption_reference_findings(str(record.get("caption") or "")))
    return missing


_MANUSCRIPT_FIGURE_RE = re.compile(
    r"\]\(\s*<?\.\./figures/([^)>#\s]+\.png)(?:#[^)>\s]+)?>?"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)",
    re.IGNORECASE,
)


def _active_manuscript_figure_refs(root: Path) -> set[str]:
    manuscript_dir = root / "manuscript"
    if not manuscript_dir.is_dir():
        return set()
    refs: set[str] = set()
    skipped = {"README.md", "SYNTAX.md", "AGENTS.md"}
    for path in sorted(manuscript_dir.glob("*.md")):
        if path.name in skipped:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        refs.update(_MANUSCRIPT_FIGURE_RE.findall(text))
    return refs


def _reference_failures(root: Path, figures: Iterable[ManuscriptFigure]) -> list[str]:
    manuscript_dir = root / "manuscript"
    if not manuscript_dir.is_dir():
        return []
    refs = _active_manuscript_figure_refs(root)
    registered = {
        Path(figure.destination).name: figure
        for figure in figures
        if figure.require_manuscript_reference
    }
    failures: list[str] = []
    inserted_unregistered = sorted(refs - set(registered))
    if inserted_unregistered:
        failures.append("inserted-but-unregistered figures: " + ", ".join(inserted_unregistered))
    uncited = sorted(name for name in registered if name not in refs)
    if uncited:
        failures.append("registered-but-uncited figures: " + ", ".join(uncited))
    return failures
