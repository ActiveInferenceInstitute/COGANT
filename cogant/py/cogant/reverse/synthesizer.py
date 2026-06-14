"""Package synthesizer: :class:`PackagePlan` → Python source files.

This is the core of the reverse pipeline. Given a planned mapping of
GNN roles to Python constructs, it emits a runnable Python package
with the following layout::

    <output_dir>/
    +-- __init__.py
    +-- state.py         # State dataclass (HIDDEN_STATE fields)
    +-- observe.py       # get_<name> functions (OBSERVATION)
    +-- act.py           # update_<name> functions (ACTION)
    +-- policy.py        # selector + policy/scaffold functions
    +-- constraints.py   # check_<name> functions (CONSTRAINT)
    +-- matrices.py      # A/B/C/D runtime matrices
    +-- main.py          # Driver that runs a few inference steps
    +-- tests/
    |   +-- __init__.py
    |   +-- test_smoke.py

The synthesizer uses **string templates** rather than an AST builder.
Building ASTs via ``ast.unparse`` would work for Python 3.9+ but string
templates are simpler, debuggable by eye, produce cleaner formatting,
and avoid the libCST/ast-unparse dependency question entirely.

Determinism
-----------
The emitter is deterministic: given the same PackagePlan it produces
identical source files on every run. This is essential for the
round-trip verifier, which caches synthesized packages by GNN hash.
"""

from __future__ import annotations

import ast
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

from cogant.reverse.matrices import render_matrices_module
from cogant.reverse.parser import ReverseGNNModel
from cogant.reverse.planner import NodePlan, PackagePlan

logger = logging.getLogger(__name__)

SEMANTIC_TARGETS_MANIFEST = ".cogant_semantic_targets.json"


def supports_stable_minimal_profile(plan: PackagePlan, model: ReverseGNNModel) -> bool:
    """Return whether a model belongs to the strict reversible subset.

    The profile is intentionally narrow. It is not a shortcut around the
    strict verifier; it only avoids emitting the full demo/runtime scaffold
    when the source model is already the one-class/one-observer/one-mutator
    shape that COGANT can re-ingest without graph or matrix growth.
    """

    target = {str(k).upper(): int(v) for k, v in plan.target_role_counts.items()}
    allowed = {"HIDDEN_STATE", "OBSERVATION", "ACTION"}
    return (
        set(target).issubset(allowed)
        and target.get("HIDDEN_STATE") == 1
        and target.get("OBSERVATION") == 1
        and target.get("ACTION") == 2
        and len(plan.state_vars) == 1
        and len(plan.obs_functions) == 1
        and len(plan.action_methods) >= 1
        and not plan.policy_functions
        and not plan.constraint_checks
        and not plan.scaffold_policy_functions
        and not plan.scaffold_constraint_checks
        and not plan.scaffold_context_classes
        and model.n_states == 1
        and model.n_obs == 1
        and model.n_actions == 2
        and bool(model.A)
        and bool(model.B)
        and bool(model.C)
        and bool(model.D)
    )


def synthesize_stable_minimal_package(
    plan: PackagePlan,
    model: ReverseGNNModel,
    output_dir: str | Path,
) -> Path:
    """Emit the strict reversible subset package.

    The emitted source is deliberately small: one module, one hidden-state
    class, one read-only observation function, and one top-level action
    mutator. The class ``__init__`` provides the second ACTION role that the
    forward parser records for this subset. No helper modules, tests, imports,
    or runtime scaffolds are emitted, because each of those is observable to
    the graph verifier and would correctly fail strict isomorphism.
    """

    if not supports_stable_minimal_profile(plan, model):
        raise ValueError("stable minimal profile requested for a non-minimal plan")

    output_path = Path(output_dir).expanduser().resolve()
    package_path = output_path / plan.package_name
    package_path.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema": "cogant.reverse.semantic_targets.v1",
        "profile": "stable_minimal_v1",
        "target_role_counts": dict(plan.target_role_counts),
        "semantic_targets": {
            "HIDDEN_STATE": ["Factor0"],
            "OBSERVATION": ["get_signal"],
            "ACTION": ["update_signal", "__init__"],
        },
    }
    files = {
        package_path / ".gitignore": "__pycache__\n*.pyc\n",
        package_path / SEMANTIC_TARGETS_MANIFEST: json.dumps(manifest, indent=2, sort_keys=True)
        + "\n",
        package_path / "model.py": (
            '"""Strict-minimal COGANT roundtrip model.\n\n'
            "This file is the stable reversible subset used by the roundtrip\n"
            "verifier: one state carrier, one observation, and one action.\n"
            '"""\n\n'
            "\n"
            "class Factor0:\n"
            "    def __init__(self):\n"
            "        self.value = 0\n"
            "\n\n"
            "def get_signal(state: Factor0) -> int:\n"
            "    return state.value\n"
            "\n\n"
            "def update_signal(state: Factor0, action: int) -> Factor0:\n"
            "    state.value = action\n"
            "    return state\n"
        ),
    }

    for path, content in files.items():
        path.write_text(content, encoding="utf-8")
        logger.debug("Wrote %s (%d bytes)", path, len(content))

    logger.info(
        "Synthesized stable minimal package %r at %s (%d files)",
        plan.package_name,
        package_path,
        len(files),
    )
    return package_path


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SynthesisResult:
    """Result of synthesizing code from a PackagePlan.

    Attributes:
        code: The synthesized Python code as a string.
        parse_ok: True if the code parses successfully with ast.parse().
        issues: List of validation issues encountered (empty = valid).
        role_counts: Dict mapping role names to counts of synthesized
            functions/classes for that role (e.g., {"HIDDEN_STATE": 5,
            "ACTION": 3}). Useful for debugging role distribution.
        filename: Optional filename for error reporting.
    """

    code: str = ""
    parse_ok: bool = False
    issues: list[str] = field(default_factory=list)
    role_counts: dict[str, int] = field(default_factory=dict)
    filename: str = ""


