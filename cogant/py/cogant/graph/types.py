"""Graph-specific type definitions for COGANT.

This module defines types related to graph analysis, querying, and
manipulation. These are specialized types for the graph module.
"""

from __future__ import annotations

from typing import TypedDict

__all__ = [
    "GraphStats",
    "CentralityDict",
    "CommunityList",
    "PathList",
    "AdjacencyMatrix",
]


# ============================================================================
# TypedDicts: Graph analysis structures
# ============================================================================


class GraphStats(TypedDict, total=False):
    """Statistics computed over a program graph.

    Captures structural properties useful for understanding graph
    complexity and connectivity.
    """

    node_count: int
    """Total number of nodes in the graph."""

    edge_count: int
    """Total number of edges in the graph."""

    density: float
    """Graph density (edges / max_possible_edges), in range [0.0, 1.0]."""

    is_dag: bool
    """Whether the graph is a directed acyclic graph (DAG)."""

    component_count: int
    """Number of connected components."""


# ============================================================================
# Type Aliases: Graph analysis types
# ============================================================================

CentralityDict = dict[str, float]
"""Centrality scores for each node.

Keys are node IDs, values are centrality scores (typically 0.0–1.0 range).
Used for betweenness, closeness, pagerank, and other centrality measures.
"""

CommunityList = list[frozenset[str]]
"""List of communities (node clusters) in the graph.

Each community is represented as a frozenset of node IDs.
Used by community detection algorithms.
"""

PathList = list[list[str]]
"""List of paths through the graph.

Each path is a sequence of node IDs representing a path from source to
destination. Used for all-pairs shortest paths and related queries.
"""

AdjacencyMatrix = list[list[int]]
"""Adjacency matrix representation of the graph.

Binary matrix where adjacency_matrix[i][j] = 1 if edge i->j exists,
0 otherwise. Used for graph algorithms that operate on matrix form.
"""
