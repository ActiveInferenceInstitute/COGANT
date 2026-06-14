"""COGANT reverse synthesis engine — GNN markdown → Python package.

The :mod:`cogant.reverse` package implements the reverse direction of the
COGANT pipeline. Where the forward direction consumes a source tree and
emits a Generalized Notation for Networks (GNN) Active Inference model,
the reverse direction consumes a GNN markdown file and synthesizes a
runnable Python package whose structure mirrors the GNN topology.

Roundtrip contract
------------------
The round-trip **cannot** reproduce the original source code verbatim —
GNN is a lossy semantic projection that discards implementation details,
argument names, control-flow, docstrings, and anything that is not a
hidden-state, observation, action, policy, or constraint role.

The public verifier reports a ``roundtrip_status`` enum plus an invariant
ledger. ``ROLE_PRESERVED`` means the semantic role multiset survived above
the configured ``role_preservation_score`` threshold. The stricter
``STRUCTURALLY_ISOMORPHIC`` status is reserved for runs that also preserve
graph counts, edge kinds, state-space shapes, matrix shapes/values, GNN
sections, generated-code compile status, and the second forward pass.

Concrete node IDs and edge weights are not expected to survive unless the
strict invariant tier says they did.

Public API
----------
* :class:`ReverseGNNModel` — parsed representation of a GNN markdown file.
* :func:`parse_gnn` — parse a GNN markdown file into a ReverseGNNModel.
* :class:`PackagePlan` — mapping plan from GNN roles to Python package files.
* :func:`plan_package` — construct a PackagePlan from a ReverseGNNModel.
* :func:`synthesize_package` — emit Python source files from a PackagePlan.
* :func:`verify_roundtrip` — round-trip idempotency verifier.
"""

from cogant.reverse.callable import MatrixFunctions, make_matrix_functions
from cogant.reverse.idempotency import (
    ROLE_PRESERVATION_THRESHOLD,
    ROUNDTRIP_STATUS_DRIFT,
    ROUNDTRIP_STATUS_FAILED,
    ROUNDTRIP_STATUS_ROLE_PRESERVED,
    ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC,
    ROUNDTRIP_STATUSES,
    RoundtripResult,
    verify_repo_roundtrip,
    verify_roundtrip,
)
from cogant.reverse.metrics import (
    DEFAULT_ISOMORPHISM_THRESHOLD,
    IsomorphismReport,
    compare_graph_structure,
    compare_matrices,
    compare_role_distributions,
    compute_isomorphism_report,
)
from cogant.reverse.parser import ReverseGNNModel, parse_gnn
from cogant.reverse.planner import NodePlan, PackagePlan, plan_package
from cogant.reverse.synthesizer import synthesize_package

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
    "ROLE_PRESERVATION_THRESHOLD",
    "ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC",
    "ROUNDTRIP_STATUS_ROLE_PRESERVED",
    "ROUNDTRIP_STATUS_DRIFT",
    "ROUNDTRIP_STATUS_FAILED",
    "ROUNDTRIP_STATUSES",
    "IsomorphismReport",
    "compare_role_distributions",
    "compare_matrices",
    "compare_graph_structure",
    "compute_isomorphism_report",
    "DEFAULT_ISOMORPHISM_THRESHOLD",
    "MatrixFunctions",
    "make_matrix_functions",
]
