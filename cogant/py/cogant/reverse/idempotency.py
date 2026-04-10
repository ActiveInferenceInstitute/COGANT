"""Round-trip idempotency verifier.

This module answers the question: "If we synthesize a Python package
from a GNN markdown file and then re-run COGANT forward on the
resulting package, do we get back an isomorphic GNN?"

The answer is almost never "yes" in the strict sense of byte-for-byte
equality — the forward pipeline derives identifiers from Python names,
and synthesis derives Python names from the GNN slots, so there will
always be some drift. What we can measure and enforce is **role-level
isomorphism**: the multiset of MappingKind labels produced by forward
on the synthesized package should closely match the multiset implied
by the source GNN's ``## ActInfOntologyAnnotation`` section and the
declared cardinalities of hidden-state, observation, and action
factors.

Definition (weak isomorphism)
-----------------------------
Let ``G`` be the source GNN and ``G' = forward(synthesize(G))``. Let
``R(G)`` be the role multiset derived from ``G``'s ActInf ontology
annotation (``HIDDEN_STATE`` for each HiddenState, ``OBSERVATION`` for
each Observation, etc). Let ``R'(G')`` be the role multiset of
forward's semantic mappings. We define::

    role_match_score(G, G') = |R(G) ∩ R'(G')| / |R(G)|

We call ``G`` and ``G'`` **weakly isomorphic** when
``role_match_score >= ROLE_MATCH_THRESHOLD`` (default 0.5). Higher
thresholds can be requested by the caller.

Note this is intentionally a soft metric. The forward pipeline emits
semantic mappings for any pattern it recognises — including patterns
the synthesizer didn't explicitly model (e.g. assert statements
become CONSTRAINT mappings). The verifier rewards overlap but does
not penalise mappings that only appear on one side.
"""

from __future__ import annotations

import logging
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
from cogant.reverse.synthesizer import synthesize_package

logger = logging.getLogger(__name__)


