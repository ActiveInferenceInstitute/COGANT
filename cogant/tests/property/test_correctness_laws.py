"""Property-based tests for the 7 COGANT correctness laws.

These tests use Hypothesis to generate arbitrary inputs and verify that
COGANT's core functions satisfy the mathematical properties claimed by
the Isomorphism Theorem and the reverse-engineering pipeline:

1. Role multiset non-negativity: compare_role_distributions in [0, 1]
2. Role self-similarity: compare_role_distributions(a, a) == 1.0
3. Role symmetry (approximate): |score(a,b) - score(b,a)| < 0.01
4. D vector normalization: render_matrices_module -> sum(D) ~ 1.0
5. A shape consistency: empty A with n_obs, n_states > 0 -> [n_obs][n_states]
6. Transition normalization: transition(uniform, k) -> sum ~ 1.0
7. Model name sanitization: parse_gnn -> valid Python identifier
"""

from __future__ import annotations

import math
import re

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from cogant.reverse.matrices import render_matrices_module
from cogant.reverse.metrics import compare_role_distributions
from cogant.reverse.parser import ReverseGNNModel, parse_gnn

pytestmark = pytest.mark.property

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Role names: short ASCII identifiers representing Active Inference roles.
_role_names = st.sampled_from(
    [
        "HIDDEN_STATE",
        "OBSERVATION",
        "ACTION",
        "POLICY",
        "PREFERENCE",
        "TRANSITION",
        "PRIOR",
        "LIKELIHOOD",
        "SENSORY",
        "ACTIVE",
        "INTERNAL",
        "EXTERNAL",
    ]
)

# Non-empty role distributions with strictly positive counts.
_role_dist = st.dictionaries(
    keys=_role_names,
    values=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=8,
)

# Possibly-empty role distributions (non-negative counts).
_role_dist_any = st.dictionaries(
    keys=_role_names,
    values=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    min_size=0,
    max_size=8,
)


# ---------------------------------------------------------------------------
# Law 1: Role multiset non-negativity
# compare_role_distributions(a, b) in [0.0, 1.0]
# ---------------------------------------------------------------------------


@given(a=_role_dist_any, b=_role_dist_any)
@settings(max_examples=200, deadline=None)
def test_law1_role_score_bounded(a: dict[str, float], b: dict[str, float]) -> None:
    """compare_role_distributions must return a value in [0.0, 1.0]."""
    score = compare_role_distributions(a, b)
    assert 0.0 <= score <= 1.0, f"score {score} out of [0, 1] for a={a}, b={b}"


# ---------------------------------------------------------------------------
# Law 2: Role self-similarity
# compare_role_distributions(a, a) == 1.0 for any non-empty a
# ---------------------------------------------------------------------------


@given(a=_role_dist)
@settings(max_examples=200, deadline=None)
def test_law2_role_self_similarity(a: dict[str, float]) -> None:
    """Comparing a non-empty distribution with itself must yield 1.0."""
    # Ensure the distribution has positive total mass.
    assume(sum(a.values()) > 0.0)
    score = compare_role_distributions(a, a)
    assert math.isclose(score, 1.0, abs_tol=1e-9), f"self-similarity score {score} != 1.0 for a={a}"


# ---------------------------------------------------------------------------
# Law 3: Role symmetry (approximate)
# |score(a, b) - score(b, a)| < 0.01
# ---------------------------------------------------------------------------


@given(a=_role_dist_any, b=_role_dist_any)
@settings(max_examples=200, deadline=None)
def test_law3_role_symmetry(a: dict[str, float], b: dict[str, float]) -> None:
    """score(a, b) and score(b, a) must differ by less than 0.01."""
    score_ab = compare_role_distributions(a, b)
    score_ba = compare_role_distributions(b, a)
    assert abs(score_ab - score_ba) < 0.01, (
        f"symmetry violation: score(a,b)={score_ab}, score(b,a)={score_ba}"
    )


# ---------------------------------------------------------------------------
# Law 4: D vector normalization
# render_matrices_module with well-formed model -> sum(D) ~ 1.0
# ---------------------------------------------------------------------------


@given(
    n_states=st.integers(min_value=1, max_value=10),
    n_obs=st.integers(min_value=1, max_value=10),
    n_actions=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=100, deadline=None)
def test_law4_d_vector_normalization(n_states: int, n_obs: int, n_actions: int) -> None:
    """Generated D vector must sum to approximately 1.0."""
    model = ReverseGNNModel(
        model_name="test_model",
        hidden_states=[f"s_f{i}" for i in range(n_states)],
        observations=[f"o_m{i}" for i in range(n_obs)],
        actions=[f"u_c{i}" for i in range(n_actions)],
        # D is left empty so render_matrices_module generates the default
        # uniform prior which must sum to 1.0.
    )
    source = render_matrices_module(model)

    # Extract the D vector from the generated source code.
    d_match = re.search(r"^D: List\[float\] = \[(.+?)\]$", source, re.MULTILINE)
    assert d_match is not None, "D vector not found in generated source"
    d_values = [float(x.strip()) for x in d_match.group(1).split(",")]
    assert len(d_values) == n_states, f"D has {len(d_values)} entries, expected {n_states}"
    d_sum = sum(d_values)
    assert math.isclose(d_sum, 1.0, abs_tol=1e-4), f"D vector sum={d_sum}, expected ~1.0"