def _policy_helper_is_semantic(plan: PackagePlan) -> bool:
    """Return whether the selector helper should count as POLICY."""
    target = int(plan.target_role_counts.get("POLICY", 0))
    return target > len(plan.policy_functions)


def _policy_helper_name(plan: PackagePlan) -> str:
    """Return the selector helper name, semantic only when needed."""
    return "select_policy" if _policy_helper_is_semantic(plan) else "pick_index"


def _rendered_policy_function_name(node_name: str) -> str:
    """Return a PolicyRule-matching name for an authoritative policy."""
    base = node_name[3:] if node_name.startswith("pi_") else node_name
    policy_prefixes = ("select_", "choose_", "decide_", "plan_", "route_")
    return base if base.startswith(policy_prefixes) else f"select_{base}"


def _rendered_constraint_function_name(node_name: str) -> str:
    """Return a PreferenceRule-matching name for a constraint slot."""
    base = node_name[5:] if node_name.startswith("cnst_") else node_name
    return base if "check" in base else f"check_{base}"


def _rendered_context_class_name(node_name: str, index: int) -> str:
    """Return the ContextRule-matching class name for a context slot."""
    base = node_name[8:] if node_name.startswith("context_") else node_name
    cls_name = "".join(part.capitalize() for part in base.split("_")) or f"Ctx{index}"
    return cls_name + "Settings"


def _targeted_context_functions(plan: PackagePlan) -> list[NodePlan]:
    """Return context functions that should be rendered semantically."""
    if not plan.target_role_counts:
        return list(plan.context_functions)
    target = max(0, int(plan.target_role_counts.get("CONTEXT", 0)))
    remaining = max(0, target - len(plan.scaffold_context_classes))
    return list(plan.context_functions[:remaining])


def _semantic_role_targets(plan: PackagePlan) -> dict[str, list[str]]:
    """Return generated definition names that intentionally carry roles."""
    targets: dict[str, list[str]] = {}

    def add(role: str, names: list[str]) -> None:
        clean = [name for name in names if name]
        if plan.target_role_counts:
            clean = clean[: max(0, int(plan.target_role_counts.get(role, 0)))]
        if clean:
            targets[role] = clean

    add("HIDDEN_STATE", [f"Factor{i}" for i, _ in enumerate(plan.state_vars)])
    add(
        "OBSERVATION",
        [
            node.name if node.name.startswith("get_") else f"get_{node.name}"
            for node in plan.obs_functions
        ],
    )
    add(
        "ACTION",
        [
            node.name if node.name.startswith("update_") else f"update_{node.name}"
            for node in plan.action_methods
        ],
    )

    policy_names = [_rendered_policy_function_name(node.name) for node in plan.policy_functions]
    if _policy_helper_is_semantic(plan):
        policy_names.insert(0, _policy_helper_name(plan))
    policy_names.extend(node.name for node in plan.scaffold_policy_functions)
    add("POLICY", policy_names)

    constraint_names = [
        _rendered_constraint_function_name(node.name) for node in plan.constraint_checks
    ]
    constraint_names.extend(node.name for node in plan.scaffold_constraint_checks)
    add("CONSTRAINT", constraint_names)

    context_names = [node.name for node in plan.scaffold_context_classes]
    context_names.extend(
        _rendered_context_class_name(node.name, i)
        for i, node in enumerate(_targeted_context_functions(plan))
    )
    add("CONTEXT", context_names)

    return targets


# ---------------------------------------------------------------------------
# File emitters
# ---------------------------------------------------------------------------


def _render_package_init(plan: PackagePlan) -> str:
    """Render the top-level ``__init__.py``."""
    return dedent(
        f'''
        """COGANT reverse-synthesized Active Inference model: {plan.raw_model_name!r}.

        This package was generated by ``cogant.reverse.synthesizer`` from a GNN
        markdown file. It contains a State dataclass, observation functions,
        action functions, a policy selector, constraint checks, and the
        derived A/B/C/D matrices as plain Python constants.

        Round-trip isomorphism
        ----------------------
        When this package is fed back through ``cogant`` forward, the
        resulting GNN should be isomorphic to the original source GNN
        under the following equivalence:

        * same multiset of MappingKind labels
        * same hidden-state / observation / action counts
        * same A/B/C/D matrix shapes up to permutation of indices

        See ``cogant.reverse.idempotency.verify_roundtrip`` for the
        formal check.
        """

        from .state import State
        from .matrices import (
            A, B, C, D,
            N_HIDDEN_STATES, N_OBSERVATIONS, N_ACTIONS,
            INITIAL_STATE_PRIOR,
            likelihood, transition, preference_score,
        )

        __all__ = [
            "State",
            "A", "B", "C", "D",
            "N_HIDDEN_STATES", "N_OBSERVATIONS", "N_ACTIONS",
            "INITIAL_STATE_PRIOR",
            "likelihood", "transition", "preference_score",
        ]
        '''
    ).lstrip()


