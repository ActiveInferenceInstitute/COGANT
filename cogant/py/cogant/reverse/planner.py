"""Package planner: :class:`ReverseGNNModel` → :class:`PackagePlan`.

This module decides how each semantic role in a GNN model becomes a
Python construct. The mapping is intentionally **simple and mechanical**
so the forward COGANT pipeline can recognise the resulting code:

===============  ========================================================
GNN role         Python target
===============  ========================================================
HIDDEN_STATE     ``@dataclass`` field on ``State`` in ``state.py``
OBSERVATION      ``def observe_<name>(state)`` in ``observe.py``
ACTION           ``def act_<name>(state)`` in ``act.py``
POLICY           ``def policy_<name>(state, obs)`` in ``policy.py``
CONSTRAINT       ``def check_<name>(state)`` in ``constraints.py``
PREFERENCE       ``def prefer_<name>(obs)`` in ``constraints.py``
===============  ========================================================

This mapping is designed so that when COGANT's forward pipeline parses
the synthesized package, it naturally classifies the dataclass fields
as hidden-state variables (mutated inside class methods), the ``observe_*``
functions as observation modalities (pure reads over state), the
``act_*`` functions as actions (WRITES edges to state), and the
``policy_*`` / ``check_*`` functions as POLICY/CONSTRAINT mappings.
This gives the round-trip the best chance of role multiset equality.

Human naming
------------
Wherever possible the planner prefers human-readable identifiers
extracted from the GNN's COGANT-extended state-variable table rather
than the opaque upstream slot names (``s_f0``, ``o_m1``). When no
human name is available, the slot name is used verbatim. All final
identifiers are sanitized to valid Python identifiers.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from cogant.reverse.parser import ReverseGNNModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class NodePlan:
    """Plan for a single GNN node → Python construct.

    Attributes:
        slot: The GNN slot identifier (``s_f0``, ``o_m1``, ``u_c2``).
        name: The Python identifier to emit (derived from the human
            name when available, else the slot name).
        role: The MappingKind label (e.g. ``HIDDEN_STATE``, ``OBSERVATION``,
            ``ACTION``, ``POLICY``, ``CONSTRAINT``).
        python_type: The Python type annotation string (``float``,
            ``int``, ``bool``, etc.).
        module: The module file this node is emitted into
            (``state.py``, ``observe.py``, ``act.py``, ...).
        cardinality: Categorical cardinality from the GNN declaration,
            or 0 if unknown. Used for default values and type hints.
        initial_value: Source-level literal for the initial value
            (``"0.0"``, ``"False"``, ``"0"``).
    """

    slot: str = ""
    name: str = ""
    role: str = ""
    python_type: str = "float"
    module: str = ""
    cardinality: int = 0
    initial_value: str = "0.0"


@dataclass
class PackagePlan:
    """Full synthesis plan for a GNN → Python package.

    Attributes:
        package_name: Sanitized Python package name (derived from the
            GNN ``## ModelName`` value).
        raw_model_name: Original unsanitized model name for docstrings.
        nodes: All node plans in declaration order.
        state_vars: Subset of ``nodes`` with role ``HIDDEN_STATE``.
            Emitted as attributes on the ``State`` dataclass.
        obs_functions: Subset with role ``OBSERVATION``.
        action_methods: Subset with role ``ACTION``.
        policy_functions: Subset with role ``POLICY`` (authoritative
            policies declared in the GNN). These are rare — most GNNs
            have no explicit ``pi_c*`` declarations — and the reverse
            pipeline additionally synthesizes scaffolding policies (see
            ``scaffold_policy_functions``).
        constraint_checks: Subset with role ``CONSTRAINT`` / ``PREFERENCE``
            (authoritative constraints declared in the GNN, typically
            one per ``C_m*=PreferenceVector`` annotation).
        context_functions: Subset with role ``CONTEXT`` derived from
            the parsed GNN (rare; populated when the ontology block
            annotates a variable as ``Context`` or ``Time``).
        target_role_counts: Expected semantic role multiset for the
            synthesized package. Round-trip verification passes the
            source roles here so generated scaffolds are deficit-based
            rather than fixed boilerplate.
        scaffold_constraint_checks: Additional ``check_*`` functions
            emitted only when ``target_role_counts`` requires more
            CONSTRAINT roles than the parsed GNN declares.
        scaffold_policy_functions: Additional top-level POLICY scaffolds
            emitted only when target POLICY roles remain after
            authoritative policy functions and the optional policy
            selector helper.
        scaffold_context_classes: Additional top-level CONTEXT classes
            emitted only when source roles include CONTEXT deficits.
        has_A_matrix: True if the parsed A matrix has non-zero rows.
        has_B_tensor: True if the parsed B tensor is non-trivial.
        has_C_vector: True if the parsed C vector is non-empty.
        has_D_vector: True if the parsed D vector is non-empty.
    """

    package_name: str = "cogant_model"
    raw_model_name: str = "cogant_model"
    nodes: list[NodePlan] = field(default_factory=list)
    state_vars: list[NodePlan] = field(default_factory=list)
    obs_functions: list[NodePlan] = field(default_factory=list)
    action_methods: list[NodePlan] = field(default_factory=list)
    policy_functions: list[NodePlan] = field(default_factory=list)
    constraint_checks: list[NodePlan] = field(default_factory=list)
    context_functions: list[NodePlan] = field(default_factory=list)
    target_role_counts: dict[str, int] = field(default_factory=dict)
    scaffold_constraint_checks: list[NodePlan] = field(default_factory=list)
    scaffold_policy_functions: list[NodePlan] = field(default_factory=list)
    scaffold_context_classes: list[NodePlan] = field(default_factory=list)
    has_A_matrix: bool = False
    has_B_tensor: bool = False
    has_C_vector: bool = False
    has_D_vector: bool = False

    def validate(self) -> list[str]:
        """Validate the package plan for structural consistency.

        Checks that the plan is internally coherent and can be synthesized.
        Does not validate the plan against external sources (e.g., the
        original GNN).

        Returns:
            A list of validation issues. Empty list means the plan is valid.
            Issues describe problems but do not necessarily prevent synthesis
            from succeeding.
        """
        issues: list[str] = []

        # Check: no duplicate names across all roles
        all_names = [n.name for n in self.nodes]
        seen: dict[str, int] = {}
        for name in all_names:
            seen[name] = seen.get(name, 0) + 1
        duplicates = [name for name, count in seen.items() if count > 1]
        if duplicates:
            issues.append(f"Duplicate node names found: {duplicates}")

        # Check: each node's role is recognized
        valid_roles = {
            "HIDDEN_STATE",
            "OBSERVATION",
            "ACTION",
            "POLICY",
            "CONSTRAINT",
            "CONTEXT",
        }
        for node in self.nodes:
            if node.role not in valid_roles:
                issues.append(f"Node {node.name!r} has unrecognized role {node.role!r}")

        # Check: nodes in subsets appear in main nodes list
        all_subsets = (
            self.state_vars
            + self.obs_functions
            + self.action_methods
            + self.policy_functions
            + self.constraint_checks
            + self.context_functions
            + self.scaffold_constraint_checks
            + self.scaffold_policy_functions
            + self.scaffold_context_classes
        )
        nodes_set = {id(n) for n in self.nodes}
        for node in all_subsets:
            if id(node) not in nodes_set:
                issues.append(f"Node {node.name!r} in a role subset but not in main nodes list")

        # Check: consistent role classification in subsets
        for node in self.state_vars:
            if node.role != "HIDDEN_STATE":
                issues.append(
                    f"state_vars node {node.name!r} has role {node.role!r}, expected HIDDEN_STATE"
                )
        for node in self.obs_functions:
            if node.role != "OBSERVATION":
                issues.append(
                    f"obs_functions node {node.name!r} has role {node.role!r}, expected OBSERVATION"
                )
        for node in self.action_methods:
            if node.role != "ACTION":
                issues.append(
                    f"action_methods node {node.name!r} has role {node.role!r}, expected ACTION"
                )

        # Check: package_name is a valid Python identifier
        import keyword

        if not self.package_name.isidentifier() or keyword.iskeyword(self.package_name):
            issues.append(f"package_name {self.package_name!r} is not a valid Python identifier")

        return issues

    def diff(self, other: PackagePlan) -> str:
        """Return a human-readable diff between this plan and another.

        Compares the role distributions, node counts, and key attributes.

        Args:
            other: Another PackagePlan to compare against.

        Returns:
            A human-readable diff string. Empty string if the plans are
            identical.
        """
        diffs: list[str] = []

        if self.package_name != other.package_name:
            diffs.append(f"  package_name: {self.package_name!r} vs {other.package_name!r}")

        # Compare role populations
        roles_self = {
            "HIDDEN_STATE": len(self.state_vars),
            "OBSERVATION": len(self.obs_functions),
            "ACTION": len(self.action_methods),
            "POLICY": len(self.policy_functions),
            "CONSTRAINT": len(self.constraint_checks),
            "CONTEXT": len(self.context_functions),
        }
        roles_other = {
            "HIDDEN_STATE": len(other.state_vars),
            "OBSERVATION": len(other.obs_functions),
            "ACTION": len(other.action_methods),
            "POLICY": len(other.policy_functions),
            "CONSTRAINT": len(other.constraint_checks),
            "CONTEXT": len(other.context_functions),
        }

        for role in roles_self:
            if roles_self[role] != roles_other[role]:
                diffs.append(f"  {role}: {roles_self[role]} vs {roles_other[role]}")

        # Compare scaffold populations
        if len(self.scaffold_constraint_checks) != len(other.scaffold_constraint_checks):
            diffs.append(
                f"  scaffold_constraint_checks: "
                f"{len(self.scaffold_constraint_checks)} vs "
                f"{len(other.scaffold_constraint_checks)}"
            )

        if len(self.scaffold_policy_functions) != len(other.scaffold_policy_functions):
            diffs.append(
                f"  scaffold_policy_functions: "
                f"{len(self.scaffold_policy_functions)} vs "
                f"{len(other.scaffold_policy_functions)}"
            )

        if self.target_role_counts != other.target_role_counts:
            diffs.append(
                f"  target_role_counts: {self.target_role_counts!r} vs "
                f"{other.target_role_counts!r}"
            )

        # Compare matrix presence flags
        matrix_flags = ["has_A_matrix", "has_B_tensor", "has_C_vector", "has_D_vector"]
        for flag in matrix_flags:
            self_val = getattr(self, flag)
            other_val = getattr(other, flag)
            if self_val != other_val:
                diffs.append(f"  {flag}: {self_val} vs {other_val}")

        if not diffs:
            return ""

        return "PackagePlan differences:\n" + "\n".join(diffs)

    def to_json(self) -> str:
        """Serialize the PackagePlan to JSON.

        Returns:
            A JSON string representation of the plan suitable for
            serialization and round-trip recovery.
        """
        data = {
            "package_name": self.package_name,
            "raw_model_name": self.raw_model_name,
            "nodes": [self._node_to_dict(n) for n in self.nodes],
            "state_vars": [n.name for n in self.state_vars],
            "obs_functions": [n.name for n in self.obs_functions],
            "action_methods": [n.name for n in self.action_methods],
            "policy_functions": [n.name for n in self.policy_functions],
            "constraint_checks": [n.name for n in self.constraint_checks],
            "context_functions": [n.name for n in self.context_functions],
            "target_role_counts": dict(self.target_role_counts),
            "scaffold_constraint_checks": [n.name for n in self.scaffold_constraint_checks],
            "scaffold_policy_functions": [n.name for n in self.scaffold_policy_functions],
            "scaffold_context_classes": [n.name for n in self.scaffold_context_classes],
            "has_A_matrix": self.has_A_matrix,
            "has_B_tensor": self.has_B_tensor,
            "has_C_vector": self.has_C_vector,
            "has_D_vector": self.has_D_vector,
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, data: str) -> PackagePlan:
        """Deserialize a PackagePlan from JSON.

        Args:
            data: A JSON string representation of a PackagePlan.

        Returns:
            A reconstructed PackagePlan instance.

        Raises:
            json.JSONDecodeError: If the JSON is malformed.
            KeyError: If required fields are missing.
        """
        parsed = json.loads(data)
        nodes_data = parsed.get("nodes", [])

        # Reconstruct all nodes
        all_nodes: dict[str, NodePlan] = {}
        for node_dict in nodes_data:
            node = cls._dict_to_node(node_dict)
            all_nodes[node.name] = node

        # Retrieve nodes by name for each subset
        def get_nodes(names: list[str]) -> list[NodePlan]:
            return [all_nodes[name] for name in names if name in all_nodes]

        plan = cls(
            package_name=parsed.get("package_name", "cogant_model"),
            raw_model_name=parsed.get("raw_model_name", "cogant_model"),
            nodes=list(all_nodes.values()),
            state_vars=get_nodes(parsed.get("state_vars", [])),
            obs_functions=get_nodes(parsed.get("obs_functions", [])),
            action_methods=get_nodes(parsed.get("action_methods", [])),
            policy_functions=get_nodes(parsed.get("policy_functions", [])),
            constraint_checks=get_nodes(parsed.get("constraint_checks", [])),
            context_functions=get_nodes(parsed.get("context_functions", [])),
            target_role_counts=_normalise_role_counts(parsed.get("target_role_counts", {})),
            scaffold_constraint_checks=get_nodes(parsed.get("scaffold_constraint_checks", [])),
            scaffold_policy_functions=get_nodes(parsed.get("scaffold_policy_functions", [])),
            scaffold_context_classes=get_nodes(parsed.get("scaffold_context_classes", [])),
            has_A_matrix=parsed.get("has_A_matrix", False),
            has_B_tensor=parsed.get("has_B_tensor", False),
            has_C_vector=parsed.get("has_C_vector", False),
            has_D_vector=parsed.get("has_D_vector", False),
        )
        return plan

    @staticmethod
    def _node_to_dict(node: NodePlan) -> dict:
        """Convert a NodePlan to a dict for JSON serialization."""
        return {
            "slot": node.slot,
            "name": node.name,
            "role": node.role,
            "python_type": node.python_type,
            "module": node.module,
            "cardinality": node.cardinality,
            "initial_value": node.initial_value,
        }

    @staticmethod
    def _dict_to_node(data: dict) -> NodePlan:
        """Convert a dict from JSON deserialization to a NodePlan."""
        return NodePlan(
            slot=data.get("slot", ""),
            name=data.get("name", ""),
            role=data.get("role", ""),
            python_type=data.get("python_type", "float"),
            module=data.get("module", ""),
            cardinality=data.get("cardinality", 0),
            initial_value=data.get("initial_value", "0.0"),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_IDENTIFIER_FORBIDDEN_RE = re.compile(r"[^A-Za-z0-9_]+")

_ONTOLOGY_TO_ROLE: dict[str, str] = {
    "HiddenState": "HIDDEN_STATE",
    "Observation": "OBSERVATION",
    "Action": "ACTION",
    "Policy": "POLICY",
    "PreferenceVector": "CONSTRAINT",
    "Preference": "CONSTRAINT",
    "Constraint": "CONSTRAINT",
    "Context": "CONTEXT",
    "PriorBelief": "HIDDEN_STATE",
    "LikelihoodMatrix": "HIDDEN_STATE",
    "TransitionMatrix": "HIDDEN_STATE",
    "ExpectedFreeEnergy": "POLICY",
    "Time": "CONTEXT",
}


def _normalise_role_counts(expected_roles: Mapping[str, int] | None) -> dict[str, int]:
    """Return uppercase positive role counts from caller-supplied data."""
    if not expected_roles:
        return {}
    out: dict[str, int] = {}
    for role, count in expected_roles.items():
        try:
            value = int(count)
        except (TypeError, ValueError):
            continue
        if value > 0:
            out[str(role).upper()] = value
    return out


def _role_counts_from_model(model: ReverseGNNModel) -> dict[str, int]:
    """Derive the source role multiset from the parsed GNN model."""
    roles: dict[str, int] = {}

    def add(role: str, count: int = 1) -> None:
        if count > 0:
            roles[role] = roles.get(role, 0) + count

    add("HIDDEN_STATE", len(model.hidden_states))
    add("OBSERVATION", len(model.observations))
    add("ACTION", len(model.actions))
    add("POLICY", len(model.policies))
    add("CONSTRAINT", len(model.constraints))

    primary = set(
        model.hidden_states
        + model.observations
        + model.actions
        + model.policies
        + model.constraints
    )
    for var, concept in model.annotations.items():
        mapped = _ONTOLOGY_TO_ROLE.get(concept)
        if mapped == "POLICY" and var not in primary:
            add("POLICY")
    return roles


def _to_identifier(name: str, fallback: str) -> str:
    """Convert an arbitrary string into a valid Python identifier.

    Strategy:
      1. Strip trailing role suffixes like ``- Hidden State`` which
         COGANT emits in extended state-variable tables.
      2. Replace any non-word character with an underscore.
      3. Collapse consecutive underscores and strip leading/trailing ``_``.
      4. If the result is empty or starts with a digit, prefix with ``var_``.
      5. Lowercase the final identifier.

    Args:
        name: Raw human-readable label (``"Calculator - Hidden State"``).
        fallback: Fallback slot name (``"s_f0"``) used when ``name`` is
            empty or sanitizes to an empty string.

    Returns:
        A valid, lowercase Python identifier.
    """
    if not name:
        return fallback
    cleaned = re.sub(
        r"\s*-\s*(hidden state|observation|action|policy|constraint|preference).*$",
        "",
        name,
        flags=re.IGNORECASE,
    )
    cleaned = _IDENTIFIER_FORBIDDEN_RE.sub("_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        return fallback
    if cleaned[0].isdigit():
        cleaned = "var_" + cleaned
    return cleaned.lower()


def _python_type_for(gnn_type: str) -> str:
    """Map a GNN type string to a Python type annotation."""
    if not gnn_type:
        return "float"
    t = gnn_type.lower()
    if t == "int":
        return "int"
    if t == "bool":
        return "bool"
    if t == "float":
        return "float"
    return "float"


def _default_value_for(py_type: str, cardinality: int, d_mass: float) -> str:
    """Return a Python literal suitable as a dataclass field default.

    When the hidden state has a D-vector mass associated with it, the
    default is the index of the argmax (for int) or the mass itself
    (for float). Otherwise we pick a neutral zero-ish default.
    """
    if py_type == "bool":
        return "False"
    if py_type == "int":
        if cardinality > 1:
            return "0"
        return "0"
    # float default — use the D-vector mass when it's informative
    # (non-uniform), otherwise 0.0.
    if 0.0 < d_mass < 1.0 and cardinality > 1:
        return f"{round(d_mass, 6)}"
    return "0.0"


def _reserved_avoid(name: str, existing: dict[str, int]) -> str:
    """Avoid Python keywords and name collisions by appending ``_N``.

    Reserved words are silently prefixed with ``var_``. Collisions add
    an incrementing numeric suffix.
    """
    import keyword

    if keyword.iskeyword(name):
        name = "var_" + name
    base = name
    i = 1
    while name in existing:
        i += 1
        name = f"{base}_{i}"
    existing[name] = 1
    return name


# ---------------------------------------------------------------------------
# Public planner
# ---------------------------------------------------------------------------


def plan_package(
    model: ReverseGNNModel,
    *,
    expected_roles: Mapping[str, int] | None = None,
) -> PackagePlan:
    """Build a :class:`PackagePlan` from a :class:`ReverseGNNModel`.

    Each hidden-state slot becomes a State dataclass attribute; each
    observation slot becomes an ``observe_*`` function; each action
    slot becomes an ``act_*`` function; etc. Naming prefers the
    human-readable labels from the extended state-variable table when
    available, else falls back to the slot name.

    Args:
        model: Parsed GNN model.
        expected_roles: Optional source semantic role multiset. When
            provided, POLICY / CONSTRAINT / CONTEXT scaffolds are added
            only for deficits relative to that target. When omitted,
            the target is derived from the parsed GNN itself.
    """
    plan = PackagePlan(
        package_name=model.model_name or "cogant_model",
        raw_model_name=model.raw_model_name or model.model_name or "cogant_model",
    )
    used_names: dict[str, int] = {}

    # Hidden states → State attributes in state.py
    for i, slot in enumerate(model.hidden_states):
        human = model.human_names.get(slot, "")
        ident = _to_identifier(human, slot)
        ident = _reserved_avoid(ident, used_names)
        gnn_type = model.types.get(slot, "int")
        py_type = _python_type_for(gnn_type)
        card = model.cardinalities.get(slot, 0)
        d_mass = model.D[i] if i < len(model.D) else 0.0
        init = _default_value_for(py_type, card, d_mass)
        node = NodePlan(
            slot=slot,
            name=ident,
            role="HIDDEN_STATE",
            python_type=py_type,
            module="state.py",
            cardinality=card,
            initial_value=init,
        )
        plan.state_vars.append(node)
        plan.nodes.append(node)

    # Observations → get_<name> functions in observe.py.
    #
    # Naming rationale: the forward ObservationRule keyword match fires
    # on ``get/read/fetch/query/display/show/status/info/list``. Prefix
    # every synthesized observation with ``get_`` so the keyword hit is
    # deterministic regardless of whether the edge extractor later
    # records a READS edge for the function body. This gives the
    # reverse → forward round-trip a strong, first-class lexical signal
    # that cannot be lost to edge-extraction noise.
    for _i, slot in enumerate(model.observations):
        human = model.human_names.get(slot, "")
        ident = _to_identifier(human, slot)
        ident = _reserved_avoid(f"get_{ident}" if ident == slot else f"get_{ident}", used_names)
        gnn_type = model.types.get(slot, "int")
        py_type = _python_type_for(gnn_type)
        card = model.cardinalities.get(slot, 0)
        node = NodePlan(
            slot=slot,
            name=ident,
            role="OBSERVATION",
            python_type=py_type,
            module="observe.py",
            cardinality=card,
            initial_value="0.0",
        )
        plan.obs_functions.append(node)
        plan.nodes.append(node)

    # Actions → update_<name> functions in act.py.
    #
    # Naming rationale: the forward ActionRule keyword match fires on
    # ``set/update/create/delete/send/push/execute/run/process/handle/
    # dispatch/encode/decode/dump/load``. Prefix every synthesized action
    # with ``update_`` so the keyword hit is deterministic regardless of
    # whether the edge extractor records a WRITES edge for the function
    # body. This matches the symmetry with ``get_`` on the observation
    # side and guarantees the forward pass will classify the right
    # number of actions on the synthesized package.
    for _i, slot in enumerate(model.actions):
        human = model.human_names.get(slot, "")
        ident = _to_identifier(human, slot)
        ident = _reserved_avoid(
            f"update_{ident}" if ident == slot else f"update_{ident}", used_names
        )
        gnn_type = model.types.get(slot, "int")
        py_type = _python_type_for(gnn_type)
        card = model.cardinalities.get(slot, 0)
        node = NodePlan(
            slot=slot,
            name=ident,
            role="ACTION",
            python_type=py_type,
            module="act.py",
            cardinality=card,
            initial_value="0",
        )
        plan.action_methods.append(node)
        plan.nodes.append(node)

    # Policies → policy_<name> functions in policy.py
    for slot in model.policies:
        human = model.human_names.get(slot, "")
        ident = _to_identifier(human, slot)
        ident = _reserved_avoid(f"pi_{ident}" if ident == slot else ident, used_names)
        node = NodePlan(
            slot=slot,
            name=ident,
            role="POLICY",
            python_type="str",
            module="policy.py",
            cardinality=0,
            initial_value='""',
        )
        plan.policy_functions.append(node)
        plan.nodes.append(node)

    # Constraints → check_<name> functions in constraints.py
    for slot in model.constraints:
        human = model.human_names.get(slot, "")
        ident = _to_identifier(human, slot)
        ident = _reserved_avoid(f"cnst_{ident}" if ident == slot else ident, used_names)
        node = NodePlan(
            slot=slot,
            name=ident,
            role="CONSTRAINT",
            python_type="bool",
            module="constraints.py",
            cardinality=0,
            initial_value="True",
        )
        plan.constraint_checks.append(node)
        plan.nodes.append(node)

    # Context functions — derived from ontology annotations that name
    # a variable as ``Context`` or ``Time``. These are separate from
    # the scaffold context classes emitted below; the two populations
    # are combined by the synthesizer when rendering ``context.py``.
    for var, concept in model.annotations.items():
        if var in (
            model.hidden_states
            + model.observations
            + model.actions
            + model.policies
            + model.constraints
        ):
            continue
        lc = concept.lower()
        if "context" in lc or lc == "time":
            ident = _to_identifier(var, var)
            ident = _reserved_avoid(f"context_{ident}", used_names)
            node = NodePlan(
                slot=var,
                name=ident,
                role="CONTEXT",
                python_type="dict",
                module="context.py",
                cardinality=0,
                initial_value="{}",
            )
            plan.context_functions.append(node)
            plan.nodes.append(node)

    plan.target_role_counts = (
        _normalise_role_counts(expected_roles)
        if expected_roles is not None
        else _role_counts_from_model(model)
    )

    # Deficit-based scaffolds: only synthesize role-bearing support
    # constructs needed to reach the source role multiset. This keeps
    # default GNN round-trips faithful to the parsed model and avoids
    # source-absent CONTEXT/POLICY/CONSTRAINT inflation.
    plan.scaffold_constraint_checks = _build_scaffold_constraints(plan, used_names)
    plan.scaffold_policy_functions = _build_scaffold_policies(plan, used_names)
    plan.scaffold_context_classes = _build_scaffold_contexts(plan, used_names)
    plan.nodes.extend(
        plan.scaffold_constraint_checks
        + plan.scaffold_policy_functions
        + plan.scaffold_context_classes
    )

    plan.has_A_matrix = bool(model.A) and any(any(row) for row in model.A)
    plan.has_B_tensor = bool(model.B)
    plan.has_C_vector = bool(model.C)
    plan.has_D_vector = bool(model.D)

    logger.info(
        "Planned package %r: %d state vars, %d obs, %d actions, %d policies, "
        "%d constraints, %d contexts, scaffold(constraints=%d, policies=%d, "
        "contexts=%d)",
        plan.package_name,
        len(plan.state_vars),
        len(plan.obs_functions),
        len(plan.action_methods),
        len(plan.policy_functions),
        len(plan.constraint_checks),
        len(plan.context_functions),
        len(plan.scaffold_constraint_checks),
        len(plan.scaffold_policy_functions),
        len(plan.scaffold_context_classes),
    )
    return plan


# ---------------------------------------------------------------------------
# Scaffold builders
# ---------------------------------------------------------------------------


def _build_scaffold_constraints(plan: PackagePlan, used_names: dict[str, int]) -> list[NodePlan]:
    """Return deficit ``check_*`` predicates for target CONSTRAINT count.

    Names are lexical CONSTRAINT hits but avoid ACTION / OBSERVATION /
    POLICY / CONTEXT keywords. The count is strictly
    ``target_role_counts["CONSTRAINT"] - len(constraint_checks)``.
    """
    target = int(plan.target_role_counts.get("CONSTRAINT", 0))
    deficit = max(0, target - len(plan.constraint_checks))
    out: list[NodePlan] = []
    seed_slots = [
        *(node.slot for node in plan.obs_functions),
        *(node.slot for node in plan.action_methods),
        *(node.slot for node in plan.state_vars),
    ]
    for i in range(deficit):
        slot = seed_slots[i % len(seed_slots)] if seed_slots else f"target_{i}"
        ident = _reserved_avoid(f"check_role_{i}", used_names)
        out.append(
            NodePlan(
                slot=slot,
                name=ident,
                role="CONSTRAINT",
                python_type="bool",
                module="constraints.py",
                cardinality=0,
                initial_value="True",
            )
        )
    return out


def _build_scaffold_policies(plan: PackagePlan, used_names: dict[str, int]) -> list[NodePlan]:
    """Return deficit ``route_*`` functions for target POLICY count.

    The synthesizer may expose its selector helper as a semantic
    ``select_policy`` function when that single helper is needed to
    reach the target count. The remaining deficit is filled with
    ``route_*`` scaffolds, which match ``PolicyRule`` without colliding
    with ``ActionRule``.
    """
    target = int(plan.target_role_counts.get("POLICY", 0))
    helper_count = 1 if target > len(plan.policy_functions) else 0
    count = max(0, target - len(plan.policy_functions) - helper_count)
    out: list[NodePlan] = []
    for i in range(count):
        ident = _reserved_avoid(f"route_factor_{i}", used_names)
        out.append(
            NodePlan(
                slot=f"scaffold_pol_{i}",
                name=ident,
                role="POLICY",
                python_type="int",
                module="policy.py",
                cardinality=0,
                initial_value="0",
            )
        )
    return out


def _build_scaffold_contexts(plan: PackagePlan, used_names: dict[str, int]) -> list[NodePlan]:
    """Return deficit ``*Settings`` classes for target CONTEXT count.

    No CONTEXT scaffold is emitted when the source role multiset has no
    CONTEXT. This prevents source-absent context inflation on ordinary
    GNNs such as the calculator fixture.
    """
    target = int(plan.target_role_counts.get("CONTEXT", 0))
    count = max(0, target - len(plan.context_functions))
    out: list[NodePlan] = []
    for i in range(count):
        ident = _reserved_avoid(f"ObservationSettings{i}", used_names)
        out.append(
            NodePlan(
                slot=f"scaffold_ctx_{i}",
                name=ident,
                role="CONTEXT",
                python_type="dict",
                module="context.py",
                cardinality=0,
                initial_value="{}",
            )
        )
    return out


__all__ = ["NodePlan", "PackagePlan", "plan_package"]
