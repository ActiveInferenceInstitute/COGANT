"""COGANT reverse synthesis engine — GNN markdown → Python package.

The :mod:`cogant.reverse` package implements the reverse direction of the
COGANT pipeline. Where the forward direction consumes a source tree and
emits a Generalized Notation for Networks (GNN) Active Inference model,
the reverse direction consumes a GNN markdown file and synthesizes a
runnable Python package whose structure mirrors the GNN topology.

Isomorphism definition
----------------------
The round-trip **cannot** reproduce the original source code verbatim —
GNN is a lossy semantic projection that discards implementation details,
argument names, control-flow, docstrings, and anything that is not a
hidden-state, observation, action, policy, or constraint role.

What the round-trip **must** preserve is graph-level isomorphism. For an
input GNN ``G`` and the GNN ``G'`` produced by synthesising ``G`` to
Python and then re-running the forward pipeline on that package, we
require:

1. **Role multiset equality**: the multiset of MappingKind labels on
   semantic mappings of ``G'`` must equal that of ``G`` (up to
   the role-match threshold).
2. **State-space cardinality**: ``|hidden_states(G')| == |hidden_states(G)|``
   and similarly for observations, actions, policies, and constraints.
3. **Matrix shape congruence**: the derived A, B, C, D matrices of
   ``G'`` have the same shape as those of ``G``.
4. **Topology homomorphism (weak)**: there is a bijection between the
   semantic nodes of ``G`` and ``G'`` under which the A/B/C/D structural
   zero/non-zero pattern is preserved up to permutation.

Concrete node IDs and edge weights are **not** required to be equal —
only the role labels, dimensions, and matrix shapes. This weaker notion
of isomorphism is what :func:`cogant.reverse.idempotency.verify_roundtrip`
measures via the ``role_match_score`` metric.

Public API
----------
* :class:`ReverseGNNModel` — parsed representation of a GNN markdown file.
* :func:`parse_gnn` — parse a GNN markdown file into a ReverseGNNModel.
* :class:`PackagePlan` — mapping plan from GNN roles to Python package files.
* :func:`plan_package` — construct a PackagePlan from a ReverseGNNModel.
* :func:`synthesize_package` — emit Python source files from a PackagePlan.
* :func:`verify_roundtrip` — round-trip idempotency verifier.
"""

from cogant.reverse.parser import ReverseGNNModel, parse_gnn
from cogant.reverse.planner import NodePlan, PackagePlan, plan_package
from cogant.reverse.synthesizer import synthesize_package
from cogant.reverse.idempotency import (
    ROLE_MATCH_THRESHOLD,
    RoundtripResult,
    verify_repo_roundtrip,
    verify_roundtrip,
)
from cogant.reverse.callable import MatrixFunctions, make_matrix_functions
from cogant.reverse.metrics import (
    DEFAULT_ISOMORPHISM_THRESHOLD,
    IsomorphismReport,
    compare_graph_structure,
    compare_matrices,
    compare_role_distributions,
    compute_isomorphism_report,
)

__all__ = [
    "ReverseGNNModel",
    "parse_gnn",
    "NodePlan",
    "PackagePlan",
    "plan_package",
    "synthesize_package",
    "RoundtripResult",
    "verify_roundtrip",
    "verify_repo_roundtrip",
    "ROLE_MATCH_THRESHOLD",
    "IsomorphismReport",
    "compare_role_distributions",
    "compare_matrices",
    "compare_graph_structure",
    "compute_isomorphism_report",
    "DEFAULT_ISOMORPHISM_THRESHOLD",
    "MatrixFunctions",
    "make_matrix_functions",
]