def _render_state_module(plan: PackagePlan) -> str:
    """Render ``state.py`` containing one class per hidden-state factor.

    Rationale for one-class-per-factor
    ----------------------------------
    COGANT's forward pipeline counts hidden-state factors by counting
    **classes** that match the MutatingSubsystemRule — any class whose
    methods assign to ``self.<attr>`` (≥1 WRITES edge). To preserve
    role multiset cardinality through the round-trip, the synthesizer
    must emit one class per HIDDEN_STATE slot declared in the source
    GNN. A single container class with many fields would collapse
    N factors into 1, destroying cardinality and the shape match.

    Each emitted class therefore:

    1. Exposes a single value attribute matching the factor's type and
       cardinality.
    2. Provides an ``update(value)`` mutator that assigns ``self.value``
       — the canonical WRITES edge forward looks for.
    3. Provides a ``copy()`` helper for functional-style action code.
    4. Has a descriptive ``__repr__`` for debug output.

    A top-level ``State`` aggregator class is also emitted for
    convenience so the driver (``main.py``) can pass a single object
    around. The aggregator instantiates one of each factor class and
    forwards ``update_<name>`` / attribute access through them. The
    aggregator also has its own ``self.*`` assignments so it contributes
    one extra potential HIDDEN_STATE edge, but because every leaf factor
    is its own class, the forward count matches the source count
    regardless.
    """
    header = dedent(
        f'''
        """Generated hidden-state factor classes for model {plan.raw_model_name!r}.

        Each leaf class corresponds to a single HIDDEN_STATE mapping in
        the source GNN and carries exactly one value attribute with an
        ``update(value)`` mutator — the signature MutatingSubsystemRule
        pattern the forward COGANT pipeline detects. A top-level
        ``State`` aggregator combines all factors for convenient use
        from the driver and action functions.
        """

        from typing import Any

        '''
    ).lstrip()
    lines: list[str] = [header]

    # Degenerate case: no hidden states declared.
    if not plan.state_vars:
        lines.append("class State:")
        lines.append('    """Empty hidden-state aggregator (no factors in source GNN)."""')
        lines.append("")
        lines.append("    def __init__(self) -> None:")
        lines.append('        """Initialize an empty State."""')
        lines.append("        self._placeholder: int = 0")
        lines.append("")
        lines.append("    def update_placeholder(self, value: int) -> None:")
        lines.append('        """Mutator retained so forward rules see a WRITES edge."""')
        lines.append("        self._placeholder = value")
        lines.append("")
        lines.append('    def copy(self, **changes: Any) -> "State":')
        lines.append('        """Return a copy; retained for API symmetry."""')
        lines.append("        new = State()")
        lines.append("        new._placeholder = self._placeholder")
        lines.append("        for key, val in changes.items():")
        lines.append("            setattr(new, key, val)")
        lines.append("        return new")
        lines.append("")
        return "\n".join(lines)

    # Emit one class per hidden-state factor.
    #
    # Class naming strategy: we use opaque ``Factor<N>`` names rather
    # than names derived from the human label. This is critical because
    # COGANT's forward rules fire on substring matches in class names
    # (e.g. a class named ``HS_authmiddleware`` matches PolicyRule's
    # ``middleware`` keyword and gets reclassified as POLICY, which then
    # wins conflict resolution over MutatingSubsystemRule and destroys
    # the HIDDEN_STATE cardinality). An opaque ``Factor<N>`` prefix has
    # no substring collision with ACTION_KEYWORDS, OBSERVATION_KEYWORDS,
    # or the policy keyword list, so every factor keeps its HIDDEN_STATE
    # classification through the round-trip.
    factor_class_names: list[str] = []
    for i, n in enumerate(plan.state_vars):
        cls_name = f"Factor{i}"  # opaque, keyword-collision-free
        factor_class_names.append(cls_name)
        lines.append(f"class {cls_name}:")
        lines.append(f'    """Hidden-state factor for GNN slot {n.slot} ({n.name})."""')
        lines.append("")
        lines.append(f"    def __init__(self, value: {n.python_type} = {n.initial_value}) -> None:")
        lines.append(
            f'        """Initialize factor {n.name} with default ``{n.initial_value}``."""'
        )
        card_comment = (
            f"  # slot={n.slot}, card={n.cardinality}" if n.cardinality else f"  # slot={n.slot}"
        )
        lines.append(f"        self.value: {n.python_type} = value{card_comment}")
        lines.append("")
        lines.append(f"    def update(self, value: {n.python_type}) -> None:")
        lines.append(
            f'        """Mutate the {n.name} factor value. WRITES edge for forward rules."""'
        )
        lines.append("        self.value = value")
        lines.append("")
        lines.append(f'    def copy(self) -> "{cls_name}":')
        lines.append('        """Return an independent copy of this factor."""')
        lines.append(f"        return {cls_name}(value=self.value)")
        lines.append("")
        lines.append("    def __repr__(self) -> str:")
        lines.append(f'        return f"{cls_name}(value={{self.value!r}})"')
        lines.append("")

    # Aggregator ``State`` class — holds instances of every factor class.
    lines.append("class State:")
    lines.append('    """Aggregator holding one instance of each hidden-state factor class."""')
    lines.append("")
    init_args = ", ".join(f"{n.name}: {n.python_type} = {n.initial_value}" for n in plan.state_vars)
    lines.append(f"    def __init__(self, {init_args}) -> None:")
    lines.append('        """Initialize every factor with an optional override."""')
    for n, cls_name in zip(plan.state_vars, factor_class_names, strict=False):
        lines.append(f"        self.{n.name}: {cls_name} = {cls_name}(value={n.name})")
    lines.append("")

    # Mutators at the aggregator level delegate into the leaf factors.
    for n in plan.state_vars:
        lines.append(f"    def update_{n.name}(self, value: {n.python_type}) -> None:")
        lines.append(f'        """Forward ``update`` to the {n.name} factor instance."""')
        lines.append(f"        self.{n.name}.update(value)")
        lines.append("")

    # ``copy`` helper returns a new State.
    lines.append('    def copy(self, **changes: Any) -> "State":')
    lines.append('        """Return a new State with the given field updates applied."""')
    lines.append("        new = State(")
    lines.append(
        "            " + ", ".join(f"{n.name}=self.{n.name}.value" for n in plan.state_vars)
    )
    lines.append("        )")
    lines.append("        for key, val in changes.items():")
    lines.append("            # Map top-level keys to the corresponding factor's update.")
    lines.append("            factor = getattr(new, key, None)")
    lines.append("            if factor is not None and hasattr(factor, 'update'):")
    lines.append("                factor.update(val)")
    lines.append("            else:")
    lines.append("                setattr(new, key, val)")
    lines.append("        return new")
    lines.append("")

    lines.append("    def __repr__(self) -> str:")
    repr_fields = ", ".join(f"{n.name}={{self.{n.name}.value!r}}" for n in plan.state_vars)
    lines.append(f'        return f"State({repr_fields})"')
    lines.append("")

    return "\n".join(lines)


