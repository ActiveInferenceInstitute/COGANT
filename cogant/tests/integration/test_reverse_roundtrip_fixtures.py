"""Full-fixture round-trip integration tests for ``cogant.reverse``.

Unlike :mod:`tests.integration.test_roundtrip`, which uses a single
inlined minimal GNN, this suite drives ``cogant.reverse`` from the
sample control-positive repositories under ``examples/control_positive``.
Each test exercises the complete forward → reverse → forward cycle and
asserts that the reconstructed GNN is role-multiset isomorphic to the
source GNN above the strict (role_match ≥ 0.7) threshold.

Fixtures
--------
* ``calculator`` — toy class-based calculator (1 hidden state factor,
  single pipeline role).
* ``event_pipeline`` — event-driven dispatcher (1 hidden state factor,
  fan-out topology).
* A hand-crafted multi-factor GNN declared inline below, used to
  verify cardinality preservation for models with more than one hidden
  state plus observations, actions, and priors.
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from cogant.reverse.idempotency import (
        RoundtripResult,
        verify_repo_roundtrip,
        verify_roundtrip,
    )

    HAS_REVERSE = True
except ImportError:  # pragma: no cover - availability sentinel
    HAS_REVERSE = False
    RoundtripResult = None  # type: ignore[assignment,misc]
    verify_roundtrip = None  # type: ignore[assignment]
    verify_repo_roundtrip = None  # type: ignore[assignment]


# Strict threshold — the reverse synthesizer is role-complete on the
# three control-positive fixtures, so every test here should clear 0.7.
# Lower to match the lenient floor in ``test_roundtrip.py`` only as a
# compatibility shim; fixtures that fail strict should be promoted into
# the lenient suite with an explanatory skipif instead.
STRICT_ROLE_MATCH_THRESHOLD = 0.7


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


REPO_ROOT = Path(__file__).resolve().parents[2]
"""Path to the cogant repository root (two levels above this file)."""


CONTROL_POSITIVE = REPO_ROOT / "examples" / "control_positive"
"""Directory containing the calculator / event_pipeline / flask_mini repos."""


# ---------------------------------------------------------------------------
# Inline hand-written GNN (does not depend on fixture repos).
# ---------------------------------------------------------------------------


HAND_WRITTEN_GNN = """\
## GNNSection
HandwrittenMiniPOMDP

## GNNVersionAndFlags
GNN v1

## ModelName
HandwrittenMiniPOMDP

## StateSpaceBlock
s_f0[3,1,type=int]
s_f1[2,1,type=int]
o_m0[2,1,type=int]
u_c0[2,1,type=int]
A_m0[2,3,type=float]
B_f0[3,3,2,type=float]
B_f1[2,2,1,type=float]
C_m0[2,type=float]
D_f0[3,1,type=float]
D_f1[2,1,type=float]

## Connections
(D_f0) > (s_f0)
(D_f1) > (s_f1)
(s_f0, A_m0) > (o_m0)
(s_f0, B_f0, u_c0) > (s_f0)
(s_f1, B_f1) > (s_f1)

## InitialParameterization
D_f0={ (0.3, 0.4, 0.3) }
D_f1={ (0.5, 0.5) }
A_m0={ ( (0.8, 0.5, 0.2), (0.2, 0.5, 0.8) ) }
C_m0={ (1.0, -1.0) }

## ActInfOntologyAnnotation
s_f0=HiddenState
s_f1=HiddenState
o_m0=Observation
u_c0=Action
A_m0=LikelihoodMatrix
B_f0=TransitionMatrix
B_f1=TransitionMatrix
C_m0=PreferenceVector
D_f0=PriorBelief
D_f1=PriorBelief

## Time
Static
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


#: Core roles that must survive the round-trip on control-positive fixtures.
#: Excludes POLICY / CONSTRAINT because the forward pipeline emits those on
#: incidental patterns in hand-written code (e.g. `handle()` methods, assert
#: statements) that the synthesizer has no reason to reproduce unless the
#: source GNN explicitly declares them. HIDDEN_STATE / OBSERVATION / ACTION
#: are the *semantic core* of a GNN and must always survive.
_CORE_ROLES = {"HIDDEN_STATE", "OBSERVATION", "ACTION"}


def _assert_strict_roundtrip(result: RoundtripResult) -> None:
    """Assert the result meets every property expected of a strict round-trip.

    Checks in order:

    1. :attr:`RoundtripResult.role_match_score` meets
       :data:`STRICT_ROLE_MATCH_THRESHOLD`.
    2. Every **core** role present in ``original_roles`` (see
       :data:`_CORE_ROLES`) also appears in ``synthesized_roles`` with
       at least one mapping. POLICY / CONSTRAINT are not required
       because forward's lexical keyword rules emit them on incidental
       patterns that the synthesizer does not reproduce by design.
    3. Every declared shape dimension survives with at least one
       value on the synthesized side.
    """
    assert isinstance(result, RoundtripResult)
    assert result.role_match_score >= STRICT_ROLE_MATCH_THRESHOLD, (
        f"role_match_score {result.role_match_score:.2%} below threshold "
        f"{STRICT_ROLE_MATCH_THRESHOLD:.2%}; original={result.original_roles}, "
        f"synthesized={result.synthesized_roles}"
    )
    for role, count in result.original_roles.items():
        if role not in _CORE_ROLES:
            continue
        assert count > 0, f"original core role {role} has count 0"
        assert result.synthesized_roles.get(role, 0) > 0, (
            f"core role {role} absent from synthesized multiset "
            f"{result.synthesized_roles}"
        )
    for dim, ok in result.shape_match.items():
        assert ok, f"shape dimension {dim} did not survive round-trip: {result.shape_match}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not HAS_REVERSE, reason="cogant.reverse not available")
