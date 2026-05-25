"""Run-directory inspection dashboard and graphical abstract generation.

The object-oriented :mod:`cogant.viz.dashboard` API is useful when callers
already hold a ``ProgramGraph`` and related objects in memory. This module is
the complementary artifact-first path: it reads a completed
``cogant/output/<target>/`` directory and writes a self-contained dashboard
plus a graphical abstract from the JSON, PNG, Markdown, and roundtrip files
that users actually inspect after a run.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from textwrap import dedent
from typing import Any, cast

__all__ = [
    "build_inspection_model",
    "render_graphical_abstract_png",
    "render_graphical_abstract_svg",
    "render_interpretability_detail_pngs",
    "render_inspection_dashboard_html",
    "write_inspection_artifacts",
]

FIGURE_SIDECAR_SCHEMA_VERSION = "1.2"


_FIGURE_CANDIDATES: tuple[tuple[str, str, str], ...] = (
    (
        "Interpretability Overview",
        "figures/interpretability_overview.png",
        "One-page graph, semantic-role, state-space, and blanket summary.",
    ),
    ("Program Graph", "figures/program_graph.png", "Typed code entities and relations."),
    (
        "State-Space Factor Graph",
        "figures/state_space_factor.png",
        "Compiled hidden states, observations, actions, and factor links.",
    ),
    (
        "A/B/C/D Matrices",
        "figures/connections_matrix.png",
        "Likelihood, transition, preference, and prior arrays.",
    ),
    (
        "Markov Blanket",
        "figures/markov_blanket.png",
        "Internal, sensory, active, and external partition.",
    ),
    ("GNN Markdown Render", "figures/model_gnn.png", "Rendered first page of model.gnn.md."),
    ("Process Gantt", "figures/process_gantt.png", "Run-stage timing and dependency trace."),
    (
        "Graphical Abstract",
        "figures/graphical_abstract.png",
        "Code-to-GNN-to-code evidence chain.",
    ),
    (
        "Roundtrip Visual Diff",
        "figures/roundtrip_diff.png",
        "Original vs regenerated graph, GNN, role, and matrix deltas.",
    ),
    (
        "Rule Evidence Trace",
        "figures/rule_trace.png",
        "Per-rule contribution and conflict-resolution summary.",
    ),
    (
        "Evidence Coverage",
        "figures/confidence_calibration.png",
        "Mapping confidence tiers, rule contributions, conflicts, and review coverage.",
    ),
    (
        "Inference Trace",
        "figures/inference_trace.png",
        "Belief, action, preference, and free-energy runtime smoke trace.",
    ),
    (
        "Package Dashboard",
        "gnn_package/visualizations/dashboard.html",
        "GNN package-level distribution dashboard.",
    ),
    ("Interpretability Overview", "interpretability_overview.png", "Root-level overview render."),
    ("Program Graph", "program_graph.png", "Root-level program graph render."),
    ("State-Space Factor Graph", "state_space_factor.png", "Root-level state-space render."),
    ("A/B/C/D Matrices", "connections_matrix.png", "Root-level matrix render."),
    ("Markov Blanket", "markov_blanket.png", "Root-level blanket render."),
    ("GNN Markdown Render", "model_gnn.png", "Root-level GNN markdown render."),
)

_ARTIFACT_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("Run bundle", "data/bundle.json"),
    ("Program graph JSON", "data/program_graph.json"),
    ("GNN package manifest", "gnn_package/manifest.json"),
    ("GNN JSON", "gnn_package/model.gnn.json"),
    ("GNN Markdown", "gnn_package/model.gnn.md"),
    ("State-space JSON", "gnn_package/state_space.json"),
    ("Markov blanket JSON", "gnn_package/markov_blanket.json"),
    ("Run summary", "reports/run_summary.md"),
    ("Static site", "site/index.html"),
    ("Inspection dashboard", "site/inspection_dashboard.html"),
    ("Roundtrip metrics", "roundtrip/metrics.json"),
    ("Roundtrip rule evidence", "roundtrip/rule_evidence_trace.json"),
    ("Forward GNN", "roundtrip/forward/model.gnn.md"),
    ("Regenerated GNN", "roundtrip/regenerated/model.gnn.md"),
    ("Reverse code directory", "roundtrip/reverse"),
    ("Rule evidence trace", "data/rule_evidence_trace.json"),
    ("Inference trace", "data/inference_trace.json"),
    ("Validation report", "data/validation_report.json"),
    ("Validation text", "validate.txt"),
)


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(value, dict):
        return cast(dict[str, Any], value)
    return {}


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return cast(dict[str, Any], value)
    return {}


def _iter_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [cast(dict[str, Any], item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [cast(dict[str, Any], item) for item in value.values() if isinstance(item, dict)]
    return []


def _collection_len(value: Any) -> int:
    if isinstance(value, dict):
        for key in ("transition_count", "total_mappings", "count"):
            count = value.get(key)
            if isinstance(count, int):
                return count
            if isinstance(count, float):
                return int(count)
        return len(value)
    if isinstance(value, (list, tuple, set)):
        return len(value)
    return 0


def _to_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _to_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _first_existing(run_dir: Path, candidates: tuple[str, ...]) -> Path | None:
    for rel in candidates:
        path = run_dir / rel
        if path.exists():
            return path
    return None


def _rel(path: Path | None, base: Path) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _node_records(program_graph: dict[str, Any]) -> list[dict[str, Any]]:
    return _iter_records(program_graph.get("nodes"))


def _edge_records(program_graph: dict[str, Any]) -> list[dict[str, Any]]:
    return _iter_records(program_graph.get("edges"))


def _record_id(record: dict[str, Any]) -> str:
    for key in ("id", "node_id", "source_id"):
        value = record.get(key)
        if isinstance(value, str):
            return value
    return ""


def _node_index(program_graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in _node_records(program_graph):
        node_id = _record_id(record)
        if node_id:
            indexed[node_id] = record
    return indexed


def _node_label(node_id: str, nodes: dict[str, dict[str, Any]]) -> str:
    record = nodes.get(node_id, {})
    for key in ("qualified_name", "name", "label"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return node_id[:12] if node_id else "unknown"


def _count_by(
    records: list[dict[str, Any]], key: str, *, default: str = "unknown"
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = record.get(key)
        name = value if isinstance(value, str) and value else default
        counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _distribution(value: Any) -> dict[str, int]:
    if isinstance(value, dict):
        out: dict[str, int] = {}
        for key, raw in value.items():
            if isinstance(raw, bool):
                out[str(key)] = int(raw)
            elif isinstance(raw, int):
                out[str(key)] = raw
            elif isinstance(raw, float):
                out[str(key)] = int(raw)
            elif isinstance(raw, (list, tuple, set, dict)):
                out[str(key)] = _collection_len(raw)
        return dict(sorted(out.items(), key=lambda item: (-item[1], item[0])))
    records = _iter_records(value)
    return _count_by(records, "kind")


def _mapping_records(mappings: dict[str, Any]) -> list[dict[str, Any]]:
    nested = mappings.get("mappings")
    if nested is not None:
        return _iter_records(nested)
    return _iter_records(mappings)


def _semantic_summary(model_gnn: dict[str, Any]) -> dict[str, Any]:
    mappings = _as_mapping(model_gnn.get("mappings"))
    summary = _as_mapping(mappings.get("summary"))
    records = _mapping_records(mappings)

    mapping_kinds = _distribution(summary.get("mapping_kinds"))
    if not mapping_kinds:
        mapping_kinds = _count_by(records, "kind")

    confidence_tiers = _distribution(summary.get("confidence_tiers"))
    if not confidence_tiers:
        confidence_tiers = _count_by(records, "confidence_tier", default="uncalibrated")

    status_distribution = _distribution(summary.get("status_distribution"))
    if not status_distribution:
        status_distribution = _count_by(records, "status", default="unreviewed")

    top_records = sorted(
        records,
        key=lambda item: _to_float(item.get("confidence_score")),
        reverse=True,
    )[:8]
    top_mappings: list[dict[str, Any]] = []
    for record in top_records:
        top_mappings.append(
            {
                "label": str(record.get("semantic_label") or record.get("id") or "mapping"),
                "kind": str(record.get("kind") or "unknown"),
                "confidence": _to_float(record.get("confidence_score")),
                "status": str(record.get("status") or "unreviewed"),
            }
        )

    total = summary.get("total_mappings")
    total_mappings = _to_int(total, len(records))
    return {
        "total": total_mappings,
        "mapping_kinds": mapping_kinds,
        "confidence_tiers": confidence_tiers,
        "status_distribution": status_distribution,
        "top_mappings": top_mappings,
    }


def _state_space_summary(state_space: dict[str, Any]) -> dict[str, Any]:
    metadata = _as_mapping(state_space.get("metadata"))
    transitions = state_space.get("transitions")
    return {
        "variables": _to_int(
            metadata.get("num_variables"),
            _collection_len(state_space.get("variables")),
        ),
        "observations": _to_int(
            metadata.get("num_observations"),
            _collection_len(state_space.get("observations")),
        ),
        "actions": _to_int(
            metadata.get("num_actions"), _collection_len(state_space.get("actions"))
        ),
        "transitions": _collection_len(transitions),
        "time_regime": str(_as_mapping(transitions).get("time_regime") or "unknown"),
    }


def _shape_text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return " x ".join(str(item) for item in value)
    if isinstance(value, str):
        return value
    return "n/a"


def _matrix_summary(model_gnn: dict[str, Any]) -> dict[str, Any]:
    matrices = _as_mapping(model_gnn.get("matrices"))
    shapes = _as_mapping(matrices.get("shapes"))
    dimensions = _as_mapping(matrices.get("dimensions"))
    shape_map = {key: _shape_text(shapes.get(key)) for key in ("A", "B", "C", "D")}
    if all(value == "n/a" for value in shape_map.values()):
        shape_map = {
            key: _shape_text(matrices.get(key))
            for key in ("A", "B", "C", "D")
            if matrices.get(key) is not None
        }
    return {
        "shapes": shape_map,
        "dimensions": {
            key: int(value)
            for key, value in dimensions.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        },
    }


def _blanket_summary(blanket: dict[str, Any]) -> dict[str, Any]:
    stats = _as_mapping(blanket.get("stats"))
    roles = _as_mapping(blanket.get("roles"))
    role_counts: dict[str, int] = {}
    for role in ("internal", "sensory", "active", "external"):
        stat_key = f"{role}_count"
        stat_value = stats.get(stat_key)
        if isinstance(stat_value, int):
            role_counts[role] = stat_value
        else:
            role_counts[role] = _collection_len(roles.get(role))
    return {
        "role_counts": role_counts,
        "stats": {
            key: value
            for key, value in stats.items()
            if isinstance(value, (int, float, str)) and not isinstance(value, bool)
        },
    }


def _quality_summary(model_gnn: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    notes = _as_mapping(model_gnn.get("validation_notes"))
    confidence = _as_mapping(model_gnn.get("confidence"))
    coverage = _as_mapping(model_gnn.get("source_coverage"))
    status = notes.get("validation_status") or validation.get("status") or validation.get("valid")
    return {
        "validation_status": str(status) if status is not None else "unknown",
        "last_validated": str(notes.get("last_validated") or validation.get("generated_at") or ""),
        "overall_confidence": _to_float(confidence.get("overall_confidence")),
        "source_coverage": _to_float(coverage.get("coverage_percentage")),
    }


def _ranked_pairs(value: Any) -> list[tuple[str, float]]:
    pairs: list[tuple[str, float]] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                key = str(item[0])
                raw = item[1]
                if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                    pairs.append((key, float(raw)))
            elif isinstance(item, dict):
                key = str(item.get("id") or item.get("node_id") or item.get("name") or "")
                raw = item.get("score") or item.get("value") or item.get("degree")
                if key and isinstance(raw, (int, float)) and not isinstance(raw, bool):
                    pairs.append((key, float(raw)))
    return pairs


def _hotspot_rows(
    analysis: dict[str, Any], nodes: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for category in ("hubs", "bottlenecks"):
        for node_id, score in _ranked_pairs(analysis.get(category))[:8]:
            rows.append(
                {
                    "category": category[:-1] if category.endswith("s") else category,
                    "node_id": node_id,
                    "label": _node_label(node_id, nodes),
                    "score": score,
                }
            )
    return rows


def _figures(run_dir: Path) -> list[dict[str, Any]]:
    seen: set[Path] = set()
    figures: list[dict[str, Any]] = []
    for title, rel_path, caption in _FIGURE_CANDIDATES:
        path = run_dir / rel_path
        if not path.is_file() or path.resolve() in seen:
            continue
        seen.add(path.resolve())
        figures.append(
            {
                "title": title,
                "path": path,
                "relative_path": _rel(path, run_dir) or path.as_posix(),
                "caption": caption,
            }
        )
    return figures


def _artifact_record(run_dir: Path, label: str, rel_path: str) -> dict[str, Any]:
    path = run_dir / rel_path
    return {
        "label": label,
        "path": rel_path,
        "present": path.exists(),
        "kind": "directory" if path.is_dir() else "file",
    }


def _first_file_under(path: Path) -> Path | None:
    if not path.is_dir():
        return None
    for candidate in sorted(path.rglob("*")):
        if candidate.is_file():
            return candidate
    return None


def _int_mapping(value: Any) -> dict[str, int]:
    """Return a string→int mapping, dropping values that cannot be counted."""
    if not isinstance(value, dict):
        return {}
    out: dict[str, int] = {}
    for key, raw in value.items():
        count = _to_int(raw, default=-1)
        if count >= 0:
            out[str(key)] = count
    return dict(sorted(out.items(), key=lambda item: item[0]))


def _roundtrip_metrics(run_dir: Path) -> tuple[dict[str, Any], Path | None]:
    path = _first_existing(
        run_dir,
        (
            "roundtrip/metrics.json",
            "roundtrip_metrics.json",
        ),
    )
    return _read_json(path), path


def _error_strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(err) for err in value]
    if value:
        return [str(value)]
    return []


def _roundtrip_role_score(metrics: dict[str, Any]) -> Any:
    return metrics.get("role_preservation_score", metrics.get("role_match_score"))


def _roundtrip_invariants(metrics: dict[str, Any]) -> dict[str, Any]:
    return _as_mapping(metrics.get("invariants") or metrics.get("roundtrip_invariants"))


def _roundtrip_summary(run_dir: Path) -> dict[str, Any]:
    metrics, metrics_path = _roundtrip_metrics(run_dir)
    forward = _first_existing(
        run_dir,
        (
            "roundtrip/forward/model.gnn.md",
            "roundtrip/forward/model.gnn.json",
            "gnn_package/model.gnn.md",
        ),
    )
    reverse_root = run_dir / "roundtrip" / "reverse"
    reverse_file = _first_file_under(reverse_root)
    if forward and reverse_file:
        status = "forward and reverse present"
    elif forward:
        status = "forward present; reverse not present"
    elif reverse_file:
        status = "reverse present; forward not present"
    else:
        status = "not present"
    if metrics:
        roundtrip_status = metrics.get("roundtrip_status")
        if roundtrip_status:
            status = str(roundtrip_status).lower()
        elif isinstance(metrics.get("is_isomorphic"), bool):
            status = "structurally_isomorphic" if metrics["is_isomorphic"] else "drift"
        else:
            status = "metrics present"
    return {
        "status": status,
        "metrics_present": bool(metrics),
        "metrics_path": _rel(metrics_path, run_dir),
        "roundtrip_status": metrics.get("roundtrip_status") if metrics else None,
        "role_preservation_score": _to_float(_roundtrip_role_score(metrics)) if metrics else None,
        "role_preserved": metrics.get("role_preserved") if metrics else None,
        "structurally_isomorphic": (
            metrics.get("structurally_isomorphic", metrics.get("is_isomorphic"))
            if metrics
            else None
        ),
        "matrix_preserved": metrics.get("matrix_preserved") if metrics else None,
        "gnn_sections_preserved": metrics.get("gnn_sections_preserved") if metrics else None,
        "generated_code_ok": metrics.get("generated_code_ok") if metrics else None,
        "matrix_score": _to_float(metrics.get("matrix_score")) if metrics else None,
        "structural_score": _to_float(metrics.get("structural_score")) if metrics else None,
        "threshold": _to_float(metrics.get("threshold")) if metrics else None,
        "role_confusion": _iter_records(metrics.get("role_confusion")) if metrics else [],
        "graph_edit_distance": _as_mapping(metrics.get("graph_edit_distance")) if metrics else {},
        "graph_delta": _as_mapping(metrics.get("graph_delta")) if metrics else {},
        "gnn_diff": _as_mapping(metrics.get("gnn_diff")) if metrics else {},
        "matrix_delta": _as_mapping(metrics.get("matrix_delta")) if metrics else {},
        "invariants": _roundtrip_invariants(metrics) if metrics else {},
        "generated_code": _as_mapping(metrics.get("generated_code")) if metrics else {},
        "original_roles": _int_mapping(metrics.get("original_roles")) if metrics else {},
        "synthesized_roles": _int_mapping(metrics.get("synthesized_roles")) if metrics else {},
        "original_graph_summary": _as_mapping(metrics.get("original_graph_summary"))
        if metrics
        else {},
        "synthesized_graph_summary": _as_mapping(metrics.get("synthesized_graph_summary"))
        if metrics
        else {},
        "shape_match": _as_mapping(metrics.get("shape_match")) if metrics else {},
        "errors": _error_strings(metrics.get("errors")) if metrics else [],
        "forward_present": forward is not None,
        "reverse_present": reverse_file is not None,
        "forward_path": _rel(forward, run_dir),
        "reverse_path": _rel(reverse_file, run_dir),
    }


def _rule_trace(run_dir: Path) -> tuple[dict[str, Any], Path | None]:
    path = _first_existing(
        run_dir,
        (
            "data/rule_evidence_trace.json",
            "rule_evidence_trace.json",
            "roundtrip/rule_evidence_trace.json",
        ),
    )
    trace = _read_json(path)
    return trace, path


def _rule_trace_summary(trace: dict[str, Any], path: Path | None, run_dir: Path) -> dict[str, Any]:
    calibration = _as_mapping(trace.get("calibration"))
    per_rule = _iter_records(calibration.get("per_rule"))
    mappings = _iter_records(trace.get("mappings"))
    reviewed_rule_count = sum(
        1 for row in per_rule if _to_float(_as_mapping(row).get("review_coverage")) > 0
    )
    review_status_summary: dict[str, int] = {}
    mapping_status_summary: dict[str, int] = {}
    reviewed_mapping_rows = 0
    for mapping in mappings:
        mapping_status = str(
            mapping.get("final_mapping_status") or mapping.get("status") or "unknown"
        )
        mapping_status_summary[mapping_status] = mapping_status_summary.get(mapping_status, 0) + 1
        review = _as_mapping(mapping.get("review"))
        review_status = str(
            review.get("status") or mapping.get("review_status") or "unreviewed"
        )
        review_status_summary[review_status] = review_status_summary.get(review_status, 0) + 1
        if review_status.lower() not in {"", "auto_proposed", "unreviewed", "none", "unknown"}:
            reviewed_mapping_rows += 1
    return {
        "path": _rel(path, run_dir),
        "mapping_count": _to_int(
            trace.get("mapping_count"), _collection_len(trace.get("mappings"))
        ),
        "rule_summary": _int_mapping(trace.get("rule_summary")),
        "kind_summary": _int_mapping(trace.get("kind_summary")),
        "confidence_tier_summary": _int_mapping(trace.get("confidence_tier_summary")),
        "mapping_status_summary": dict(sorted(mapping_status_summary.items())),
        "review_status_summary": dict(sorted(review_status_summary.items())),
        "conflict_events": _iter_records(trace.get("conflict_events")),
        "calibration": calibration,
        "per_rule_count": len(per_rule),
        "reviewed_rule_count": reviewed_rule_count,
        "unreviewed_rule_count": max(len(per_rule) - reviewed_rule_count, 0),
        "reviewed_mapping_rows": reviewed_mapping_rows,
        "unreviewed_mapping_rows": max(len(mappings) - reviewed_mapping_rows, 0),
        "per_rule": per_rule[:12],
    }


def _inference_trace(run_dir: Path) -> tuple[dict[str, Any], Path | None]:
    path = _first_existing(
        run_dir,
        (
            "data/inference_trace.json",
            "inference_trace.json",
            "analysis/inference_trace.json",
        ),
    )
    return _read_json(path), path


def _inference_summary(trace: dict[str, Any], path: Path | None, run_dir: Path) -> dict[str, Any]:
    records = _iter_records(trace.get("trace"))
    free_energy = [
        _to_float(record.get("free_energy"))
        for record in records
        if record.get("free_energy") is not None
    ]
    actions = [str(record.get("action")) for record in records if record.get("action") is not None]
    preferences = [
        _to_float(record.get("preference_satisfaction"))
        for record in records
        if record.get("preference_satisfaction") is not None
    ]
    return {
        "path": _rel(path, run_dir),
        "steps": len(records),
        "final_free_energy": free_energy[-1] if free_energy else None,
        "mean_free_energy": sum(free_energy) / len(free_energy) if free_energy else None,
        "actions": actions,
        "mean_preference_satisfaction": (
            sum(preferences) / len(preferences) if preferences else None
        ),
        "trace_count": len(records),
        "trace": records[:12],
    }


def build_inspection_model(run_dir: Path | str) -> dict[str, Any]:
    """Summarize a completed COGANT run directory for visual inspection."""

    root = Path(run_dir).resolve()
    program_path = _first_existing(
        root,
        (
            "data/program_graph.json",
            "program_graph.json",
            "gnn_package/program_graph.json",
            "gnn_pipeline/program_graph.json",
        ),
    )
    model_path = _first_existing(
        root,
        ("gnn_package/model.gnn.json", "data/model.gnn.json", "model.gnn.json"),
    )
    state_path = _first_existing(
        root,
        ("gnn_package/state_space.json", "data/state_space.json", "state_space.json"),
    )
    blanket_path = _first_existing(
        root,
        ("gnn_package/markov_blanket.json", "data/markov_blanket.json", "markov_blanket.json"),
    )
    validation_path = _first_existing(
        root, ("data/validation_report.json", "validation_report.json")
    )
    manifest_path = _first_existing(root, ("gnn_package/manifest.json", "manifest.json"))
    hotspot_path = _first_existing(root, ("analysis/graph_hotspots.json", "graph_hotspots.json"))

    program_graph = _read_json(program_path)
    model_gnn = _read_json(model_path)
    state_space = _read_json(state_path)
    blanket = _read_json(blanket_path)
    validation = _read_json(validation_path)
    manifest = _read_json(manifest_path)
    hotspots = _read_json(hotspot_path)
    rule_trace, rule_trace_path = _rule_trace(root)
    inference_trace, inference_trace_path = _inference_trace(root)

    node_records = _node_records(program_graph)
    edge_records = _edge_records(program_graph)
    node_lookup = _node_index(program_graph)
    manifest_state = _as_mapping(manifest.get("state_space_stats"))
    manifest_graph = _as_mapping(manifest.get("graph_stats"))
    semantic = _semantic_summary(model_gnn)
    state = _state_space_summary(state_space)
    if manifest_state:
        state["variables"] = _to_int(manifest_state.get("variables"), _to_int(state["variables"]))
        state["observations"] = _to_int(
            manifest_state.get("observations"),
            _to_int(state["observations"]),
        )
        state["actions"] = _to_int(manifest_state.get("actions"), _to_int(state["actions"]))

    graph_nodes = _to_int(manifest_graph.get("nodes"), len(node_records))
    graph_edges = _to_int(manifest_graph.get("edges"), len(edge_records))
    no_run_data = (
        program_path is None
        and model_path is None
        and state_path is None
        and blanket_path is None
        and (root / "data" / "bundle.json").exists() is False
        and graph_nodes == 0
        and graph_edges == 0
        and _to_int(semantic.get("total"), 0) == 0
    )

    artifacts = [
        _artifact_record(root, label, rel_path) for label, rel_path in _ARTIFACT_CANDIDATES
    ]

    return {
        "run_id": root.name,
        "run_dir": root.as_posix(),
        "generated_at": datetime.now(UTC).isoformat(),
        "package_timestamp": str(manifest.get("timestamp") or ""),
        "paths": {
            "program_graph": _rel(program_path, root),
            "model_gnn": _rel(model_path, root),
            "state_space": _rel(state_path, root),
            "markov_blanket": _rel(blanket_path, root),
            "manifest": _rel(manifest_path, root),
            "hotspots": _rel(hotspot_path, root),
        },
        "program": {
            "nodes": graph_nodes,
            "edges": graph_edges,
            "node_kinds": _count_by(node_records, "kind"),
            "edge_kinds": _count_by(edge_records, "kind"),
        },
        "semantic": semantic,
        "state_space": state,
        "matrices": _matrix_summary(model_gnn),
        "blanket": _blanket_summary(blanket),
        "quality": _quality_summary(model_gnn, validation),
        "roundtrip": _roundtrip_summary(root),
        "rule_trace": _rule_trace_summary(rule_trace, rule_trace_path, root),
        "inference": _inference_summary(inference_trace, inference_trace_path, root),
        "no_run_data": no_run_data,
        "hotspots": _hotspot_rows(hotspots, node_lookup),
        "figures": _figures(root),
        "artifacts": artifacts,
    }


def _fmt_int(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{int(value):,}"
    return "0"


def _fmt_percent(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{float(value):.0f}%"
    return "0%"


def _status_is_valid(value: Any) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"valid", "true", "ok", "pass", "passed", "success", "successful"}:
        return True
    if text in {"invalid", "false", "fail", "failed", "error"}:
        return False
    return None


def _run_evidence_confidence(model: dict[str, Any]) -> float:
    """Composite confidence for the generated visual evidence stack."""
    program = _as_mapping(model.get("program"))
    semantic = _as_mapping(model.get("semantic"))
    state = _as_mapping(model.get("state_space"))
    matrices = _as_mapping(model.get("matrices"))
    matrix_shapes = _as_mapping(matrices.get("shapes"))
    blanket = _as_mapping(model.get("blanket"))
    role_counts = _as_mapping(blanket.get("role_counts"))
    quality = _as_mapping(model.get("quality"))
    roundtrip = _as_mapping(model.get("roundtrip"))
    figures = cast(list[dict[str, Any]], model.get("figures") or [])

    scores: list[float] = []

    if _to_int(program.get("nodes")) or _to_int(program.get("edges")):
        scores.append(1.0)
    if _to_int(semantic.get("total")):
        scores.append(1.0)
    if (
        _to_int(state.get("variables"))
        or _to_int(state.get("observations"))
        or _to_int(state.get("actions"))
    ):
        scores.append(1.0)
    if any(value and value != "n/a" for value in matrix_shapes.values()):
        scores.append(1.0)
    if sum(_to_int(value) for value in role_counts.values()) > 0:
        scores.append(1.0)

    coverage = _to_float(quality.get("source_coverage"))
    if coverage > 0.0:
        scores.append(max(0.0, min(1.0, coverage / 100.0)))

    valid = _status_is_valid(quality.get("validation_status"))
    if valid is not None:
        scores.append(1.0 if valid else 0.0)

    role_score = roundtrip.get("role_preservation_score", roundtrip.get("role_match_score"))
    if role_score is not None:
        scores.append(max(0.0, min(1.0, _to_float(role_score))))
    elif isinstance(roundtrip.get("role_preserved"), bool):
        scores.append(1.0 if roundtrip["role_preserved"] else 0.0)
    elif isinstance(roundtrip.get("structurally_isomorphic"), bool):
        scores.append(1.0 if roundtrip["structurally_isomorphic"] else 0.0)

    if figures:
        scores.append(max(0.0, min(1.0, len(figures) / 4.0)))

    return sum(scores) / len(scores) if scores else _to_float(quality.get("overall_confidence"))


def _svg_lines(text: str, *, max_chars: int = 20) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join([*current, word])
        if len(trial) > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines[:3]


def _svg_text_block(
    lines: list[str],
    *,
    x: int,
    y: int,
    size: int,
    fill: str,
    weight: str = "500",
    anchor: str = "middle",
) -> str:
    tspans: list[str] = []
    for idx, line in enumerate(lines):
        dy = 0 if idx == 0 else size + 5
        tspans.append(f'<tspan x="{x}" dy="{dy}">{escape(line)}</tspan>')
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{"".join(tspans)}</text>'
    )


def _graphical_abstract_svg(model: dict[str, Any]) -> str:
    program = _as_mapping(model.get("program"))
    semantic = _as_mapping(model.get("semantic"))
    state = _as_mapping(model.get("state_space"))
    matrices = _as_mapping(model.get("matrices"))
    matrix_shapes = _as_mapping(matrices.get("shapes"))
    blanket = _as_mapping(model.get("blanket"))
    role_counts = _as_mapping(blanket.get("role_counts"))
    quality = _as_mapping(model.get("quality"))
    roundtrip = _as_mapping(model.get("roundtrip"))
    rt_role_score = roundtrip.get("role_preservation_score", roundtrip.get("role_match_score"))
    rt_detail = (
        f"role {_fmt_percent(_to_float(rt_role_score) * 100.0)}"
        if rt_role_score is not None
        else "artifact trace"
    )
    evidence_confidence = _run_evidence_confidence(model)

    stages = [
        (
            "Source Code",
            "static and structural evidence",
            _fmt_percent(quality.get("source_coverage")),
            "#2f6f9f",
        ),
        (
            "Program Graph",
            f"{_fmt_int(program.get('nodes'))} nodes / {_fmt_int(program.get('edges'))} edges",
            "typed entities",
            "#7a5cfa",
        ),
        (
            "Semantic Roles",
            f"{_fmt_int(semantic.get('total'))} mappings",
            ", ".join(list(_as_mapping(semantic.get("mapping_kinds")).keys())[:3]) or "role map",
            "#c46a2f",
        ),
        (
            "State Space",
            (
                f"{_fmt_int(state.get('variables'))} variables, "
                f"{_fmt_int(state.get('observations'))} observations"
            ),
            f"{_fmt_int(state.get('actions'))} actions",
            "#0b7a75",
        ),
        (
            "GNN Matrices",
            "A " + str(matrix_shapes.get("A", "n/a")),
            "B " + str(matrix_shapes.get("B", "n/a")),
            "#546a7b",
        ),
        (
            "Markov Blanket",
            f"{_fmt_int(role_counts.get('internal'))} internal / {_fmt_int(role_counts.get('sensory'))} sensory",
            f"{_fmt_int(role_counts.get('active'))} active / {_fmt_int(role_counts.get('external'))} external",
            "#8c4a6f",
        ),
        (
            "Roundtrip",
            str(roundtrip.get("status") or "not present"),
            rt_detail,
            "#4f7d4f",
        ),
    ]

    box_w = 164
    box_h = 142
    gap = 26
    start_x = 38
    y = 166
    parts = [
        (
            '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="620" '
            'viewBox="0 0 1400 620" role="img" aria-labelledby="title desc">'
        ),
        '<title id="title">COGANT graphical abstract</title>',
        (
            '<desc id="desc">Artifact-derived visual summary of the code to graph '
            "to GNN to roundtrip evidence chain.</desc>"
        ),
        "<defs>",
        '<marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">',
        '<path d="M2,2 L10,6 L2,10 Z" fill="#4a5568"/>',
        "</marker>",
        "</defs>",
        '<rect width="1400" height="620" fill="#f7f8fb"/>',
        (
            '<text x="700" y="58" text-anchor="middle" font-size="34" '
            'font-weight="700" fill="#172033">COGANT graphical abstract</text>'
        ),
        (
            f'<text x="700" y="94" text-anchor="middle" font-size="17" fill="#526070">'
            f"Run {escape(str(model.get('run_id') or 'unknown'))}: code evidence to typed graph, "
            "GNN artifacts, blanket interface, and roundtrip trace</text>"
        ),
    ]

    for idx, (title, metric, subtitle, color) in enumerate(stages):
        x = start_x + idx * (box_w + gap)
        parts.append(
            f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="8" '
            f'fill="#ffffff" stroke="{color}" stroke-width="3"/>'
        )
        parts.append(f'<rect x="{x}" y="{y}" width="{box_w}" height="14" rx="7" fill="{color}"/>')
        parts.append(
            _svg_text_block(
                _svg_lines(title, max_chars=18),
                x=x + box_w // 2,
                y=y + 44,
                size=18,
                fill="#172033",
                weight="700",
            )
        )
        parts.append(
            _svg_text_block(
                _svg_lines(metric, max_chars=24),
                x=x + box_w // 2,
                y=y + 84,
                size=14,
                fill="#243142",
                weight="600",
            )
        )
        parts.append(
            _svg_text_block(
                _svg_lines(subtitle, max_chars=24),
                x=x + box_w // 2,
                y=y + 122,
                size=12,
                fill="#526070",
                weight="500",
            )
        )
        if idx < len(stages) - 1:
            ax = x + box_w + 5
            parts.append(
                f'<path d="M{ax},{y + box_h // 2} L{ax + gap - 10},{y + box_h // 2}" '
                'stroke="#4a5568" stroke-width="3" marker-end="url(#arrow)"/>'
            )

    evidence_y = 382
    evidence = [
        ("Inspection", f"{len(cast(list[Any], model.get('figures') or []))} rendered figures"),
        ("Confidence", _fmt_percent(evidence_confidence * 100.0)),
        ("Validation", str(quality.get("validation_status") or "unknown")),
        ("Dashboard", "site/inspection_dashboard.html"),
    ]
    parts.append(
        '<text x="70" y="356" font-size="21" font-weight="700" fill="#172033">Evidence stack</text>'
    )
    for idx, (label, value) in enumerate(evidence):
        x = 70 + idx * 315
        parts.append(
            f'<rect x="{x}" y="{evidence_y}" width="270" height="92" rx="8" '
            'fill="#ffffff" stroke="#d5dce6" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{x + 18}" y="{evidence_y + 32}" font-size="14" font-weight="700" fill="#526070">'
            f"{escape(label)}</text>"
        )
        parts.append(
            _svg_text_block(
                _svg_lines(value, max_chars=27),
                x=x + 18,
                y=evidence_y + 62,
                size=16,
                fill="#172033",
                weight="700",
                anchor="start",
            )
        )
    parts.append(
        '<text x="70" y="548" font-size="13" fill="#526070">'
        "Generated from on-disk COGANT run artifacts; missing stages remain "
        "explicit rather than inferred.</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def render_graphical_abstract_svg(
    run_dir: Path | str,
    output_svg: Path | str | None = None,
) -> Path:
    """Write an SVG graphical abstract for a completed run directory."""

    root = Path(run_dir).resolve()
    out = (
        Path(output_svg).resolve()
        if output_svg is not None
        else root / "figures" / "graphical_abstract.svg"
    )
    model = build_inspection_model(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_graphical_abstract_svg(model), encoding="utf-8")
    return out


def render_graphical_abstract_png(
    run_dir: Path | str,
    output_png: Path | str | None = None,
    *,
    output_svg: Path | str | None = None,
) -> Path | None:
    """Write a PNG graphical abstract by rasterizing the generated SVG."""

    root = Path(run_dir).resolve()
    svg = render_graphical_abstract_svg(root, output_svg)
    png = (
        Path(output_png).resolve()
        if output_png is not None
        else root / "figures" / "graphical_abstract.png"
    )
    from cogant.viz.png_export import render_svg_file_to_png

    if render_svg_file_to_png(svg, png):
        return png
    return None


def _bar_svg(
    title: str,
    items: list[tuple[str, float]],
    *,
    color: str = "#2f6f9f",
    width: int = 1100,
    height: int = 520,
) -> str:
    max_value = max([value for _, value in items] or [1.0])
    bar_area = width - 280
    row_h = 34
    y0 = 82
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" role="img">'
        ),
        '<rect width="100%" height="100%" fill="#f7f8fb"/>',
        f'<text x="48" y="42" font-size="26" font-weight="700" fill="#172033">{escape(title)}</text>',
    ]
    for idx, (label, value) in enumerate(items[:11]):
        y = y0 + idx * row_h
        length = int((value / max_value) * bar_area) if max_value else 0
        parts.append(
            f'<text x="48" y="{y + 18}" font-size="13" fill="#243142">{escape(label[:42])}</text>'
        )
        parts.append(
            f'<rect x="270" y="{y}" width="{max(length, 2)}" height="22" rx="4" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{285 + max(length, 2)}" y="{y + 17}" font-size="13" fill="#526070">{value:g}</text>'
        )
    if not items:
        parts.append('<text x="48" y="110" font-size="16" fill="#526070">No data found.</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _write_svg_png(svg_text: str, svg_path: Path, png_path: Path) -> Path | None:
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg_text, encoding="utf-8")
    from cogant.viz.png_export import render_svg_file_to_png

    return png_path if render_svg_file_to_png(svg_path, png_path) else None


def _sha256_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _png_dimensions(path: Path) -> dict[str, int] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return {
        "width": int.from_bytes(data[16:20], "big"),
        "height": int.from_bytes(data[20:24], "big"),
    }


def _png_visual_qa(path: Path) -> dict[str, object]:
    dimensions = _png_dimensions(path) or {}
    qa: dict[str, object] = {
        "width": dimensions.get("width"),
        "height": dimensions.get("height"),
        "min_dimension_ok": bool(
            dimensions and dimensions.get("width", 0) >= 320 and dimensions.get("height", 0) >= 180
        ),
        "nonblank": None,
        "estimated_unique_colors": None,
        "color_diversity_ok": None,
    }
    try:
        from PIL import Image
    except ImportError:
        return qa
    try:
        with Image.open(path) as image:
            image = image.convert("RGBA")
            width, height = image.size
            step_x = max(width // 96, 1)
            step_y = max(height // 96, 1)
            pixels = [
                image.getpixel((x, y))
                for y in range(0, height, step_y)
                for x in range(0, width, step_x)
            ]
    except Exception:
        return qa
    unique_count = len(set(pixels))
    qa.update(
        {
            "nonblank": unique_count > 1,
            "estimated_unique_colors": unique_count,
            "color_diversity_ok": unique_count >= 4,
        }
    )
    return qa


def _detail_source_artifact(root: Path, stem: str) -> Path | None:
    candidates = {
        "roundtrip_diff": (
            "roundtrip/metrics.json",
            "reports/roundtrip_metrics.json",
        ),
        "rule_trace": (
            "data/rule_evidence_trace.json",
            "rule_evidence_trace.json",
        ),
        "confidence_calibration": (
            "data/rule_evidence_trace.json",
            "rule_evidence_trace.json",
        ),
        "inference_trace": (
            "data/inference_trace.json",
            "inference_trace.json",
        ),
    }
    return _first_existing(root, candidates.get(stem, ()))


def _detail_displayed_counts(model: dict[str, Any], stem: str) -> dict[str, object]:
    if stem == "roundtrip_diff":
        roundtrip = _as_mapping(model.get("roundtrip"))
        invariants = _as_mapping(
            roundtrip.get("invariants") or roundtrip.get("roundtrip_invariants")
        )
        return {
            "diff_rows": 6,
            "invariants": len(invariants),
            "status_panels": 1,
        }
    if stem == "rule_trace":
        trace = _as_mapping(model.get("rule_trace"))
        mapping_count = _to_int(
            trace.get("mapping_count"),
            len(cast(list[Any], trace.get("mappings") or trace.get("rows") or [])),
        )
        return {
            "rules": len(_as_mapping(trace.get("rule_summary"))),
            "mappings": mapping_count,
            "conflict_events": len(cast(list[Any], trace.get("conflict_events") or [])),
        }
    if stem == "confidence_calibration":
        trace = _as_mapping(model.get("rule_trace"))
        per_rule = cast(list[Any], trace.get("per_rule") or [])
        reviewed = _to_int(
            trace.get("reviewed_rule_count"),
            sum(1 for row in per_rule if _to_float(_as_mapping(row).get("review_coverage")) > 0),
        )
        total = _to_int(trace.get("per_rule_count"), len(per_rule))
        mapping_count = _to_int(trace.get("mapping_count"))
        review_status = _as_mapping(trace.get("review_status_summary"))
        return {
            "mappings": mapping_count,
            "rules": len(_as_mapping(trace.get("rule_summary"))),
            "confidence_tiers": len(_as_mapping(trace.get("confidence_tier_summary"))),
            "conflict_events": len(cast(list[Any], trace.get("conflict_events") or [])),
            "reviewed_mapping_rows": _to_int(trace.get("reviewed_mapping_rows")),
            "unreviewed_mapping_rows": _to_int(trace.get("unreviewed_mapping_rows")),
            "review_status_kinds": len(review_status),
            "rule_rows": total,
            "reviewed_rule_rows": reviewed,
            "unreviewed_rule_rows": max(total - reviewed, 0),
        }
    if stem == "inference_trace":
        inference = _as_mapping(model.get("inference"))
        displayed = len(cast(list[Any], inference.get("trace") or []))
        return {
            "steps": _to_int(inference.get("trace_count"), displayed),
            "displayed_steps": displayed,
            "panels": 4,
        }
    return {"panels": 1}


def _write_detail_figure_sidecar(root: Path, stem: str, png: Path, model: dict[str, Any]) -> None:
    source = _detail_source_artifact(root, stem)
    dimensions = _png_dimensions(png)
    displayed_counts = _detail_displayed_counts(model, stem)
    try:
        from cogant import __version__ as renderer_version
    except Exception:
        renderer_version = "unknown"
    metadata = {
        "schema_version": FIGURE_SIDECAR_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "key": stem,
        "figure": png.name,
        "renderer": "cogant.viz.inspection_dashboard.render_interpretability_detail_pngs",
        "renderer_version": renderer_version,
        "source_artifact": str(source.relative_to(root)) if source else None,
        "source_artifact_digest": _sha256_path(source),
        "layout_method": "dashboard evidence panel",
        "layout_seed": None,
        "displayed_counts": displayed_counts,
        "panel_metadata": {
            "panel": stem,
            "reading_order": "title, primary metric bars, diagnostic annotation, legend",
        },
        "panels": [
            {
                "key": stem,
                "displayed_counts": displayed_counts,
                "reading_order": "title, primary metric bars, diagnostic annotation, legend",
            }
        ],
        "visual_qa": _png_visual_qa(png),
        "known_limitations": "Dashboard-derived panel; inspect the source JSON for exact machine-readable values.",
        "image": {
            "path": png.name,
            "bytes": png.stat().st_size if png.exists() else None,
            "sha256": _sha256_path(png),
            "dimensions_px": dimensions,
        },
    }
    png.with_suffix(".figure.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _roundtrip_diff_svg(model: dict[str, Any]) -> str:
    roundtrip = _as_mapping(model.get("roundtrip"))
    graph_delta = _as_mapping(roundtrip.get("graph_delta"))
    graph_edit = _as_mapping(roundtrip.get("graph_edit_distance"))
    original_graph = _as_mapping(roundtrip.get("original_graph_summary"))
    synthesized_graph = _as_mapping(roundtrip.get("synthesized_graph_summary"))
    matrix_delta = _as_mapping(roundtrip.get("matrix_delta"))
    gnn_diff = _as_mapping(roundtrip.get("gnn_diff"))
    invariants = _as_mapping(roundtrip.get("invariants") or roundtrip.get("roundtrip_invariants"))
    node_delta = graph_delta.get("node_delta")
    if node_delta is None:
        node_delta = _to_float(original_graph.get("node_count")) - _to_float(
            synthesized_graph.get("node_count")
        )
    edge_delta = graph_delta.get("edge_delta")
    if edge_delta is None:
        edge_delta = _to_float(original_graph.get("edge_count")) - _to_float(
            synthesized_graph.get("edge_count")
        )
    normalized_graph_edit = graph_edit.get("normalized")
    if normalized_graph_edit is None:
        normalized_graph_edit = _as_mapping(graph_delta.get("edit_distance")).get("normalized")
    rows = [
        ("node delta", abs(_to_float(node_delta))),
        ("edge delta", abs(_to_float(edge_delta))),
        ("graph edit %", _to_float(normalized_graph_edit) * 100.0),
        ("missing GNN sections", float(len(gnn_diff.get("missing_sections") or []))),
        ("extra GNN sections", float(len(gnn_diff.get("extra_sections") or []))),
        (
            "matrix max |delta|",
            _to_float(matrix_delta.get("max_abs_delta", matrix_delta.get("max_value_delta"))),
        ),
    ]
    svg = _bar_svg("Roundtrip visual diff", rows, color="#7a5cfa")
    status = (
        roundtrip.get("roundtrip_status")
        or roundtrip.get("status")
        or (
            "STRUCTURALLY_ISOMORPHIC"
            if roundtrip.get("structurally_isomorphic")
            else "not recorded"
        )
    )
    status_line = (
        '<text x="48" y="444" font-size="13" font-weight="700" fill="#172033">'
        f"Status taxonomy: {escape(str(status))}; strict structure, role, matrix, GNN, "
        "and generated-code checks are separated."
        "</text>"
    )
    invariant_lines: list[str] = []
    for key, value in sorted(invariants.items())[:8]:
        invariant_lines.append(
            f'<text x="48" y="{470 + len(invariant_lines) * 18}" font-size="12" fill="#526070">'
            f"{escape(key)}: {'pass' if bool(value) else 'check'}</text>"
        )
    return svg.replace("</svg>", status_line + "\n" + "\n".join(invariant_lines) + "\n</svg>")


def _rule_trace_svg(model: dict[str, Any]) -> str:
    trace = _as_mapping(model.get("rule_trace"))
    rules = _as_mapping(trace.get("rule_summary"))
    items = [(str(key), float(value)) for key, value in rules.items()]
    svg = _bar_svg("Rule contribution trace", items, color="#c46a2f")
    conflicts = _to_int(trace.get("conflicts") or trace.get("conflict_count"))
    if not conflicts:
        conflicts = len(cast(list[Any], trace.get("conflict_events") or []))
    mappings = _to_int(trace.get("mapping_count"))
    reviewed = _as_mapping(trace.get("review_summary"))
    accepted = _to_int(reviewed.get("accepted"))
    rejected = _to_int(reviewed.get("rejected"))
    note = (
        '<text x="48" y="474" font-size="13" fill="#526070">'
        f"Mappings recorded: {mappings}; conflict outcomes: {conflicts}; "
        f"reviewer accepted/rejected: {accepted}/{rejected}. "
        "Bars count rule contributions, not recall."
        "</text>"
    )
    return svg.replace("</svg>", note + "\n</svg>")


def _coverage_bar(
    *,
    label: str,
    value: int,
    max_value: int,
    x: int,
    y: int,
    width: int,
    color: str,
    unit: str = "",
) -> str:
    bar_width = int((value / max(max_value, 1)) * width)
    return "\n".join(
        [
            f'<text x="{x}" y="{y + 17}" font-size="15" font-weight="600" fill="#243142">{escape(label[:38])}</text>',
            f'<rect x="{x + 260}" y="{y}" width="{width}" height="22" rx="5" fill="#e8edf3"/>',
            (
                f'<rect x="{x + 260}" y="{y}" width="{max(bar_width, 2 if value else 0)}" '
                f'height="22" rx="5" fill="{color}"/>'
            ),
            (
                f'<text x="{x + 274 + max(bar_width, 0)}" y="{y + 17}" '
                f'font-size="13" fill="#526070">{value:g}{unit}</text>'
            ),
        ]
    )


def _metric_card(x: int, y: int, label: str, value: str, detail: str, color: str) -> str:
    return "\n".join(
        [
            f'<rect x="{x}" y="{y}" width="285" height="104" rx="8" fill="#ffffff" stroke="#d5dce6"/>',
            f'<rect x="{x}" y="{y}" width="285" height="8" rx="4" fill="{color}"/>',
            f'<text x="{x + 18}" y="{y + 38}" font-size="13" font-weight="700" fill="#526070">{escape(label)}</text>',
            f'<text x="{x + 18}" y="{y + 70}" font-size="25" font-weight="800" fill="#172033">{escape(value)}</text>',
            f'<text x="{x + 18}" y="{y + 91}" font-size="12" fill="#526070">{escape(detail[:42])}</text>',
        ]
    )


def _confidence_calibration_svg(model: dict[str, Any]) -> str:
    trace = _as_mapping(model.get("rule_trace"))
    rules = _as_mapping(trace.get("rule_summary"))
    tiers = _as_mapping(trace.get("confidence_tier_summary"))
    review_status = _as_mapping(trace.get("review_status_summary"))
    mapping_status = _as_mapping(trace.get("mapping_status_summary"))
    per_rule = cast(list[dict[str, Any]], trace.get("per_rule") or [])
    mappings = _to_int(trace.get("mapping_count"))
    conflicts = len(cast(list[Any], trace.get("conflict_events") or []))
    reviewed_rule_rows = _to_int(
        trace.get("reviewed_rule_count"),
        sum(1 for row in per_rule if _to_float(_as_mapping(row).get("review_coverage")) > 0),
    )
    total_rule_rows = _to_int(trace.get("per_rule_count"), len(per_rule))
    unreviewed_rule_rows = max(total_rule_rows - reviewed_rule_rows, 0)
    reviewed_mapping_rows = _to_int(trace.get("reviewed_mapping_rows"))
    unreviewed_mapping_rows = _to_int(
        trace.get("unreviewed_mapping_rows"), max(mappings - reviewed_mapping_rows, 0)
    )

    width, height = 1400, 720
    max_rule = max([_to_int(value) for value in rules.values()] or [1])
    max_tier = max([_to_int(value) for value in tiers.values()] or [1])
    max_status = max([_to_int(value) for value in review_status.values()] or [1, mappings])
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        ),
        '<title id="title">Evidence coverage and review-readiness panel</title>',
        (
            '<desc id="desc">Rule-evidence coverage view showing proposed mappings, '
            "confidence tiers, rule contributions, conflicts, and reviewer coverage.</desc>"
        ),
        '<rect width="100%" height="100%" fill="#f7f8fb"/>',
        (
            '<text id="titleText" x="48" y="48" font-size="30" font-weight="800" '
            'fill="#172033">Evidence coverage and review-readiness</text>'
        ),
        (
            '<text x="48" y="78" font-size="15" fill="#526070">'
            "Generated from rule_evidence_trace.json; use for review prioritization, not calibration proof."
            "</text>"
        ),
        _metric_card(
            48,
            112,
            "Proposed mappings",
            _fmt_int(mappings),
            "semantic assignments in trace",
            "#2f6f9f",
        ),
        _metric_card(
            358,
            112,
            "Rule families",
            _fmt_int(len(rules)),
            "contributing translation rules",
            "#c46a2f",
        ),
        _metric_card(
            668,
            112,
            "Conflict outcomes",
            _fmt_int(conflicts),
            "events recorded for review",
            "#8c4a6f",
        ),
        _metric_card(
            978,
            112,
            "Reviewed rows",
            _fmt_int(reviewed_mapping_rows),
            f"{unreviewed_mapping_rows} mapping rows still unreviewed",
            "#0b7a75",
        ),
        '<rect x="48" y="252" width="622" height="300" rx="8" fill="#ffffff" stroke="#d5dce6"/>',
        '<text x="72" y="292" font-size="19" font-weight="800" fill="#172033">Rule contribution counts</text>',
        '<text x="72" y="316" font-size="12" fill="#526070">Bars count emitted proposals by rule family.</text>',
        '<rect x="730" y="252" width="622" height="300" rx="8" fill="#ffffff" stroke="#d5dce6"/>',
        '<text x="754" y="292" font-size="19" font-weight="800" fill="#172033">Confidence and review status</text>',
        '<text x="754" y="316" font-size="12" fill="#526070">Confidence tiers summarize proposals; review rows show annotation coverage.</text>',
    ]
    for idx, (rule, value) in enumerate(sorted(rules.items(), key=lambda item: (-_to_int(item[1]), item[0]))[:6]):
        parts.append(
            _coverage_bar(
                label=str(rule),
                value=_to_int(value),
                max_value=max_rule,
                x=72,
                y=344 + idx * 34,
                width=250,
                color="#c46a2f",
            )
        )
    if not rules:
        parts.append('<text x="72" y="354" font-size="15" fill="#526070">No rule evidence found.</text>')

    y = 344
    for tier, value in sorted(tiers.items(), key=lambda item: (-_to_int(item[1]), item[0]))[:4]:
        parts.append(
            _coverage_bar(
                label=f"tier: {tier}",
                value=_to_int(value),
                max_value=max_tier,
                x=754,
                y=y,
                width=230,
                color="#2f6f9f",
            )
        )
        y += 34
    for status, value in sorted(review_status.items(), key=lambda item: (-_to_int(item[1]), item[0]))[:4]:
        parts.append(
            _coverage_bar(
                label=f"review: {status}",
                value=_to_int(value),
                max_value=max_status,
                x=754,
                y=y + 12,
                width=230,
                color="#0b7a75",
            )
        )
        y += 34
    if mapping_status:
        status_line = ", ".join(
            f"{key}: {_to_int(value)}"
            for key, value in sorted(mapping_status.items(), key=lambda item: item[0])[:4]
        )
        parts.append(
            f'<text x="754" y="520" font-size="12" fill="#526070">Final mapping status: {escape(status_line)}</text>'
        )

    warning_fill = "#fff7e6" if reviewed_mapping_rows == 0 else "#eef8f5"
    warning_stroke = "#d79b35" if reviewed_mapping_rows == 0 else "#0b7a75"
    parts.extend(
        [
            f'<rect x="48" y="584" width="1304" height="88" rx="8" fill="{warning_fill}" stroke="{warning_stroke}" stroke-width="2"/>',
            (
                f'<text x="72" y="619" font-size="18" font-weight="800" fill="#172033">'
                f"{reviewed_mapping_rows} reviewed mapping rows; {reviewed_rule_rows} reviewed rule rows"
                "</text>"
            ),
            (
                f'<text x="72" y="645" font-size="14" fill="#526070">'
                f"{unreviewed_mapping_rows} mapping rows and {unreviewed_rule_rows} rule-summary rows have no reviewer annotation. "
                "The panel supports audit triage only; it does not estimate calibration, recall, or posterior semantic truth."
                "</text>"
            ),
        ]
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _polyline(values: list[float], *, x: int, y: int, width: int, height: int) -> str:
    if not values:
        return ""
    lo = min(values)
    hi = max(values)
    span = hi - lo if hi != lo else 1.0
    pts: list[str] = []
    for idx, value in enumerate(values):
        px = x + (idx / max(len(values) - 1, 1)) * width
        py = y + height - ((value - lo) / span) * height
        pts.append(f"{px:.1f},{py:.1f}")
    return " ".join(pts)


def _inference_trace_svg(model: dict[str, Any]) -> str:
    inference = _as_mapping(model.get("inference"))
    records = cast(list[dict[str, Any]], inference.get("trace") or [])
    fe = [_to_float(row.get("free_energy")) for row in records]
    prefs = [_to_float(row.get("preference_satisfaction")) for row in records]
    width, height = 1100, 520
    fe_points = _polyline(fe, x=70, y=96, width=720, height=220)
    pref_points = _polyline(prefs, x=70, y=96, width=720, height=220)
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" role="img">'
        ),
        '<rect width="100%" height="100%" fill="#f7f8fb"/>',
        '<text x="48" y="42" font-size="26" font-weight="700" fill="#172033">Deterministic inference trace</text>',
        '<rect x="60" y="82" width="750" height="260" rx="8" fill="#ffffff" stroke="#d5dce6"/>',
        '<line x1="70" y1="316" x2="790" y2="316" stroke="#9aa6b2"/>',
        '<line x1="70" y1="96" x2="70" y2="316" stroke="#9aa6b2"/>',
        '<text x="430" y="338" text-anchor="middle" font-size="12" fill="#526070">step</text>',
        '<text x="48" y="206" text-anchor="middle" font-size="12" fill="#526070" '
        'transform="rotate(-90 48 206)">normalized diagnostic value</text>',
    ]
    if fe_points:
        parts.append(
            f'<polyline points="{fe_points}" fill="none" stroke="#8c4a6f" stroke-width="4"/>'
        )
    if pref_points:
        parts.append(
            f'<polyline points="{pref_points}" fill="none" stroke="#0b7a75" stroke-width="4"/>'
        )
    parts.append(
        '<text x="840" y="118" font-size="16" font-weight="700" fill="#172033">Policy/actions</text>'
    )
    for idx, row in enumerate(records[:8]):
        parts.append(
            f'<text x="840" y="{150 + idx * 28}" font-size="13" fill="#243142">'
            f"t={row.get('t')} action={row.get('action')} obs={row.get('observation')} "
            f"belief={escape(str(row.get('belief') or []))}</text>"
        )
    parts.append(
        '<circle cx="840" cy="384" r="7" fill="#8c4a6f"/>'
        '<text x="856" y="389" font-size="13" fill="#526070">free energy</text>'
    )
    parts.append(
        '<circle cx="840" cy="414" r="7" fill="#0b7a75"/>'
        '<text x="856" y="419" font-size="13" fill="#526070">'
        "preference satisfaction</text>"
    )
    parts.append(
        '<text x="840" y="452" font-size="12" fill="#526070">'
        "Belief vectors are listed per selected action; free-energy and preference axes are "
        "plotted separately from policy labels.</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def render_interpretability_detail_pngs(run_dir: Path | str) -> dict[str, Path]:
    """Write dashboard companion figures for roundtrip, rules, calibration, and inference."""

    root = Path(run_dir).resolve()
    model = build_inspection_model(root)
    figures = root / "figures"
    outputs: dict[str, Path] = {}
    specs = {
        "roundtrip_diff": _roundtrip_diff_svg(model),
        "rule_trace": _rule_trace_svg(model),
        "confidence_calibration": _confidence_calibration_svg(model),
        "inference_trace": _inference_trace_svg(model),
    }
    for stem, svg_text in specs.items():
        png = _write_svg_png(svg_text, figures / f"{stem}.svg", figures / f"{stem}.png")
        if png is not None:
            _write_detail_figure_sidecar(root, stem, png, model)
            outputs[stem] = png
    return outputs


def _metric(label: str, value: str, detail: str = "") -> str:
    return (
        '<div class="metric">'
        f'<div class="metric-label">{escape(label)}</div>'
        f'<div class="metric-value">{escape(value)}</div>'
        f'<div class="metric-detail">{escape(detail)}</div>'
        "</div>"
    )


def _table_from_mapping(title: str, mapping: dict[str, Any]) -> str:
    rows = []
    for key, value in mapping.items():
        rows.append(f"<tr><td>{escape(str(key))}</td><td>{escape(str(value))}</td></tr>")
    body = "\n".join(rows) or '<tr><td colspan="2">No data</td></tr>'
    return (
        f'<section class="panel"><h2>{escape(title)}</h2>'
        f"<table><tbody>{body}</tbody></table></section>"
    )


def _artifact_table(artifacts: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for item in artifacts:
        present = bool(item.get("present"))
        cls = "ok" if present else "missing"
        label = escape(str(item.get("label") or "artifact"))
        path = escape(str(item.get("path") or ""))
        status = "present" if present else "missing"
        if present and path:
            if path.startswith("site/"):
                path_html = f'<a href="{path[5:]}">{path}</a>'
            else:
                path_html = f'<a href="../{path}">{path}</a>'
        else:
            path_html = path
        rows.append(f'<tr><td>{label}</td><td class="{cls}">{status}</td><td>{path_html}</td></tr>')
    return "\n".join(rows)


def _relative_url(path: Path, html_dir: Path) -> str:
    return Path(os.path.relpath(path, html_dir)).as_posix()


def _asset_src(path: Path, html_dir: Path, *, embed_assets: bool) -> str:
    if embed_assets:
        suffix = path.suffix.lower()
        if suffix == ".png":
            mime = "image/png"
        elif suffix == ".svg":
            mime = "image/svg+xml"
        elif suffix in {".jpg", ".jpeg"}:
            mime = "image/jpeg"
        else:
            return _relative_url(path, html_dir)
        try:
            payload = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError:
            return _relative_url(path, html_dir)
        return f"data:{mime};base64,{payload}"
    return _relative_url(path, html_dir)


def _figure_grid(figures: list[dict[str, Any]], html_dir: Path, *, embed_assets: bool) -> str:
    cards: list[str] = []
    for figure in figures[:10]:
        path = figure.get("path")
        if not isinstance(path, Path):
            continue
        title = escape(str(figure.get("title") or path.name))
        caption = escape(str(figure.get("caption") or ""))
        if path.suffix.lower() == ".html":
            link_html = (
                f'<a href="{escape(_relative_url(path, html_dir))}">'
                f"{escape(str(figure.get('relative_path') or path.name))}</a>"
            )
            cards.append(
                '<article class="figure-card figure-link">'
                f"<h3>{title}</h3>"
                f"{link_html}"
                f"<p>{caption}</p>"
                "</article>"
            )
            continue
        src = escape(_asset_src(path, html_dir, embed_assets=embed_assets))
        cards.append(
            '<article class="figure-card">'
            f"<h3>{title}</h3>"
            f'<img src="{src}" alt="{title}">'
            f"<p>{caption}</p>"
            "</article>"
        )
    if not cards:
        return '<div class="empty">No rendered figures found.</div>'
    return "\n".join(cards)


def _hotspot_table(rows: list[dict[str, Any]]) -> str:
    body: list[str] = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{escape(str(row.get('category') or 'node'))}</td>"
            f"<td>{escape(str(row.get('label') or row.get('node_id') or 'unknown'))}</td>"
            f"<td>{_to_float(row.get('score')):.3g}</td>"
            "</tr>"
        )
    return "\n".join(body) or '<tr><td colspan="3">No hotspot report found.</td></tr>'


def _top_mapping_table(rows: list[dict[str, Any]]) -> str:
    body: list[str] = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{escape(str(row.get('kind') or 'unknown'))}</td>"
            f"<td>{escape(str(row.get('label') or 'mapping'))}</td>"
            f"<td>{_to_float(row.get('confidence')):.2f}</td>"
            f"<td>{escape(str(row.get('status') or 'unreviewed'))}</td>"
            "</tr>"
        )
    return "\n".join(body) or '<tr><td colspan="4">No mapping records found.</td></tr>'


def _roundtrip_metric_detail(roundtrip: dict[str, Any]) -> str:
    role_score = roundtrip.get("role_preservation_score", roundtrip.get("role_match_score"))
    if role_score is not None:
        details = [f"role {_fmt_percent(_to_float(role_score) * 100.0)}"]
        matrix_score = roundtrip.get("matrix_score")
        if matrix_score is not None:
            details.append(f"matrix {_fmt_percent(_to_float(matrix_score) * 100.0)}")
        structural_score = roundtrip.get("structural_score")
        if structural_score is not None:
            details.append(f"struct {_fmt_percent(_to_float(structural_score) * 100.0)}")
        return " · ".join(details)
    return str(roundtrip.get("forward_path") or "")


def _roundtrip_metrics_table(roundtrip: dict[str, Any]) -> str:
    shape_match = _as_mapping(roundtrip.get("shape_match"))
    graph_edit = _as_mapping(roundtrip.get("graph_edit_distance"))
    generated_code = _as_mapping(roundtrip.get("generated_code"))
    shape_text = ", ".join(
        f"{key}={'ok' if bool(value) else 'drift'}" for key, value in sorted(shape_match.items())
    )
    errors = roundtrip.get("errors")
    error_count = len(errors) if isinstance(errors, list) else 0
    rows = [
        ("Status", str(roundtrip.get("status") or "not present")),
        (
            "Role preservation",
            (
                _fmt_percent(
                    _to_float(
                        roundtrip.get(
                            "role_preservation_score",
                            roundtrip.get("role_match_score"),
                        )
                    )
                    * 100.0
                )
                if roundtrip.get("role_preservation_score", roundtrip.get("role_match_score"))
                is not None
                else "n/a"
            ),
        ),
        (
            "Matrix score",
            (
                _fmt_percent(_to_float(roundtrip.get("matrix_score")) * 100.0)
                if roundtrip.get("matrix_score") is not None
                else "n/a"
            ),
        ),
        (
            "Structural score",
            (
                _fmt_percent(_to_float(roundtrip.get("structural_score")) * 100.0)
                if roundtrip.get("structural_score") is not None
                else "n/a"
            ),
        ),
        (
            "Graph edit distance",
            (
                _fmt_percent(_to_float(graph_edit.get("normalized")) * 100.0)
                if graph_edit
                else "n/a"
            ),
        ),
        (
            "Threshold",
            (
                _fmt_percent(_to_float(roundtrip.get("threshold")) * 100.0)
                if roundtrip.get("threshold") is not None
                else "n/a"
            ),
        ),
        ("Shape match", shape_text or "n/a"),
        ("Generated code", str(generated_code.get("status") or "n/a")),
        ("Generated tests", str(generated_code.get("test_status") or "n/a")),
        ("Warnings", str(error_count)),
        ("Metrics artifact", str(roundtrip.get("metrics_path") or "not found")),
    ]
    return "\n".join(
        f"<tr><td>{escape(label)}</td><td>{escape(value)}</td></tr>" for label, value in rows
    )


def _roundtrip_role_diff_table(roundtrip: dict[str, Any]) -> str:
    confusion = _iter_records(roundtrip.get("role_confusion"))
    if confusion:
        rows: list[str] = []
        for row in confusion:
            role = str(row.get("role") or "unknown")
            orig = _to_int(row.get("original"))
            synth = _to_int(row.get("synthesized"))
            delta = _to_int(row.get("delta"), synth - orig)
            cls = "ok" if delta == 0 else "missing"
            sign = "+" if delta > 0 else ""
            rows.append(
                "<tr>"
                f"<td>{escape(role)}</td>"
                f"<td>{orig}</td>"
                f"<td>{synth}</td>"
                f'<td class="{cls}">{sign}{delta}</td>'
                "</tr>"
            )
        return "\n".join(rows)

    original = _int_mapping(roundtrip.get("original_roles"))
    synthesized = _int_mapping(roundtrip.get("synthesized_roles"))
    roles = sorted(set(original) | set(synthesized))
    if not roles:
        return '<tr><td colspan="4">No roundtrip role metrics found.</td></tr>'
    fallback_rows: list[str] = []
    for role in roles:
        orig = original.get(role, 0)
        synth = synthesized.get(role, 0)
        delta = synth - orig
        cls = "ok" if delta == 0 else "missing"
        sign = "+" if delta > 0 else ""
        fallback_rows.append(
            "<tr>"
            f"<td>{escape(role)}</td>"
            f"<td>{orig}</td>"
            f"<td>{synth}</td>"
            f'<td class="{cls}">{sign}{delta}</td>'
            "</tr>"
        )
    return "\n".join(fallback_rows)


def _roundtrip_structural_delta_table(roundtrip: dict[str, Any]) -> str:
    graph_delta = _as_mapping(roundtrip.get("graph_delta"))
    gnn_diff = _as_mapping(roundtrip.get("gnn_diff"))
    matrix_delta = _as_mapping(roundtrip.get("matrix_delta"))
    matrix_records = _as_mapping(matrix_delta.get("matrices"))
    matrix_rows: list[str] = []
    for key in ("A", "B", "C", "D"):
        record = _as_mapping(matrix_records.get(key))
        matrix_rows.append(
            "<tr>"
            f"<td>{escape(key)}</td>"
            f"<td>{escape(str(record.get('original_shape') or []))}</td>"
            f"<td>{escape(str(record.get('synthesized_shape') or []))}</td>"
            f"<td>{escape('ok' if record.get('shape_match') else 'drift')}</td>"
            "</tr>"
        )
    rows = [
        ("Node delta", str(graph_delta.get("node_delta", "n/a"))),
        ("Edge delta", str(graph_delta.get("edge_delta", "n/a"))),
        (
            "GNN section score",
            (_fmt_percent(_to_float(gnn_diff.get("section_score")) * 100.0) if gnn_diff else "n/a"),
        ),
        (
            "Missing GNN sections",
            ", ".join(str(x) for x in gnn_diff.get("missing_sections", [])) or "none",
        ),
        (
            "Extra GNN sections",
            ", ".join(str(x) for x in gnn_diff.get("extra_sections", [])) or "none",
        ),
        (
            "Matrix shape score",
            (
                _fmt_percent(_to_float(matrix_delta.get("shape_score")) * 100.0)
                if matrix_delta
                else "n/a"
            ),
        ),
    ]
    summary_rows = "\n".join(
        f"<tr><td>{escape(label)}</td><td>{escape(value)}</td></tr>" for label, value in rows
    )
    matrix_body = "\n".join(matrix_rows) or '<tr><td colspan="4">No matrix deltas.</td></tr>'
    return (
        '<div class="split">'
        f"<table><thead><tr><th>Diff</th><th>Value</th></tr></thead><tbody>{summary_rows}</tbody></table>"
        f"<table><thead><tr><th>Matrix</th><th>Original</th><th>Roundtrip</th><th>Status</th></tr></thead><tbody>{matrix_body}</tbody></table>"
        "</div>"
    )


def _invariants_table(roundtrip: dict[str, Any]) -> str:
    invariants = _as_mapping(roundtrip.get("invariants") or roundtrip.get("roundtrip_invariants"))
    rows: list[str] = []
    for key, value in sorted(invariants.items()):
        cls = "ok" if bool(value) else "missing"
        rows.append(
            f'<tr><td>{escape(str(key))}</td><td class="{cls}">{"pass" if bool(value) else "check"}</td></tr>'
        )
    return "\n".join(rows) or '<tr><td colspan="2">No invariant report found.</td></tr>'


def _roundtrip_diagnostics_panel(roundtrip: dict[str, Any]) -> str:
    return f"""
    <section class="panel">
      <h2>Roundtrip Diagnostics</h2>
      <div class="split">
        <div>
          <table>
            <thead><tr><th>Metric</th><th>Value</th></tr></thead>
            <tbody>{_roundtrip_metrics_table(roundtrip)}</tbody>
          </table>
        </div>
        <div>
          <table>
            <thead><tr><th>Role</th><th>Original</th><th>Roundtrip</th><th>Delta</th></tr></thead>
            <tbody>{_roundtrip_role_diff_table(roundtrip)}</tbody>
          </table>
        </div>
      </div>
      <h3>Structural and GNN Diff</h3>
      {_roundtrip_structural_delta_table(roundtrip)}
      <h3>Roundtrip Invariants</h3>
      <table>
        <thead><tr><th>Invariant</th><th>Status</th></tr></thead>
        <tbody>{_invariants_table(roundtrip)}</tbody>
      </table>
    </section>