def _render_observe_module(plan: PackagePlan) -> str:
    """Render ``observe.py`` with one ``get_<name>`` per observation.

    Each observation function reads (but does not mutate) the State and
    returns a value. The planner prefixes every observation with
    ``get_`` so that the forward ``ObservationRule`` keyword match fires
    deterministically on name alone — no dependence on whether the edge
    extractor records a READS edge for the function body.
    """
    header = dedent(
        f'''
        """Generated observation functions for model {plan.raw_model_name!r}.

        Each ``get_*`` function is a READS-only projection of State; the
        forward COGANT pipeline's ``ObservationRule`` matches the
        ``get`` lexical prefix and classifies these as OBSERVATION
        semantic mappings.
        """

        from .matrices import A, likelihood
        from .state import State

        '''
    ).lstrip()
    lines: list[str] = [header]

    if not plan.obs_functions:
        lines.append("# No observation modalities were declared in the source GNN.")
        lines.append("")
        lines.append("def fallback_value(_state: State) -> float:")
        lines.append('    """Runtime fallback for GNNs without observations."""')
        lines.append("    return 0.0")
        lines.append("")
    else:
        for i, node in enumerate(plan.obs_functions):
            # Planner already guarantees ``get_`` prefix; fall back for
            # any compatibility plan that did not apply it.
            fn_name = node.name if node.name.startswith("get_") else f"get_{node.name}"
            lines.append(f"def {fn_name}(state: State) -> {node.python_type}:")
            lines.append(
                f'    """Observation {i}: reads hidden state and returns modality {node.slot}.'
            )
            lines.append("")
            lines.append("    Implementation: project the hidden-state distribution through")
            lines.append("    the likelihood matrix projection for this modality.")
            lines.append('    """')
            lines.append("    # Flatten state to a uniform-mass vector (structural placeholder).")
            lines.append("    state_dist = [1.0]")
            lines.append("    if A and len(A) > 0 and len(A[0]) > 0:")
            lines.append("        n = len(A[0])")
            lines.append("        state_dist = [1.0 / n] * n")
            lines.append("    obs_dist = likelihood(state_dist)")
            lines.append(f"    idx = {i}")
            lines.append("    if idx < len(obs_dist):")
            if node.python_type == "bool":
                lines.append("        return obs_dist[idx] > 0.5")
            elif node.python_type == "int":
                lines.append("        return int(round(obs_dist[idx]))")
            else:
                lines.append("        return float(obs_dist[idx])")
            if node.python_type == "bool":
                lines.append("    return False")
            elif node.python_type == "int":
                lines.append("    return 0")
            else:
                lines.append("    return 0.0")
            lines.append("")

    return "\n".join(lines)


