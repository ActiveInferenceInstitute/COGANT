"""Graph stage configuration.

Controls how the program-graph builder bounds the graph it constructs
and which nodes it keeps.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GraphConfig(BaseModel):
    """Configuration for the graph-building stage.

    Attributes:
        max_nodes: Upper bound on the number of nodes retained.
        max_edges: Upper bound on the number of edges retained.
        prune_isolated: Drop nodes with no incident edges.
        include_builtins: Retain language/runtime builtins in the graph.
    """

    max_nodes: int = Field(default=10_000, ge=1, description="Maximum nodes in the graph")
    max_edges: int = Field(default=50_000, ge=1, description="Maximum edges in the graph")
    prune_isolated: bool = Field(default=True, description="Drop nodes with no edges")
    include_builtins: bool = Field(default=False, description="Keep language builtins in the graph")

    model_config = ConfigDict(frozen=True)
