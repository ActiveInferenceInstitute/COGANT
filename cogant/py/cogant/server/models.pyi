from typing import Any, ClassVar

from _typeshed import Incomplete as Incomplete
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    model_config: ClassVar[Incomplete]
    repo_path: str
    stages: list[str] | None
    skip_dynamic: bool

class AnalyzeResponse(BaseModel):
    nodes: int
    edges: int
    mappings: int
    roles: dict[str, int]
    errors: list[str]

class HealthResponse(BaseModel):
    status: str
    version: str
    docs: str

class ExplainResponse(BaseModel):
    model_config: ClassVar[Incomplete]
    node_name: str
    node_id: str
    node_kind: str
    assigned_role: str | None
    rules_fired: list[dict[str, Any]]
    rules_considered: list[dict[str, Any]]
    blanket_role: str
    target: str
    mapping_label: str | None
    mapping_description: str | None
    metadata: dict[str, Any]

class RoundtripRequest(BaseModel):
    model_config: ClassVar[Incomplete]
    repo_path: str
    threshold: float

class RoundtripResponse(BaseModel):
    role_match_score: float
    is_isomorphic: bool
    original_roles: dict[str, int]
    synthesized_roles: dict[str, int]
    threshold: float
    errors: list[str]

class GraphNode(BaseModel):
    id: str
    name: str
    kind: str
    role: str | None

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: str

class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]

class ErrorResponse(BaseModel):
    detail: str
    error_type: str
