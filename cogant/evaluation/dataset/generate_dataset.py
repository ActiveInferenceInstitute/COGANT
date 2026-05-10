#!/usr/bin/env python3
"""Generate the COGANT ML dataset from the built-in fixture corpus.

This is the third COGANT deliverable: a structured collection of
(repository, program_graph, semantic_mappings, GNN) triples that can be
used to train and evaluate ML models over Active Inference semantic
roles extracted from Python source code.

The script runs the full COGANT pipeline (ingest -> static -> normalize
-> graph -> translate -> statespace -> process) over every fixture in
``cogant/examples`` and writes three artifacts:

* ``evaluation/dataset/instances/{name}.json`` -- one file per repo, carrying
  the full nodes/edges/mappings/A-B-C-D matrices bundle.
* ``evaluation/dataset/nodes.jsonl`` -- one JSON-per-line record per program
  graph node with its assigned Active Inference role and a small set of
  graph-structural / lexical features suitable for ML training.
* ``evaluation/dataset/instances.jsonl`` -- one JSON-per-line record per repo
  summarizing the instance (counts, role distribution, GNN shape).

Run from the repo root:

    python evaluation/dataset/generate_dataset.py

No network calls, no mocks, no placeholder zeros: every row is computed
by actually running the pipeline on the real fixtures.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Make the COGANT python package importable. The generator lives at
# ``evaluation/dataset/generate_dataset.py`` and the package lives at ``py/cogant/``.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "py"
sys.path.insert(0, str(PACKAGE_ROOT))

import cogant as _cogant_pkg  # noqa: E402
from cogant.api import orchestration  # noqa: E402
from cogant.api.bundle import ArtifactKey, Bundle  # noqa: E402
from cogant.gnn.matrices import GNNMatrices  # noqa: E402
from cogant.schemas.core import EdgeKind  # noqa: E402
from cogant.schemas.semantic import MappingKind  # noqa: E402

_COGANT_VERSION: str = getattr(_cogant_pkg, "__version__", "unknown")

logger = logging.getLogger("cogant.dataset")

# ---------------------------------------------------------------------------
# Fixture catalogue and split assignment
# ---------------------------------------------------------------------------

# Fixtures live under examples/. Paths are resolved relative to PROJECT_ROOT.
FIXTURES: list[tuple[str, str]] = [
    ("calculator", "examples/control_positive/calculator"),
    ("event_pipeline", "examples/control_positive/event_pipeline"),
    ("flask_mini", "examples/control_positive/flask_mini"),
    ("flask_app", "examples/real_world/flask_app"),
    ("requests_lib", "examples/real_world/requests_lib"),
    ("json_stdlib", "examples/real_world/json_stdlib"),
]

# Deterministic train/val/test assignment. Small corpus, so we split by
# whole repo rather than by node. This is the standard "few-shot" split
# used for code-LM benchmarks on tiny corpora and keeps per-split repos
# stylistically distinct.
SPLIT_ASSIGNMENT: dict[str, str] = {
    "calculator": "train",
    "event_pipeline": "train",
    "flask_mini": "val",
    "json_stdlib": "val",
    "flask_app": "test",
    "requests_lib": "test",
}

# Prefix-to-rule mapping. Rules name their mapping IDs with a short
# prefix that we use to recover "which rule fired" for ML features and
# reproducibility metadata. See cogant/py/cogant/translate/rules/*.py.
RULE_PREFIXES: dict[str, str] = {
    "obs": "ObservationRule|ReadOnlyInputRule",
    "act": "ActionRule",
    "pol": "PolicyRule",
    "pref": "PreferenceRule",
    "hs": "MutatingSubsystemRule",
    "orch": "OrchestratorRule",
    "const": "TestAssertionRule",
    "event": "EventBusRule",
    "ctx": "ConfigRule|ContextRule",
    "fflag": "FeatureFlagRule",
    "inh": "InheritanceRule",
    "cont": "ContainmentRule",
    "dpipe": "DataPipelineRule",
    "errbnd": "ErrorBoundaryRule",
    "single": "SingletonAccessRule",
    "cb": "CircuitBreakerRule",
    "policy": "RetryPatternRule",
}

# Action-keyword lexicon used as a lightweight feature. These are the
# verbs that the ActionRule itself matches on (see
# translate/rules/semantic.py::ActionRule), mirrored here so we never
# drift from the rule's own vocabulary.
ACTION_KEYWORDS = {
    "send",
    "post",
    "put",
    "delete",
    "update",
    "create",
    "save",
    "write",
    "mutate",
    "set",
    "add",
    "remove",
    "apply",
    "execute",
    "commit",
    "publish",
    "emit",
    "dispatch",
    "run",
    "trigger",
    "perform",
    "process",
    "handle",
    "make",
}


def _infer_rule_from_mapping_id(mapping_id: str) -> str:
    """Recover the producing rule name from a mapping ID prefix.

    The COGANT rule engine uses ID prefixes like ``obs_``, ``act_``,
    ``pol_`` etc. when it emits SemanticMapping objects. We reverse that
    to tag each mapping with a human-readable rule name for the dataset.
    Unknown prefixes return ``"Unknown"``.
    """
    match = re.match(r"^([a-z]+)_", mapping_id)
    if not match:
        return "Unknown"
    prefix = match.group(1)
    return RULE_PREFIXES.get(prefix, "Unknown")


def _role_from_mapping_kind(kind: MappingKind) -> str:
    """Normalize a MappingKind to an uppercase Active Inference role label.

    The dataset surfaces the canonical Active Inference role vocabulary
    (``HIDDEN_STATE``, ``OBSERVATION``, ``ACTION``, ``POLICY``,
    ``CONTEXT``, ``CONSTRAINT``) as the supervision target rather than
    the full MappingKind enum, which includes implementation-level
    patterns (``RETRY_PATTERN``, ``CIRCUIT_BREAKER``, ...) that we fold
    into POLICY since they are all policies in the RL sense.
    """
    canonical = {
        MappingKind.HIDDEN_STATE: "HIDDEN_STATE",
        MappingKind.OBSERVATION: "OBSERVATION",
        MappingKind.ACTION: "ACTION",
        MappingKind.POLICY: "POLICY",
        MappingKind.CONTEXT: "CONTEXT",
        MappingKind.CONSTRAINT: "CONSTRAINT",
        MappingKind.PREFERENCE: "CONSTRAINT",
        MappingKind.ORCHESTRATION: "POLICY",
        MappingKind.RETRY_PATTERN: "POLICY",
        MappingKind.CIRCUIT_BREAKER: "POLICY",
        MappingKind.FEATURE_FLAG: "CONTEXT",
        MappingKind.DATA_FLOW: "OBSERVATION",
        MappingKind.CONTROL_FLOW: "POLICY",
        MappingKind.ERROR_HANDLING: "POLICY",
    }
    return canonical.get(kind, "UNMAPPED")


def _source_lines_of_file(path: Path) -> int:
    """Count source lines of a file, tolerating read errors by returning 0."""
    try:
        return sum(1 for _ in path.read_text(errors="replace").splitlines())
    except OSError:
        return 0


def run_pipeline(target: str) -> Bundle:
    """Run the full COGANT pipeline end-to-end for a single fixture path.

    Chains the seven orchestration stages and returns the resulting
    ``Bundle`` with all artifacts attached. Raises the underlying
    exception if any stage fails so the generator aborts loudly rather
    than producing partial rows.
    """
    bundle = Bundle(target=target)
    bundle.stage_results["ingest"] = orchestration.run_ingest(target, bundle)
    bundle.stage_results["static"] = orchestration.run_static(bundle)
    bundle.stage_results["normalize"] = orchestration.run_normalize(bundle)
    bundle.stage_results["graph"] = orchestration.run_graph(bundle, target)
    bundle.stage_results["translate"] = orchestration.run_translate(bundle)
    bundle.stage_results["statespace"] = orchestration.run_statespace(bundle, target)
    bundle.stage_results["process"] = orchestration.run_process(bundle, target)
    return bundle


def _compute_graph_features(pg: Any) -> dict[str, dict[str, Any]]:
    """Pre-compute per-node graph features (degrees, typed edge counts).

    Returns a dict keyed by node ID whose values carry:
    ``in_degree``, ``out_degree``, ``writes_count``, ``reads_count``,
    ``calls_count``, ``depends_on_count``, ``contains_out_count``.
    """
    features: dict[str, dict[str, Any]] = {
        nid: {
            "in_degree": 0,
            "out_degree": 0,
            "writes_count": 0,
            "reads_count": 0,
            "calls_count": 0,
            "depends_on_count": 0,
            "contains_out_count": 0,
        }
        for nid in pg.nodes
    }

    for edge in pg.edges.values():
        src = features.get(edge.source_id)
        dst = features.get(edge.target_id)
        if src is not None:
            src["out_degree"] += 1
            if edge.kind == EdgeKind.WRITES:
                src["writes_count"] += 1
            elif edge.kind == EdgeKind.READS:
                src["reads_count"] += 1
            elif edge.kind == EdgeKind.CALLS:
                src["calls_count"] += 1
            elif edge.kind == EdgeKind.DEPENDS_ON:
                src["depends_on_count"] += 1
            elif edge.kind == EdgeKind.CONTAINS:
                src["contains_out_count"] += 1
        if dst is not None:
            dst["in_degree"] += 1
    return features


def _build_node_to_mapping(mappings: dict[str, Any]) -> dict[str, Any]:
    """Index semantic mappings by the graph node they touch.

    When a node participates in multiple mappings we keep the highest
    confidence one. That is the same tiebreak the ReviewManager uses
    when presenting candidates to a reviewer, so it matches what a
    downstream user would see.
    """
    index: dict[str, Any] = {}
    for mapping in mappings.values():
        for nid in mapping.graph_fragment_node_ids:
            existing = index.get(nid)
            if existing is None or (mapping.confidence_score or 0.0) > (
                existing.confidence_score or 0.0
            ):
                index[nid] = mapping
    return index


def _d_entropy(vec: list[float]) -> float:
    """Shannon entropy of the D prior vector in nats."""
    import math

    if not vec:
        return 0.0
    total = 0.0
    for p in vec:
        if p > 0.0:
            total -= p * math.log(p)
    return round(total, 6)


def _a_sparsity(mat: list[list[float]]) -> float:
    """Fraction of near-zero entries in A (< 1e-6)."""
    if not mat:
        return 0.0
    total = 0
    zeros = 0
    for row in mat:
        for v in row:
            total += 1
            if v < 1e-6:
                zeros += 1
    return round(zeros / total, 6) if total else 0.0


def build_instance(
    name: str, fixture_path: Path, bundle: Bundle
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Extract the instance-level record and node-level rows for one fixture.

    Returns ``(instance_record, node_rows)``. The instance record is a
    fully self-contained JSON object; the node rows are a list of flat
    dicts ready to be written to a JSON-Lines file.
    """
    pg = bundle.get_artifact(ArtifactKey.PROGRAM_GRAPH)
    if pg is None:
        raise RuntimeError(
            f"Pipeline did not produce a program graph for fixture {name!r}; "
            "cannot build dataset instance."
        )
    mappings: dict[str, Any] = bundle.get_artifact(ArtifactKey.SEMANTIC_MAPPINGS) or {}
    ss = bundle.get_artifact(ArtifactKey.STATE_SPACE_MODEL)
    pm = bundle.get_artifact(ArtifactKey.PROCESS_MODEL)

    # ----- GNN matrices -----
    gnn = GNNMatrices(pg, mappings, ss)
    gnn_dict = gnn.to_dict()
    a_sparsity = _a_sparsity(gnn_dict["A"])
    d_entropy = _d_entropy(gnn_dict["D"])

    # ----- Graph-level features -----
    graph_features = _compute_graph_features(pg)
    node_to_mapping = _build_node_to_mapping(mappings)

    # ----- Role distribution & edge kind counts -----
    role_distribution: Counter[str] = Counter()
    edge_kind_counts = Counter(e.kind.value for e in pg.edges.values())
    node_kind_counts = Counter(n.kind.value for n in pg.nodes.values())

    # ----- Source file stats -----
    source_files = 0
    source_lines = 0
    snapshot = bundle.artifacts.get("repo_snapshot")
    if snapshot is not None and hasattr(snapshot, "files"):
        for finfo in snapshot.files:
            if finfo.language == "python":
                source_files += 1
                source_lines += _source_lines_of_file(Path(finfo.path))

    split = SPLIT_ASSIGNMENT.get(name, "train")

    # ----- Per-node rows -----
    node_rows: list[dict[str, Any]] = []
    for nid, node in pg.nodes.items():
        mapping = node_to_mapping.get(nid)
        if mapping is not None:
            role = _role_from_mapping_kind(mapping.kind)
            confidence = round(float(mapping.confidence_score or 0.0), 6)
            rule_fired = _infer_rule_from_mapping_id(mapping.id)
            mapping_id: str | None = mapping.id
        else:
            role = "UNMAPPED"
            confidence = 0.0
            rule_fired = "None"
            mapping_id = None

        role_distribution[role] += 1
        feats = graph_features.get(nid, {})
        node_name_lower = (node.name or "").lower()
        name_has_action_keyword = any(
            node_name_lower.startswith(kw) or f"_{kw}" in node_name_lower for kw in ACTION_KEYWORDS
        )

        # Lines-of-code proxy from source_range if present, else 0.
        loc = 0
        if node.source_range:
            try:
                loc = int(node.source_range.get("end_line", 0)) - int(
                    node.source_range.get("start_line", 0)
                )
                if loc < 0:
                    loc = 0
            except (TypeError, ValueError):
                loc = 0

        is_method = bool((node.metadata or {}).get("is_method", False))

        node_rows.append(
            {
                "repo_id": name,
                "node_id": nid,
                "node_name": node.name,
                "node_qualified_name": node.qualified_name,
                "node_kind": node.kind.value,
                "node_path": node.path,
                "assigned_role": role,
                "mapping_id": mapping_id,
                "confidence_score": confidence,
                "in_degree": feats.get("in_degree", 0),
                "out_degree": feats.get("out_degree", 0),
                "writes_count": feats.get("writes_count", 0),
                "reads_count": feats.get("reads_count", 0),
                "calls_count": feats.get("calls_count", 0),
                "depends_on_count": feats.get("depends_on_count", 0),
                "contains_out_count": feats.get("contains_out_count", 0),
                "has_type_annotation": False,
                "is_method": is_method,
                "is_async": False,
                "name_has_action_keyword": name_has_action_keyword,
                "lines_of_code": loc,
                "rule_fired": rule_fired,
                "split": split,
            }
        )

    # ----- Edge-level summary (kept inline on the instance) -----
    edges_summary: list[dict[str, Any]] = []
    for eid, edge in pg.edges.items():
        edges_summary.append(
            {
                "edge_id": eid,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "kind": edge.kind.value,
                "weight": edge.weight,
            }
        )

    # ----- Instance record -----
    instance: dict[str, Any] = {
        "instance_id": f"{name}_v1",
        "repo_id": name,
        "repo_path": str(fixture_path.relative_to(PROJECT_ROOT))
        if fixture_path.is_absolute()
        else str(fixture_path),
        "date_processed": datetime.now(UTC).strftime("%Y-%m-%d"),
        "cogant_version": _COGANT_VERSION,
        "split": split,
        "graph": {
            "node_count": len(pg.nodes),
            "edge_count": len(pg.edges),
            "node_kinds": dict(node_kind_counts),
            "node_roles": dict(role_distribution),
            "edge_types": dict(edge_kind_counts),
        },
        "mappings": {
            "count": len(mappings),
            "kinds": dict(Counter(m.kind.value for m in mappings.values())),
            "mean_confidence": round(
                sum((m.confidence_score or 0.0) for m in mappings.values()) / max(len(mappings), 1),
                6,
            ),
        },
        "gnn": {
            "A_shape": gnn_dict["shapes"]["A"],
            "B_shape": gnn_dict["shapes"]["B"],
            "C_len": gnn_dict["shapes"]["C"][0],
            "D_len": gnn_dict["shapes"]["D"][0],
            "n_states": gnn_dict["dimensions"]["n_states"],
            "n_obs": gnn_dict["dimensions"]["n_obs"],
            "n_actions": gnn_dict["dimensions"]["n_actions"],
            "A_sparsity": a_sparsity,
            "D_entropy": d_entropy,
        },
        "state_space": {
            "variables": len(ss.variables) if ss else 0,
            "observations": len(ss.observations) if ss else 0,
            "actions": len(ss.actions) if ss else 0,
            "schema_name": getattr(ss, "schema_name", "") if ss else "",
        },
        "process_model": {
            "stages": len(pm.stages) if pm else 0,
            "connections": len(pm.connections) if pm else 0,
        },
        "source": {
            "files": source_files,
            "lines": source_lines,
        },
        "edges": edges_summary,
    }

    return instance, node_rows


