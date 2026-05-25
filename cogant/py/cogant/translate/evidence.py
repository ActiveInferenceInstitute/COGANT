"""Rule-evidence traces and reviewer-calibration summaries.

The forward translator produces semantic mappings; this module turns those
mappings into a compact audit artifact that can be kept beside generated GNN
packages, roundtrip metrics, dashboards, and manuscript figures.  The trace is
intentionally additive: it accepts the lightweight dataclass mappings used by
the current engine and tolerates missing metadata so old runs remain readable.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

__all__ = [
    "apply_reviewer_annotations",
    "build_rule_evidence_trace",
    "calibrate_rule_evidence_trace",
    "load_reviewer_annotations",
]


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_jsonable(v) for v in value]
    if hasattr(value, "value"):
        return _jsonable(value.value)
    if hasattr(value, "__dict__"):
        return {str(k): _jsonable(v) for k, v in vars(value).items() if not str(k).startswith("_")}
    return str(value)


def _mapping_values(mappings: Any) -> list[Any]:
    if mappings is None:
        return []
    if isinstance(mappings, dict):
        return list(mappings.values())
    if isinstance(mappings, list | tuple):
        return list(mappings)
    return [mappings]


def _name(value: Any, default: str = "unknown") -> str:
    if value is None:
        return default
    raw = getattr(value, "value", None) or getattr(value, "name", None) or value
    text = str(raw)
    return text if text else default


def _node_lookup(graph: Any) -> dict[str, Any]:
    nodes = getattr(graph, "nodes", None)
    if isinstance(nodes, dict):
        return {str(k): v for k, v in nodes.items()}
    if isinstance(nodes, list):
        out: dict[str, Any] = {}
        for node in nodes:
            node_id = getattr(node, "id", None)
            if node_id is None and isinstance(node, dict):
                node_id = node.get("id")
            if node_id is not None:
                out[str(node_id)] = node
        return out
    return {}


def _node_snippets(graph: Any, node_ids: list[str]) -> list[str]:
    lookup = _node_lookup(graph)
    snippets: list[str] = []
    for node_id in node_ids[:8]:
        node = lookup.get(str(node_id))
        if node is None:
            snippets.append(str(node_id))
            continue
        label = (
            getattr(node, "qualified_name", None)
            or getattr(node, "name", None)
            or getattr(node, "label", None)
        )
        kind = _name(getattr(node, "kind", None), default="node")
        path = getattr(node, "path", None)
        if label and path:
            snippets.append(f"{kind}:{label} ({path})")
        elif label:
            snippets.append(f"{kind}:{label}")
        else:
            snippets.append(str(node_id))
    return snippets


def _normalise_annotations(annotations: Any) -> dict[str, dict[str, Any]]:
    if annotations is None:
        return {}
    if isinstance(annotations, Path | str):
        return load_reviewer_annotations(annotations)
    if isinstance(annotations, dict):
        if "annotations" in annotations:
            return _normalise_annotations(annotations.get("annotations"))
        return {
            str(k): v if isinstance(v, dict) else {"status": str(v)} for k, v in annotations.items()
        }
    if isinstance(annotations, list):
        out: dict[str, dict[str, Any]] = {}
        for item in annotations:
            if not isinstance(item, dict):
                continue
            mapping_id = item.get("mapping_id") or item.get("id")
            if mapping_id is not None:
                out[str(mapping_id)] = dict(item)
        return out
    return {}


def load_reviewer_annotations(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load reviewer annotations from a JSON file.

    Accepted shapes are either ``{"mapping_id": {"status": "accepted"}}`` or
    ``{"annotations": [{"mapping_id": "...", "status": "rejected"}]}``.
    Unknown records are ignored rather than raising so annotation files can
    carry extra notebook or dashboard metadata.
    """

    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return _normalise_annotations(data)


def apply_reviewer_annotations(
    trace: dict[str, Any],
    annotations: dict[str, dict[str, Any]] | list[dict[str, Any]] | str | Path | None,
) -> dict[str, Any]:
    """Apply accepted/rejected reviewer labels to a trace in place."""

    annotation_map = _normalise_annotations(annotations)
    records = trace.get("mappings")
    if not isinstance(records, list):
        return trace
    for record in records:
        if not isinstance(record, dict):
            continue
        mapping_id = str(record.get("mapping_id") or record.get("id") or "")
        annotation = annotation_map.get(mapping_id)
        if not annotation:
            record.setdefault("review", {"status": "unreviewed"})
            continue
        status = str(annotation.get("status") or annotation.get("label") or "reviewed")
        record["review"] = {**annotation, "status": status}
        if status in {"accepted", "approved", "correct"}:
            record["final_mapping_status"] = "accepted"
        elif status in {"rejected", "incorrect", "false_positive"}:
            record["final_mapping_status"] = "rejected"
        else:
            record["final_mapping_status"] = status
    return trace