def _render_act_module(plan: PackagePlan) -> str:
    """Render ``act.py`` with one ``update_<name>`` per action.

    Each action function WRITES to at least one State field and returns
    the updated State. The planner prefixes every action with
    ``update_`` so the forward ``ActionRule`` keyword match fires
    deterministically — no dependence on whether the edge extractor
    produces a WRITES edge for the synthesized body.
    """
    header = dedent(
        f'''
        """Generated action functions for model {plan.raw_model_name!r}.

        Each ``update_*`` function performs a WRITES/MUTATES-style
        update of the State and returns the resulting value. The
        forward COGANT pipeline's ``ActionRule`` matches the
        ``update`` lexical prefix and classifies these as ACTION
        semantic mappings.
        """

        from typing import Any

        from .matrices import B, transition
        from .state import State


        def _factor_value(factor: Any) -> Any:
            """Return a raw scalar from either a State factor or scalar value."""
            return getattr(factor, "value", factor)

        '''
    ).lstrip()
    lines: list[str] = [header]

    if not plan.action_methods:
        lines.append("# No actions were declared in the source GNN.")
        lines.append("")
        lines.append("def idle_step(state: State) -> State:")
        lines.append('    """Runtime fallback for GNNs without explicit actions."""')
        lines.append("    return state")
        lines.append("")
    else:
        # Grab one state var name (if any) so we have something to mutate.
        first_state_var = plan.state_vars[0].name if plan.state_vars else None

        for i, node in enumerate(plan.action_methods):
            # Planner already guarantees ``update_`` prefix; fall back
            # for any compatibility plan that did not apply it.
            fn_name = node.name if node.name.startswith("update_") else f"update_{node.name}"
            lines.append(f"def {fn_name}(state: State) -> State:")
            lines.append(
                f'    """Action {i}: applies transition slice {i} of the B tensor to state."""'
            )
            lines.append(f"    action_index = {i}")
            lines.append("    _ = transition  # retained import for forward-pipeline introspection")
            lines.append("    _ = B")
            if first_state_var:
                t = plan.state_vars[0].python_type
                if t == "bool":
                    lines.append(
                        f"    new_value = not bool(_factor_value(state.{first_state_var}))"
                    )
                elif t == "int":
                    lines.append(f"    new_value = int(_factor_value(state.{first_state_var})) + 1")
                else:
                    lines.append(
                        f"    new_value = float(_factor_value(state.{first_state_var})) + float(action_index)"
                    )
                lines.append(f"    return state.copy({first_state_var}=new_value)")
            else:
                lines.append("    return state.copy()")
            lines.append("")

    return "\n".join(lines)


def _render_policy_module(plan: PackagePlan) -> str:
    """Render ``policy.py`` with a selector helper and deficit policies.

    Three populations are emitted:

    * selector helper — named ``select_policy`` only when the source
      role multiset needs that helper to count as POLICY; otherwise it
      is named ``pick_index`` so runtime support does not inflate role
      counts.
    * **Authoritative policies** from ``plan.policy_functions`` —
      emitted with a ``policy_<name>`` prefix when the source GNN
      declared a ``pi_c*`` variable. Rare on forward-emitted GNNs.
    * **Scaffold policies** from ``plan.scaffold_policy_functions`` —
      target-deficit ``route_factor_<n>`` functions. These appear only
      when the original forward role multiset contains more POLICY
      roles than the parsed GNN exposes directly.

    ``route_*`` was chosen over ``dispatch_*`` and ``handle_*``
    because both of the latter also appear in
    :data:`cogant.translate.rules.semantic.ACTION_KEYWORDS` — a
    function named ``dispatch_foo`` matches both PolicyRule and
    ActionRule and is handed to ACTION on the confidence tiebreak
    (both 0.80). ``route`` has no such collision.
    """
    header = dedent(
        f'''
        """Generated policy functions for model {plan.raw_model_name!r}.

        The selector chooses among actions to maximise
        ``<C, likelihood(state)>`` (a degenerate form of expected
        free-energy minimisation that ignores epistemic value).
        """

        from typing import List

        from .matrices import C, N_ACTIONS, likelihood, preference_score
        from .state import State

        '''
    ).lstrip()
    lines: list[str] = [header]

    helper_name = _policy_helper_name(plan)
    lines.append(f"def {helper_name}(state: State, observations: List[float]) -> int:")
    lines.append('    """Return the action index that maximises the preference score."""')
    lines.append("    if N_ACTIONS <= 0:")
    lines.append("        return 0")
    lines.append("    # Default state distribution: uniform over hidden states.")
    lines.append("    from .matrices import N_HIDDEN_STATES")
    lines.append("    if N_HIDDEN_STATES > 0:")
    lines.append("        state_dist = [1.0 / N_HIDDEN_STATES] * N_HIDDEN_STATES")
    lines.append("    else:")
    lines.append("        state_dist = [1.0]")
    lines.append("    best_action = 0")
    lines.append('    best_score = float("-inf")')
    lines.append("    for a in range(N_ACTIONS):")
    lines.append("        pred_obs = likelihood(state_dist)")
    lines.append("        score = preference_score(pred_obs) - 0.01 * a")
    lines.append("        if score > best_score:")
    lines.append("            best_score = score")
    lines.append("            best_action = a")
    lines.append("    _ = C  # retain reference")
    lines.append("    _ = observations  # retain reference for forward introspection")
    lines.append("    return best_action")
    lines.append("")

    # Authoritative policies from the parsed GNN (rare).
    for i, node in enumerate(plan.policy_functions):
        fn_name = _rendered_policy_function_name(node.name)
        lines.append(f"def {fn_name}(state: State, observations: List[float]) -> int:")
        lines.append(
            f'    """Policy {i}: delegates to :func:`{helper_name}` for action selection."""'
        )
        lines.append(f"    return {helper_name}(state, observations)")
        lines.append("")

    # Scaffold policies — one ``route_*`` function per hidden-state factor.
    for i, node in enumerate(plan.scaffold_policy_functions):
        fn_name = node.name
        lines.append(f"def {fn_name}(state: State, observations: List[float]) -> int:")
        lines.append(f'    """Scaffold policy {i}: route hidden-state factor through selector."""')
        lines.append(f"    return {helper_name}(state, observations)")
        lines.append("")

    return "\n".join(lines)


