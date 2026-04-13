"""Protocol (structural typing) definitions for COGANT.

This module defines Protocol classes that specify structural contracts for
key components across the COGANT pipeline. Protocols enable structural
subtyping and late binding without requiring explicit inheritance.

All Protocols are runtime-checkable where appropriate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from cogant.schemas.graph import ProgramGraph
    from cogant.schemas.semantic_mapping import SemanticMapping

__all__ = [
    "Translatable",
    "Analyzable",
    "Serializable",
    "Visualizable",
    "Validatable",
    "Exportable",
    "Exportable2",
    "PipelineStage",
    "TranslationRule",
    "GraphBackend",
    "StaticAnalyzer",
    "DiagramRenderer",
    "ReportGenerator",
    "NetworkAnalyzer",
]


# ============================================================================
# Core Protocol Interfaces
# ============================================================================


@runtime_checkable
class Translatable(Protocol):
    """Protocol for objects that can be translated to semantic mappings.

    A Translatable implements the core translation step of the COGANT
    pipeline: taking a program graph and producing semantic mappings
    (assignments of hidden states, observations, actions, etc.).
    """

    def translate(self, graph: ProgramGraph) -> SemanticMapping:
        """Translate a program graph to semantic mappings.

        Args:
            graph: The program graph to translate.

        Returns:
            SemanticMapping representing the translation result.
        """
        ...


@runtime_checkable
class Analyzable(Protocol):
    """Protocol for objects that can be analyzed for properties and metrics.

    An Analyzable provides introspection capabilities, returning structured
    analysis results (e.g., complexity, coverage, connectivity metrics).
    """

    def analyze(self) -> dict[str, Any]:
        """Analyze the object and return a dictionary of metrics.

        Returns:
            Dictionary with analysis results (keys may include 'complexity',
            'coverage', 'density', 'node_count', etc.).
        """
        ...


@runtime_checkable
class Serializable(Protocol):
    """Protocol for objects that can be serialized to and from dictionaries.

    A Serializable can be converted to a plain dict representation (for
    JSON/YAML serialization) and reconstructed from that dict.
    """

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary suitable for JSON/YAML serialization.
        """
        ...

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Serializable:
        """Reconstruct from dictionary representation.

        Args:
            d: Dictionary produced by to_dict().

        Returns:
            Instance reconstructed from the dictionary.
        """
        ...


@runtime_checkable
class Visualizable(Protocol):
    """Protocol for objects that can be visualized in multiple formats.

    A Visualizable can produce Mermaid diagrams (for markdown) and PNG
    images (for detailed rendering).
    """

    def to_mermaid(self) -> str:
        """Generate a Mermaid diagram string.

        Returns:
            Mermaid diagram specification (markdown-compatible).
        """
        ...

    def to_png(self, output_path: str) -> str:
        """Generate a PNG image file.

        Args:
            output_path: File path where PNG will be written.

        Returns:
            Absolute path to the generated PNG file.
        """
        ...


@runtime_checkable
class Validatable(Protocol):
    """Protocol for objects that can be validated for correctness.

    A Validatable performs self-checks and returns a list of issues
    (errors, warnings, or info) found during validation.
    """

    def validate(self) -> list[str]:
        """Validate the object and return issues found.

        Returns:
            List of validation issue strings. Empty list if valid.
        """
        ...


@runtime_checkable
class Exportable(Protocol):
    """Protocol for objects that can be exported in multiple formats.

    An Exportable can write itself to disk in various formats
    (markdown, JSON, YAML, etc.).
    """

    def export(self, output_path: str, format: str) -> str:
        """Export to file in the specified format.

        Args:
            output_path: Directory or file path where output will be written.
            format: Export format ('markdown', 'json', 'yaml', etc.).

        Returns:
            Absolute path to the exported file.
        """
        ...


# ============================================================================
# Pipeline Protocol Interfaces
# ============================================================================


@runtime_checkable
class PipelineStage(Protocol):
    """Protocol for stages in the COGANT processing pipeline.

    A PipelineStage is a self-contained step (extract, build, translate,
    export) that processes a context and produces a result.
    """

    name: str
    """Human-readable name of this stage."""

    def run(self, context: Any) -> Any:
        """Execute this stage.

        Args:
            context: Pipeline context containing prior stage outputs,
                configuration, and shared state.

        Returns:
            Stage result (typically an updated context or StageResult object).
        """
        ...


# ============================================================================
# Translation Protocol Interfaces
# ============================================================================