"""


def _rule_trace_panel(rule_trace: dict[str, Any]) -> str:
    per_rule = cast(list[dict[str, Any]], rule_trace.get("per_rule") or [])
    rows: list[str] = []
    for row in per_rule[:12]:
        proxy = row.get("precision_proxy")
        proxy_text = f"{float(proxy):.2f}" if isinstance(proxy, int | float) else "unlabelled"
        rows.append(
            "<tr>"
            f"<td>{escape(str(row.get('rule_id') or 'unknown'))}</td>"
            f"<td>{_to_int(row.get('total'))}</td>"
            f"<td>{_to_int(row.get('accepted'))}</td>"
            f"<td>{_to_int(row.get('rejected'))}</td>"
            f"<td>{_fmt_percent(_to_float(row.get('review_coverage')) * 100.0)}</td>"
            f"<td>{escape(proxy_text)}</td>"
            "</tr>"
        )
    body = "\n".join(rows) or '<tr><td colspan="6">No rule trace found.</td></tr>'
    rule_trace_header = (
        "<thead><tr><th>Rule</th><th>Total</th><th>Accepted</th><th>Rejected</th>"
        "<th>Review Coverage</th><th>Precision Proxy</th></tr></thead>"
    )
    return f"""
    <section class="panel">
      <h2>Rule Evidence Trace</h2>
      <div class="split">
        {_table_from_mapping("Rule Contributions", _as_mapping(rule_trace.get("rule_summary")))}
        {_table_from_mapping("Confidence Tiers", _as_mapping(rule_trace.get("confidence_tier_summary")))}
      </div>
      <table>
        {rule_trace_header}
        <tbody>{body}</tbody>
      </table>
    </section>