@pytest.mark.skipif(
    not (CONTROL_POSITIVE / "calculator").is_dir(),
    reason="calculator fixture repo missing",
)
def test_calculator_roundtrip(tmp_path: Path) -> None:
    """Full forward→reverse→forward round-trip on the calculator fixture.

    The calculator repo is the simplest class-based fixture and should
    produce a tight role multiset (1 HIDDEN_STATE) that survives the
    round-trip with role_match_score = 1.0.
    """
    result = verify_repo_roundtrip(
        CONTROL_POSITIVE / "calculator",
        output_dir=tmp_path / "calculator-rt",
        role_threshold=STRICT_ROLE_MATCH_THRESHOLD,
    )
    _assert_strict_roundtrip(result)
    assert result.is_isomorphic, result.summary()


@pytest.mark.slow
@pytest.mark.skipif(not HAS_REVERSE, reason="cogant.reverse not available")
@pytest.mark.skipif(
    not (CONTROL_POSITIVE / "event_pipeline").is_dir(),
    reason="event_pipeline fixture repo missing",
)
def test_event_pipeline_roundtrip(tmp_path: Path) -> None:
    """Round-trip on the event_pipeline fixture under the strict gate.

    Event-driven dispatcher with multiple method mutations; exercises
    the WRITES-edge path in MutatingSubsystemRule more aggressively
    than the calculator. Historically this fan-out topology was a
    documented gap (synthesizer reconstructed only ~47% of roles), but
    the synthesizer now clears ``STRICT_ROLE_MATCH_THRESHOLD = 0.7`` on
    this fixture, so it is held to the strict gate alongside the other
    control-positive fixtures.
    """
    result = verify_repo_roundtrip(
        CONTROL_POSITIVE / "event_pipeline",
        output_dir=tmp_path / "event-rt",
        role_threshold=STRICT_ROLE_MATCH_THRESHOLD,
    )
    _assert_strict_roundtrip(result)


@pytest.mark.slow
@pytest.mark.skipif(not HAS_REVERSE, reason="cogant.reverse not available")
def test_hand_written_gnn_roundtrip(tmp_path: Path) -> None:
    """Round-trip a hand-crafted multi-factor POMDP written inline.

    This test is independent of any fixture repo: the GNN source lives
    in :data:`HAND_WRITTEN_GNN` and is written to a temp file. It
    exercises cardinality preservation for models with more than one
    hidden state plus observations, actions, and priors.
    """
    gnn_file = tmp_path / "hand_written.gnn.md"
    gnn_file.write_text(HAND_WRITTEN_GNN, encoding="utf-8")

    result = verify_roundtrip(
        gnn_file,
        tmp_dir=tmp_path / "reverse-out",
        role_threshold=STRICT_ROLE_MATCH_THRESHOLD,
        keep_tmp=True,
    )
    _assert_strict_roundtrip(result)
    assert result.is_isomorphic, result.summary()

    # Hand-written source declares 2 hidden states — the synthesized
    # package must reproduce at least 2 HIDDEN_STATE classes.
    assert result.synthesized_roles.get("HIDDEN_STATE", 0) >= 2, (
        f"expected ≥2 HIDDEN_STATE mappings, got {result.synthesized_roles}"
    )


@pytest.mark.slow
@pytest.mark.skipif(not HAS_REVERSE, reason="cogant.reverse not available")
def test_roundtrip_result_has_expected_fields(tmp_path: Path) -> None:
    """``RoundtripResult`` exposes the documented attribute surface.

    This test is a structural check rather than a scoring test — it
    protects the :class:`cogant.reverse.idempotency.RoundtripResult`
    public API from silent shape drift. The minimal GNN used here is
    too simple to score highly, so the test does not assert on
    ``role_match_score`` thresholds; it only checks that the result
    object has the right fields and that they hold values of the
    expected types.
    """
    gnn_file = tmp_path / "minimal.gnn.md"
    gnn_file.write_text(HAND_WRITTEN_GNN, encoding="utf-8")
    result = verify_roundtrip(
        gnn_file, tmp_dir=tmp_path / "fields", role_threshold=0.5
    )

    assert isinstance(result, RoundtripResult)
    assert isinstance(result.is_isomorphic, bool)
    assert isinstance(result.role_match_score, float)
    assert 0.0 <= result.role_match_score <= 1.0
    assert isinstance(result.original_roles, dict)
    assert isinstance(result.synthesized_roles, dict)
    assert isinstance(result.shape_match, dict)
    assert isinstance(result.errors, list)
    assert hasattr(result, "package_path")

    # summary() returns a human-readable one-line report.
    summary_text = result.summary()
    assert isinstance(summary_text, str)
    assert len(summary_text) > 0
    assert "role_match" in summary_text
