"""Round-trip idempotency verifier.

This module answers the question: "If we synthesize a Python package
from a GNN markdown file and then re-run COGANT forward on the
resulting package, what survived the round-trip?"

Earlier versions used one role-overlap score and called the result
"isomorphic". That was too strong: COGANT can preserve the semantic
roles that matter for active-inference interpretation while still
changing graph counts, section text, matrix values, or generated-code
behavior. The public contract is now an invariant ledger plus a
``roundtrip_status`` taxonomy:

``STRUCTURALLY_ISOMORPHIC``
    The strict tier: role preservation passes, graph node/edge counts
    and edge kinds match, state-space and matrix invariants hold, GNN
    sections are preserved, generated code imports/compiles, and the
    second forward pass succeeded.

``ROLE_PRESERVED``
    The useful weaker tier: the source and regenerated artifacts
    preserve the semantic role multiset above the configured threshold,
    but at least one strict structural invariant drifted or was not
    observable.

``DRIFT``
    The round-trip completed but role preservation did not meet the
    configured threshold.

``FAILED``
    Synthesis or the second forward pass failed.

The role metric is intentionally soft. The forward pipeline emits
semantic mappings for any pattern it recognises, including patterns
the synthesizer did not explicitly model. The verifier rewards overlap
but reports extra/missing roles, graph deltas, matrix deltas, and GNN
section deltas instead of hiding them behind an overloaded
"isomorphism" label.
"""

from __future__ import annotations

import json
import logging
import py_compile
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cogant.reverse.metrics import (
    compare_graph_structure,
    compare_matrices,
)
from cogant.reverse.parser import ReverseGNNModel, parse_gnn
from cogant.reverse.planner import plan_package
from cogant.reverse.synthesizer import SEMANTIC_TARGETS_MANIFEST, synthesize_package

logger = logging.getLogger(__name__)


ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC = "STRUCTURALLY_ISOMORPHIC"
ROUNDTRIP_STATUS_ROLE_PRESERVED = "ROLE_PRESERVED"
ROUNDTRIP_STATUS_DRIFT = "DRIFT"
ROUNDTRIP_STATUS_FAILED = "FAILED"
ROUNDTRIP_STATUSES = (
    ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC,
    ROUNDTRIP_STATUS_ROLE_PRESERVED,
    ROUNDTRIP_STATUS_DRIFT,
    ROUNDTRIP_STATUS_FAILED,
)

ROLE_PRESERVATION_THRESHOLD = 0.5
"""Default minimum role-preservation score for the weaker success tier."""

# Deprecated compatibility alias for callers that have not yet moved to
# ``ROLE_PRESERVATION_THRESHOLD``. New JSON/CLI surfaces do not emit this name.
ROLE_MATCH_THRESHOLD = ROLE_PRESERVATION_THRESHOLD

MATRIX_VALUE_TOLERANCE = 1e-9
"""Maximum absolute A/B/C/D value delta allowed for strict preservation."""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class IdempotencyReport:
    """Detailed structural and semantic idempotency analysis.

    Attributes:
        is_idempotent: True if the round-trip preserved structural and
            semantic properties above their respective thresholds.
        forward_roles: Role multiset from the original forward pipeline
            run on the source code (before synthesis).
        reverse_roles: Role multiset from the re-run of forward on
            the synthesized code.
        differences: List of human-readable differences found between
            forward_roles and reverse_roles.
        score: A composite score in [0.0, 1.0] combining role match,
            structural match, and semantic match. Higher is better.
    """

    is_idempotent: bool = False
    forward_roles: dict[str, int] = field(default_factory=dict)
    reverse_roles: dict[str, int] = field(default_factory=dict)
    differences: list[str] = field(default_factory=list)
    score: float = 0.0


