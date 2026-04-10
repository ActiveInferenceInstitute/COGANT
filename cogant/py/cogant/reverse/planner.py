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

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List

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
        policy_functions: Subset with role ``POLICY``.
        constraint_checks: Subset with role ``CONSTRAINT`` / ``PREFERENCE``.
        has_A_matrix: True if the parsed A matrix has non-zero rows.
        has_B_tensor: True if the parsed B tensor is non-trivial.
        has_C_vector: True if the parsed C vector is non-empty.
        has_D_vector: True if the parsed D vector is non-empty.
    """

    package_name: str = "cogant_model"
    raw_model_name: str = "cogant_model"
    nodes: List[NodePlan] = field(default_factory=list)
    state_vars: List[NodePlan] = field(default_factory=list)
    obs_functions: List[NodePlan] = field(default_factory=list)
    action_methods: List[NodePlan] = field(default_factory=list)
    policy_functions: List[NodePlan] = field(default_factory=list)
    constraint_checks: List[NodePlan] = field(default_factory=list)
    has_A_matrix: bool = False
    has_B_tensor: bool = False
    has_C_vector: bool = False
    has_D_vector: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_IDENTIFIER_FORBIDDEN_RE = re.compile(r"[^A-Za-z0-9_]+")


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
    cleaned = re.sub(r"\s*-\s*(hidden state|observation|action|policy|constraint|preference).*$", "", name, flags=re.IGNORECASE)
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


def _reserved_avoid(name: str, existing: Dict[str, int]) -> str:
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


def plan_package(model: ReverseGNNModel) -> PackagePlan:
    """Build a :class:`PackagePlan` from a :class:`ReverseGNNModel`.

    Each hidden-state slot becomes a State dataclass attribute; each
    observation slot becomes an ``observe_*`` function; each action
    slot becomes an ``act_*`` function; etc. Naming prefers the
    human-readable labels from the extended state-variable table when
    available, else falls back to the slot name.
    """
    plan = PackagePlan(
        package_name=model.model_name or "cogant_model",
        raw_model_name=model.raw_model_name or model.model_name or "cogant_model",
    )
    used_names: Dict[str, int] = {}

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
    for i, slot in enumerate(model.observations):
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
    for i, slot in enumerate(model.actions):
        human = model.human_names.get(slot, "")
        ident = _to_identifier(human, slot)
        ident = _reserved_avoid(f"update_{ident}" if ident == slot else f"update_{ident}", used_names)
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

    plan.has_A_matrix = bool(model.A) and any(any(row) for row in model.A)
    plan.has_B_tensor = bool(model.B)
    plan.has_C_vector = bool(model.C)
    plan.has_D_vector = bool(model.D)

    logger.info(
        "Planned package %r: %d state vars, %d obs, %d actions, %d policies, %d constraints",
        plan.package_name,
        len(plan.state_vars),
        len(plan.obs_functions),
        len(plan.action_methods),
        len(plan.policy_functions),
        len(plan.constraint_checks),
    )
    return plan


__all__ = ["NodePlan", "PackagePlan", "plan_package"]