# ---------------------------------------------------------------------------
# Law 5: A shape consistency
# If n_obs and n_states > 0 and A is empty -> generated A has shape
# [n_obs][n_states]
# ---------------------------------------------------------------------------


@given(
    n_states=st.integers(min_value=1, max_value=8),
    n_obs=st.integers(min_value=1, max_value=8),
)
@settings(max_examples=100, deadline=None)
def test_law5_a_shape_consistency(n_states: int, n_obs: int) -> None:
    """When A is empty but n_obs and n_states > 0, generated A must be [n_obs][n_states]."""
    model = ReverseGNNModel(
        model_name="shape_test",
        hidden_states=[f"s_f{i}" for i in range(n_states)],
        observations=[f"o_m{i}" for i in range(n_obs)],
        actions=["u_c0"],
        # A left empty to trigger fallback generation.
    )
    source = render_matrices_module(model)

    # Extract the A matrix definition from generated source.
    # The format is: A: List[List[float]] = [\n    [row0],\n    [row1],\n]
    a_block_match = re.search(
        r"^A: List\[List\[float\]\] = \[\n(.*?)\n\]$",
        source,
        re.MULTILINE | re.DOTALL,
    )
    assert a_block_match is not None, "A matrix block not found in generated source"
    row_matches = re.findall(r"\[([^\[\]]+)\]", a_block_match.group(1))
    assert len(row_matches) == n_obs, f"A has {len(row_matches)} rows, expected {n_obs}"
    for i, row_str in enumerate(row_matches):
        cols = [float(x.strip()) for x in row_str.split(",")]
        assert len(cols) == n_states, f"A row {i} has {len(cols)} cols, expected {n_states}"


# ---------------------------------------------------------------------------
# Law 6: Transition normalization
# transition(uniform, k) -> sum ~ 1.0 for any valid action k
# ---------------------------------------------------------------------------


@given(
    n_states=st.integers(min_value=1, max_value=8),
    n_actions=st.integers(min_value=1, max_value=5),
    action_idx=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=100, deadline=None)
def test_law6_transition_normalization(
    n_states: int,
    n_actions: int,
    action_idx: int,
) -> None:
    """transition(uniform_dist, k) must return a distribution summing to ~1.0."""
    model = ReverseGNNModel(
        model_name="trans_test",
        hidden_states=[f"s_f{i}" for i in range(n_states)],
        observations=[f"o_m{i}" for i in range(max(1, n_states))],
        actions=[f"u_c{i}" for i in range(n_actions)],
    )
    source = render_matrices_module(model)

    # Execute the generated module to get the transition function.
    namespace: dict = {}
    exec(source, namespace)  # noqa: S102

    transition_fn = namespace["transition"]
    uniform = [1.0 / n_states] * n_states

    # Clamp action_idx to valid range for the generated module.
    k = action_idx % n_actions
    result = transition_fn(uniform, k)

    assert len(result) == n_states, (
        f"transition returned {len(result)} entries, expected {n_states}"
    )
    result_sum = sum(result)
    assert math.isclose(result_sum, 1.0, abs_tol=1e-6), (
        f"transition sum={result_sum}, expected ~1.0"
    )


# ---------------------------------------------------------------------------
# Law 7: Model name sanitization
# parse_gnn -> model.model_name is a valid Python identifier
# ---------------------------------------------------------------------------

# Strategy: arbitrary non-empty strings that exercise the sanitizer.
_model_names = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S", "Z"),
        max_codepoint=0x7E,
    ),
    min_size=1,
    max_size=60,
)


@given(raw_name=_model_names)
@settings(max_examples=200, deadline=None)
def test_law7_model_name_sanitization(raw_name: str) -> None:
    """parse_gnn must produce a model_name that is a valid Python identifier."""
    # Ensure the name has non-whitespace content so the parser actually
    # invokes the sanitizer rather than falling back to the dataclass default.
    assume(raw_name.strip())
    # Build minimal GNN markdown with the given model name.
    gnn_md = f"## ModelName\n{raw_name}\n## StateSpaceBlock\n## Connections\n"
    model = parse_gnn(gnn_md)
    assert model.model_name.isidentifier(), (
        f"model_name {model.model_name!r} is not a valid Python identifier (raw_name={raw_name!r})"
    )
    # Additionally, verify it contains no uppercase (the sanitizer lowercases).
    assert model.model_name == model.model_name.lower(), (
        f"model_name {model.model_name!r} is not lowercased"
    )