@dataclass(init=False)
class RoundtripResult:
    """Outcome of a single round-trip verification run.

    Attributes:
        roundtrip_status: One of ``ROUNDTRIP_STATUSES``.
        role_preservation_score: Fraction of source-GNN roles that were
            recovered by the forward pipeline on the synthesized
            package. Range ``[0.0, 1.0]``.
        role_preserved: True when ``role_preservation_score`` meets
            the configured threshold.
        structurally_isomorphic: True only when the full strict
            invariant ledger passes.
        matrix_preserved: True when observed A/B/C/D shapes and values
            are preserved within tolerance.
        gnn_sections_preserved: True when Markdown section membership
            survives the round-trip exactly.
        generated_code_ok: True when synthesized Python files import
            through ``py_compile``.
        matrix_score: Frobenius-based similarity of the A/B/C/D
            matrix stacks produced by the two sides of the round-trip.
            Range ``[0.0, 1.0]``. Defaults to ``0.0`` when matrices
            were not available on either side of the comparison.
        structural_score: Graph-structure similarity (node/edge role
            multiset symmetric difference, normalized and inverted).
            Range ``[0.0, 1.0]``. Defaults to ``0.0`` when the
            round-trip did not expose a node/edge view.
        original_roles: Role multiset derived from the source GNN
            (``{role_name: count}``).
        synthesized_roles: Role multiset from the forward pipeline's
            semantic mappings after reverse-synthesis.
        shape_match: Dict describing whether n_states, n_obs, and
            n_actions dimensions survived the round-trip.
    package_path: Absolute path to the synthesized package (kept
            on disk if the caller passed a persistent ``tmp_dir``).
        original_graph_summary: Node/edge/kind summary for the first
            graph view in the comparison.
        synthesized_graph_summary: Node/edge/kind summary for the
            graph produced by the forward re-run.
        graph_delta: Count and kind deltas between the graph summaries.
        gnn_diff: Section-level diff between original and regenerated
            GNN Markdown when both sides are available.
        matrix_delta: Shape/value deltas for A/B/C/D matrices when
            parseable GNN matrix blocks are available.
        invariants: Explicit pass/fail invariants for the
            code → graph → GNN → code → graph cycle.
        rule_evidence_trace: Rule/mapping evidence artifact from the
            synthesized forward pass, suitable for dashboard review.
        errors: Non-fatal warnings collected during the round-trip.
    """

    roundtrip_status: str
    role_preservation_score: float
    role_preserved: bool
    structurally_isomorphic: bool
    matrix_preserved: bool
    gnn_sections_preserved: bool
    generated_code_ok: bool
    matrix_score: float = 0.0
    structural_score: float = 0.0
    original_roles: dict[str, int]
    synthesized_roles: dict[str, int]
    shape_match: dict[str, bool]
    package_path: Path | None = None
    original_graph_summary: dict[str, Any]
    synthesized_graph_summary: dict[str, Any]
    graph_delta: dict[str, Any]
    gnn_diff: dict[str, Any]
    matrix_delta: dict[str, Any]
    invariants: dict[str, Any]
    rule_evidence_trace: dict[str, Any]
    errors: list[str]

    def __init__(
        self,
        *,
        roundtrip_status: str | None = None,
        role_preservation_score: float = 0.0,
        role_preserved: bool | None = None,
        structurally_isomorphic: bool | None = None,
        matrix_preserved: bool | None = None,
        gnn_sections_preserved: bool | None = None,
        generated_code_ok: bool | None = None,
        matrix_score: float = 0.0,
        structural_score: float = 0.0,
        original_roles: dict[str, int] | None = None,
        synthesized_roles: dict[str, int] | None = None,
        shape_match: dict[str, bool] | None = None,
        package_path: Path | None = None,
        original_graph_summary: dict[str, Any] | None = None,
        synthesized_graph_summary: dict[str, Any] | None = None,
        graph_delta: dict[str, Any] | None = None,
        gnn_diff: dict[str, Any] | None = None,
        matrix_delta: dict[str, Any] | None = None,
        invariants: dict[str, Any] | None = None,
        rule_evidence_trace: dict[str, Any] | None = None,
        errors: list[str] | None = None,
        # Backward-compatible input aliases. They are accepted so older
        # in-package tests and third-party callers fail gently, but the
        # public JSON/CLI contract no longer emits them.
        is_isomorphic: bool | None = None,
        role_match_score: float | None = None,
        roundtrip_invariants: dict[str, Any] | None = None,
    ) -> None:
        if role_match_score is not None:
            role_preservation_score = role_match_score
        if invariants is None and roundtrip_invariants is not None:
            invariants = roundtrip_invariants

        self.role_preservation_score = float(role_preservation_score)
        if role_preserved is None:
            role_preserved = (
                bool(is_isomorphic)
                if is_isomorphic is not None
                else self.role_preservation_score >= ROLE_PRESERVATION_THRESHOLD
            )
        self.role_preserved = bool(role_preserved)

        self.invariants = dict(invariants or {})
        if matrix_preserved is None:
            matrix_preserved = bool(self.invariants.get("matrix_preserved", False))
        if gnn_sections_preserved is None:
            gnn_sections_preserved = bool(self.invariants.get("gnn_sections_preserved", False))
        if generated_code_ok is None:
            generated_code_ok = bool(self.invariants.get("generated_code_ok", False))
        if structurally_isomorphic is None and is_isomorphic is not None:
            structurally_isomorphic = bool(is_isomorphic)
        elif structurally_isomorphic is None:
            structurally_isomorphic = _strict_invariants_preserved(
                role_preserved=self.role_preserved,
                matrix_preserved=bool(matrix_preserved),
                gnn_sections_preserved=bool(gnn_sections_preserved),
                generated_code_ok=bool(generated_code_ok),
                invariants=self.invariants,
            )

        self.matrix_preserved = bool(matrix_preserved)
        self.gnn_sections_preserved = bool(gnn_sections_preserved)
        self.generated_code_ok = bool(generated_code_ok)
        self.structurally_isomorphic = bool(structurally_isomorphic)
        self.roundtrip_status = roundtrip_status or _roundtrip_status_from_invariants(
            role_preserved=self.role_preserved,
            structurally_isomorphic=self.structurally_isomorphic,
            errors=errors or [],
        )
        if self.roundtrip_status not in ROUNDTRIP_STATUSES:
            self.roundtrip_status = ROUNDTRIP_STATUS_FAILED

        self.matrix_score = float(matrix_score)
        self.structural_score = float(structural_score)
        self.original_roles = dict(original_roles or {})
        self.synthesized_roles = dict(synthesized_roles or {})
        self.shape_match = dict(shape_match or {})
        self.package_path = package_path
        self.original_graph_summary = dict(original_graph_summary or {})
        self.synthesized_graph_summary = dict(synthesized_graph_summary or {})
        self.graph_delta = dict(graph_delta or {})
        self.gnn_diff = dict(gnn_diff or {})
        self.matrix_delta = dict(matrix_delta or {})
        self.rule_evidence_trace = dict(rule_evidence_trace or {})
        self.errors = list(errors or [])

    @property
    def is_isomorphic(self) -> bool:
        """Deprecated compatibility view; use ``structurally_isomorphic``."""
        return self.structurally_isomorphic

    @property
    def role_match_score(self) -> float:
        """Deprecated compatibility view; use ``role_preservation_score``."""
        return self.role_preservation_score

    @property
    def roundtrip_invariants(self) -> dict[str, Any]:
        """Deprecated compatibility view; use ``invariants``."""
        return self.invariants

    def summary(self) -> str:
        """Return a human-readable single-line summary of the result."""
        return (
            f"[{self.roundtrip_status}] role_preservation={self.role_preservation_score:.2%} "
            f"matrix={self.matrix_score:.2f} "
            f"struct={self.structural_score:.2f} "
            f"orig={dict(self.original_roles)} "
            f"synth={dict(self.synthesized_roles)}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Upstream ontology concept → canonical MappingKind role name used by
# COGANT. Anything not in this map falls back to "UNKNOWN" — it won't
# match any forward-derived role but will show up in the ``original``
# multiset for diagnostic purposes.
_ONTOLOGY_TO_ROLE: dict[str, str] = {
    "HiddenState": "HIDDEN_STATE",
    "Observation": "OBSERVATION",
    "Action": "ACTION",
    "Policy": "POLICY",
    "PreferenceVector": "PREFERENCE",
    "Preference": "PREFERENCE",
    "Constraint": "CONSTRAINT",
    "Context": "CONTEXT",
    "PriorBelief": "HIDDEN_STATE",  # Priors are tied to hidden states.
    "LikelihoodMatrix": "HIDDEN_STATE",
    "TransitionMatrix": "HIDDEN_STATE",
    "ExpectedFreeEnergy": "POLICY",
    "Time": "CONTEXT",
}


def _role_multiset_from_model(model: ReverseGNNModel) -> Counter[str]:
    """Derive the expected role multiset from a parsed GNN model.

    Rather than trust the ontology annotations alone (which often
    duplicate entries — s_f0, D_f0, B_f0 all map to HiddenState /
    PriorBelief / TransitionMatrix), we count primary slots:

    * one HIDDEN_STATE per hidden-state slot declared in StateSpaceBlock
    * one OBSERVATION per observation modality
    * one ACTION per action/control factor
    * one POLICY per declared policy slot
    * one CONSTRAINT per declared constraint/preference slot

    We then fold in any additional ontology-only annotations (e.g. a
    bare ``G=ExpectedFreeEnergy`` line) as a separate POLICY tick.
    """
    roles: Counter[str] = Counter()
    roles["HIDDEN_STATE"] += len(model.hidden_states)
    roles["OBSERVATION"] += len(model.observations)
    roles["ACTION"] += len(model.actions)
    roles["POLICY"] += len(model.policies)
    roles["CONSTRAINT"] += len(model.constraints)

    # Standalone annotations that introduce a concept not already
    # accounted for by a StateSpaceBlock slot (e.g. ``G=ExpectedFreeEnergy``).
    for var, concept in model.annotations.items():
        mapped = _ONTOLOGY_TO_ROLE.get(concept)
        if mapped != "POLICY":
            continue
        if var in model.hidden_states + model.observations + model.actions:
            continue
        if var in model.policies:
            continue
        roles["POLICY"] += 1

    # Drop zero-count entries so the diagnostic output is compact.
    return Counter({k: v for k, v in roles.items() if v > 0})


def _mapping_subject(mapping: Any) -> str:
    """Extract the program definition name represented by a mapping."""
    label = str(getattr(mapping, "semantic_label", "") or "")
    if " - " in label:
        return label.split(" - ", 1)[0]
    description = str(getattr(mapping, "description", "") or "")
    marker = "'"
    if marker in description:
        parts = description.split(marker)
        if len(parts) >= 3:
            return parts[1]
    return ""


def _role_multiset_from_mappings(
    mappings: Any,
    *,
    semantic_targets: dict[str, list[str]] | None = None,
) -> Counter[str]:
    """Derive a role multiset from a forward-pipeline semantic mappings dict."""
    roles: Counter[str] = Counter()
    if mappings is None:
        return roles
    target_sets = {
        str(role).upper(): set(names) for role, names in (semantic_targets or {}).items() if names
    }
    values = mappings.values() if isinstance(mappings, dict) else list(mappings)
    for mapping in values:
        kind = getattr(mapping, "kind", None)
        if kind is None:
            continue
        name = getattr(kind, "name", None) or getattr(kind, "value", None) or str(kind)
        role = str(name).upper()
        if target_sets:
            subject = _mapping_subject(mapping)
            if subject not in target_sets.get(role, set()):
                continue
        roles[role] += 1
    return roles


def _load_semantic_targets(repo_path: Path) -> dict[str, list[str]]:
    """Load generated semantic-target names for a synthesized package."""
    manifest_path = repo_path / SEMANTIC_TARGETS_MANIFEST
    if not manifest_path.exists():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    raw_targets = payload.get("semantic_targets")
    if not isinstance(raw_targets, dict):
        return {}
    targets: dict[str, list[str]] = {}
    for role, names in raw_targets.items():
        if not isinstance(names, list):
            continue
        clean = [str(name) for name in names if isinstance(name, str) and name]
        if clean:
            targets[str(role).upper()] = clean
    return targets


def _model_matrices(model: ReverseGNNModel) -> dict[str, Any]:
    """Return the A/B/C/D matrices of a ReverseGNNModel as a metrics dict.

    Only non-empty matrices are included; :func:`compare_matrices`
    treats missing keys correctly.
    """
    out: dict[str, Any] = {}
    if getattr(model, "A", None):
        out["A"] = model.A
    if getattr(model, "B", None):
        out["B"] = model.B
    if getattr(model, "C", None):
        out["C"] = model.C
    if getattr(model, "D", None):
        out["D"] = model.D
    return out


def _state_space_matrices(state_space: Any) -> dict[str, Any]:
    """Best-effort A/B/C/D extractor for a compiled StateSpaceModel.

    Returns an empty dict when the compiled state-space object does
    not expose matrix slots (the common case today) — the metrics
    layer will then fall back to its neutral matrix score.
    """
    if state_space is None:
        return {}
    out: dict[str, Any] = {}
    for key in ("A", "B", "C", "D"):
        val = getattr(state_space, key, None)
        if val is not None:
            out[key] = val
    return out


def _counter_from_graph_values(values: Any, attr: str) -> Counter[str]:
    """Count ``attr``/dict-key values across graph nodes or edges."""
    counts: Counter[str] = Counter()
    if isinstance(values, dict):
        iterable: list[Any] = list(values.values())
    elif isinstance(values, list | tuple):
        iterable = list(values)
    else:
        iterable = []
    for item in iterable:
        raw = getattr(item, attr, None)
        if raw is None and isinstance(item, dict):
            raw = item.get(attr)
        name = getattr(raw, "value", None) or getattr(raw, "name", None) or raw
        counts[str(name or "unknown")] += 1
    return counts


def _graph_summary(graph: Any) -> dict[str, Any]:
    """Return a stable count summary for a ProgramGraph-like object."""
    if graph is None:
        return {
            "node_count": 0,
            "edge_count": 0,
            "node_kinds": {},
            "edge_kinds": {},
        }
    nodes = getattr(graph, "nodes", None)
    edges = getattr(graph, "edges", None)
    if nodes is None and isinstance(graph, dict):
        nodes = graph.get("nodes")
        edges = graph.get("edges")
    node_count = len(nodes) if isinstance(nodes, dict | list | tuple) else 0
    edge_count = len(edges) if isinstance(edges, dict | list | tuple) else 0
    summary = {
        "node_count": node_count,
        "edge_count": edge_count,
        "node_kinds": dict(sorted(_counter_from_graph_values(nodes, "kind").items())),
        "edge_kinds": dict(sorted(_counter_from_graph_values(edges, "kind").items())),
    }
    root_ids = getattr(graph, "root_ids", None)
    if root_ids:
        summary["root_count"] = len(root_ids)
    return summary


def _role_graph_summary(roles: Counter[str] | dict[str, int]) -> dict[str, Any]:
    """Represent role counts as a graph-summary fallback."""
    total = sum(int(v) for v in roles.values())
    return {
        "node_count": total,
        "edge_count": 0,
        "node_kinds": dict(sorted((str(k), int(v)) for k, v in roles.items())),
        "edge_kinds": {},
        "source": "role_multiset",
    }


def _count_delta(original: dict[str, int], synthesized: dict[str, int]) -> dict[str, int]:
    keys = sorted(set(original) | set(synthesized))
    return {key: int(synthesized.get(key, 0)) - int(original.get(key, 0)) for key in keys}


def _graph_delta(original: dict[str, Any], synthesized: dict[str, Any]) -> dict[str, Any]:
    """Compute transparent graph count/kind deltas."""
    node_delta = int(synthesized.get("node_count", 0)) - int(original.get("node_count", 0))
    edge_delta = int(synthesized.get("edge_count", 0)) - int(original.get("edge_count", 0))
    node_kind_delta = _count_delta(
        {str(k): int(v) for k, v in (original.get("node_kinds") or {}).items()},
        {str(k): int(v) for k, v in (synthesized.get("node_kinds") or {}).items()},
    )
    edge_kind_delta = _count_delta(
        {str(k): int(v) for k, v in (original.get("edge_kinds") or {}).items()},
        {str(k): int(v) for k, v in (synthesized.get("edge_kinds") or {}).items()},
    )
    edit_distance = (
        abs(node_delta)
        + abs(edge_delta)
        + sum(abs(v) for v in node_kind_delta.values())
        + sum(abs(v) for v in edge_kind_delta.values())
    )
    denominator = max(
        int(original.get("node_count", 0))
        + int(original.get("edge_count", 0))
        + int(synthesized.get("node_count", 0))
        + int(synthesized.get("edge_count", 0)),
        1,
    )
    return {
        "node_delta": node_delta,
        "edge_delta": edge_delta,
        "node_kind_delta": node_kind_delta,
        "edge_kind_delta": edge_kind_delta,
        "edit_distance": {
            "distance": edit_distance,
            "normalized": edit_distance / denominator,
        },
    }


def _shape_of(value: Any) -> list[int]:
    if isinstance(value, list | tuple):
        if not value:
            return [0]
        return [len(value), *_shape_of(value[0])]
    return []


def _flatten_numeric(value: Any) -> list[float]:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return [float(value)]
    if isinstance(value, list | tuple):
        out: list[float] = []
        for item in value:
            out.extend(_flatten_numeric(item))
        return out
    return []


def _matrix_delta(original: dict[str, Any], synthesized: dict[str, Any]) -> dict[str, Any]:
    """Compare matrix shapes and numeric entries for A/B/C/D."""
    matrices: dict[str, Any] = {}
    shape_matches = 0
    compared = 0
    value_max_abs_delta = 0.0
    value_length_mismatch = False
    for key in ("A", "B", "C", "D"):
        left = original.get(key)
        right = synthesized.get(key)
        left_shape = _shape_of(left)
        right_shape = _shape_of(right)
        present = left is not None or right is not None
        if present:
            compared += 1
        if present and left_shape == right_shape:
            shape_matches += 1
        left_vals = _flatten_numeric(left)
        right_vals = _flatten_numeric(right)
        # A length mismatch means elements were dropped or added: a truncated
        # ``zip`` would compare only the overlap and could report max_abs=0.0
        # ("values preserved") even though the matrix changed size. Flag it so
        # ``matrix_values_preserved`` cannot read a dropped element as zero drift.
        key_length_mismatch = present and len(left_vals) != len(right_vals)
        if key_length_mismatch:
            value_length_mismatch = True
        deltas = [abs(a - b) for a, b in zip(left_vals, right_vals, strict=False)]
        max_abs = max(deltas) if deltas else None
        if max_abs is not None:
            value_max_abs_delta = max(value_max_abs_delta, max_abs)
        matrices[key] = {
            "original_shape": left_shape,
            "synthesized_shape": right_shape,
            "shape_match": bool(present and left_shape == right_shape),
            "original_values": len(left_vals),
            "synthesized_values": len(right_vals),
            "max_abs_delta": max_abs,
            "length_mismatch": key_length_mismatch,
        }
    return {
        "matrices": matrices,
        "shape_match_count": shape_matches,
        "compared_count": compared,
        "shape_score": shape_matches / compared if compared else 0.0,
        "max_abs_delta": value_max_abs_delta,
        "length_mismatch": value_length_mismatch,
    }


def _matrix_preserved(matrix_delta: dict[str, Any]) -> bool:
    """Return whether observed matrices preserve shape and values."""
    compared_count = int(matrix_delta.get("compared_count", 0) or 0)
    if compared_count == 0:
        return False
    max_abs_delta = float(matrix_delta.get("max_abs_delta", 0.0) or 0.0)
    return matrix_delta.get("shape_score") == 1.0 and max_abs_delta <= MATRIX_VALUE_TOLERANCE


def _gnn_sections(markdown: str) -> list[str]:
    sections: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            if name:
                sections.append(name)
    return sections


def _gnn_diff(original_markdown: str, synthesized_markdown: str) -> dict[str, Any]:
    """Section-level GNN Markdown diff."""
    original = _gnn_sections(original_markdown)
    synthesized = _gnn_sections(synthesized_markdown)
    original_counter = Counter(original)
    synthesized_counter = Counter(synthesized)
    missing = sorted((original_counter - synthesized_counter).elements())
    extra = sorted((synthesized_counter - original_counter).elements())
    common = sum((original_counter & synthesized_counter).values())
    denominator = max(len(original), len(synthesized), 1)
    return {
        "original_section_count": len(original),
        "synthesized_section_count": len(synthesized),
        "missing_sections": missing,
        "extra_sections": extra,
        "common_section_count": common,
        "section_score": common / denominator,
        "byte_delta": len(synthesized_markdown.encode("utf-8"))
        - len(original_markdown.encode("utf-8")),
    }


def _roundtrip_invariants(
    *,
    role_preservation_score: float,
    role_threshold: float,
    shape_match: dict[str, bool],
    graph_delta: dict[str, Any],
    matrix_delta: dict[str, Any],
    gnn_diff: dict[str, Any],
    generated_code_ok: bool,
    forward_error: Any = None,
) -> dict[str, Any]:
    """Return explicit boolean invariants for the roundtrip contract."""
    graph_edit = graph_delta.get("edit_distance") if isinstance(graph_delta, dict) else {}
    graph_norm = graph_edit.get("normalized") if isinstance(graph_edit, dict) else None
    node_delta = int(graph_delta.get("node_delta", 0)) if graph_delta else 0
    edge_delta = int(graph_delta.get("edge_delta", 0)) if graph_delta else 0
    edge_kind_delta = graph_delta.get("edge_kind_delta") if graph_delta else {}
    graph_node_edge_preserved = bool(graph_delta) and node_delta == 0 and edge_delta == 0
    edge_kinds_preserved = bool(edge_kind_delta is not None) and all(
        int(value) == 0 for value in dict(edge_kind_delta or {}).values()
    )
    matrix_ok = _matrix_preserved(matrix_delta)
    gnn_sections_ok = gnn_diff.get("section_score") == 1.0 if gnn_diff else False
    return {
        "role_preserved": role_preservation_score >= role_threshold,
        "role_threshold": role_threshold,
        "state_space_shape_preserved": all(shape_match.values()) if shape_match else False,
        "graph_node_edge_preserved": graph_node_edge_preserved,
        "edge_kinds_preserved": edge_kinds_preserved,
        "graph_edit_within_soft_bound": (
            float(graph_norm) <= 0.25 if isinstance(graph_norm, int | float) else False
        ),
        "matrix_shape_preserved": (
            matrix_delta.get("shape_score") == 1.0 if matrix_delta.get("compared_count") else False
        ),
        "matrix_values_preserved": (
            float(matrix_delta.get("max_abs_delta", 0.0) or 0.0) <= MATRIX_VALUE_TOLERANCE
            and not matrix_delta.get("length_mismatch", False)
            if matrix_delta.get("compared_count")
            else False
        ),
        "matrix_preserved": matrix_ok,
        "gnn_sections_preserved": gnn_sections_ok,
        "generated_code_ok": generated_code_ok,
        "forward_rerun_success": forward_error is None,
    }


def _strict_invariants_preserved(
    *,
    role_preserved: bool,
    matrix_preserved: bool,
    gnn_sections_preserved: bool,
    generated_code_ok: bool,
    invariants: dict[str, Any],
) -> bool:
    """Return the strict structural-isomorphism tier from the ledger."""
    return bool(
        role_preserved
        and invariants.get("state_space_shape_preserved", False)
        and invariants.get("graph_node_edge_preserved", False)
        and invariants.get("edge_kinds_preserved", False)
        and matrix_preserved
        and gnn_sections_preserved
        and generated_code_ok
        and invariants.get("forward_rerun_success", False)
    )


def _roundtrip_status_from_invariants(
    *,
    role_preserved: bool,
    structurally_isomorphic: bool,
    errors: list[str] | None,
) -> str:
    """Return the public status enum for a round-trip result."""
    if errors:
        return ROUNDTRIP_STATUS_FAILED
    if structurally_isomorphic:
        return ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC
    if role_preserved:
        return ROUNDTRIP_STATUS_ROLE_PRESERVED
    return ROUNDTRIP_STATUS_DRIFT


def _generated_code_status(package_path: Path) -> tuple[bool, list[str]]:
    """Compile generated Python files as a deterministic smoke check."""
    errors: list[str] = []
    for py_file in sorted(package_path.rglob("*.py")):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{py_file.relative_to(package_path)}: {exc.msg}")
    return not errors, errors


def _nodes_edges_from_mappings(mappings: Any) -> tuple[list[dict[str, Any]], list[Any]]:
    """Project a semantic-mappings dict into simple node/edge lists.

    Each mapping becomes a node labelled by its ``kind``. We do not
    currently materialise edges here — :func:`compare_graph_structure`
    handles the edge-less case correctly.
    """
    nodes: list[dict[str, Any]] = []
    edges: list[Any] = []
    if mappings is None:
        return nodes, edges
    values = mappings.values() if isinstance(mappings, dict) else list(mappings)
    for mapping in values:
        kind = getattr(mapping, "kind", None)
        if kind is None:
            continue
        name = getattr(kind, "name", None) or getattr(kind, "value", None) or str(kind)
        nodes.append({"role": str(name).upper()})
    return nodes, edges


def _run_forward(repo_path: Path) -> dict[str, Any]:
    """Run the COGANT forward pipeline on ``repo_path``.

    Returns a dict with keys ``mappings`` (the semantic-mapping dict),
    ``state_space`` (the compiled StateSpaceModel), and ``error``
    (non-None on failure).
    """
    result: dict[str, Any] = {
        "mappings": {},
        "state_space": None,
        "process_model": None,
        "program_graph": None,
        "gnn_markdown": "",
        "rule_evidence_trace": {},
        "semantic_targets": _load_semantic_targets(repo_path),
        "match_log": [],
        "error": None,
    }
    try:
        # Local import to keep idempotency.py importable even when
        # downstream optional deps for Session are missing.
        from cogant.api.session import Session

        session = Session(target=str(repo_path))
        session.extract_static()
        session.build_graph()
        session.translate_to_gnn()
        session.compile_state_space()
        bundle = session._bundle_internal()
        result["mappings"] = bundle.artifacts.get("_semantic_mappings", {}) or {}
        result["state_space"] = bundle.artifacts.get("_state_space_model")
        result["process_model"] = bundle.artifacts.get("_process_model")
        result["program_graph"] = bundle.artifacts.get("_program_graph")
        result["rule_evidence_trace"] = bundle.artifacts.get("_rule_evidence_trace") or {}
        engine = bundle.artifacts.get("_translation_engine")
        if engine is not None and hasattr(engine, "get_match_log"):
            result["match_log"] = engine.get_match_log()
        if (
            result["program_graph"] is not None
            and result["state_space"] is not None
            and result["process_model"] is not None
        ):
            from cogant.gnn.formatter import GNNMarkdownFormatter

            formatter = GNNMarkdownFormatter(
                program_graph=result["program_graph"],
                state_space_model=result["state_space"],
                process_model=result["process_model"],
                semantic_mappings=result["mappings"],
            )
            result["gnn_markdown"] = formatter.format()
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Forward pipeline failed on %s", repo_path)
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


# ---------------------------------------------------------------------------
# Idempotency checkers
# ---------------------------------------------------------------------------


def check_structural_idempotency(original_graph: Any, roundtrip_graph: Any) -> IdempotencyReport:
    """Check structural idempotency of two program graphs.

    Compares the node and edge populations of two graphs to determine
    if they have the same structural shape.

    Args:
        original_graph: The original ProgramGraph or compatible structure.
        roundtrip_graph: The ProgramGraph from the re-run.

    Returns:
        An IdempotencyReport describing structural similarities and
        differences.
    """
    report = IdempotencyReport()

    # Extract node/edge information from both graphs
    orig_nodes, orig_edges = _nodes_edges_from_mappings(original_graph)
    rt_nodes, rt_edges = _nodes_edges_from_mappings(roundtrip_graph)

    # Compare node role multisets
    orig_role_counts = Counter(node.get("role", "UNKNOWN") for node in orig_nodes)
    rt_role_counts = Counter(node.get("role", "UNKNOWN") for node in rt_nodes)

    report.forward_roles = dict(orig_role_counts)
    report.reverse_roles = dict(rt_role_counts)

    # Find differences
    all_roles = set(orig_role_counts.keys()) | set(rt_role_counts.keys())
    for role in sorted(all_roles):
        orig_count = orig_role_counts.get(role, 0)
        rt_count = rt_role_counts.get(role, 0)
        if orig_count != rt_count:
            report.differences.append(f"Role {role}: {orig_count} → {rt_count}")

    # Compute a simple structural score
    if orig_role_counts and rt_role_counts:
        intersection = sum(
            min(orig_role_counts.get(r, 0), rt_role_counts.get(r, 0)) for r in all_roles
        )
        union = sum(max(orig_role_counts.get(r, 0), rt_role_counts.get(r, 0)) for r in all_roles)
        report.score = intersection / union if union > 0 else 0.0
    else:
        report.score = 0.0

    report.is_idempotent = len(report.differences) == 0

    return report


def check_semantic_idempotency(
    original_mappings: dict[str, Any], roundtrip_mappings: dict[str, Any]
) -> IdempotencyReport:
    """Check semantic idempotency of two semantic-mapping dicts.

    Compares the role populations and distributions of two sets of
    semantic mappings.

    Args:
        original_mappings: Semantic mappings from the original forward run.
        roundtrip_mappings: Semantic mappings from the re-run.

    Returns:
        An IdempotencyReport describing semantic similarities and
        differences.
    """
    report = IdempotencyReport()

    orig_roles = _role_multiset_from_mappings(original_mappings)
    rt_roles = _role_multiset_from_mappings(roundtrip_mappings)

    report.forward_roles = dict(orig_roles)
    report.reverse_roles = dict(rt_roles)

    # Find differences
    all_roles = set(orig_roles.keys()) | set(rt_roles.keys())
    for role in sorted(all_roles):
        orig_count = orig_roles.get(role, 0)
        rt_count = rt_roles.get(role, 0)
        if orig_count != rt_count:
            report.differences.append(f"Role {role}: {orig_count} → {rt_count}")

    # Compute Jensen-Shannon-like score
    if orig_roles and rt_roles:
        intersection = sum(min(orig_roles.get(r, 0), rt_roles.get(r, 0)) for r in all_roles)
        union = sum(max(orig_roles.get(r, 0), rt_roles.get(r, 0)) for r in all_roles)
        report.score = intersection / union if union > 0 else 0.0
    else:
        report.score = 0.0

    report.is_idempotent = len(report.differences) == 0

    return report


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify_roundtrip(
    gnn_path: str | Path,
    tmp_dir: str | Path | None = None,
    *,
    role_threshold: float = ROLE_PRESERVATION_THRESHOLD,
    keep_tmp: bool = False,
) -> RoundtripResult:
    """Run a full round-trip on a GNN markdown file and score the result.

    Args:
        gnn_path: Path to a GNN markdown file produced by COGANT (or
            any conforming emitter).
        tmp_dir: Optional directory where the synthesized package
            should be written. If None, a temporary directory is
            created and removed after the run (unless ``keep_tmp``
            is True).
        role_threshold: Minimum ``role_preservation_score`` for the
            weaker role-preserved success tier. Defaults to
            :data:`ROLE_PRESERVATION_THRESHOLD`.
        keep_tmp: When True, do not delete the temporary directory
            after the run. Useful for debugging.

    Returns:
        A :class:`RoundtripResult` summarising the run. The result is
        always returned — exceptions inside the forward pipeline are
        captured as ``errors`` rather than raised.
    """
    gnn_path = Path(gnn_path).expanduser().resolve()

    # 1. Parse the source GNN.
    model = parse_gnn(gnn_path)
    original_roles = _role_multiset_from_model(model)

    # 2. Plan and synthesize into a temporary directory.
    cleanup_dir: Path | None = None
    if tmp_dir is None:
        tmp_dir_obj = Path(tempfile.mkdtemp(prefix="cogant-roundtrip-"))
        if not keep_tmp:
            cleanup_dir = tmp_dir_obj
    else:
        tmp_dir_obj = Path(tmp_dir).expanduser().resolve()
        tmp_dir_obj.mkdir(parents=True, exist_ok=True)

    plan = plan_package(model, expected_roles=original_roles)
    package_path = synthesize_package(plan, model, tmp_dir_obj)

    # 3. Run the forward pipeline on the synthesized package.
    forward = _run_forward(package_path)

    synthesized_roles = _role_multiset_from_mappings(
        forward.get("mappings"),
        semantic_targets=forward.get("semantic_targets"),
    )

    # 4. role_preservation_score = mean over every role present on either
    #    side of min(orig,synth)/max(orig,synth) — the formula documented
    #    in manuscript appendix S01. A role introduced OR dropped on one
    #    side scores 0.0 for that role; both-zero scores 1.0 (vacuous).
    #    (Prior code computed recall-only Sum(min)/Sum(orig), which
    #    saturated at exactly 1.0 for ANY superset synthesis and did NOT
    #    match the documented s_role — keystone defect, review 2026-05-19.)
    _roles = set(original_roles) | set(synthesized_roles)
    if not _roles:
        score = 1.0  # vacuous: empty-model round-trip
    else:
        _components: list[float] = []
        for _r in _roles:
            _o = original_roles.get(_r, 0)
            _s = synthesized_roles.get(_r, 0)
            if _o == 0 and _s == 0:
                _components.append(1.0)
            elif _o == 0 or _s == 0:
                _components.append(0.0)
            else:
                _components.append(min(_o, _s) / max(_o, _s))
        score = sum(_components) / len(_components)

    # 5. Check shape match. For the degenerate case where the original
    # has zero obs/actions, the forward pipeline is allowed to produce
    # anything — we only compare dims where the source had something.
    ss = forward.get("state_space")
    synth_n_states = len(getattr(ss, "variables", {}) or {}) if ss else 0
    synth_n_obs = len(getattr(ss, "observations", {}) or {}) if ss else 0
    synth_n_actions = len(getattr(ss, "actions", {}) or {}) if ss else 0

    shape_match: dict[str, bool] = {}
    if model.n_states > 0:
        shape_match["n_states"] = synth_n_states >= 1
    if model.n_obs > 0:
        shape_match["n_obs"] = synth_n_obs >= 1
    if model.n_actions > 0:
        shape_match["n_actions"] = synth_n_actions >= 1

    # Compute auxiliary distance metrics (matrix Frobenius + graph
    # structure) from whatever the forward pipeline exposed. These
    # never cause the round-trip to fail — they are reported as
    # diagnostic signal alongside the authoritative role_match_score.
    matrix_score = compare_matrices(
        _model_matrices(model),
        _state_space_matrices(forward.get("state_space")),
    )
    original_gnn_md = gnn_path.read_text(encoding="utf-8")
    synthesized_gnn_md = str(forward.get("gnn_markdown") or "")
    synth_model: ReverseGNNModel | None = None
    if synthesized_gnn_md:
        regenerated_dir = tmp_dir_obj / "regenerated"
        regenerated_dir.mkdir(parents=True, exist_ok=True)
        synthesized_gnn_path = regenerated_dir / "model.gnn.md"
        synthesized_gnn_path.write_text(synthesized_gnn_md, encoding="utf-8")
        try:
            synth_model = parse_gnn(synthesized_gnn_path)
            matrix_score = compare_matrices(_model_matrices(model), _model_matrices(synth_model))
        except Exception as exc:  # pragma: no cover - best effort diagnostics
            logger.debug("Could not parse regenerated GNN %s: %s", synthesized_gnn_path, exc)
    # For the orig side we lack a real semantic-mapping view, so
    # synthesise node dicts directly from the role multiset derived
    # from the parsed GNN. The synth side uses the real mappings.
    orig_nodes = [{"role": role} for role, count in original_roles.items() for _ in range(count)]
    synth_nodes, _synth_edges = _nodes_edges_from_mappings(forward.get("mappings"))
    structural_score = compare_graph_structure(orig_nodes, [], synth_nodes, [])
    original_graph_summary = _role_graph_summary(original_roles)
    synthesized_graph_summary = _graph_summary(forward.get("program_graph"))
    graph_delta = _graph_delta(original_graph_summary, synthesized_graph_summary)
    matrix_delta = _matrix_delta(
        _model_matrices(model),
        _model_matrices(synth_model)
        if synth_model is not None
        else _state_space_matrices(forward.get("state_space")),
    )
    gnn_diff = _gnn_diff(original_gnn_md, synthesized_gnn_md) if synthesized_gnn_md else {}
    generated_code_ok, generated_code_errors = _generated_code_status(package_path)
    errors = list(generated_code_errors)
    if forward.get("error"):
        errors.append(str(forward["error"]))
    invariants = _roundtrip_invariants(
        role_preservation_score=score,
        role_threshold=role_threshold,
        shape_match=shape_match,
        graph_delta=graph_delta,
        matrix_delta=matrix_delta,
        gnn_diff=gnn_diff,
        generated_code_ok=generated_code_ok,
        forward_error=forward.get("error"),
    )
    role_preserved = bool(invariants["role_preserved"])
    matrix_preserved = bool(invariants["matrix_preserved"])
    gnn_sections_preserved = bool(invariants["gnn_sections_preserved"])
    structurally_isomorphic = _strict_invariants_preserved(
        role_preserved=role_preserved,
        matrix_preserved=matrix_preserved,
        gnn_sections_preserved=gnn_sections_preserved,
        generated_code_ok=generated_code_ok,
        invariants=invariants,
    )

    result = RoundtripResult(
        roundtrip_status=_roundtrip_status_from_invariants(
            role_preserved=role_preserved,
            structurally_isomorphic=structurally_isomorphic,
            errors=errors,
        ),
        role_preservation_score=score,
        role_preserved=role_preserved,
        structurally_isomorphic=structurally_isomorphic,
        matrix_preserved=matrix_preserved,
        gnn_sections_preserved=gnn_sections_preserved,
        generated_code_ok=generated_code_ok,
        matrix_score=matrix_score,
        structural_score=structural_score,
        original_roles=dict(original_roles),
        synthesized_roles=dict(synthesized_roles),
        shape_match=shape_match,
        package_path=package_path,
        original_graph_summary=original_graph_summary,
        synthesized_graph_summary=synthesized_graph_summary,
        graph_delta=graph_delta,
        gnn_diff=gnn_diff,
        matrix_delta=matrix_delta,
        invariants=invariants,
        rule_evidence_trace=forward.get("rule_evidence_trace") or {},
        errors=errors,
    )

    # 6. Cleanup.
    if cleanup_dir is not None:
        try:
            shutil.rmtree(cleanup_dir, ignore_errors=True)
            # The package_path becomes stale; clear it so callers don't
            # try to read deleted files.
            result.package_path = None
        except OSError:  # pragma: no cover - defensive
            pass

    logger.info("Round-trip result: %s", result.summary())
    return result


def verify_repo_roundtrip(
    repo_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    role_threshold: float = ROLE_PRESERVATION_THRESHOLD,
) -> RoundtripResult:
    """Run forward → reverse → forward on an existing repository.

    This is the entry point used by the ``cogant roundtrip`` CLI
    subcommand. It:

    1. Runs the forward pipeline on ``repo_path`` and emits a GNN plus
       a **first** semantic-mappings multiset ``R1``.
    2. Parses the emitted GNN back into a ReverseGNNModel.
    3. Synthesizes a Python package from the plan.
    4. Runs the forward pipeline again on the synthesized package and
       collects a **second** semantic-mappings multiset ``R2``.
    5. Compares ``R1`` and ``R2`` directly; the role-preservation score is
       ``|R1 ∩ R2| / |R1|`` under multiset intersection.

    This comparison style (forward-vs-forward) is the strictest role
    preservation measurement for an existing repository:
    it asks whether the *same* pipeline sees the *same* roles in the
    synthesized package that it saw in the original. The alternative
    (parse the GNN, compare to forward-on-synth) is weaker because it
    mixes two different rule systems — the parser's role derivation
    and the forward pipeline's semantic rules — on the two sides of
    the comparison.

    Args:
        repo_path: Repository to round-trip.
        output_dir: Directory to write intermediate artifacts into.
            If None, a temporary directory is used and cleaned up.
        role_threshold: Minimum role match score to accept.

    Returns:
        :class:`RoundtripResult` with ``original_roles`` drawn from the
        first forward pass and ``synthesized_roles`` drawn from the
        second.
    """
    from cogant.api.session import Session

    repo_path = Path(repo_path).expanduser().resolve()
    using_tmp = output_dir is None
    work_dir = Path(output_dir or tempfile.mkdtemp(prefix="cogant-roundtrip-")).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    gnn_dir = work_dir / "forward"
    gnn_dir.mkdir(parents=True, exist_ok=True)
    reverse_dir = work_dir / "reverse"
    reverse_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Stage 1: forward on the original repo → GNN markdown + mappings.
        session = Session(target=str(repo_path))
        session.extract_static()
        session.build_graph()
        session.translate_to_gnn()
        session.compile_state_space()
        bundle = session._bundle_internal()

        original_mappings = bundle.artifacts.get("_semantic_mappings", {}) or {}
        original_roles = _role_multiset_from_mappings(original_mappings)
        original_state_space = bundle.artifacts.get("_state_space_model")
        original_graph = bundle.artifacts.get("_program_graph")
        original_trace = bundle.artifacts.get("_rule_evidence_trace") or {}

        from cogant.gnn.formatter import GNNMarkdownFormatter

        formatter = GNNMarkdownFormatter(
            program_graph=bundle.artifacts["_program_graph"],
            state_space_model=bundle.artifacts["_state_space_model"],
            process_model=bundle.artifacts["_process_model"],
            semantic_mappings=original_mappings,
        )
        gnn_md = formatter.format()
        gnn_path = gnn_dir / "model.gnn.md"
        gnn_path.write_text(gnn_md, encoding="utf-8")
        logger.info("Wrote forward GNN to %s", gnn_path)

        # Stage 2+3: parse → plan → synthesize.
        model = parse_gnn(gnn_path)
        plan = plan_package(model, expected_roles=original_roles)
        package_path = synthesize_package(plan, model, reverse_dir)

        # Stage 4: forward on the synthesized package.
        forward = _run_forward(package_path)
        synthesized_roles = _role_multiset_from_mappings(
            forward.get("mappings"),
            semantic_targets=forward.get("semantic_targets"),
        )
        synthesized_gnn_md = str(forward.get("gnn_markdown") or "")
        synthesized_gnn_path = work_dir / "regenerated" / "model.gnn.md"
        synth_model: ReverseGNNModel | None = None
        if synthesized_gnn_md:
            synthesized_gnn_path.parent.mkdir(parents=True, exist_ok=True)
            synthesized_gnn_path.write_text(synthesized_gnn_md, encoding="utf-8")
            try:
                synth_model = parse_gnn(synthesized_gnn_path)
            except Exception as exc:  # pragma: no cover - best effort diagnostics
                logger.debug("Could not parse regenerated GNN %s: %s", synthesized_gnn_path, exc)

        # role_preservation_score = mean over every role present on either
        # side of min(orig,synth)/max(orig,synth) — the formula documented
        # in manuscript appendix S01. A role introduced OR dropped scores
        # 0.0 for that role; both-zero scores 1.0 (vacuous). (Prior code:
        # recall-only Sum(min)/Sum(orig), saturated at 1.0 for ANY superset
        # synthesis — keystone defect, review 2026-05-19.)
        _roles = set(original_roles) | set(synthesized_roles)
        if not _roles:
            score = 1.0
        else:
            _comp: list[float] = []
            for _r in _roles:
                _o = original_roles.get(_r, 0)
                _s = synthesized_roles.get(_r, 0)
                if _o == 0 and _s == 0:
                    _comp.append(1.0)
                elif _o == 0 or _s == 0:
                    _comp.append(0.0)
                else:
                    _comp.append(min(_o, _s) / max(_o, _s))
            score = sum(_comp) / len(_comp)

        # Shape match: compare the two state-space models directly.
        shape_match: dict[str, bool] = {}
        orig_ss = original_state_space
        new_ss = forward.get("state_space")
        orig_n_states = len(getattr(orig_ss, "variables", {}) or {}) if orig_ss else 0
        orig_n_obs = len(getattr(orig_ss, "observations", {}) or {}) if orig_ss else 0
        orig_n_actions = len(getattr(orig_ss, "actions", {}) or {}) if orig_ss else 0
        new_n_states = len(getattr(new_ss, "variables", {}) or {}) if new_ss else 0
        new_n_obs = len(getattr(new_ss, "observations", {}) or {}) if new_ss else 0
        new_n_actions = len(getattr(new_ss, "actions", {}) or {}) if new_ss else 0
        if orig_n_states > 0:
            shape_match["n_states"] = new_n_states >= 1
        if orig_n_obs > 0:
            shape_match["n_obs"] = new_n_obs >= 1
        if orig_n_actions > 0:
            shape_match["n_actions"] = new_n_actions >= 1

        # Auxiliary distance metrics. The repo round-trip has access
        # to two compiled state-space models, so we can compare their
        # matrix slots directly when available.
        matrix_score = compare_matrices(
            _model_matrices(model),
            _model_matrices(synth_model)
            if synth_model is not None
            else _state_space_matrices(new_ss),
        )
        orig_nodes, orig_edges = _nodes_edges_from_mappings(original_mappings)
        synth_nodes, synth_edges = _nodes_edges_from_mappings(forward.get("mappings"))
        structural_score = compare_graph_structure(orig_nodes, orig_edges, synth_nodes, synth_edges)
        original_graph_summary = _graph_summary(original_graph)
        synthesized_graph_summary = _graph_summary(forward.get("program_graph"))
        graph_delta = _graph_delta(original_graph_summary, synthesized_graph_summary)
        matrix_delta = _matrix_delta(
            _model_matrices(model),
            _model_matrices(synth_model)
            if synth_model is not None
            else _state_space_matrices(new_ss),
        )
        gnn_diff = _gnn_diff(gnn_md, synthesized_gnn_md) if synthesized_gnn_md else {}
        generated_code_ok, generated_code_errors = _generated_code_status(package_path)
        errors = list(generated_code_errors)
        if forward.get("error"):
            errors.append(str(forward["error"]))
        invariants = _roundtrip_invariants(
            role_preservation_score=score,
            role_threshold=role_threshold,
            shape_match=shape_match,
            graph_delta=graph_delta,
            matrix_delta=matrix_delta,
            gnn_diff=gnn_diff,
            generated_code_ok=generated_code_ok,
            forward_error=forward.get("error"),
        )
        role_preserved = bool(invariants["role_preserved"])
        matrix_preserved = bool(invariants["matrix_preserved"])
        gnn_sections_preserved = bool(invariants["gnn_sections_preserved"])
        structurally_isomorphic = _strict_invariants_preserved(
            role_preserved=role_preserved,
            matrix_preserved=matrix_preserved,
            gnn_sections_preserved=gnn_sections_preserved,
            generated_code_ok=generated_code_ok,
            invariants=invariants,
        )

        result = RoundtripResult(
            roundtrip_status=_roundtrip_status_from_invariants(
                role_preserved=role_preserved,
                structurally_isomorphic=structurally_isomorphic,
                errors=errors,
            ),
            role_preservation_score=score,
            role_preserved=role_preserved,
            structurally_isomorphic=structurally_isomorphic,
            matrix_preserved=matrix_preserved,
            gnn_sections_preserved=gnn_sections_preserved,
            generated_code_ok=generated_code_ok,
            matrix_score=matrix_score,
            structural_score=structural_score,
            original_roles=dict(original_roles),
            synthesized_roles=dict(synthesized_roles),
            shape_match=shape_match,
            package_path=package_path,
            original_graph_summary=original_graph_summary,
            synthesized_graph_summary=synthesized_graph_summary,
            graph_delta=graph_delta,
            gnn_diff=gnn_diff,
            matrix_delta=matrix_delta,
            invariants=invariants,
            rule_evidence_trace={
                "original": original_trace,
                "synthesized": forward.get("rule_evidence_trace") or {},
            },
            errors=errors,
        )
        logger.info("Repo round-trip result: %s", result.summary())
        return result
    finally:
        if using_tmp:
            shutil.rmtree(work_dir, ignore_errors=True)


__all__ = [
    "IdempotencyReport",
    "RoundtripResult",
    "verify_roundtrip",
    "verify_repo_roundtrip",
    "ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC",
    "ROUNDTRIP_STATUS_ROLE_PRESERVED",
    "ROUNDTRIP_STATUS_DRIFT",
    "ROUNDTRIP_STATUS_FAILED",
    "ROUNDTRIP_STATUSES",
    "ROLE_PRESERVATION_THRESHOLD",
    "ROLE_MATCH_THRESHOLD",
    "check_structural_idempotency",
    "check_semantic_idempotency",
]