"""


def _inference_panel(inference: dict[str, Any]) -> str:
    records = cast(list[dict[str, Any]], inference.get("trace") or [])
    rows: list[str] = []
    for row in records[:10]:
        rows.append(
            "<tr>"
            f"<td>{escape(str(row.get('t')))}</td>"
            f"<td>{escape(str(row.get('belief') or []))}</td>"
            f"<td>{escape(str(row.get('action')))}</td>"
            f"<td>{escape(str(row.get('observation')))}</td>"
            f"<td>{_to_float(row.get('preference_satisfaction')):.2f}</td>"
            f"<td>{_to_float(row.get('free_energy')):.3f}</td>"
            "</tr>"
        )
    body = "\n".join(rows) or '<tr><td colspan="6">No inference trace found.</td></tr>'
    preference_metric = _metric(
        "Preference",
        _fmt_percent(_to_float(inference.get("mean_preference_satisfaction")) * 100.0),
        "mean satisfaction",
    )
    return f"""
    <section class="panel">
      <h2>Runtime Inference Trace</h2>
      <div class="metric-grid">
        {_metric("Steps", _fmt_int(inference.get("steps")), str(inference.get("path") or ""))}
        {_metric("Mean VFE", f"{_to_float(inference.get('mean_free_energy')):.3f}", "lower is better")}
        {_metric("Final VFE", f"{_to_float(inference.get('final_free_energy')):.3f}", "deterministic smoke")}
        {preference_metric}
      </div>
      <table>
        <thead><tr><th>t</th><th>Belief</th><th>Action</th><th>Obs</th><th>Preference</th><th>VFE</th></tr></thead>
        <tbody>{body}</tbody>
      </table>
    </section>
