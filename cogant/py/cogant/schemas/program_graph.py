"""
ProgramGraph: Semantic graph representation of program structure.

Models the code as a directed multigraph with nodes (code elements)
and edges (semantic relationships). Forms the foundation of all downstream analyses.
"""

from typing import Any

from pydantic import ConfigDict, Field, ValidationInfo, field_validator

from cogant.schemas.core import EdgeKind as EdgeKind
from cogant.schemas.core import NodeKind as NodeKind

from .base import (
    CogantBaseModel,
    ConfidenceMetric,
    EvidenceRef,
    LocationInfo,
    StableID,
    TypeInfo,
)


class Node(CogantBaseModel):
    """
    A semantic node representing a code element (module, class, function, etc.).
    """

    id: StableID = Field(..., description="Unique stable identifier")
    kind: NodeKind = Field(..., description="Type of code element")
    label: str = Field(..., description="Human-readable name of element")
    language: str = Field(..., description="Programming language (e.g., 'python')")
    location: LocationInfo = Field(..., description="File path and span information")

    # Type system
    type_info: TypeInfo | None = Field(default=None, description="Type signature if applicable")

    # Structure
    parent_id: StableID | None = Field(
        default=None, description="ID of containing scope (module, class, etc.)"
    )
    children_ids: list[StableID] = Field(
        default_factory=list,
        description="IDs of directly contained elements",
    )

    # Semantics
    is_public: bool = Field(default=False, description="Whether element is part of public API")
    is_exported: bool = Field(default=False, description="Whether element is explicitly exported")
    is_test: bool = Field(default=False, description="Whether element is test code")
    is_generated: bool = Field(
        default=False,
        description="Whether element was auto-generated",
    )

    # Metadata
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Language-specific attributes (e.g., decorators, modifiers)",
    )
    documentation: str | None = Field(default=None, description="Extracted docstring/documentation")
    tags: list[str] = Field(default_factory=list, description="User/analyzer-defined tags")

    # Provenance
    provenance: list[EvidenceRef] = Field(
        default_factory=list,
        description="Evidence supporting this node's existence and properties",
    )

    @field_validator("children_ids")
    @classmethod
    def validate_no_self_children(cls, v: list[StableID], info: ValidationInfo) -> list[StableID]:
        """Ensure node doesn't list itself as child."""
        if "id" in info.data:
            if info.data["id"] in v:
                raise ValueError("Node cannot be its own child")
        return v


class Edge(CogantBaseModel):
    """
    A directed semantic relationship between two nodes.
    """

    id: StableID = Field(..., description="Unique identifier for edge")
    source_id: StableID = Field(..., description="Source node ID")
    target_id: StableID = Field(..., description="Target node ID")
    kind: EdgeKind = Field(..., description="Type of relationship")

    # Edge properties
    is_directed: bool = Field(
        default=True, description="Whether edge is directed (should always be True)"
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Edge weight for analysis (e.g., call frequency, confidence)",
    )

    # Metadata
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Language-specific attributes (e.g., call context, conditions)",
    )
    label: str | None = Field(default=None, description="Human-readable label for edge")
    tags: list[str] = Field(default_factory=list, description="User/analyzer-defined tags")

    # Provenance
    provenance: list[EvidenceRef] = Field(
        default_factory=list,
        description="Evidence supporting this edge",
    )

    # Confidence
    confidence: ConfidenceMetric | None = Field(
        default=None,
        description="Confidence in edge's validity (for inferred edges)",
    )


class ProgramGraph(CogantBaseModel):
    """
    Semantic multigraph representation of program structure.

    Contains all code elements (nodes) and their relationships (edges),
    forming the foundation for downstream semantic and dataflow analyses.
    """

    graph_id: StableID = Field(..., description="Unique identifier for this graph")
    language: str = Field(..., description="Primary programming language")
    version: str = Field(default="1.0.0", description="Schema version")

    # Core graph data
    nodes: list[Node] = Field(default_factory=list, description="All semantic nodes in graph")
    edges: list[Edge] = Field(default_factory=list, description="All semantic edges in graph")

    # Indices for fast lookup (optional but recommended)
    node_index: dict[StableID, int] = Field(
        default_factory=dict,
        description="Map node IDs to their index in nodes list",
    )
    edge_index: dict[StableID, int] = Field(
        default_factory=dict,
        description="Map edge IDs to their index in edges list",
    )

    # Statistics
    stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Graph statistics (node counts by kind, edge counts by kind, etc.)",
    )

    # Metadata
    root_ids: list[StableID] = Field(
        default_factory=list,
        description="IDs of root nodes (e.g., repository, top-level modules)",
    )
    external_dependencies: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of external module names to versions",
    )

    @field_validator("edges")
    @classmethod
    def validate_edge_endpoints(cls, edges: list[Edge], info: ValidationInfo) -> list[Edge]:
        """Ensure all edges reference valid nodes."""
        if "nodes" in info.data:
            node_ids = {node.id for node in info.data["nodes"]}
            for edge in edges:
                if edge.source_id not in node_ids:
                    raise ValueError(f"Edge {edge.id}: source {edge.source_id} not found in nodes")
                if edge.target_id not in node_ids:
                    raise ValueError(f"Edge {edge.id}: target {edge.target_id} not found in nodes")
        return edges

    def add_node(self, node: Node) -> None:
        """Add a node to the graph and update indices."""
        self.node_index[node.id] = len(self.nodes)
        self.nodes.append(node)

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph and update indices."""
        self.edge_index[edge.id] = len(self.edges)
        self.edges.append(edge)

    def get_node(self, node_id: StableID) -> Node | None:
        """Retrieve node by ID using index."""
        if node_id in self.node_index:
            return self.nodes[self.node_index[node_id]]
        return None

    def get_edge(self, edge_id: StableID) -> Edge | None:
        """Retrieve edge by ID using index."""
        if edge_id in self.edge_index:
            return self.edges[self.edge_index[edge_id]]
        return None

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Semantic multigraph representation of program structure",
            "version": "1.0.0",
        }
    )
