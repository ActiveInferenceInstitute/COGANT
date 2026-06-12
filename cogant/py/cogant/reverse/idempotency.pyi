from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "IdempotencyReport",
    "RoundtripResult",
    "verify_roundtrip",
    "verify_repo_roundtrip",
    "ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC",
    "ROUNDTRIP_STATUS_ROLE_PRESERVED",
    "ROUNDTRIP_STATUS_DRIFT",
    "ROUNDTRIP_STATUS_FAILED",
    "ROUNDTRIP_STATUSES",
    "ROLE_PRESERVATION_THRESHOLD",
    "ROLE_MATCH_THRESHOLD",
    "check_structural_idempotency",
    "check_semantic_idempotency",
]

ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC: str
ROUNDTRIP_STATUS_ROLE_PRESERVED: str
ROUNDTRIP_STATUS_DRIFT: str
ROUNDTRIP_STATUS_FAILED: str
ROUNDTRIP_STATUSES: tuple[str, ...]
ROLE_PRESERVATION_THRESHOLD: float
ROLE_MATCH_THRESHOLD: float

@dataclass
class IdempotencyReport:
    is_idempotent: bool = ...
    forward_roles: dict[str, int] = field(default_factory=dict)
    reverse_roles: dict[str, int] = field(default_factory=dict)
    differences: list[str] = field(default_factory=list)
    score: float = ...

@dataclass
class RoundtripResult:
    roundtrip_status: str = ...
    role_preservation_score: float = ...
    role_preserved: bool = ...
    structurally_isomorphic: bool = ...
    matrix_preserved: bool = ...
    gnn_sections_preserved: bool = ...
    generated_code_ok: bool = ...
    vacuous_roundtrip: bool = ...
    matrix_score: float = ...
    structural_score: float = ...
    original_roles: dict[str, int] = field(default_factory=dict)
    synthesized_roles: dict[str, int] = field(default_factory=dict)
    shape_match: dict[str, bool] = field(default_factory=dict)
    package_path: Path | None = ...
    original_graph_summary: dict[str, Any] = field(default_factory=dict)
    synthesized_graph_summary: dict[str, Any] = field(default_factory=dict)
    graph_delta: dict[str, Any] = field(default_factory=dict)
    gnn_diff: dict[str, Any] = field(default_factory=dict)
    matrix_delta: dict[str, Any] = field(default_factory=dict)
    invariants: dict[str, Any] = field(default_factory=dict)
    rule_evidence_trace: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    @property
    def is_isomorphic(self) -> bool: ...
    @property
    def role_match_score(self) -> float: ...
    @property
    def roundtrip_invariants(self) -> dict[str, Any]: ...
    def summary(self) -> str: ...

def check_structural_idempotency(
    original_graph: Any, roundtrip_graph: Any
) -> IdempotencyReport: ...
def check_semantic_idempotency(
    original_mappings: dict[str, Any], roundtrip_mappings: dict[str, Any]
) -> IdempotencyReport: ...
def verify_roundtrip(
    gnn_path: str | Path,
    tmp_dir: str | Path | None = None,
    *,
    role_threshold: float = ...,
    keep_tmp: bool = False,
) -> RoundtripResult: ...
def verify_repo_roundtrip(
    repo_path: str | Path, output_dir: str | Path | None = None, *, role_threshold: float = ...
) -> RoundtripResult: ...
