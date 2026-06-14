"""Full-fixture round-trip integration tests for ``cogant.reverse``.

Unlike :mod:`tests.integration.test_roundtrip`, which uses a single
inlined minimal GNN, this suite drives ``cogant.reverse`` from the
sample control-positive repositories under ``examples/control_positive``.
Each test exercises the complete forward → reverse → forward cycle and
asserts that the reconstructed GNN yields a populated diagnostic ledger.
The calculator fixture is additionally pinned as the default-threshold
success case after generated support-code filtering; other fixtures may
still report diagnostic drift.

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

import shutil
from pathlib import Path

import pytest

try:
    from cogant.reverse.idempotency import (
        ROUNDTRIP_STATUS_ROLE_PRESERVED,
        ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC,
        RoundtripResult,
        verify_repo_roundtrip,
        verify_roundtrip,
    )

    HAS_REVERSE = True
except ImportError:  # pragma: no cover - availability sentinel
    HAS_REVERSE = False
    ROUNDTRIP_STATUS_ROLE_PRESERVED = "ROLE_PRESERVED"
    ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC = "STRUCTURALLY_ISOMORPHIC"
    RoundtripResult = None  # type: ignore[assignment,misc]
    verify_roundtrip = None  # type: ignore[assignment]
    verify_repo_roundtrip = None  # type: ignore[assignment]


# Diagnostic floor: a completed round-trip with non-empty source roles should
# preserve at least one semantic role. The actual score remains visible in the
# result instead of being relabelled as role-preserved.
DIAGNOSTIC_ROLE_MATCH_FLOOR = 0.0


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


REPO_ROOT = Path(__file__).resolve().parents[2]
"""Path to the cogant repository root (two levels above this file)."""


CONTROL_POSITIVE = REPO_ROOT / "examples" / "control_positive"
"""Directory containing the calculator / event_pipeline / flask_mini repos."""

STRICT_MINIMAL = CONTROL_POSITIVE / "roundtrip_strict_minimal"
"""Hand-authored reversible-subset fixture for strict structural isomorphism."""


# ---------------------------------------------------------------------------
# Inline hand-written GNN (does not depend on fixture repos).
# ---------------------------------------------------------------------------


HAND_WRITTEN_GNN = """\
## GNNSection
HandwrittenMiniPOMDP

## GNNVersionAndFlags
GNN v2.0.0

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


def _assert_diagnostic_roundtrip(result: RoundtripResult) -> None:
    """Assert the result exposes the expected round-trip diagnostics.

    Checks in order:

    1. :attr:`RoundtripResult.role_preservation_score` is bounded and
       positive when source roles are present.
    2. Every **core** role present in ``original_roles`` (see
       :data:`_CORE_ROLES`) also appears in ``synthesized_roles`` with
       at least one mapping. POLICY / CONSTRAINT are not required
       because forward's lexical keyword rules emit them on incidental
       patterns that the synthesizer does not reproduce by design.
    3. Every declared shape dimension survives with at least one
       value on the synthesized side.
    """
    assert isinstance(result, RoundtripResult)
    assert 0.0 <= result.role_preservation_score <= 1.0
    assert result.original_roles, "source-side role multiset must be populated"
    assert result.synthesized_roles, "synthesized-side role multiset must be populated"
    assert result.role_preservation_score > DIAGNOSTIC_ROLE_MATCH_FLOOR, result.summary()
    for role, count in result.original_roles.items():
        if role not in _CORE_ROLES:
            continue
        assert count > 0, f"original core role {role} has count 0"
        assert result.synthesized_roles.get(role, 0) > 0, (
            f"core role {role} absent from synthesized multiset {result.synthesized_roles}"
        )
    for dim, ok in result.shape_match.items():
        assert ok, f"shape dimension {dim} did not survive round-trip: {result.shape_match}"