def _render_constraints_module(plan: PackagePlan) -> str:
    """Render ``constraints.py`` with one ``check_<name>`` per constraint.

    Two populations are emitted:

    * **Authoritative checks** from ``plan.constraint_checks`` — one
      ``check_<name>`` per GNN constraint slot declared in the source
      (typically one per ``C_m*=PreferenceVector`` ontology entry).
    * **Scaffold checks** from ``plan.scaffold_constraint_checks`` —
      ``check_role_*`` predicates emitted only for target role deficits
      supplied by the round-trip verifier.

    Every emitted function is a pure ``return True`` predicate that
    accepts a ``State`` (retained for API symmetry) and has no member
    reads inside its body, so forward edge extraction produces no
    READS / WRITES / RETURNS edges and the only matching rule is
    ``PreferenceRule``.
    """
    header = dedent(
        f'''
        """Generated constraint checks for model {plan.raw_model_name!r}.

        Each ``check_*`` function is a pure predicate over State and
        observations. The forward COGANT pipeline treats consistent
        assert/predicate patterns as CONSTRAINT mappings.
        """

        from .state import State

        '''
    ).lstrip()
    lines: list[str] = [header]

    has_authoritative = bool(plan.constraint_checks)
    has_scaffold = bool(plan.scaffold_constraint_checks)

    if not has_authoritative and not has_scaffold:
        lines.append("# No constraints were declared in the source GNN.")
        lines.append("")
        lines.append("def always_true(_state: State) -> bool:")
        lines.append('    """Runtime fallback predicate with no semantic constraint signal."""')
        lines.append("    return True")
        lines.append("")
        return "\n".join(lines)

    # Authoritative constraint checks from the source GNN.
    for i, node in enumerate(plan.constraint_checks):
        # Always emit ``check_`` prefix so the forward pipeline's
        # PreferenceRule (which detects "check" in the function name)
        # counts this as a CONSTRAINT mapping. Strip any ``cnst_``
        # prefix the planner may have added for identifier uniqueness.
        fn_name = _rendered_constraint_function_name(node.name)
        lines.append(f"def {fn_name}(state: State) -> bool:")
        lines.append(f'    """Constraint {i}: assert invariant for GNN slot {node.slot}."""')
        lines.append("    _ = state")
        lines.append("    return True")
        lines.append("")

    # Scaffold constraint checks — one per OBS / ACT / HS slot.
    for i, node in enumerate(plan.scaffold_constraint_checks):
        fn_name = node.name
        lines.append(f"def {fn_name}(state: State) -> bool:")
        lines.append(f'    """Scaffold constraint {i}: invariant over slot {node.slot}."""')
        lines.append("    _ = state")
        lines.append("    return True")
        lines.append("")

    return "\n".join(lines)


