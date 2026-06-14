"""
GNN markdown formatter with canonical section ordering.

Emits comprehensive GNN markdown with all sections in proper order:
Model Metadata, Repository Metadata, Source Coverage, State Space,
Observation Modalities, Actions/Policies, Connections, Factors,
Transition Structure, Likelihood Structure, Preferences/Constraints,
Time Settings, Parameterization, Ontology Mapping, Provenance,
Confidence, Rendering Hints, Validation Notes.
"""

import logging
import traceback
from typing import Any

from cogant.gnn.formatter.dynamics import _DynamicsSectionsMixin
from cogant.gnn.formatter.metadata import _MetadataSectionsMixin
from cogant.gnn.formatter.semantic import _SemanticSectionsMixin
from cogant.gnn.formatter.structural import _StructuralSectionsMixin
from cogant.gnn.formatter.upstream import (
    _UpstreamSectionsMixin,
)
from cogant.process.extractor import ProcessModel
from cogant.schemas.core import EdgeKind
from cogant.schemas.graph import ProgramGraph
from cogant.statespace.compiler import StateSpaceModel

logger = logging.getLogger(__name__)


class GNNMarkdownFormatter(
    _UpstreamSectionsMixin,
    _MetadataSectionsMixin,
    _StructuralSectionsMixin,
    _DynamicsSectionsMixin,
    _SemanticSectionsMixin,
):
    """
    Formats complete GNN models to canonical markdown with all sections.

    The emitted markdown is simultaneously a valid upstream GNN v2.0.0-engine file
    (containing ``## GNNSection``, ``## GNNVersionAndFlags``,
    ``## ModelName``, ``## StateSpaceBlock``, ``## Connections``,
    ``## InitialParameterization``, ``## Equations``, ``## Time``,
    ``## ActInfOntologyAnnotation``, ``## ModelParameters``, ``## Footer``,
    and ``## Signature``) and a COGANT-extended bundle with
    richer metadata, provenance, Markov blanket, and validation
    sections appended below the upstream header.
    """

    # Canonical section order. The upstream GNN v2.0.0 header comes FIRST
    # so the file parses cleanly in the upstream type-checker
    # (``src/5_type_checker.py``). COGANT's extended sections follow and
    # are treated as ignored extras by upstream tooling.
    SECTION_ORDER = [
        "upstream_header",
        "model_metadata",
        "repository_metadata",
        "source_coverage",
        "state_space",
        "observation_modalities",
        "actions_policies",
        "program_graph_connections",
        "factors",
        "transition_structure",
        "likelihood_structure",
        "preferences_constraints",
        "time_settings",
        "parameterization",
        "ontology_mapping",
        "markov_blanket",
        "provenance",
        "confidence",
        "rendering_hints",
        "validation_notes",
    ]

    def __init__(
        self,
        program_graph: ProgramGraph,
        state_space_model: StateSpaceModel,
        process_model: ProcessModel,
        semantic_mappings: dict[str, Any],
    ):
        """
        Initialize the formatter.

        Args:
            program_graph: The program graph.
            state_space_model: The state space model.
            process_model: The process model.
            semantic_mappings: Semantic mappings dictionary.
        """
        self.graph = program_graph
        self.state_space = state_space_model
        self.process = process_model
        self.mappings = semantic_mappings

    def format(self) -> str:
        """
        Format the complete GNN model as markdown.

        Returns:
            Formatted markdown string.
        """
        logger.info("Formatting GNN model to markdown...")

        # Debug: check mappings type
        if not isinstance(self.mappings, dict):
            logger.warning(f"WARNING: mappings is {type(self.mappings)}, not dict. Converting...")
            if isinstance(self.mappings, list):
                self.mappings = {m.id: m for m in self.mappings}
            else:
                self.mappings = {}

        sections = {}
        methods = [
            ("upstream_header", self._format_upstream_header),
            ("model_metadata", self._format_model_metadata),
            ("repository_metadata", self._format_repository_metadata),
            ("source_coverage", self._format_source_coverage),
            ("state_space", self._format_state_space),
            ("observation_modalities", self._format_observation_modalities),
            ("actions_policies", self._format_actions_policies),
            ("program_graph_connections", self._format_connections),
            ("factors", self._format_factors),
            ("transition_structure", self._format_transition_structure),
            ("likelihood_structure", self._format_likelihood_structure),
            ("preferences_constraints", self._format_preferences),
            ("time_settings", self._format_time_settings),
            ("parameterization", self._format_parameterization),
            ("ontology_mapping", self._format_ontology_mapping),
            ("markov_blanket", self._format_markov_blanket),
            ("provenance", self._format_provenance),
            ("confidence", self._format_confidence),
            ("rendering_hints", self._format_rendering_hints),
            ("validation_notes", self._format_validation_notes),
        ]

        for section_name, method in methods:
            try:
                sections[section_name] = method()
            except Exception as e:
                logger.error(f"Failed to format {section_name}: {type(e).__name__}: {e}")
                traceback.print_exc()
                sections[section_name] = f"[Error formatting {section_name}: {e}]"

        # Emit in canonical order
        output = []
        for section_name in self.SECTION_ORDER:
            if section_name in sections and sections[section_name]:
                output.append(sections[section_name])

        return "\n\n".join(output)

    @staticmethod
    def _action_effects(action: Any) -> list[str]:
        """Read action effects across schema variants."""
        effects = getattr(action, "effects", None)
        if effects is None:
            effects = getattr(action, "affects_state_vars", None)
        return list(effects or [])

    def _derive_probability_from_edges(self, action_id: str | None) -> float | None:
        """
        Derive action transition probability from edge weights in the graph.

        Args:
            action_id: The action ID or name to look up in graph.

        Returns:
            Normalized probability derived from edge weights, or None if not found.
        """
        if not action_id:
            return None

        # Find action node in graph
        action_node = None
        for node in self.graph.nodes.values():
            if action_id in node.id or action_id in node.name:
                action_node = node
                break

        if not action_node:
            return None

        # Get CALLS and WRITES edges from action
        outgoing_edges = self.graph.get_edges_from(action_node.id)
        total_weight = 0.0
        edge_count = 0

        for edge in outgoing_edges:
            if edge.kind in (EdgeKind.CALLS, EdgeKind.WRITES, EdgeKind.RETURNS):
                total_weight += edge.weight
                edge_count += 1

        if edge_count > 0:
            # Normalize weight to [0, 1]
            avg_weight = total_weight / edge_count
            return min(1.0, avg_weight / 10.0) if avg_weight > 0 else 0.5

        return None

    def format_section(self, section_name: str) -> str | None:
        """
        Format a specific section.

        Args:
            section_name: Name of the section.

        Returns:
            Formatted section or None.
        """
        method_name = f"_format_{section_name}"
        if hasattr(self, method_name):
            result: str | None = getattr(self, method_name)()
            return result
        return None