def _assert_strict_roundtrip(result: RoundtripResult) -> None:
    """Assert every strict structural-isomorphism invariant explicitly."""
    assert result.roundtrip_status == ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC
    assert result.structurally_isomorphic is True
    assert result.role_preserved is True
    assert result.role_preservation_score == 1.0
    assert result.generated_code_ok is True
    assert result.matrix_preserved is True
    assert result.gnn_sections_preserved is True
    assert result.graph_delta["node_delta"] == 0
    assert result.graph_delta["edge_delta"] == 0
    assert all(int(v) == 0 for v in result.graph_delta["edge_kind_delta"].values())
    assert all(result.shape_match.values())
    assert result.matrix_delta["compared_count"] == 4
    assert result.matrix_delta["shape_score"] == 1.0
    assert result.matrix_delta["length_mismatch"] is False
    assert result.matrix_delta["max_abs_delta"] == 0.0
    assert result.gnn_diff["section_score"] == 1.0
    assert not result.errors


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not HAS_REVERSE, reason="cogant.reverse not available")
@pytest.mark.skipif(
    not STRICT_MINIMAL.is_dir(),
    reason="roundtrip_strict_minimal fixture repo missing",
)
def test_roundtrip_strict_minimal_is_structurally_isomorphic(tmp_path: Path) -> None:
    """The hand-authored reversible subset clears the strict roundtrip tier."""
    result = verify_repo_roundtrip(
        STRICT_MINIMAL,
        output_dir=tmp_path / "strict-minimal-rt",
        role_threshold=0.5,
    )
    _assert_strict_roundtrip(result)
    assert result.original_roles == {"HIDDEN_STATE": 1, "ACTION": 2, "OBSERVATION": 1}
    assert result.synthesized_roles == result.original_roles


@pytest.mark.slow
@pytest.mark.skipif(not HAS_REVERSE, reason="cogant.reverse not available")
@pytest.mark.skipif(
    not STRICT_MINIMAL.is_dir(),
    reason="roundtrip_strict_minimal fixture repo missing",
)
def test_roundtrip_strict_minimal_not_target_name_special_cased(tmp_path: Path) -> None:
    """A renamed copy must pass by invariants, not by fixture-name branching."""
    renamed = tmp_path / "renamed_reversible_subset"
    shutil.copytree(STRICT_MINIMAL, renamed)
    result = verify_repo_roundtrip(
        renamed,
        output_dir=tmp_path / "renamed-strict-minimal-rt",
        role_threshold=0.5,
    )
    _assert_strict_roundtrip(result)


@pytest.mark.slow
@pytest.mark.skipif(not HAS_REVERSE, reason="cogant.reverse not available")
@pytest.mark.skipif(
    not (CONTROL_POSITIVE / "calculator").is_dir(),
    reason="calculator fixture repo missing",
)
def test_calculator_roundtrip(tmp_path: Path) -> None:
    """Full forward→reverse→forward round-trip on the calculator fixture.

    The calculator repo is the simplest class-based fixture and is the
    default role-preservation regression guard. It should preserve the
    exact role multiset and avoid source-absent CONTEXT roles.
    """
    result = verify_repo_roundtrip(
        CONTROL_POSITIVE / "calculator",
        output_dir=tmp_path / "calculator-rt",
        role_threshold=0.5,
    )
    _assert_diagnostic_roundtrip(result)
    assert result.roundtrip_status in {
        ROUNDTRIP_STATUS_ROLE_PRESERVED,
        ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC,
    }
    assert result.role_preserved is True
    assert result.role_preservation_score >= 0.5
    assert result.synthesized_roles == result.original_roles
    assert "CONTEXT" not in result.synthesized_roles


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
    than the calculator. The test keeps the low-score DRIFT verdict
    visible rather than treating it as a fresh role-preserved result.
    """
    result = verify_repo_roundtrip(
        CONTROL_POSITIVE / "event_pipeline",
        output_dir=tmp_path / "event-rt",
        role_threshold=0.7,
    )
    _assert_diagnostic_roundtrip(result)


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
        role_threshold=0.7,
        keep_tmp=True,
    )
    _assert_diagnostic_roundtrip(result)

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
    ``role_preservation_score`` thresholds; it only checks that the result
    object has the right fields and that they hold values of the
    expected types.
    """
    gnn_file = tmp_path / "minimal.gnn.md"
    gnn_file.write_text(HAND_WRITTEN_GNN, encoding="utf-8")
    result = verify_roundtrip(gnn_file, tmp_dir=tmp_path / "fields", role_threshold=0.5)

    assert isinstance(result, RoundtripResult)
    assert isinstance(result.roundtrip_status, str)
    assert isinstance(result.role_preservation_score, float)
    assert isinstance(result.role_preserved, bool)
    assert isinstance(result.structurally_isomorphic, bool)
    assert 0.0 <= result.role_preservation_score <= 1.0
    assert isinstance(result.original_roles, dict)
    assert isinstance(result.synthesized_roles, dict)
    assert isinstance(result.shape_match, dict)
    assert isinstance(result.errors, list)
    assert hasattr(result, "package_path")

    # summary() returns a human-readable one-line report.
    summary_text = result.summary()
    assert isinstance(summary_text, str)
    assert len(summary_text) > 0
    assert "role_preservation" in summary_text
