from .base import CogantBaseModel as CogantBaseModel, ConfidenceMetric as ConfidenceMetric, EvidenceRef as EvidenceRef, LocationInfo as LocationInfo, StableID as StableID, TypeInfo as TypeInfo
from _typeshed import Incomplete
from cogant.schemas.core import EdgeKind as EdgeKind, NodeKind as NodeKind
from pydantic import ValidationInfo as ValidationInfo
from typing import Any, ClassVar

class Node(CogantBaseModel):
    id: StableID
    kind: NodeKind
    label: str
    language: str
    location: LocationInfo
    type_info: TypeInfo | None
    parent_id: StableID | None
    children_ids: list[StableID]
    is_public: bool
    is_exported: bool
    is_test: bool
    is_generated: bool
    attributes: dict[str, Any]
    documentation: str | None
    tags: list[str]
    provenance: list[EvidenceRef]
    @classmethod
    def validate_no_self_children(cls, v: list[StableID], info: ValidationInfo) -> list[StableID]: ...

class Edge(CogantBaseModel):
    id: StableID
    source_id: StableID
    target_id: StableID
    kind: EdgeKind
    is_directed: bool
    weight: float
    attributes: dict[str, Any]
    label: str | None
    tags: list[str]
    provenance: list[EvidenceRef]
    confidence: ConfidenceMetric | None

class ProgramGraph(CogantBaseModel):
    graph_id: StableID
    language: str
    version: str
    nodes: list[Node]
    edges: list[Edge]
    node_index: dict[StableID, int]
    edge_index: dict[StableID, int]
    stats: dict[str, Any]
    root_ids: list[StableID]
    external_dependencies: dict[str, str]
    @classmethod
    def validate_edge_endpoints(cls, edges: list[Edge], info: ValidationInfo) -> list[Edge]: ...
    def add_node(self, node: Node) -> None: ...
    def add_edge(self, edge: Edge) -> None: ...
    def get_node(self, node_id: StableID) -> Node | None: ...
    def get_edge(self, edge_id: StableID) -> Edge | None: ...
    model_config: ClassVar[Incomplete]