ROLE_MATCH_THRESHOLD = 0.5
"""Default minimum role-match score for ``is_isomorphic`` to be True."""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class RoundtripResult:
    """Outcome of a single round-trip verification run.

    Attributes:
        is_isomorphic: True when the role-match score met the threshold.
        role_match_score: Fraction of source-GNN roles that were
            recovered by the forward pipeline on the synthesized
            package. Range ``[0.0, 1.0]``.
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
        errors: Non-fatal warnings collected during the round-trip.
    """

    is_isomorphic: bool = False
    role_match_score: float = 0.0
    matrix_score: float = 0.0
    structural_score: float = 0.0
    original_roles: dict[str, int] = field(default_factory=dict)
    synthesized_roles: dict[str, int] = field(default_factory=dict)
    shape_match: dict[str, bool] = field(default_factory=dict)
    package_path: Path | None = None
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Return a human-readable single-line summary of the result."""
        status = "ISO" if self.is_isomorphic else "DRIFT"
        return (
            f"[{status}] role_match={self.role_match_score:.2%} "
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


def _role_multiset_from_model(model: ReverseGNNModel) -> Counter:
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
    roles: Counter = Counter()
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


def _role_multiset_from_mappings(mappings: Any) -> Counter:
    """Derive a role multiset from a forward-pipeline semantic mappings dict."""
    roles: Counter = Counter()
    if mappings is None:
        return roles
    values = mappings.values() if isinstance(mappings, dict) else list(mappings)
    for mapping in values:
        kind = getattr(mapping, "kind", None)
        if kind is None:
            continue
        name = getattr(kind, "name", None) or getattr(kind, "value", None) or str(kind)
        roles[name.upper()] += 1
    return roles


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


def _nodes_edges_from_mappings(mappings: Any) -> tuple[list, list]:
    """Project a semantic-mappings dict into simple node/edge lists.

    Each mapping becomes a node labelled by its ``kind``. We do not
    currently materialise edges here — :func:`compare_graph_structure`
    handles the edge-less case correctly.
    """
    nodes: list = []
    edges: list = []
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
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Forward pipeline failed on %s", repo_path)
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify_roundtrip(
    gnn_path: str | Path,
    tmp_dir: str | Path | None = None,
    *,
    role_threshold: float = ROLE_MATCH_THRESHOLD,
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
        role_threshold: Minimum ``role_match_score`` for the round-trip
            to be reported as isomorphic. Defaults to
            :data:`ROLE_MATCH_THRESHOLD`.
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

    plan = plan_package(model)
    package_path = synthesize_package(plan, model, tmp_dir_obj)

    # 3. Run the forward pipeline on the synthesized package.
    forward = _run_forward(package_path)

    synthesized_roles = _role_multiset_from_mappings(forward.get("mappings"))

    # 4. Compute role-match score (overlap / original).
    if sum(original_roles.values()) == 0:
        score = 1.0  # Empty-model round-trip is vacuously isomorphic.
    else:
        overlap = sum((original_roles & synthesized_roles).values())
        score = overlap / sum(original_roles.values())

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
    # For the orig side we lack a real semantic-mapping view, so
    # synthesise node dicts directly from the role multiset derived
    # from the parsed GNN. The synth side uses the real mappings.
    orig_nodes = [
        {"role": role} for role, count in original_roles.items() for _ in range(count)
    ]
    synth_nodes, _synth_edges = _nodes_edges_from_mappings(forward.get("mappings"))
    structural_score = compare_graph_structure(
        orig_nodes, [], synth_nodes, []
    )

    result = RoundtripResult(
        is_isomorphic=score >= role_threshold,
        role_match_score=score,
        matrix_score=matrix_score,
        structural_score=structural_score,
        original_roles=dict(original_roles),
        synthesized_roles=dict(synthesized_roles),
        shape_match=shape_match,
        package_path=package_path,
    )
    if forward.get("error"):
        result.errors.append(str(forward["error"]))

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
    role_threshold: float = ROLE_MATCH_THRESHOLD,
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
    5. Compares ``R1`` and ``R2`` directly; the role-match score is
       ``|R1 ∩ R2| / |R1|`` under multiset intersection.

    This comparison style (forward-vs-forward) is the strictest
    definition of round-trip isomorphism for an existing repository:
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
        plan = plan_package(model)
        package_path = synthesize_package(plan, model, reverse_dir)

        # Stage 4: forward on the synthesized package.
        forward = _run_forward(package_path)
        synthesized_roles = _role_multiset_from_mappings(forward.get("mappings"))

        # Score: overlap / |original| under multiset intersection.
        if sum(original_roles.values()) == 0:
            score = 1.0
        else:
            overlap = sum((original_roles & synthesized_roles).values())
            score = overlap / sum(original_roles.values())

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
            _state_space_matrices(orig_ss),
            _state_space_matrices(new_ss),
        )
        orig_nodes, orig_edges = _nodes_edges_from_mappings(original_mappings)
        synth_nodes, synth_edges = _nodes_edges_from_mappings(
            forward.get("mappings")
        )
        structural_score = compare_graph_structure(
            orig_nodes, orig_edges, synth_nodes, synth_edges
        )

        result = RoundtripResult(
            is_isomorphic=score >= role_threshold,
            role_match_score=score,
            matrix_score=matrix_score,
            structural_score=structural_score,
            original_roles=dict(original_roles),
            synthesized_roles=dict(synthesized_roles),
            shape_match=shape_match,
            package_path=package_path,
        )
        if forward.get("error"):
            result.errors.append(str(forward["error"]))
        logger.info("Repo round-trip result: %s", result.summary())
        return result
    finally:
        if using_tmp:
            shutil.rmtree(work_dir, ignore_errors=True)


__all__ = [
    "RoundtripResult",
    "verify_roundtrip",
    "verify_repo_roundtrip",
    "ROLE_MATCH_THRESHOLD",
]