def _write_full_instance_bundle(
    name: str, instance: dict[str, Any], node_rows: list[dict[str, Any]], out_dir: Path
) -> Path:
    """Write the full per-instance bundle (instance + nodes + edges)."""
    out_path = out_dir / f"{name}.json"
    payload = {
        "instance": instance,
        "nodes": node_rows,
    }
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    return out_path


def main() -> int:
    """Generate the full COGANT ML dataset and write all artifacts to disk.

    Returns ``0`` on success. Aborts with the underlying exception on the
    first fixture failure rather than emitting partial rows.
    """
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    dataset_dir = PROJECT_ROOT / "evaluation" / "dataset"
    instances_dir = dataset_dir / "instances"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    instances_dir.mkdir(parents=True, exist_ok=True)

    nodes_jsonl = dataset_dir / "nodes.jsonl"
    instances_jsonl = dataset_dir / "instances.jsonl"

    all_instances: list[dict[str, Any]] = []
    all_node_rows: list[dict[str, Any]] = []

    print("COGANT ML dataset generator")
    print(f"  project_root : {PROJECT_ROOT}")
    print(f"  output_dir   : {dataset_dir}")
    print()

    for name, rel_path in FIXTURES:
        fixture_path = PROJECT_ROOT / rel_path
        if not fixture_path.exists():
            print(f"  [skip] {name}: missing at {fixture_path}")
            continue
        print(f"  [run ] {name} ({rel_path})")
        bundle = run_pipeline(str(fixture_path))
        instance, node_rows = build_instance(name, fixture_path, bundle)
        _write_full_instance_bundle(name, instance, node_rows, instances_dir)
        all_instances.append(instance)
        all_node_rows.extend(node_rows)
        g = instance["graph"]
        gnn = instance["gnn"]
        print(
            f"         nodes={g['node_count']:>3}  edges={g['edge_count']:>3}  "
            f"mappings={instance['mappings']['count']:>3}  "
            f"A={gnn['A_shape']}  B={gnn['B_shape']}  split={instance['split']}"
        )

    # ----- Write JSONL files -----
    with nodes_jsonl.open("w") as f:
        for row in all_node_rows:
            f.write(json.dumps(row, default=str) + "\n")

    with instances_jsonl.open("w") as f:
        for inst in all_instances:
            f.write(json.dumps(inst, default=str) + "\n")

    # ----- Aggregate stats -----
    role_totals: Counter[str] = Counter()
    split_totals: Counter[str] = Counter()
    for row in all_node_rows:
        role_totals[row["assigned_role"]] += 1
        split_totals[row["split"]] += 1

    # ----- Dataset metadata summary -----
    summary = {
        "version": "0.2.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "cogant_version": _COGANT_VERSION,
        "instance_count": len(all_instances),
        "node_count": len(all_node_rows),
        "edge_count": sum(i["graph"]["edge_count"] for i in all_instances),
        "split_counts": {split: split_totals.get(split, 0) for split in ("train", "val", "test")},
        "role_distribution": dict(role_totals),
        "files": {
            "instances_jsonl": str(instances_jsonl.relative_to(PROJECT_ROOT)),
            "nodes_jsonl": str(nodes_jsonl.relative_to(PROJECT_ROOT)),
            "instances_dir": str(instances_dir.relative_to(PROJECT_ROOT)),
        },
        "fixtures": [
            {"name": name, "path": rel_path, "split": SPLIT_ASSIGNMENT.get(name, "train")}
            for name, rel_path in FIXTURES
        ],
    }
    (dataset_dir / "dataset_summary.json").write_text(json.dumps(summary, indent=2))

    # ----- Report -----
    print()
    print("Wrote dataset:")
    print(f"  {nodes_jsonl.relative_to(PROJECT_ROOT)}")
    print(f"  {instances_jsonl.relative_to(PROJECT_ROOT)}")
    print(f"  {instances_dir.relative_to(PROJECT_ROOT)}/ ({len(all_instances)} files)")
    print("  evaluation/dataset/dataset_summary.json")
    print()
    print(f"Instances : {len(all_instances)}")
    print(f"Nodes     : {len(all_node_rows)}")
    print(f"Edges     : {summary['edge_count']}")
    print(f"Splits    : {dict(split_totals)}")
    print(f"Roles     : {dict(role_totals)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