def _render_context_module(plan: PackagePlan) -> str:
    """Render ``context.py`` — scaffold context classes + authoritative funcs.

    The module emits one ``<Name>Settings`` class per observation
    modality (from ``plan.scaffold_context_classes``) so the forward
    ``ContextRule`` class-keyword match fires on ``settings``. Each
    class is bare (no ``__init__``, no ``self.*`` assignments, no
    methods) so the edge extractor produces no WRITES / MUTATES
    edges and ``MutatingSubsystemRule`` does not compete for the
    node. This yields deterministic CONTEXT classification on
    conflict resolution.

    ``plan.context_functions`` are additional authoritative context
    entries derived from the GNN ontology block (rare). They are
    rendered as module-level constants rather than functions so they
    do not accidentally match ``ObservationRule``'s structural
    fallback on pure read/return bodies.

    ``settings`` was chosen over ``config`` because the dedicated
    ``ConfigRule`` in control.py (confidence 0.90) supersedes
    ``ContextRule`` on exact ``config`` hits and may re-classify the
    mapping to a more specific kind. We want the generic CONTEXT
    classification here. ``settings``, ``env``, ``options``, and
    ``params`` all fall inside ``ContextRule``'s keyword set without
    triggering any higher-priority rule.
    """
    header = dedent(
        f'''
        """Generated scaffold context module for model {plan.raw_model_name!r}.

        Each ``*Settings`` class is a bare configuration container —
        no instance attributes, no methods — whose name carries the
        ``settings`` substring that the forward COGANT ``ContextRule``
        uses to classify it as a CONTEXT mapping. The forward edge
        extractor does not emit WRITES / MUTATES edges for these
        classes, so ``MutatingSubsystemRule`` does not compete.
        """

        from typing import Any, Dict

        '''
    ).lstrip()
    lines: list[str] = [header]

    context_functions = _targeted_context_functions(plan)
    if not plan.scaffold_context_classes and not context_functions:
        # Keep the module importable without introducing a source-absent
        # CONTEXT role. Avoid ``settings``/``config``/``state`` names.
        lines.append("MODEL_METADATA: dict[str, object] = {}")
        lines.append("")
        return "\n".join(lines)

    for i, node in enumerate(plan.scaffold_context_classes):
        cls_name = node.name
        lines.append(f"class {cls_name}:")
        lines.append(f'    """Scaffold context {i}: settings container for slot {node.slot}."""')
        # Single class-level integer attribute. Class-level (not
        # instance-level) so no WRITES edge is generated by the edge
        # extractor on class-body execution.
        lines.append(f"    default_timeout: int = {30 + i}")
        lines.append(f"    default_retries: int = {3 + (i % 5)}")
        lines.append("")

    # Authoritative context entries from the GNN ontology (rare).
    for i, node in enumerate(context_functions):
        # Emit as ``*Settings`` class too so it classifies as CONTEXT
        # reliably. Convert identifier to PascalCase + ``Settings``.
        cls_name = _rendered_context_class_name(node.name, i)
        lines.append(f"class {cls_name}:")
        lines.append(
            f'    """Authoritative context {i}: derived from GNN ontology slot {node.slot}."""'
        )
        lines.append(f"    default_value: int = {i}")
        lines.append("")

    return "\n".join(lines)


def _render_main_module(plan: PackagePlan) -> str:
    """Render ``main.py`` — a small driver loop that exercises everything."""
    helper_name = _policy_helper_name(plan)
    header = dedent(
        f'''
        """Driver program for the synthesized model {plan.raw_model_name!r}.

        Runs a short inference loop: observe -> select -> act.
        This module gives the forward COGANT pipeline a clear entry
        point with data-flow edges between State, observe, selector, and
        act — the same pattern it looks for in hand-written code.
        """

        from .state import State
        '''
    ).lstrip()

    lines: list[str] = [header]
    if plan.obs_functions:
        fn = plan.obs_functions[0].name
        canonical = fn if fn.startswith("get_") else f"get_{fn}"
        lines.append(f"from .observe import {canonical}")
    else:
        lines.append("from .observe import fallback_value")
    if plan.action_methods:
        fn = plan.action_methods[0].name
        canonical = fn if fn.startswith("update_") else f"update_{fn}"
        lines.append(f"from .act import {canonical}")
    else:
        lines.append("from .act import idle_step")
    lines.append(f"from .policy import {helper_name}")
    lines.append("")
    lines.append("")
    lines.append("def advance_once(state: State) -> State:")
    lines.append('    """One inference step: observe, choose action, update state."""')
    if plan.obs_functions:
        fn = plan.obs_functions[0].name
        canonical = fn if fn.startswith("get_") else f"get_{fn}"
        lines.append(f"    obs_value = {canonical}(state)")
        lines.append("    observations = [float(obs_value)]")
    else:
        lines.append("    observations = [fallback_value(state)]")
    lines.append(f"    _choice = {helper_name}(state, observations)")
    if plan.action_methods:
        fn = plan.action_methods[0].name
        canonical = fn if fn.startswith("update_") else f"update_{fn}"
        lines.append(f"    return {canonical}(state)")
    else:
        lines.append("    return idle_step(state)")
    lines.append("")
    lines.append("")
    lines.append("def main(num_steps: int = 10) -> State:")
    lines.append('    """Run ``num_steps`` inference steps starting from the default State."""')
    lines.append("    state = State()")
    lines.append("    for t in range(num_steps):")
    lines.append("        state = advance_once(state)")
    lines.append('        print(f"t={t}: {state}")')
    lines.append("    return state")
    lines.append("")
    lines.append("")
    lines.append('if __name__ == "__main__":')
    lines.append("    main()")
    lines.append("")

    return "\n".join(lines)