def calibrate_rule_evidence_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Summarise reviewer labels as per-rule precision/recall proxies.

    COGANT does not infer a hidden ground truth here.  The denominators are
    reviewer annotations: accepted/(accepted+rejected) is a precision proxy,
    and reviewed/total is annotation coverage.  Recall remains ``None`` unless
    downstream tools add explicit false-negative counts.
    """

    records = trace.get("mappings")
    if not isinstance(records, list):
        records = []
    by_rule: dict[str, Counter[str]] = defaultdict(Counter)
    overall: Counter[str] = Counter()
    for record in records:
        if not isinstance(record, dict):
            continue
        rule_id = str(record.get("rule_id") or "unknown")
        review = record.get("review")
        status = "unreviewed"
        if isinstance(review, dict):
            status = str(review.get("status") or status)
        if status in {"approved", "correct"}:
            status = "accepted"
        if status in {"incorrect", "false_positive"}:
            status = "rejected"
        by_rule[rule_id][status] += 1
        by_rule[rule_id]["total"] += 1
        overall[status] += 1
        overall["total"] += 1

    per_rule: list[dict[str, Any]] = []
    for rule_id, counts in sorted(by_rule.items()):
        accepted = counts.get("accepted", 0)
        rejected = counts.get("rejected", 0)
        reviewed = accepted + rejected + counts.get("partial", 0) + counts.get("reviewed", 0)
        denominator = accepted + rejected
        per_rule.append(
            {
                "rule_id": rule_id,
                "total": counts.get("total", 0),
                "accepted": accepted,
                "rejected": rejected,
                "unreviewed": counts.get("unreviewed", 0),
                "reviewed": reviewed,
                "precision_proxy": (accepted / denominator) if denominator else None,
                "review_coverage": reviewed / counts["total"] if counts.get("total") else 0.0,
                "recall_proxy": None,
            }
        )

    accepted = overall.get("accepted", 0)
    rejected = overall.get("rejected", 0)
    denominator = accepted + rejected
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "overall": {
            "total": overall.get("total", 0),
            "accepted": accepted,
            "rejected": rejected,
            "unreviewed": overall.get("unreviewed", 0),
            "precision_proxy": (accepted / denominator) if denominator else None,
        },
        "per_rule": per_rule,
    }


def build_rule_evidence_trace(
    mappings: Any,
    *,
    graph: Any = None,
    match_log: list[dict[str, Any]] | None = None,
    annotations: dict[str, dict[str, Any]] | list[dict[str, Any]] | str | Path | None = None,
) -> dict[str, Any]:
    """Build a JSON-ready trace of rule decisions and mapping evidence."""

    records: list[dict[str, Any]] = []
    rule_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    tier_counts: Counter[str] = Counter()

    for mapping in _mapping_values(mappings):
        mapping_id = str(getattr(mapping, "id", "") or getattr(mapping, "mapping_id", "") or "")
        metadata = getattr(mapping, "metadata", {}) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        node_ids = [str(x) for x in getattr(mapping, "graph_fragment_node_ids", []) or []]
        edge_ids = [str(x) for x in getattr(mapping, "graph_fragment_edge_ids", []) or []]
        rule_id = str(metadata.get("rule_id") or "unknown")
        kind = _name(getattr(mapping, "kind", None))
        tier = _name(getattr(mapping, "confidence_tier", None), default="uncalibrated")
        provenance = getattr(mapping, "provenance", []) or []
        prov_records = [_jsonable(p) for p in provenance]
        prov_conf = []
        for item in prov_records:
            if not isinstance(item, dict):
                continue
            confidence = item.get("confidence")
            if isinstance(confidence, int | float):
                prov_conf.append(float(confidence))
        evidence_snippets = _node_snippets(graph, node_ids)
        for prov in prov_records[:5]:
            if isinstance(prov, dict):
                source = prov.get("source")
                if source:
                    evidence_snippets.append(f"provenance:{source}")
        rule_counts[rule_id] += 1
        kind_counts[kind] += 1
        tier_counts[tier] += 1
        confidence_score = float(getattr(mapping, "confidence_score", 0.0) or 0.0)
        conflict_penalties = getattr(mapping, "conflict_penalties", []) or []
        records.append(
            {
                "mapping_id": mapping_id,
                "rule_id": rule_id,
                "rule_priority": int(metadata.get("rule_priority", 0) or 0),
                "kind": kind,
                "semantic_label": str(getattr(mapping, "semantic_label", "") or mapping_id),
                "description": str(getattr(mapping, "description", "") or ""),
                "matched_node_ids": node_ids,
                "matched_edge_ids": edge_ids,
                "evidence_snippets": evidence_snippets[:12],
                "confidence_score": confidence_score,
                "confidence_tier": tier,
                "confidence_components": {
                    "evidence_count": int(
                        getattr(mapping, "evidence_count", 0) or len(prov_records)
                    ),
                    "evidence_diversity": float(getattr(mapping, "evidence_diversity", 0.0) or 0.0),
                    "parser_certainty": float(getattr(mapping, "parser_certainty", 0.0) or 0.0),
                    "provenance_confidence_mean": (
                        sum(prov_conf) / len(prov_conf) if prov_conf else None
                    ),
                    "conflict_penalty_sum": sum(float(x) for x in conflict_penalties),
                },
                "conflict_resolution": _jsonable(metadata.get("conflict_resolution", [])),
                "final_mapping_status": str(getattr(mapping, "status", "") or "auto_proposed"),
                "review": {"status": str(getattr(mapping, "status", "") or "auto_proposed")},
                "match": _jsonable(metadata.get("match", {})),
            }
        )

    trace = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "mapping_count": len(records),
        "rule_summary": dict(sorted(rule_counts.items())),
        "kind_summary": dict(sorted(kind_counts.items())),
        "confidence_tier_summary": dict(sorted(tier_counts.items())),
        "mappings": records,
        "match_log": _jsonable(match_log or []),
        "conflict_events": [
            event
            for event in _jsonable(match_log or [])
            if isinstance(event, dict) and event.get("event_type") == "conflict_resolved"
        ],
    }
    apply_reviewer_annotations(trace, annotations)
    trace["calibration"] = calibrate_rule_evidence_trace(trace)
    return trace