@runtime_checkable
class TranslationRule(Protocol):
    """Protocol for translation rules applied by the fixpoint engine.

    A TranslationRule encapsulates a single declarative translation rule:
    a predicate (applies_to) and an action (apply). The fixpoint engine
    iterates over rules until no more rules fire (fixpoint reached).
    """

    name: str
    """Stable rule identifier (e.g., 'rule_hidden_state_from_class')."""

    family: str
    """Rule family: 'structural', 'semantic', 'control', 'behavioral',
    or 'resilience'."""

    def applies_to(self, node: Any, graph: ProgramGraph) -> bool:
        """Check if this rule applies to the given node.

        Args:
            node: GraphNode to test.
            graph: Full program graph for contextual checks.

        Returns:
            True if the rule should fire on this node.
        """
        ...

    def apply(self, node: Any, graph: ProgramGraph) -> Any:
        """Apply the rule to the given node.

        Should only be called if applies_to() returned True.

        Args:
            node: GraphNode to process.
            graph: Full program graph for contextual operations.

        Returns:
            RuleResult containing the semantic mapping produced.
        """
        ...


# ============================================================================
# Graph Backend Protocol Interface
# ============================================================================


@runtime_checkable
class GraphBackend(Protocol):
    """Protocol for graph storage backends.

    A GraphBackend abstracts the underlying storage (networkx, PyArrow,
    database, etc.) so the graph operations can be backend-agnostic.
    """

    def add_node(self, id: str, **attrs: Any) -> None:
        """Add a node to the graph.

        Args:
            id: Unique node identifier.
            **attrs: Arbitrary node attributes (kind, name, file, etc.).
        """
        ...

    def add_edge(self, src: str, dst: str, **attrs: Any) -> None:
        """Add an edge (relationship) to the graph.

        Args:
            src: Source node ID.
            dst: Destination node ID.
            **attrs: Arbitrary edge attributes (kind, weight, etc.).
        """
        ...

    def nodes(self) -> list[str]:
        """Return list of all node IDs in the graph.

        Returns:
            List of node identifiers.
        """
        ...

    def edges(self) -> list[tuple[str, str]]:
        """Return list of all edges in the graph.

        Returns:
            List of (source_id, destination_id) tuples.
        """
        ...


# ============================================================================
# Additional Protocol Interfaces
# ============================================================================


@runtime_checkable
class StaticAnalyzer(Protocol):
    """Protocol for static analysis tools.

    A StaticAnalyzer examines source code and produces a dictionary of
    metrics and findings without executing the code.
    """

    def analyze(self, source: str) -> dict[str, Any]:
        """Analyze source code and return metrics.

        Args:
            source: Source code as a string.

        Returns:
            Dictionary of analysis results (metrics, findings, etc.).
        """
        ...


@runtime_checkable
class DiagramRenderer(Protocol):
    """Protocol for rendering diagrams in multiple formats.

    A DiagramRenderer produces visual output (Mermaid, PNG, PDF) from
    graph or analysis data structures.
    """

    def to_mermaid(self) -> str:
        """Generate a Mermaid diagram.

        Returns:
            Mermaid diagram specification as a string.
        """
        ...

    def to_png(self, output_path: str) -> str:
        """Generate a PNG image file.

        Args:
            output_path: File path where PNG will be written.

        Returns:
            Absolute path to the generated PNG file.
        """
        ...


@runtime_checkable
class ReportGenerator(Protocol):
    """Protocol for generating human-readable reports.

    A ReportGenerator formats analysis results into readable text and
    visual reports (PDF, HTML, Markdown, etc.).
    """

    def generate(self, data: Any) -> str:
        """Generate a report as a string.

        Args:
            data: Data structure to format into a report.

        Returns:
            Report content as a string (may include formatting).
        """
        ...

    def to_pdf(self, output_path: str) -> str:
        """Generate a PDF report file.

        Args:
            output_path: File path where PDF will be written.

        Returns:
            Absolute path to the generated PDF file.
        """
        ...


@runtime_checkable
class NetworkAnalyzer(Protocol):
    """Protocol for analyzing graph/network structures.

    A NetworkAnalyzer computes graph metrics, finds communities, and
    identifies structural patterns in networks.
    """

    def compute_metrics(self) -> dict[str, Any]:
        """Compute network metrics.

        Returns:
            Dictionary of graph metrics (node_count, density, etc.).
        """
        ...

    def find_communities(self) -> list[frozenset[str]]:
        """Find communities (clusters) in the network.

        Returns:
            List of communities, each as a frozenset of node IDs.
        """
        ...


@runtime_checkable
class Exportable2(Protocol):
    """Protocol for exporting in multiple formats with batch export.

    An Exportable2 extends Exportable with support for exporting to
    multiple formats in a single operation.
    """

    def export_all(self, output_dir: str, formats: list[str]) -> dict[str, str]:
        """Export to multiple formats at once.

        Args:
            output_dir: Directory where output files will be written.
            formats: List of desired export formats.

        Returns:
            Dictionary mapping format name to output file path.
        """
        ...