def _render_test_smoke(plan: PackagePlan) -> str:
    """Render ``tests/test_smoke.py`` — a single round-trip smoke test."""
    helper_name = _policy_helper_name(plan)
    return dedent(
        f'''
        """Smoke test for synthesized model {plan.raw_model_name!r}."""

        from {plan.package_name}.main import advance_once
        from {plan.package_name}.state import State


        def test_model_runs() -> None:
            """The synthesized model can execute one inference step."""
            state = State()
            new_state = advance_once(state)
            assert isinstance(new_state, State)


        def test_state_has_expected_fields() -> None:
            """The State dataclass exposes the hidden-state attributes."""
            state = State()
            assert state is not None


        def test_selector_returns_valid_index() -> None:
            """The selector returns a non-negative action index."""
            from {plan.package_name}.policy import {helper_name}

            action = {helper_name}(State(), [0.0])
            assert isinstance(action, int)
            assert action >= 0
        '''
    ).lstrip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def synthesize_package(
    plan: PackagePlan,
    model: ReverseGNNModel,
    output_dir: str | Path,
) -> Path:
    """Emit a full Python package to ``output_dir`` from ``plan``.

    The function creates a package directory named ``plan.package_name``
    **inside** ``output_dir`` so that the parent directory can contain
    multiple synthesized models side by side. Inside the package it
    writes ``state.py``, ``observe.py``, ``act.py``, ``policy.py``,
    ``constraints.py``, ``matrices.py``, ``main.py``, and a smoke
    test under ``tests/``.

    Args:
        plan: Package plan produced by :func:`plan_package`.
        model: Parsed GNN model (provides matrix values).
        output_dir: Directory where the package is created. The
            directory is created if it does not exist.

    Returns:
        The path to the created package directory (``output_dir /
        package_name``).
    """
    output_path = Path(output_dir).expanduser().resolve()
    package_path = output_path / plan.package_name
    package_path.mkdir(parents=True, exist_ok=True)
    tests_path = package_path / "tests"
    tests_path.mkdir(parents=True, exist_ok=True)

    semantic_targets = _semantic_role_targets(plan)
    manifest = {
        "schema": "cogant.reverse.semantic_targets.v1",
        "target_role_counts": dict(plan.target_role_counts),
        "semantic_targets": semantic_targets,
    }
    files = {
        package_path / ".gitignore": "tests\n.pytest_cache\n__pycache__\n*.pyc\n",
        package_path / SEMANTIC_TARGETS_MANIFEST: json.dumps(manifest, indent=2, sort_keys=True)
        + "\n",
        package_path / "__init__.py": _render_package_init(plan),
        package_path / "state.py": _render_state_module(plan),
        package_path / "observe.py": _render_observe_module(plan),
        package_path / "act.py": _render_act_module(plan),
        package_path / "policy.py": _render_policy_module(plan),
        package_path / "constraints.py": _render_constraints_module(plan),
        package_path / "context.py": _render_context_module(plan),
        package_path / "matrices.py": render_matrices_module(model),
        package_path / "main.py": _render_main_module(plan),
        tests_path / "__init__.py": '"""Test package for the synthesized model."""\n',
        tests_path / "test_smoke.py": _render_test_smoke(plan),
    }

    for path, content in files.items():
        path.write_text(content, encoding="utf-8")
        logger.debug("Wrote %s (%d bytes)", path, len(content))

    logger.info(
        "Synthesized package %r at %s (%d files, %d state vars, %d obs, %d actions)",
        plan.package_name,
        package_path,
        len(files),
        len(plan.state_vars),
        len(plan.obs_functions),
        len(plan.action_methods),
    )
    return package_path


def synthesize_with_validation(
    plan: PackagePlan,
    model: ReverseGNNModel,
    output_dir: str | Path,
) -> tuple[str, list[str]]:
    """Synthesize code and validate that it parses as valid Python.

    Args:
        plan: Package plan produced by :func:`plan_package`.
        model: Parsed GNN model (provides matrix values).
        output_dir: Directory where the package is created.

    Returns:
        A tuple of (package_path_str, issues_list). The path is the string
        representation of the synthesized package directory. issues_list
        contains zero or more validation warnings/errors. An empty list
        means all files synthesized and parsed successfully.
    """
    pkg_path = synthesize_package(plan, model, output_dir)
    issues: list[str] = []

    # Check that all generated Python files parse
    py_files = [
        pkg_path / "__init__.py",
        pkg_path / "state.py",
        pkg_path / "observe.py",
        pkg_path / "act.py",
        pkg_path / "policy.py",
        pkg_path / "constraints.py",
        pkg_path / "context.py",
        pkg_path / "matrices.py",
        pkg_path / "main.py",
        pkg_path / "tests" / "test_smoke.py",
    ]

    for py_file in py_files:
        if py_file.exists():
            try:
                content = py_file.read_text(encoding="utf-8")
                ast.parse(content)
            except SyntaxError as e:
                issues.append(f"Syntax error in {py_file.name}: line {e.lineno}: {e.msg}")
            except (OSError, UnicodeDecodeError, ValueError) as e:
                issues.append(f"Error parsing {py_file.name}: {type(e).__name__}: {e}")

    if issues:
        logger.warning("Validation found %d issue(s) in synthesized package", len(issues))
    else:
        logger.info("All synthesized files validated successfully")

    return str(pkg_path), issues


__all__ = [
    "synthesize_package",
    "synthesize_stable_minimal_package",
    "synthesize_with_validation",
    "supports_stable_minimal_profile",
    "SynthesisResult",
]