"""


def _dashboard_html(
    model: dict[str, Any],
    html_dir: Path,
    *,
    embed_assets: bool,
) -> str:
    program = _as_mapping(model.get("program"))
    semantic = _as_mapping(model.get("semantic"))
    state = _as_mapping(model.get("state_space"))
    matrices = _as_mapping(model.get("matrices"))
    blanket = _as_mapping(model.get("blanket"))
    quality = _as_mapping(model.get("quality"))
    roundtrip = _as_mapping(model.get("roundtrip"))
    rule_trace = _as_mapping(model.get("rule_trace"))
    inference = _as_mapping(model.get("inference"))
    figures = cast(list[dict[str, Any]], model.get("figures") or [])
    artifacts = cast(list[dict[str, Any]], model.get("artifacts") or [])
    hotspots = cast(list[dict[str, Any]], model.get("hotspots") or [])
    top_mappings = cast(list[dict[str, Any]], semantic.get("top_mappings") or [])
    no_run_data = bool(model.get("no_run_data"))

    abstract = _graphical_abstract_svg(model)
    roundtrip_detail = _roundtrip_metric_detail(roundtrip)
    evidence_confidence = _run_evidence_confidence(model)
    run_id = escape(str(model.get("run_id") or "run"))
    package_timestamp = escape(str(model.get("package_timestamp") or "generated run"))
    state_detail = (
        f"{_fmt_int(state.get('observations'))} observations · "
        f"{_fmt_int(state.get('actions'))} actions"
    )
    coverage_detail = f"evidence {_fmt_percent(evidence_confidence * 100.0)}"
    css = dedent(
        """
        :root {
            --ink: #172033;
            --muted: #526070;
            --paper: #f7f8fb;
            --panel: #ffffff;
            --line: #d5dce6;
            --blue: #2f6f9f;
            --violet: #7a5cfa;
            --green: #0b7a75;
            --amber: #c46a2f;
            --rose: #8c4a6f;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: var(--paper);
            color: var(--ink);
            line-height: 1.45;
            letter-spacing: 0;
        }
        a { color: var(--blue); }
        header {
            background: #111827;
            color: #ffffff;
            padding: 24px clamp(18px, 4vw, 48px);
            border-bottom: 5px solid var(--green);
        }
        header h1 { margin: 0 0 6px; font-size: 30px; }
        header p { margin: 0; color: #cbd5e1; }
        main {
            max-width: 100vw;
            overflow-x: clip;
            padding: 22px clamp(16px, 4vw, 48px) 48px;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(min(160px, 100%), 1fr));
            gap: 12px;
            margin-bottom: 18px;
        }
        .metric {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 14px;
            min-height: 104px;
        }
        .metric-label {
            color: var(--muted);
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }
        .metric-value {
            margin-top: 8px;
            font-size: 27px;
            font-weight: 750;
            overflow-wrap: anywhere;
        }
        .metric-detail {
            min-height: 18px;
            color: var(--muted);
            font-size: 13px;
            margin-top: 4px;
            overflow-wrap: anywhere;
        }
        .no-run-data {
            grid-column: 1 / -1;
            background: #fff4e8;
            border: 3px solid #c2410c;
            border-radius: 10px;
            padding: 18px 20px;
            box-shadow: 0 0 0 4px rgba(194, 65, 12, 0.12);
        }
        .no-run-data-title {
            color: #7c2d12;
            font-size: 28px;
            font-weight: 800;
            margin: 0 0 8px;
        }
        .no-run-data-body {
            color: #7c2d12;
            font-size: 16px;
            font-weight: 700;
            margin: 0;
        }
        .panel {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
            padding: 18px;
            margin: 16px 0;
        }
        .panel h2 { margin: 0 0 14px; font-size: 20px; }
        .abstract svg { width: 100%; max-width: 100%; height: auto; display: block; }
        .figure-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr));
            gap: 14px;
        }
        .figure-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 12px;
            background: #ffffff;
        }
        .figure-card h3 { margin: 0 0 10px; font-size: 15px; }
        .figure-card img {
            width: 100%;
            aspect-ratio: 16 / 10;
            object-fit: contain;
            background: #f3f5f8;
            border: 1px solid #e1e6ef;
            border-radius: 6px;
        }
        .figure-card p { color: var(--muted); font-size: 13px; margin: 10px 0 0; }
        .figure-link { min-height: 160px; }
        .split {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr));
            gap: 16px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            table-layout: fixed;
        }
        th, td {
            border-bottom: 1px solid #e5eaf1;
            padding: 9px 8px;
            text-align: left;
            vertical-align: top;
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        th {
            color: var(--muted);
            font-size: 12px;
            text-transform: uppercase;
        }
        .ok { color: var(--green); font-weight: 700; }
        .missing { color: #a13c3c; font-weight: 700; }
        .empty {
            border: 1px dashed var(--line);
            border-radius: 8px;
            color: var(--muted);
            padding: 18px;
            background: #ffffff;
        }
        footer {
            color: var(--muted);
            font-size: 12px;
            padding: 20px clamp(16px, 4vw, 48px) 36px;
            overflow-wrap: anywhere;
        }
        @media (max-width: 700px) {
            header h1 { font-size: 24px; }
            .metric-value { font-size: 22px; }
            th, td { font-size: 13px; }
        }
        """
    ).strip()
    metrics_section = (
        (
            '      <div class="no-run-data" role="alert">'
            '<p class="no-run-data-title">⚠ NO RUN DATA</p>'
            '<p class="no-run-data-body">This target has not been processed — there is no program graph, GNN package, or run bundle here. '
            "Run `run_all.py` / `cogant viz` against a real target. This is NOT a zero-valued result; the metrics below are absent, not zero."
            "</p>"
            "</div>"
        )
        if no_run_data
        else f"""      {_metric("Program graph", _fmt_int(program.get("nodes")), f"{_fmt_int(program.get('edges'))} edges")}
      {_metric("Semantic roles", _fmt_int(semantic.get("total")), "mapped graph fragments")}
      {_metric("State space", _fmt_int(state.get("variables")), state_detail)}
      {_metric("Coverage", _fmt_percent(quality.get("source_coverage")), coverage_detail)}
      {_metric("Roundtrip", str(roundtrip.get("status") or "not present"), roundtrip_detail)}"""
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>COGANT Inspection Dashboard - {run_id}</title>
  <style>{css}</style>
</head>
<body>
  <header>
    <h1>COGANT Inspection Dashboard</h1>
    <p>{run_id} · {package_timestamp}</p>
  </header>
  <main>
    <section class="metric-grid" aria-label="Run metrics">
{metrics_section}
    </section>

    <section class="panel abstract">
      <h2>Graphical Abstract</h2>
      {abstract}
    </section>

    <section class="panel">
      <h2>Visual Evidence</h2>
      <div class="figure-grid">
        {_figure_grid(figures, html_dir, embed_assets=embed_assets)}
      </div>
    </section>

    <div class="split">
      {_table_from_mapping("Node Kinds", _as_mapping(program.get("node_kinds")))}
      {_table_from_mapping("Semantic Role Counts", _as_mapping(semantic.get("mapping_kinds")))}
      {_table_from_mapping("Confidence Tiers", _as_mapping(semantic.get("confidence_tiers")))}
      {_table_from_mapping("Mapping Status", _as_mapping(semantic.get("status_distribution")))}
      {_table_from_mapping("Matrix Shapes", _as_mapping(matrices.get("shapes")))}
      {_table_from_mapping("Blanket Roles", _as_mapping(blanket.get("role_counts")))}
    </div>

    <section class="panel">
      <h2>Top Semantic Mappings</h2>
      <table>
        <thead><tr><th>Kind</th><th>Mapping</th><th>Confidence</th><th>Status</th></tr></thead>
        <tbody>{_top_mapping_table(top_mappings)}</tbody>
      </table>
    </section>

    {_roundtrip_diagnostics_panel(roundtrip)}

    {_rule_trace_panel(rule_trace)}

    {_inference_panel(inference)}

    <section class="panel">
      <h2>Code Graph Hotspots</h2>
      <table>
        <thead><tr><th>Category</th><th>Node</th><th>Score</th></tr></thead>
        <tbody>{_hotspot_table(hotspots)}</tbody>
      </table>
    </section>

    <section class="panel">
      <h2>Artifact Inventory</h2>
      <table>
        <thead><tr><th>Artifact</th><th>Status</th><th>Path</th></tr></thead>
        <tbody>{_artifact_table(artifacts)}</tbody>
      </table>
    </section>
  </main>
  <footer>
    Generated {escape(str(model.get("generated_at") or ""))} from {escape(str(model.get("run_dir") or ""))}.
  </footer>
</body>
</html>
"""
    return html


def _link_dashboard_from_site(run_dir: Path, dashboard_path: Path) -> bool:
    """Add the inspection dashboard to an existing generated site index."""
    site_index = run_dir / "site" / "index.html"
    if not site_index.is_file():
        return False
    try:
        text = site_index.read_text(encoding="utf-8")
    except OSError:
        return False
    if dashboard_path.name in text:
        return False

    rel = Path(os.path.relpath(dashboard_path, site_index.parent)).as_posix()
    nav_item = f'      <li><a href="{escape(rel)}">Inspection Dashboard</a></li>\n'
    nav_start = text.find("<nav")
    search_from = nav_start if nav_start >= 0 else 0
    ul_end = text.find("</ul>", search_from)
    if ul_end >= 0:
        updated = text[:ul_end] + nav_item + text[ul_end:]
    else:
        link_section = (
            "\n<section>\n"
            "  <h2>Inspection Dashboard</h2>\n"
            f'  <p><a href="{escape(rel)}">Open the inspection dashboard</a></p>\n'
            "</section>\n"
        )
        body_end = text.find("</body>")
        if body_end >= 0:
            updated = text[:body_end] + link_section + text[body_end:]
        else:
            updated = text + link_section
    try:
        site_index.write_text(updated, encoding="utf-8")
    except OSError:
        return False
    return True


def render_inspection_dashboard_html(
    run_dir: Path | str,
    output_html: Path | str | None = None,
    *,
    embed_assets: bool = True,
) -> Path:
    """Write the artifact-first HTML inspection dashboard for a run directory."""

    root = Path(run_dir).resolve()
    out = (
        Path(output_html).resolve()
        if output_html is not None
        else root / "site" / "inspection_dashboard.html"
    )
    model = build_inspection_model(root)
    rel_out = _rel(out, root) or out.as_posix()
    artifacts = cast(list[dict[str, Any]], model.get("artifacts") or [])
    for artifact in artifacts:
        if artifact.get("label") == "Inspection dashboard":
            artifact["path"] = rel_out
            artifact["present"] = True
            artifact["kind"] = "file"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_dashboard_html(model, out.parent, embed_assets=embed_assets), encoding="utf-8")
    _link_dashboard_from_site(root, out)
    return out


def write_inspection_artifacts(
    run_dir: Path | str,
    *,
    dashboard_html: Path | str | None = None,
    graphical_abstract_svg: Path | str | None = None,
    graphical_abstract_png: Path | str | None = None,
    embed_assets: bool = True,
) -> dict[str, Path]:
    """Write dashboard, SVG, and best-effort PNG artifacts for a run directory."""

    root = Path(run_dir).resolve()
    written: dict[str, Path] = {}
    try:
        from cogant.runtime.inference_demo import write_inference_trace_artifact

        written["inference_trace_json"] = write_inference_trace_artifact(root)
    except Exception:
        pass
    svg = render_graphical_abstract_svg(root, graphical_abstract_svg)
    written["graphical_abstract_svg"] = svg
    png = render_graphical_abstract_png(
        root,
        graphical_abstract_png,
        output_svg=svg,
    )
    if png is not None:
        written["graphical_abstract_png"] = png
    for key, path in render_interpretability_detail_pngs(root).items():
        written[f"{key}_png"] = path
    html = render_inspection_dashboard_html(root, dashboard_html, embed_assets=embed_assets)
    written["inspection_dashboard_html"] = html
    return written
