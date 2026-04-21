import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "IsomorphismReport",
    "compare_role_distributions",
    "compare_matrices",
    "compare_graph_structure",
    "compute_isomorphism_report",
    "DEFAULT_ISOMORPHISM_THRESHOLD",
    "MATRIX_KEYS",
]

DEFAULT_ISOMORPHISM_THRESHOLD: float
MATRIX_KEYS: tuple[str, ...]

@dataclass
class IsomorphismReport:
    structural_score: float = ...
    role_score: float = ...
    matrix_score: float = ...
    total_score: float = ...
    is_isomorphic: bool = ...
    breakdown: dict[str, Any] = field(default_factory=dict)
    def summary(self) -> str: ...

def compare_role_distributions(
    roles_a: Mapping[str, float], roles_b: Mapping[str, float]
) -> float: ...
def compare_matrices(matrices_a: Mapping[str, Any], matrices_b: Mapping[str, Any]) -> float: ...
def compare_graph_structure(
    nodes_a: Sequence[Any], edges_a: Sequence[Any], nodes_b: Sequence[Any], edges_b: Sequence[Any]
) -> float: ...
def compute_isomorphism_report(
    gnn_a: Mapping[str, Any], gnn_b: Mapping[str, Any], threshold: float = ...
) -> IsomorphismReport: ...

_ = math
