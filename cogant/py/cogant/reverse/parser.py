"""GNN markdown → :class:`ReverseGNNModel` parser.

This module is the inverse of :mod:`cogant.gnn.formatter`. It reads a
GNN v2.0.0.x markdown file (including the v2.0.0.0-engine bundle emitted by
current COGANT) and extracts the structured content required to synthesize a
Python package: the state space, observation modalities, actions,
policies, constraints, ontology annotations, and A/B/C/D matrices.

The parser is deliberately **tolerant**: it accepts both current bare upstream
connection syntax (``D_f0>s_f0``) and compatibility parenthesised examples
(``(D_f0) > (s_f0)``), both bracketed matrix blocks
(``A[[rows=3][cols=2]]``) and InitialParameterization tuple blocks
(``D_f0={ (0.3, 0.3, 0.4) }``), and any mix of COGANT's extended
sections alongside the upstream header. Sections the parser does not
recognise are ignored rather than causing an error, so the parser
tolerates future COGANT extensions.

The parser does **not** consult the ProgramGraph; it relies entirely on
the markdown text. This keeps the reverse pipeline standalone — a GNN
file alone is sufficient to produce a ReverseGNNModel.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

logger = logging.getLogger(__name__)


class ReverseModelError(ValueError):
    """Raised when a parsed model cannot provide executable semantics."""

    code = "INVALID_REVERSE_MODEL"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ReverseGNNModel:
    """Parsed GNN model ready for planning and synthesis.

    Attributes:
        model_name: The ``## ModelName`` value (sanitized upstream
            identifier, safe for use as a Python package name).
        raw_model_name: The unsanitized ``## ModelName`` value as it
            appears in the markdown (may contain non-identifier chars).
        hidden_states: Names of hidden-state factors (``s_f0``, ``s_f1``,
            ...). Each entry is the upstream variable name.
        observations: Names of observation modalities
            (``o_m0``, ``o_m1``, ...).
        actions: Names of action/control factors (``u_c0``, ``u_c1``, ...).
        policies: Names of policy variables (rare; usually empty).
        constraints: Names of constraint/preference variables.
        annotations: Map from variable name → ontology concept
            (``"s_f0" -> "HiddenState"``, ``"A_m0" -> "LikelihoodMatrix"``,
            etc). Populated from ``## ActInfOntologyAnnotation`` and the
            extended ``## State Space`` section.
        cardinalities: Map from variable name → categorical dimension
            (from ``## StateSpaceBlock`` like ``s_f0[10,1,type=int]``).
        types: Map from variable name → upstream type string
            (``int``, ``float``, ``bool``).
        A: Likelihood matrix ``P(o | s)`` of shape ``[n_obs x n_states]``.
            Populated from ``## InitialParameterization`` or from the
            bracket-style ``A`` matrix header in the GNN file if present.
            May be empty when the model has no observations.
        B: Transition tensor ``P(s' | s, a)`` of shape
            ``[n_states x n_states x n_actions]``. May be empty.
        C: Log-preference vector over observations of shape ``[n_obs]``.
        D: Prior distribution over hidden states of shape ``[n_states]``.
        connections: Raw list of arrow-syntax connection strings from
            ``## Connections`` (used for debugging and topology checks).
        human_names: Map from ``s_f0``-style slot to the human-readable
            name pulled from ``## State Space`` → ``### State Variables``.
            Used by the planner to produce meaningful Python identifiers.
    """

    model_name: str = "cogant_model"
    raw_model_name: str = "cogant_model"
    hidden_states: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    policies: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    annotations: dict[str, str] = field(default_factory=dict)
    cardinalities: dict[str, int] = field(default_factory=dict)
    types: dict[str, str] = field(default_factory=dict)
    A: list[list[float]] = field(default_factory=list)
    B: list[list[list[float]]] = field(default_factory=list)
    C: list[float] = field(default_factory=list)
    D: list[float] = field(default_factory=list)
    connections: list[str] = field(default_factory=list)
    human_names: dict[str, str] = field(default_factory=dict)
    degraded: bool = False
    diagnostics: list[str] = field(default_factory=list)

    @property
    def n_hidden_factors(self) -> int:
        """Number of named hidden-state factors in the source ontology."""
        return len(self.hidden_states)

    @property
    def n_states(self) -> int:
        """Number of hidden dimensions represented by this model.

        Matrix dimensions are authoritative when present.  Before matrices
        are parsed, retain the declared factor count so callers can inspect
        a syntactically valid but not-yet-executable model.
        """
        if self.D:
            if len(self.D) == 1 and len(self.hidden_states) == 1:
                declared = self.cardinalities.get(self.hidden_states[0], 0)
                if declared > 1:
                    return declared
            return len(self.D)
        if self.B:
            return len(self.B)
        return len(self.hidden_states)

    @property
    def n_obs(self) -> int:
        """Number of observation dimensions represented by this model."""
        if self.C:
            return len(self.C)
        if self.A:
            return len(self.A)
        return len(self.observations)

    @property
    def n_actions(self) -> int:
        """Number of action dimensions represented by this model."""
        if self.B and self.B[0] and self.B[0][0]:
            return len(self.B[0][0])
        return len(self.actions)

    def validate(self) -> list[str]:
        """Return evidence and dimension errors without inventing values."""
        errors: list[str] = []
        if self.hidden_states and not self.D:
            errors.append("D is required when hidden-state variables are declared")
        if self.observations and not self.C:
            errors.append("C is required when observation variables are declared")
        if self.actions and not self.B:
            errors.append("B is required when action variables are declared")
        if self.D and any(value < 0 for value in self.D):
            errors.append("D contains a negative probability")
        return errors


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------

# Matches ``## <header>`` at column 0 and captures the header text.
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

# Matches a StateSpaceBlock variable declaration like ``s_f0[10,1,type=int]``
# or ``A_m0[2,2,type=float]``. We keep the match deliberately permissive so
# a missing type= suffix or a trailing comment is tolerated.
_VAR_DECL_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([^\]]+?)\s*\]\s*$")

# Matches an ontology annotation like ``s_f0=HiddenState``.
_ONTOLOGY_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")

# Matches a ``D_f0={ (0.1, 0.2, 0.7) }`` style initial parameterization line.
_IPARAM_VEC_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{\s*(.+)\s*\}\s*$")

# Matches ``identity(card,card,act)`` initial parameterization shorthand.
_IPARAM_IDENTITY_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*identity\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)\s*$"
)

# Matches A/B/C/D bracketed matrix block header lines inside
# ``gnn-matrices`` fences, e.g., ``A[[rows=2][cols=3]]``.
_MATRIX_BLOCK_HEADER_RE = re.compile(
    r"^\s*([ABCD])\[\[rows=(\d+)\](?:\[cols=(\d+)\])?(?:\[depth=(\d+)\])?\]\s*$"
)

# Matches a single float number in a row line.
_FLOAT_RE = re.compile(r"[-+]?\d*\.\d+(?:[eE][-+]?\d+)?|[-+]?\d+(?:[eE][-+]?\d+)?")


def _split_sections(text: str) -> dict[str, list[str]]:
    """Split markdown into a dict of section_name → list of body occurrences.

    COGANT emits some headers (notably ``## Connections``) twice — once
    for the upstream GNN block and once for the COGANT-extended program
    graph edge dump. We return a list of bodies per header so callers
    can pick the first (upstream) or last (extended) occurrence as
    needed. The upstream GNN type-checker only honours the first
    occurrence, and so does this parser for canonical sections.
    """
    sections: dict[str, list[str]] = {}
    matches = list(_SECTION_RE.finditer(text))
    for idx, match in enumerate(matches):
        header = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip("\n")
        sections.setdefault(header, []).append(body)
    return sections


def _parse_cardinality_and_type(decl: str) -> tuple[int | None, str | None]:
    """Parse ``10,1,type=int`` style declaration into ``(10, "int")``."""
    card: int | None = None
    type_str: str | None = None
    parts = [p.strip() for p in decl.split(",")]
    for p in parts:
        if p.startswith("type="):
            type_str = p.split("=", 1)[1].strip()
        elif card is None and p.isdigit():
            card = int(p)
    return card, type_str


def _parse_tuple_vector(body: str) -> list[float]:
    """Parse a ``(0.1, 0.2, 0.7)`` tuple into a list of floats.

    Tolerates nested tuples (``((a,b),(c,d))``) by flattening, which is
    intentional: the caller for A-matrices expects a flat row-major list.
    """
    nums = _FLOAT_RE.findall(body)
    return [float(n) for n in nums]


def _parse_state_space_block(body: str, model: ReverseGNNModel) -> None:
    """Populate variable lists and cardinalities from ``## StateSpaceBlock``.

    Sorts factor-indexed variables by their numeric suffix so ``s_f10``
    follows ``s_f9`` rather than ``s_f1``.
    """
    hidden: dict[int, str] = {}
    obs: dict[int, str] = {}
    acts: dict[int, str] = {}
    constraints: dict[int, str] = {}
    policies: dict[int, str] = {}

    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _VAR_DECL_RE.match(line)
        if not match:
            continue
        name = match.group(1)
        decl = match.group(2)
        card, type_str = _parse_cardinality_and_type(decl)
        if card is not None:
            model.cardinalities[name] = card
        if type_str is not None:
            model.types[name] = type_str

        # Classify by name prefix; use the numeric suffix for stable ordering.
        suffix_match = re.match(r"([A-Za-z_]+?)(\d+)$", name)
        if suffix_match:
            prefix = suffix_match.group(1)
            idx = int(suffix_match.group(2))
        else:
            prefix = name
            idx = 0

        if prefix in ("s_f", "s"):
            hidden[idx] = name
        elif prefix in ("o_m", "o"):
            obs[idx] = name
        elif prefix in ("u_c", "u", "a_c"):
            acts[idx] = name
        elif prefix in ("pi_c", "pi", "policy_"):
            policies[idx] = name
        elif prefix in ("c_f", "constraint_"):
            constraints[idx] = name
        # A_m, B_f, C_m, D_f are matrices — we skip them here; they are
        # folded into the annotations dict if ActInfOntologyAnnotation
        # names them, and we compute values separately.

    model.hidden_states = [hidden[i] for i in sorted(hidden)]
    model.observations = [obs[i] for i in sorted(obs)]
    model.actions = [acts[i] for i in sorted(acts)]
    model.policies = [policies[i] for i in sorted(policies)]
    model.constraints = [constraints[i] for i in sorted(constraints)]

    for idx, slot in enumerate(model.hidden_states):
        if model.cardinalities.get(slot, 0) <= 0:
            for source in (f"D_f{idx}", f"B_f{idx}"):
                card = model.cardinalities.get(source)
                if card is not None and card > 0:
                    model.cardinalities[slot] = card
                    break


def _parse_ontology_annotation(body: str, model: ReverseGNNModel) -> None:
    """Populate ``model.annotations`` from ``## ActInfOntologyAnnotation``.

    Also treats explicit Policy / Constraint / Preference annotations as
    additional entries in the corresponding variable lists when the
    variable was not already classified by StateSpaceBlock.
    """
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _ONTOLOGY_RE.match(line)
        if not match:
            continue
        var_name = match.group(1)
        concept = match.group(2)
        model.annotations[var_name] = concept

        # If the ontology block introduces a variable that wasn't classified
        # by StateSpaceBlock prefix heuristics, register it by concept type.
        lc = concept.lower()
        all_classified = (
            model.hidden_states
            + model.observations
            + model.actions
            + model.policies
            + model.constraints
        )
        if "hiddenstate" in lc.replace(" ", "") or "hidden" == lc:
            if var_name not in all_classified and (
                not model.hidden_states or re.match(r"^(s_f|s)\d+$", var_name)
            ):
                model.hidden_states.append(var_name)
        elif "observation" in lc and var_name not in all_classified:
            if not model.observations or re.match(r"^(o_m|o)\d+$", var_name):
                model.observations.append(var_name)
        elif "action" in lc and var_name not in all_classified:
            if not model.actions or re.match(r"^(u_c|u|a_c)\d+$", var_name):
                model.actions.append(var_name)
        elif "policy" in lc and var_name not in model.policies:
            if var_name not in all_classified and (
                not model.policies or re.match(r"^(pi_c|pi|policy_)\d+$", var_name)
            ):
                model.policies.append(var_name)
        elif ("constraint" in lc or "preference" in lc) and var_name not in model.constraints:
            if var_name not in all_classified and (
                not model.constraints or re.match(r"^(c_f|constraint_)\d+$", var_name)
            ):
                model.constraints.append(var_name)


def _parse_initial_parameterization(body: str, model: ReverseGNNModel) -> None:
    """Populate A, B, C, D from ``## InitialParameterization``.

    Supports both the tuple-vector form (``D_f0={ (0.3, 0.3, 0.4) }``)
    and the identity shorthand (``B_f0=identity(2,2,1)``). When the
    block gives per-factor shapes for D_fN but we have multiple hidden
    states, we aggregate per-factor D values into the global D vector
    by taking the first element of each factor's distribution.
    """
    per_factor_D: dict[str, list[float]] = {}
    per_factor_C: dict[str, list[float]] = {}
    per_factor_A: dict[str, list[list[float]]] = {}
    per_factor_B: dict[str, list[list[list[float]]]] = {}

    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # identity(card,card,depth) shorthand — used for B_fN.
        id_match = _IPARAM_IDENTITY_RE.match(line)
        if id_match:
            name = id_match.group(1)
            rows = int(id_match.group(2))
            cols = int(id_match.group(3))
            depth = int(id_match.group(4))
            tensor = [
                [[1.0 if (r == c) else 0.0 for _ in range(depth)] for c in range(cols)]
                for r in range(rows)
            ]
            if name.startswith("B_"):
                per_factor_B[name] = tensor
            continue

        # ``D_f0={ ( ... ) }`` / ``A_m0={ ( (row0), (row1), ... ) }`` / ``C_m0={ ( ... ) }``
        vec_match = _IPARAM_VEC_RE.match(line)
        if vec_match:
            name = vec_match.group(1)
            inner = vec_match.group(2)
            floats = _parse_tuple_vector(inner)
            if name.startswith("D_"):
                per_factor_D[name] = floats
            elif name.startswith("C_"):
                per_factor_C[name] = floats
            elif name.startswith("A_"):
                # Attempt to reshape: count inner tuples to infer row count.
                inner_groups = re.findall(r"\(([^()]+)\)", inner)
                if inner_groups:
                    rows_list = [_parse_tuple_vector(g) for g in inner_groups]
                    per_factor_A[name] = rows_list
                else:
                    per_factor_A[name] = [floats]
            continue

    # A factorized upstream block does not always include a global A/B/C/D
    # tensor.  Preserve the historical projection as an explicitly degraded
    # compatibility representation so reverse tooling can still inspect and
    # compile legacy files.  The diagnostics are carried into generated
    # provenance by callers; this is never treated as equivalent to a global
    # matrix block.
    def declared_dimension(names: list[str]) -> int:
        """Return the Cartesian dimension when factor cardinalities exist.

        Older callers construct ``ReverseGNNModel`` with one entry per
        global state and no cardinality metadata.  In that compatibility
        shape the number of names remains the dimension.  Parsed upstream
        models, however, declare one name per factor and put the categorical
        size on that name; their executable matrix dimension is the product
        of those sizes.
        """
        cardinalities = [model.cardinalities.get(name, 0) for name in names]
        if cardinalities and all(card > 0 for card in cardinalities):
            return math.prod(cardinalities)
        return len(names)

    hidden_dimension = declared_dimension(model.hidden_states)
    observation_dimension = declared_dimension(model.observations)
    action_dimension = declared_dimension(model.actions)

    # A state-only compatibility fragment historically exposed factor-level
    # D values.  Keep that inspection shape until the rest of the executable
    # model is present; complete models take the Cartesian projection below.
    project_hidden = bool(model.observations or model.actions)

    if model.hidden_states and not model.D:
        factor_vectors = [
            per_factor_D.get(f"D_f{i}")
            or (
                [1.0 / model.cardinalities[slot]] * model.cardinalities[slot]
                if model.cardinalities.get(slot, 0) > 0
                else [1.0]
            )
            for i, slot in enumerate(model.hidden_states)
        ]
        if project_hidden and hidden_dimension != len(model.hidden_states) and all(
            len(values) == model.cardinalities.get(slot, 0)
            for values, slot in zip(factor_vectors, model.hidden_states, strict=False)
        ):
            D_vec = [
                math.prod(values[index] for values, index in zip(factor_vectors, indexes, strict=False))
                for indexes in product(*(range(len(values)) for values in factor_vectors))
            ]
        else:
            # Legacy model objects already use one name per global state.
            D_vec = [max(values) if values else 1.0 for values in factor_vectors]
        total = sum(D_vec) or 1.0
        model.D = [value / total for value in D_vec]
        if project_hidden:
            model.degraded = True
            model.diagnostics.append(
                "factorized D declarations projected to the executable Cartesian prior"
            )

    if model.observations and not model.C:
        factor_vectors = [
            per_factor_C.get(f"C_m{i}")
            or [0.0] * max(model.cardinalities.get(slot, 1), 1)
            for i, slot in enumerate(model.observations)
        ]
        if observation_dimension != len(model.observations) and all(
            len(values) == model.cardinalities.get(slot, 0)
            for values, slot in zip(factor_vectors, model.observations, strict=False)
        ):
            model.C = [
                sum(values[index] for values, index in zip(factor_vectors, indexes, strict=False))
                for indexes in product(*(range(len(values)) for values in factor_vectors))
            ]
        else:
            model.C = [(values[0] if values else 0.0) for values in factor_vectors]
        model.degraded = True
        model.diagnostics.append(
            "factorized C declarations projected to executable observation preferences"
        )

    if model.observations and model.hidden_states and not model.A:
        n_obs = observation_dimension
        n_states = hidden_dimension
        raw_rows: list[list[float]] = []
        for i in range(len(model.observations)):
            rows = per_factor_A.get(f"A_m{i}", [])
            if len(rows) == n_obs and all(len(row) == n_states for row in rows):
                raw_rows.extend([list(row) for row in rows])
            else:
                row = rows[0] if rows and len(rows[0]) == n_states else []
                raw_rows.append(list(row) if row else [1.0] * n_states)
        if n_obs != len(raw_rows):
            # A factorized source may not provide a global modality matrix.
            # Preserve a valid, explicitly degraded shape rather than
            # silently reusing one modality for every Cartesian outcome.
            raw_rows = [[1.0] * n_states for _ in range(n_obs)]
        # Normalize each projected likelihood column.  A one-modality
        # factorized declaration therefore remains a valid categorical
        # likelihood rather than leaking the source row's arbitrary scale.
        model.A = [[0.0] * n_states for _ in range(n_obs)]
        for column in range(n_states):
            total = sum(row[column] for row in raw_rows)
            if total <= 0.0:
                total = float(n_obs)
                for row_idx in range(n_obs):
                    model.A[row_idx][column] = 1.0 / total
            else:
                for row_idx in range(n_obs):
                    model.A[row_idx][column] = raw_rows[row_idx][column] / total
        model.degraded = True
        model.diagnostics.append(
            "factorized A declarations projected to executable modality/state dimensions"
        )

    if model.hidden_states and model.actions and not model.B:
        n_states = hidden_dimension
        n_actions = action_dimension
        model.B = [
            [[1.0 if row == col else 0.0 for _ in range(n_actions)] for col in range(n_states)]
            for row in range(n_states)
        ]
        model.degraded = True
        model.diagnostics.append(
            "factorized B declarations projected to executable identity transitions"
        )


def _parse_state_variables_extended(body: str, model: ReverseGNNModel) -> None:
    """Parse the ``## State Space`` → ``### State Variables`` table.

    Extracts human-readable variable names and attaches them to the
    ``human_names`` map so the planner can produce meaningful Python
    attribute names.
    """
    in_table = False
    headers: list[str] = []
    idx = 0
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("| ID ") or stripped.startswith("|ID"):
            in_table = True
            headers = [c.strip().lower() for c in stripped.strip("|").split("|")]
            continue
        if in_table and stripped.startswith("|---"):
            continue
        if in_table and stripped.startswith("|") and not stripped.startswith("| ID"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 2:
                # Cell index of 'name' column.
                try:
                    name_col = headers.index("name")
                except ValueError:
                    name_col = 1
                name = cells[name_col] if name_col < len(cells) else cells[1]
                slot = f"s_f{idx}"
                if name and name != "Name":
                    model.human_names[slot] = name
                idx += 1
        elif in_table and not stripped.startswith("|"):
            in_table = False


def _parse_connections(body: str, model: ReverseGNNModel) -> None:
    """Store raw connection lines for later topology diagnostics.

    Only keeps lines that use the GNN arrow syntax (``>`` between two
    variable tokens). Markdown table rows, separator lines, and English
    prose that happen to contain ``-`` are filtered out.
    """
    # Upstream Connections syntax: optional leading ``(``, ident, optional
    # trailing ``)``, then ``>`` or ``->``, then the same. Must contain at
    # least one variable identifier on each side of the arrow.
    arrow_re = re.compile(r"^\s*\(?[A-Za-z_][\w,\s]*\)?\s*-?>\s*\(?[A-Za-z_][\w,\s]*\)?\s*$")
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "|")):
            continue
        if arrow_re.match(stripped):
            model.connections.append(stripped)


def _normalize_reverse_dimensions(model: ReverseGNNModel) -> None:
    """Align parsed variable declarations with authoritative matrix semantics."""
    model.hidden_states = [
        name for name in model.hidden_states if re.match(r"^(s_f|s)\d+$", name)
    ]
    model.observations = [
        name for name in model.observations if re.match(r"^(o_m|o)\d+$", name)
    ]
    model.actions = [
        name for name in model.actions if re.match(r"^(u_c|u|a_c)\d+$", name)
    ]

    if model.D and not model.degraded:
        model.hidden_states = [model.hidden_states[0] if model.hidden_states else "s_f0"]
    if model.C and not model.degraded:
        model.observations = [model.observations[0] if model.observations else "o_m0"]
    if model.B and model.B[0] and model.B[0][0] and not model.degraded:
        model.actions = [model.actions[0] if model.actions else "u_c0"]

    for idx, slot in enumerate(model.hidden_states):
        if model.D and not model.degraded and model.cardinalities.get(slot, 0) <= 0:
            model.cardinalities[slot] = len(model.D)
        elif model.cardinalities.get(slot, 0) <= 0:
            for source in (f"D_f{idx}", f"B_f{idx}"):
                card = model.cardinalities.get(source)
                if card is not None and card > 0:
                    model.cardinalities[slot] = card
                    break

    for idx, slot in enumerate(model.observations):
        if model.C and not model.degraded and model.cardinalities.get(slot, 0) <= 0:
            model.cardinalities[slot] = len(model.C)
        elif model.cardinalities.get(slot, 0) <= 0:
            for source in (f"C_m{idx}", f"A_m{idx}"):
                card = model.cardinalities.get(source)
                if card is not None and card > 0:
                    model.cardinalities[slot] = card
                    break

    for slot in model.actions:
        if (
            model.B
            and model.B[0]
            and model.B[0][0]
            and not model.degraded
            and model.cardinalities.get(slot, 0) <= 0
        ):
            model.cardinalities[slot] = len(model.B[0][0])


def _parse_matrices_fenced_block(text: str, model: ReverseGNNModel) -> None:
    """Optionally parse the ``gnn-matrices`` fenced code block.

    When COGANT's extended ``## State Space`` → "Active Inference
    Matrices" block is present, it contains authoritative A/B/C/D
    values that override the aggregate forms we derived from
    ``## InitialParameterization``. This gives the reverse synthesizer
    the most accurate matrix values available.
    """
    fence_match = re.search(r"```gnn-matrices\s*\n(.*?)\n```", text, re.DOTALL)
    if not fence_match:
        return
    block = fence_match.group(1)
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        header = _MATRIX_BLOCK_HEADER_RE.match(line)
        if not header:
            i += 1
            continue
        tag = header.group(1)
        rows = int(header.group(2))
        cols = int(header.group(3)) if header.group(3) else 0
        depth = int(header.group(4)) if header.group(4) else 0
        i += 1
        if tag == "A":
            A: list[list[float]] = []
            while i < len(lines) and len(A) < rows:
                row_line = lines[i].strip()
                if row_line and not row_line.startswith("#"):
                    vals = [float(x) for x in _FLOAT_RE.findall(row_line)]
                    if len(vals) == cols:
                        A.append(vals)
                i += 1
            if A:
                model.A = A
        elif tag == "B":
            # Block format: ``# action=k`` header followed by rows rows.
            B: list[list[list[float]]] = [[[0.0] * depth for _ in range(cols)] for _ in range(rows)]
            current_action = -1
            row_idx = 0
            while i < len(lines):
                row_line = lines[i].strip()
                if not row_line:
                    i += 1
                    continue
                act_match = re.match(r"#\s*action\s*=\s*(\d+)", row_line)
                if act_match:
                    current_action = int(act_match.group(1))
                    row_idx = 0
                    i += 1
                    continue
                if row_line.startswith("#"):
                    i += 1
                    continue
                if row_line.startswith(("A[[", "B[[", "C[[", "D[[")):
                    break
                if current_action < 0:
                    i += 1
                    continue
                vals = [float(x) for x in _FLOAT_RE.findall(row_line)]
                if len(vals) == cols and row_idx < rows:
                    for c in range(cols):
                        B[row_idx][c][current_action] = vals[c]
                    row_idx += 1
                i += 1
            if B and B[0]:
                model.B = B
        elif tag == "C":
            C: list[float] = []
            while i < len(lines) and len(C) < rows:
                row_line = lines[i].strip()
                if row_line and not row_line.startswith("#"):
                    vals = [float(x) for x in _FLOAT_RE.findall(row_line)]
                    if vals:
                        C.extend(vals[:1])
                i += 1
            if C:
                model.C = C[:rows]
        elif tag == "D":
            D: list[float] = []
            while i < len(lines) and len(D) < rows:
                row_line = lines[i].strip()
                if row_line and not row_line.startswith("#"):
                    vals = [float(x) for x in _FLOAT_RE.findall(row_line)]
                    if vals:
                        D.extend(vals[:1])
                i += 1
            if D:
                model.D = D[:rows]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_gnn(gnn: str | Path) -> ReverseGNNModel:
    """Parse a GNN markdown file or string into a :class:`ReverseGNNModel`.

    Args:
        gnn: Either a path to a ``.gnn.md`` file or a raw markdown
            string. If the argument is a string that does not point to
            an existing file, it is treated as the raw markdown text.

    Returns:
        A populated :class:`ReverseGNNModel`. Fields that cannot be parsed
        from the source remain empty. Consumers must treat an incomplete
        model as invalid evidence rather than filling missing semantics.

    Example:
        >>> from cogant.reverse.parser import parse_gnn
        >>> gnn = '''## ModelName
        ... Demo
        ...
        ... ## StateSpaceBlock
        ... s_f0[2,1,type=int]
        ... o_m0[2,1,type=int]
        ... '''
        >>> model = parse_gnn(gnn)
        >>> model.raw_model_name
        'Demo'
    """
    if isinstance(gnn, Path):
        text = gnn.read_text(encoding="utf-8")
    elif isinstance(gnn, str):
        # Guard against long markdown strings being mistaken for paths
        # (``Path(long_str).is_file()`` raises OSError: file name too
        # long on macOS and Linux). Only probe the filesystem when the
        # argument is short and lacks newlines.
        looks_like_path = "\n" not in gnn and len(gnn) < 4096 and (Path(gnn).suffix or "/" in gnn)
        if looks_like_path and Path(gnn).is_file():
            text = Path(gnn).read_text(encoding="utf-8")
        else:
            text = gnn  # Raw markdown string.
    else:
        raise TypeError(f"parse_gnn: expected str or Path, got {type(gnn).__name__}")

    model = ReverseGNNModel()
    sections = _split_sections(text)

    def first(name: str) -> str | None:
        """Return the first body under section ``name``, or ``None`` if absent."""
        bodies = sections.get(name)
        return bodies[0] if bodies else None

    def last(name: str) -> str | None:
        """Return the last body under section ``name``, or ``None`` if absent."""
        bodies = sections.get(name)
        return bodies[-1] if bodies else None

    # Model name: prefer the upstream ``## ModelName`` section.
    body = first("ModelName") or first("GNNSection")
    if body:
        raw = body.strip().splitlines()
        if raw:
            model.raw_model_name = raw[0].strip()
            model.model_name = _sanitize_identifier(raw[0].strip())

    body = first("StateSpaceBlock")
    if body:
        _parse_state_space_block(body, model)

    body = first("ActInfOntologyAnnotation")
    if body:
        _parse_ontology_annotation(body, model)

    body = first("InitialParameterization")
    if body:
        _parse_initial_parameterization(body, model)

    # COGANT extended section with the human-readable state variable
    # table (header is ``## State Space``). This gives the planner
    # meaningful Python identifier roots. Use first() — the last
    # ``## State Space`` occurrence may be the matrices section.
    body = first("State Space")
    if body:
        _parse_state_variables_extended(body, model)

    # For connections, the upstream ``## Connections`` is authoritative.
    # The COGANT extended ``## Connections`` subsection (Contains /
    # Reads / Writes tables) comes later and has the same header; we
    # only want the first (upstream) occurrence for arrow-syntax edges.
    body = first("Connections")
    if body:
        _parse_connections(body, model)

    # Pull the authoritative A/B/C/D from the fenced gnn-matrices block
    # if present — it overrides the aggregate forms derived above.
    _parse_matrices_fenced_block(text, model)
    _normalize_reverse_dimensions(model)

    logger.info(
        "Parsed GNN model %r: n_states=%d n_obs=%d n_actions=%d",
        model.model_name,
        model.n_states,
        model.n_obs,
        model.n_actions,
    )
    return model


def _sanitize_identifier(name: str) -> str:
    """Return a valid Python identifier derived from an arbitrary name.

    Replaces non-alphanumeric characters with underscores, prefixes a
    leading digit with ``_``, and lowercases the result so the output is
    suitable as both a Python package name and a module name.
    """
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name.strip())
    if not cleaned:
        cleaned = "cogant_model"
    if cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned.lower()


__all__ = ["ReverseGNNModel", "parse_gnn"]
