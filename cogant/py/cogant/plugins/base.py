"""Base plugin protocol classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""

    name: str
    version: str
    author: str = ""
    description: str = ""


class Plugin(ABC):
    """Base plugin class."""

    def __init__(self, metadata: PluginMetadata):
        """Initialize plugin with metadata."""
        self.metadata = metadata
        logger.info(f"Loaded plugin: {metadata.name} v{metadata.version}")

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin with configuration."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown plugin gracefully."""
        pass


class LanguagePlugin(Plugin):
    """
    Plugin for language-specific analysis.

    Provides:
      - Language detection
      - AST parsing
      - Type extraction
      - Symbol resolution
    """

    supported_languages: Set[str] = set()

    @abstractmethod
    def parse(self, source_code: str) -> Dict[str, Any]:
        """Parse source code and return AST."""
        pass

    @abstractmethod
    def extract_symbols(self, ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract symbols from AST."""
        pass

    @abstractmethod
    def extract_types(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Extract type information."""
        pass

    @abstractmethod
    def resolve_imports(self, ast: Dict[str, Any]) -> List[str]:
        """Resolve import dependencies."""
        pass


class TracePlugin(Plugin):
    """
    Plugin for dynamic trace ingestion.

    Provides:
      - Trace file parsing
      - Call graph extraction
      - Coverage parsing
      - Performance data ingestion
    """

    @abstractmethod
    def parse_trace(self, trace_file: str) -> Dict[str, Any]:
        """Parse trace file and return trace data."""
        pass

    @abstractmethod
    def parse_coverage(self, coverage_file: str) -> Dict[str, Any]:
        """Parse coverage file (coverage.xml, .coverage, etc)."""
        pass

    @abstractmethod
    def extract_call_graph(self, trace_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract call graph from trace."""
        pass


class NormalizerPlugin(Plugin):
    """
    Plugin for normalizing different representations.

    Provides:
      - Representation unification
      - Schema validation
      - Cross-language normalization
    """

    @abstractmethod
    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data to canonical form."""
        pass

    @abstractmethod
    def validate_schema(self, data: Dict[str, Any]) -> bool:
        """Validate data against schema."""
        pass


class TranslationRulePlugin(Plugin):
    """
    Plugin for custom GNN translation rules.

    Provides:
      - Custom node/edge mapping rules
      - Feature engineering
      - Custom embedding strategies
    """

    @abstractmethod
    def translate_nodes(self, graph_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Translate program graph nodes to GNN nodes."""
        pass

    @abstractmethod
    def translate_edges(self, graph_edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Translate program graph edges to GNN edges."""
        pass

    @abstractmethod
    def compute_features(self, node: Dict[str, Any]) -> List[float]:
        """Compute feature vector for a node."""
        pass


class StateSpacePlugin(Plugin):
    """
    Plugin for state space model compilation.

    Provides:
      - State extraction
      - Observation definition
      - Action mapping
      - Policy learning
    """

    @abstractmethod
    def extract_states(self, gnn_model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract states from GNN model."""
        pass

    @abstractmethod
    def extract_observations(
        self, gnn_model: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Define observation space."""
        pass

    @abstractmethod
    def extract_actions(self, gnn_model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Define action space."""
        pass

    @abstractmethod
    def learn_policies(
        self, states: List[Dict], observations: List[Dict], actions: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Learn policies from model."""
        pass


class ProcessModelPlugin(Plugin):
    """
    Plugin for process/execution model extraction.

    Provides:
      - Pipeline stage extraction
      - Dependency analysis
      - Execution ordering
    """

    @abstractmethod
    def extract_stages(self, bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract process stages."""
        pass

    @abstractmethod
    def extract_dependencies(self, stages: List[Dict]) -> List[Dict[str, Any]]:
        """Extract dependencies between stages."""
        pass

    @abstractmethod
    def compute_ordering(
        self, stages: List[Dict], dependencies: List[Dict]
    ) -> List[str]:
        """Compute execution order."""
        pass


class ExportPlugin(Plugin):
    """
    Plugin for custom export formats.

    Provides:
      - Format-specific export
      - Data transformation
      - File writing
    """

    supported_formats: Set[str] = set()

    @abstractmethod
    def export(
        self, bundle: Dict[str, Any], output_path: str, format: str
    ) -> None:
        """Export bundle in specified format."""
        pass

    @abstractmethod
    def get_format_info(self, format: str) -> Dict[str, Any]:
        """Get information about export format."""
        pass


class ValidationPlugin(Plugin):
    """
    Plugin for custom validation checks.

    Provides:
      - Data validation
      - Consistency checks
      - Quality metrics
    """

    @abstractmethod
    def validate(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Run validation checks."""
        pass

    @abstractmethod
    def compute_quality_metrics(self, bundle: Dict[str, Any]) -> Dict[str, float]:
        """Compute quality/completeness metrics."""
        pass


class VisualizationPlugin(Plugin):
    """
    Plugin for custom visualizations.

    Provides:
      - Domain-specific visualizations
      - Custom rendering
      - Interactive views
    """

    supported_visualizations: Set[str] = set()

    @abstractmethod
    def render(
        self, bundle: Dict[str, Any], output_path: str, viz_type: str
    ) -> None:
        """Render visualization."""
        pass

    @abstractmethod
    def get_viz_info(self, viz_type: str) -> Dict[str, Any]:
        """Get information about visualization type."""
        pass
