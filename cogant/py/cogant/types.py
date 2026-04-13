"""Shared type definitions and type aliases for COGANT.

This module defines the top-level type infrastructure including TypedDicts,
type aliases, and semantic type hints used across the COGANT codebase.
All definitions are typing-only (no runtime objects) to avoid circular imports.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

__all__ = [
    # TypedDicts
    "NodeAttrs",
    "EdgeAttrs",
    "GNNBundle",
    "MatrixDict",
    "PipelineResultDict",
    "RuleResultDict",
    "ValidationIssue",
    "ComplexityEntry",
    "CouplingEntry",
    "DeadCodeEntry",
    "HalsteadDict",
    "GraphMetricsDict",
    "ExportResultDict",
    "AnalysisBundleDict",
    "VisualizationResult",
    # Type aliases
    "NodeId",
    "EdgeKind",
    "RoleName",
    "FilePath",
    "ConfidenceScore",
    "AMatrix",
    "BMatrix",
    "CVector",
    "DVector",
    "MermaidStr",
    "DotStr",
    "JsonStr",
    "CentralityDict",
]


# ============================================================================
# TypedDicts: Structured dictionary schemas
# ============================================================================


class NodeAttrs(TypedDict, total=False):
    """Attributes of a node in the program graph.

    Represents a single node with its structural properties and metadata.
    """

    id: str
    """Unique identifier for the node."""

    kind: str
    """Type of node (e.g., 'function', 'class', 'module', 'file')."""

    name: str
    """Human-readable name of the node."""

    file: str
    """File path where the node is defined."""

    line: int
    """Line number where the node starts in the source file."""

    role: str
    """Semantic role (e.g., 'HIDDEN_STATE', 'OBSERVATION', 'ACTION')."""

    confidence: float
    """Confidence score for the node's analysis (0.0–1.0)."""


class EdgeAttrs(TypedDict, total=False):
    """Attributes of an edge in the program graph.

    Represents a single edge (relationship) between nodes.
    """

    src: str
    """Source node ID."""

    dst: str
    """Destination node ID."""

    kind: str
    """Type of edge (e.g., 'calls', 'reads', 'writes', 'inherits')."""

    weight: float
    """Edge weight indicating frequency or strength (typically 0.0–1.0)."""


class MatrixDict(TypedDict, total=False):
    """Active Inference matrices in a GNN bundle.

    Defines the generative model for the active inference agent:
    - A: observation likelihood (how states map to observations)
    - B: state transitions (how states and actions change state)
    - C: preferred observations (preference over observations)
    - D: initial state distribution (prior)
    """

    A: list[list[float]]
    """Observation likelihood matrix (states -> observations)."""

    B: list[list[list[float]]]
    """State transition tensor (states × actions -> next states)."""

    C: list[float]
    """Preference vector (relative preferences over observations)."""

    D: list[float]
    """Prior state distribution (initial belief state)."""


class GNNBundle(TypedDict, total=False):
    """Complete GNN export bundle from a COGANT run.

    Represents the full output: matrices, metadata, and all supporting
    information needed to instantiate an active inference agent.
    """

    version: str
    """GNN format version (e.g., '0.5.0')."""

    source_hash: str
    """Hash of the source code analyzed."""

    matrices: MatrixDict
    """Active inference matrices (A, B, C, D)."""

    roles: dict[str, str]
    """Mapping of semantic roles to node IDs."""

    metadata: dict[str, Any]
    """Additional metadata (analysis date, tool version, parameters)."""


class PipelineResultDict(TypedDict, total=False):
    """Result of a full COGANT pipeline run.

    Aggregates all outputs from extraction through export, including
    timing, warnings, and validation scores.
    """

    status: str
    """Pipeline status ('success', 'partial', 'failed')."""

    timing: dict[str, float]
    """Timing for each stage (seconds)."""

    warnings: list[str]
    """Non-fatal warnings encountered."""

    gnn_bundle: GNNBundle
    """Completed GNN bundle."""

    validator_score: int
    """Validation score (0–100)."""


class RuleResultDict(TypedDict, total=False):
    """Result of applying a single translation rule to a node.

    Captures the outcome: rule name, node affected, semantic role assigned,
    confidence, and supporting evidence.
    """

    rule_name: str
    """Name of the translation rule."""

    node_id: str
    """ID of the node the rule was applied to."""

    role: str
    """Semantic role assigned by the rule."""

    confidence: float
    """Confidence of the assignment (0.0–1.0)."""

    evidence: str
    """Human-readable evidence justifying the assignment."""


class ValidationIssue(TypedDict, total=False):
    """A validation issue found during analysis.

    Represents a single problem detected by validation checks, with
    severity level, message, and optional location information.
    """

    severity: Literal["error", "warning", "info"]
    """Severity level of the issue."""

    message: str
    """Human-readable description of the issue."""

    location: str
    """Source location (file:line or node ID)."""


# ============================================================================
# Type Aliases: Semantic type hints for clarity and precision
# ============================================================================

NodeId = str
"""Unique identifier for a node in the program graph."""

EdgeKind = str
"""Type classifier for edges (e.g., 'calls', 'reads', 'writes', 'inherits')."""

RoleName = str
"""Semantic role name (e.g., 'HIDDEN_STATE', 'OBSERVATION', 'ACTION')."""

FilePath = str
"""File system path to a source code file."""

ConfidenceScore = float
"""Confidence score in range [0.0, 1.0]."""

AMatrix = list[list[float]]
"""Observation likelihood matrix: states -> observations.

Shape: (num_observations, num_hidden_states)
"""

BMatrix = list[list[list[float]]]
"""State transition matrix: states × actions -> next states.

Shape: (num_hidden_states, num_actions, num_hidden_states)
"""

CVector = list[float]
"""Preference vector over observations.

Shape: (num_observations,)
Log preference for each observation.
"""

DVector = list[float]
"""Prior distribution over hidden states.

Shape: (num_hidden_states,)
Initial belief state (log probabilities).
"""

MermaidStr = str
"""String containing a Mermaid diagram specification.

Used for graph visualization in markdown output.
"""

DotStr = str
"""String containing a Graphviz DOT specification.

Used for graph visualization in PNG/SVG output.
"""

JsonStr = str
"""String containing JSON-formatted data.

Typically used for serialization and data exchange.
"""

CentralityDict = dict[str, float]
"""Centrality scores for each node in a graph.

Keys are node IDs, values are centrality scores (typically 0.0–1.0).
"""


# ============================================================================
# TypedDicts: Static Analysis
# ============================================================================


class ComplexityEntry(TypedDict, total=False):
    """Complexity metrics for a single symbol.

    Records cyclomatic and cognitive complexity for a function, method,
    or class definition.
    """

    symbol_name: str
    """Name of the symbol (function, method, or class)."""

    file: str
    """File path where the symbol is defined."""

    line: int
    """Line number of the symbol definition."""

    cyclomatic: int
    """Cyclomatic complexity (decision point count)."""

    cognitive: int
    """Cognitive complexity (nesting + decision points)."""


class CouplingEntry(TypedDict, total=False):
    """Module coupling metrics.

    Records instability, abstractness, and stability metrics for a module.
    """

    module: str
    """Module name."""

    afferent: int
    """Afferent coupling (Ca): modules depending on this module."""

    efferent: int
    """Efferent coupling (Ce): modules this module depends on."""

    instability: float
    """Instability metric I = Ce / (Ca + Ce), range [0, 1]."""

    abstractness: float
    """Abstractness metric A = abstract_classes / total_classes."""

    distance: float
    """Distance from main sequence D = |A + I - 1|."""


class DeadCodeEntry(TypedDict, total=False):
    """Dead code detection result.

    Records symbols that may be unreachable or unused.
    """

    symbol_name: str
    """Name of the potentially dead symbol."""

    file: str
    """File path where symbol is defined."""

    line: int
    """Line number of the symbol."""

    kind: str
    """Type of symbol (function, class, variable, etc.)."""

    confidence: float
    """Confidence score (0.0–1.0) that this is actually dead code."""


class HalsteadDict(TypedDict, total=False):
    """Halstead metrics for software complexity.

    Records distinct operators, operands, and derived metrics.
    """

    n1: int
    """Distinct operators count."""

    n2: int
    """Distinct operands count."""

    N1: int
    """Total operators count."""

    N2: int
    """Total operands count."""

    vocabulary: int
    """Vocabulary (n1 + n2)."""

    length: int
    """Program length (N1 + N2)."""

    volume: float
    """Volume: length * log2(vocabulary)."""

    difficulty: float
    """Difficulty: (n1/2) * (N2/n2)."""

    effort: float
    """Effort: difficulty * volume."""


class GraphMetricsDict(TypedDict, total=False):
    """Metrics computed over a program graph.

    Structural properties for understanding graph complexity and connectivity.
    """

    node_count: int
    """Total number of nodes in the graph."""

    edge_count: int
    """Total number of edges in the graph."""

    density: float
    """Graph density (edges / max_possible_edges)."""

    is_dag: bool
    """Whether the graph is a directed acyclic graph."""

    diameter: int | None
    """Graph diameter (max shortest path length), or None if disconnected."""


class ExportResultDict(TypedDict, total=False):
    """Result of exporting in multiple formats.

    Mapping of format name to output file path.
    """

    format: str
    """Export format (markdown, json, yaml, csv, etc.)."""

    output_path: str
    """Absolute path to the exported file."""


class AnalysisBundleDict(TypedDict, total=False):
    """Complete bundle of analysis results from a COGANT pipeline run.

    Aggregates all outputs from extraction, analysis, translation, and export.
    """

    program_graph: Any
    """The constructed program graph."""

    semantic_mappings: Any
    """Semantic role assignments (hidden states, observations, actions)."""

    gnn_bundle: GNNBundle
    """Compiled active inference GNN bundle."""

    validator_score: int
    """Validation score (0–100)."""

    timing: dict[str, float]
    """Timing for each stage (seconds)."""

    complexity_report: Any
    """Complexity analysis results."""

    coupling_report: Any
    """Coupling analysis results."""


class VisualizationResult(TypedDict, total=False):
    """Result of rendering a visualization.

    Records the output file and rendering properties.
    """

    format: str
    """Output format (png, pdf, svg, mermaid, etc.)."""

    output_path: str
    """Absolute path to the generated file."""

    width_px: int
    """Image width in pixels (if applicable)."""

    height_px: int
    """Image height in pixels (if applicable)."""

    file_size_bytes: int
    """Size of the output file in bytes."""
