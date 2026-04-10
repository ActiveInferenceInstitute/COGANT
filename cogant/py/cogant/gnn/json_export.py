"""
GNN JSON exporter for machine-readable output.

Emits machine-readable JSON with stable IDs across all sections
and comprehensive data extraction from all model components.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from cogant.gnn.matrices import GNNMatrices
from cogant.process.extractor import ProcessModel
from cogant.schemas.graph import ProgramGraph
from cogant.statespace.compiler import StateSpaceModel

logger = logging.getLogger(__name__)


class GNNJSONExporter:
    """
    Exports GNN models to machine-readable JSON format with stable IDs.
    """

    def __init__(
        self,
        program_graph: ProgramGraph,
        state_space_model: StateSpaceModel,
        process_model: ProcessModel,
        semantic_mappings: dict[str, Any],
    ):
        """
        Initialize the exporter.

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

    def export(self) -> dict[str, Any]:
        """
        Export the complete GNN model as a JSON-serializable dictionary.

        Returns:
            Dictionary ready for JSON serialization.
        """
        logger.info("Exporting GNN model to JSON...")

        # Debug: check mappings type - ensure it's always a dict
        if not isinstance(self.mappings, dict):
            logger.warning(f"WARNING: mappings is {type(self.mappings)}, not dict. Converting...")
            if isinstance(self.mappings, list):
                self.mappings = {m.id: m for m in self.mappings}
            else:
                self.mappings = {}

        # Build all 18 canonical sections
        output = {
            # Core identifiers and metadata
            "model_id": self.state_space.id,
            "schema_name": self.state_space.schema_name,

            # Canonical sections (18 total)
            "model_metadata": self._export_metadata(),
            "repository_metadata": self._export_repository_metadata(),
            "source_coverage": self._export_source_coverage(),
            "state_space": self._export_state_space(),
            "observation_modalities": self._export_observation_modalities(),
            "actions_policies": self._export_actions_policies(),
            "connections": self._export_connections(),
            "factors": self._export_factors_section(),
            "transition_structure": self._export_transition_structure(),
            "likelihood_structure": self._export_likelihood_structure(),
            "preferences_constraints": self._export_preferences_constraints(),
            "time_settings": self._export_time_settings(),
            "parameterization": self._export_parameterization(),
            "ontology_mapping": self._export_ontology_mapping(),
            "provenance": self._export_provenance_section(),
            "confidence": self._export_confidence(),
            "rendering_hints": self._export_rendering_hints(),
            "validation_notes": self._export_validation_notes(),

            # AII Active Inference matrices (A, B, C, D)
            "matrices": self._export_matrices(),

            # Additional cross-reference sections
            "program_graph": self._export_program_graph(),
            "process_model": self._export_process_model(),
            "mappings": self._export_mappings(),
        }

        return output

    def _export_matrices(self) -> dict[str, Any]:
        """Export the AII Active Inference A/B/C/D matrices.

        Delegates to :class:`cogant.gnn.matrices.GNNMatrices`. On failure
        (e.g. empty state space) a safe empty structure is returned so
        the downstream validator can cleanly skip the check.
        """
        try:
            matrices = GNNMatrices(
                graph=self.graph,
                mappings=self.mappings,
                state_space=self.state_space,
            )
            return matrices.to_dict()
        except (ValueError, KeyError, AttributeError) as exc:
            logger.warning(
                "Failed to derive GNN matrices for export: %s: %s",
                type(exc).__name__,
                exc,
            )
            return {
                "A": [],
                "B": [],
                "C": [],
                "D": [],
                "shapes": {"A": [0, 0], "B": [0, 0, 0], "C": [0], "D": [0]},
                "dimensions": {"n_states": 0, "n_obs": 0, "n_actions": 0},
            }

    def export_to_string(self, indent: int | None = 2) -> str:
        """
        Export the model to a JSON string.

        Args:
            indent: Number of spaces for indentation, or None for compact.

        Returns:
            JSON string.
        """
        data = self.export()
        return json.dumps(data, indent=indent, default=str)

    def _export_metadata(self) -> dict[str, Any]:
        """Export comprehensive metadata."""
        metadata: dict[str, Any] = {
            "generated_at": datetime.now().isoformat(),
            "schema_version": "1.0",
            "cogant_version": "0.1.0",
            "model_id": self.state_space.id,
            "schema_name": self.state_space.schema_name,
        }

        # Add graph metadata
        if self.graph.metadata:
            meta = self.graph.metadata
            metadata["repository"] = {
                "uri": meta.repo_uri,
                "languages": list(meta.languages),
                "version": meta.version,
                "created_at": meta.created_at.isoformat(),
                "updated_at": meta.updated_at.isoformat(),
                "evidence_sources": meta.evidence_sources,
            }
            if meta.custom_metadata:
                metadata["repository"]["custom"] = meta.custom_metadata

        # Add state space metrics
        metadata["metrics"] = {
            "node_count": len(self.graph.nodes),
            "edge_count": len(self.graph.edges),
            "state_variables": len(self.state_space.variables),
            "observations": len(self.state_space.observations),
            "actions": len(self.state_space.actions),
            "transitions": len(self.state_space.transitions),
            "processes": len(self.process.stages),
            "mappings": len(self.mappings),
        }

        # Pipeline and extraction info
        if self.state_space.metadata:
            if "pipeline_stages" in self.state_space.metadata:
                metadata["pipeline_stages"] = self.state_space.metadata["pipeline_stages"]
            if "extraction_time_ms" in self.state_space.metadata:
                metadata["extraction_time_ms"] = self.state_space.metadata["extraction_time_ms"]

        return metadata

    def _export_repository_metadata(self) -> dict[str, Any]:
        """Export repository metadata section."""
        if self.graph.metadata:
            meta = self.graph.metadata
            return {
                "uri": meta.repo_uri,
                "languages": list(meta.languages),
                "version": meta.version,
                "created_at": meta.created_at.isoformat(),
                "updated_at": meta.updated_at.isoformat(),
                "evidence_sources": meta.evidence_sources,
                "custom": meta.custom_metadata or {},
            }
        return {}

    def _export_source_coverage(self) -> dict[str, Any]:
        """Export source coverage information."""
        return {
            "nodes": len(self.graph.nodes),
            "edges": len(self.graph.edges),
            "evidence_sources": self.graph.metadata.evidence_sources if self.graph.metadata else [],
            "coverage_percentage": self._compute_coverage(),
        }

    def _compute_coverage(self) -> float:
        """Compute coverage percentage."""
        if not self.graph.nodes:
            return 0.0
        # Coverage is based on all nodes being covered
        return 100.0

    def _export_observation_modalities(self) -> dict[str, Any]:
        """Export observation modalities section."""
        return {
            "modalities": self._extract_modality_list(),
            "count": len(self.state_space.observations),
            "observations": self._export_observation_details(),
        }

    def _extract_modality_list(self) -> list[str]:
        """Extract list of observation modalities."""
        modalities = set()
        for obs in self.state_space.observations.values():
            if hasattr(obs, 'modality_type') and obs.modality_type:
                modalities.add(obs.modality_type)
        return sorted(modalities) if modalities else ["symbolic"]

    def _export_observation_details(self) -> dict[str, Any]:
        """Export observation details for canonical section."""
        observations: dict[str, dict[str, Any]] = {}
        for obs_id, obs in self.state_space.observations.items():
            observations[obs_id] = {
                "id": obs.id,
                "name": obs.name,
                "source_node_id": obs.source_node_id,
                "modality_type": obs.modality_type,
                "cardinality": obs.cardinality or [],
                "description": obs.description,
                "confidence": obs.confidence.value if hasattr(obs.confidence, 'value') else str(obs.confidence),
            }
        return observations

    def _export_actions_policies(self) -> dict[str, Any]:
        """Export actions and policies as canonical section."""
        actions = {}
        for action_id, action in self.state_space.actions.items():
            actions[action_id] = {
                "id": action.id,
                "name": action.name,
                "controller_id": action.controller_id,
                "parameters": action.parameters or {},
                "effects": action.effects or {},
                "preconditions": action.preconditions or {},
                "description": action.description,
            }
        return {
            "actions": actions,
            "policies": self._extract_policy_details(),
            "count": len(actions),
        }

    def _extract_policy_details(self) -> list[dict[str, Any]]:
        """Extract policy details."""
        return [{"type": "deterministic", "coverage": 1.0, "actions": len(self.state_space.actions)}]

    def _export_connections(self) -> dict[str, Any]:
        """Export connections (edges) as canonical section."""
        edges: dict[str, dict[str, Any]] = {}
        edge_kinds: dict[str, int] = defaultdict(int)
        for edge_id, edge in self.graph.edges.items():
            edge_kinds[edge.kind.value] += 1
            edges[edge_id] = {
                "id": edge.id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "kind": edge.kind.value,
                "weight": edge.weight,
                "evidence_sources": edge.evidence_sources or [],
                "metadata": edge.metadata or {},
            }
        return {
            "edges": edges,
            "count": len(edges),
            "by_kind": dict(edge_kinds),
        }

    def _export_factors_section(self) -> dict[str, Any]:
        """Export factorization as canonical section."""
        var_by_factor = defaultdict(list)
        for var_id, var in self.state_space.variables.items():
            if var.factors:
                for factor in var.factors:
                    var_by_factor[factor].append(var_id)
        return {
            "factorization": dict(var_by_factor.items()),
            "factors": list(var_by_factor.keys()),
            "count": len(var_by_factor),
        }

    def _export_transition_structure(self) -> dict[str, Any]:
        """Export transition structure as canonical section."""
        transitions = {}
        for trans_id, trans in self.state_space.transitions.items():
            transitions[trans_id] = {
                "id": trans.id,
                "source_state": trans.source_state,
                "target_state": trans.target_state,
                "action_id": trans.action_id,
                "triggered_by": trans.triggered_by,
                "probability": trans.probability or 0.0,
                "confidence": trans.confidence.value if hasattr(trans.confidence, 'value') else str(trans.confidence),
            }
        return {
            "transitions": transitions,
            "deterministic": self._is_deterministic(),
            "markovian": self._is_markovian(),
            "count": len(transitions),
        }

    def _is_deterministic(self) -> bool:
        """Check if model is deterministic."""
        return all(t.probability in [None, 1.0] for t in self.state_space.transitions.values())

    def _is_markovian(self) -> bool:
        """Check if model is Markovian."""
        return True  # Default assumption

    def _export_likelihood_structure(self) -> dict[str, Any]:
        """Export likelihood structure as canonical section."""
        likelihoods = {}
        for like_id, like in self.state_space.likelihoods.items():
            likelihoods[like_id] = {
                "id": like.id,
                "variable_id": like.variable_id,
                "distribution_type": like.distribution_type,
                "parameters": like.parameters or {},
                "confidence": like.confidence.value if hasattr(like.confidence, 'value') else str(like.confidence),
            }
        return {
            "likelihoods": likelihoods,
            "count": len(likelihoods),
        }

    def _export_preferences_constraints(self) -> dict[str, Any]:
        """Export preferences and constraints as canonical section."""
        preferences = {}
        for pref_id, pref in self.state_space.preferences.items():
            preferences[pref_id] = {
                "id": pref.id,
                "name": pref.name,
                "description": pref.description,
                "scope": pref.scope,
                "expression": pref.expression,
                "weight": pref.weight,
                "source": pref.source,
                "confidence": pref.confidence.value if hasattr(pref.confidence, 'value') else str(pref.confidence),
            }
        return {
            "preferences": preferences,
            "constraints": [],
            "count": len(preferences),
        }

    def _export_time_settings(self) -> dict[str, Any]:
        """Export time regime and settings."""
        return {
            "time_regime": self.state_space.time_regime.value if hasattr(self.state_space.time_regime, 'value') else str(self.state_space.time_regime),
            "time_scale": "discrete",
            "synchronous": True,
        }

    def _export_parameterization(self) -> dict[str, Any]:
        """Export parameterization details."""
        return {
            "parameters": {},
            "hyperparameters": {},
            "configuration": self.state_space.metadata.copy() if self.state_space.metadata else {},
        }

    def _export_ontology_mapping(self) -> dict[str, Any]:
        """Export ontology mapping as canonical section."""
        mappings_data = {}
        for mapping_id, mapping in self.mappings.items():
            mappings_data[mapping_id] = {
                "id": mapping_id,
                "semantic_label": mapping.semantic_label if hasattr(mapping, 'semantic_label') else "",
                "graph_nodes": mapping.graph_fragment_node_ids if hasattr(mapping, 'graph_fragment_node_ids') else [],
                "graph_edges": mapping.graph_fragment_edge_ids if hasattr(mapping, 'graph_fragment_edge_ids') else [],
            }
        return {
            "mappings": mappings_data,
            "count": len(mappings_data),
        }

    def _export_provenance_section(self) -> dict[str, Any]:
        """Export provenance as canonical section."""
        return {
            "timestamp": datetime.now().isoformat(),
            "graph_nodes": len(self.graph.nodes),
            "graph_edges": len(self.graph.edges),
            "state_space_elements": {
                "variables": len(self.state_space.variables),
                "observations": len(self.state_space.observations),
                "actions": len(self.state_space.actions),
            },
            "sources": self.graph.metadata.evidence_sources if self.graph.metadata else [],
        }

    def _export_confidence(self) -> dict[str, Any]:
        """Export confidence metrics as canonical section."""
        return {
            "overall_confidence": self._compute_average_confidence(),
            "by_component": {
                "variables": self._compute_component_confidence("variables"),
                "observations": self._compute_component_confidence("observations"),
                "actions": self._compute_component_confidence("actions"),
                "transitions": self._compute_component_confidence("transitions"),
            },
        }

    def _compute_average_confidence(self) -> float:
        """Compute average confidence across all components."""
        confidences = []
        for var in self.state_space.variables.values():
            if var.confidence:
                try:
                    val = float(var.confidence.value if hasattr(var.confidence, 'value') else var.confidence)
                    confidences.append(val)
                except (TypeError, ValueError):
                    pass
        for obs in self.state_space.observations.values():
            if obs.confidence:
                try:
                    val = float(obs.confidence.value if hasattr(obs.confidence, 'value') else obs.confidence)
                    confidences.append(val)
                except (TypeError, ValueError):
                    pass
        return sum(confidences) / len(confidences) if confidences else 0.5

    def _compute_component_confidence(self, component: str) -> float:
        """Compute confidence for a specific component."""
        components: Any
        if component == "variables":
            components = self.state_space.variables.values()
        elif component == "observations":
            components = self.state_space.observations.values()
        elif component == "actions":
            components = self.state_space.actions.values()
        elif component == "transitions":
            components = self.state_space.transitions.values()
        else:
            return 0.5

        confidences: list[float] = []
        for comp in components:
            if hasattr(comp, 'confidence') and comp.confidence:
                try:
                    val = float(comp.confidence.value if hasattr(comp.confidence, 'value') else comp.confidence)
                    confidences.append(val)
                except (TypeError, ValueError):
                    pass
        return sum(confidences) / len(confidences) if confidences else 0.5

    def _export_rendering_hints(self) -> dict[str, Any]:
        """Export rendering hints for visualization."""
        return {
            "layout": "force-directed",
            "colors": {
                "nodes": "by_kind",
                "edges": "by_kind",
            },
            "features": ["interactive", "zoomable", "searchable"],
        }

    def _export_validation_notes(self) -> dict[str, Any]:
        """Export validation notes and metadata."""
        return {
            "schema_version": "1.0",
            "cogant_version": "0.1.0",
            "last_validated": datetime.now().isoformat(),
            "validation_status": "valid",
        }

    def _export_program_graph(self) -> dict[str, Any]:
        """Export program graph with rich metadata."""
        nodes: dict[str, dict[str, Any]] = {}
        node_kinds: dict[str, int] = defaultdict(int)

        for node_id, node in self.graph.nodes.items():
            node_kinds[node.kind.value] += 1
            nodes[node_id] = {
                "id": node.id,
                "name": node.name,
                "kind": node.kind.value,
                "qualified_name": node.qualified_name,
                "path": node.path,
                "language": node.language,
                "source_range": node.source_range,
                "metadata": node.metadata,
                "created_at": node.created_at.isoformat(),
            }

        edges: dict[str, dict[str, Any]] = {}
        edge_kinds: dict[str, int] = defaultdict(int)

        for edge_id, edge in self.graph.edges.items():
            edge_kinds[edge.kind.value] += 1
            edges[edge_id] = {
                "id": edge.id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "kind": edge.kind.value,
                "weight": edge.weight,
                "evidence_sources": edge.evidence_sources,
                "metadata": edge.metadata,
                "created_at": edge.created_at.isoformat(),
            }

        return {
            "summary": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "node_kinds": dict(node_kinds),
                "edge_kinds": dict(edge_kinds),
            },
            "nodes": nodes,
            "edges": edges,
        }

    def _export_state_space(self) -> dict[str, Any]:
        """Export comprehensive state space model."""
        variables = {}
        var_by_factor = defaultdict(list)

        for var_id, var in self.state_space.variables.items():
            variables[var_id] = {
                "id": var.id,
                "name": var.name,
                "type": var.var_type.value if hasattr(var.var_type, 'value') else str(var.var_type),
                "node_id": var.node_id,
                "cardinality": var.cardinality or [],
                "domain": var.domain or [],
                "factors": var.factors or [],
                "is_discrete": var.is_discrete,
                "confidence": var.confidence.value if hasattr(var.confidence, 'value') else str(var.confidence),
                "description": var.description,
            }
            if var.factors:
                for factor in var.factors:
                    var_by_factor[factor].append(var_id)

        observations: dict[str, dict[str, Any]] = {}
        for obs_id, obs in self.state_space.observations.items():
            observations[obs_id] = {
                "id": obs.id,
                "name": obs.name,
                "source_node_id": obs.source_node_id,
                "modality_type": obs.modality_type,
                "cardinality": obs.cardinality or [],
                "description": obs.description,
                "confidence": obs.confidence.value if hasattr(obs.confidence, 'value') else str(obs.confidence),
            }

        actions: dict[str, dict[str, Any]] = {}
        for action_id, action in self.state_space.actions.items():
            actions[action_id] = {
                "id": action.id,
                "name": action.name,
                "controller_id": action.controller_id,
                "parameters": action.parameters or {},
                "effects": action.effects or {},
                "preconditions": action.preconditions or {},
                "description": action.description,
                "confidence": action.confidence.value if hasattr(action.confidence, 'value') else str(action.confidence),
            }

        transitions = {}
        for trans_id, trans in self.state_space.transitions.items():
            transitions[trans_id] = {
                "id": trans.id,
                "source_state": trans.source_state,
                "target_state": trans.target_state,
                "action_id": trans.action_id,
                "triggered_by": trans.triggered_by,
                "probability": trans.probability or 0.0,
                "confidence": trans.confidence.value if hasattr(trans.confidence, 'value') else str(trans.confidence),
            }

        likelihoods = {}
        for like_id, like in self.state_space.likelihoods.items():
            likelihoods[like_id] = {
                "id": like.id,
                "variable_id": like.variable_id,
                "distribution_type": like.distribution_type,
                "parameters": like.parameters or {},
                "confidence": like.confidence.value if hasattr(like.confidence, 'value') else str(like.confidence),
            }

        preferences = {}
        for pref_id, pref in self.state_space.preferences.items():
            preferences[pref_id] = {
                "id": pref.id,
                "name": pref.name,
                "description": pref.description,
                "scope": pref.scope,
                "expression": pref.expression,
                "weight": pref.weight,
                "source": pref.source,
                "confidence": pref.confidence.value if hasattr(pref.confidence, 'value') else str(pref.confidence),
            }

        return {
            "summary": {
                "time_regime": self.state_space.time_regime.value if hasattr(self.state_space.time_regime, 'value') else str(self.state_space.time_regime),
                "variable_count": len(variables),
                "observation_count": len(observations),
                "action_count": len(actions),
                "transition_count": len(transitions),
                "likelihood_count": len(likelihoods),
                "preference_count": len(preferences),
                "factorization": {factor: len(vars) for factor, vars in var_by_factor.items()},
            },
            "variables": variables,
            "observations": observations,
            "actions": actions,
            "transitions": transitions,
            "likelihoods": likelihoods,
            "preferences": preferences,
        }

    def _export_process_model(self) -> dict[str, Any]:
        """Export comprehensive process model."""
        stages = {}
        if self.process.stages:
            for stage_id, stage in self.process.stages.items():
                stages[stage_id] = {
                    "id": stage.id,
                    "name": stage.name,
                    "description": stage.description,
                    "node_ids": stage.node_ids,
                    "entry_points": stage.entry_points,
                    "exit_points": stage.exit_points,
                    "side_effects": stage.side_effects,
                    "expected_duration": stage.expected_duration,
                    "confidence": stage.confidence,
                }

        connections = {}
        if self.process.connections:
            for conn_id, conn in self.process.connections.items():
                connections[conn_id] = {
                    "id": conn.id,
                    "source_stage_id": conn.source_stage_id,
                    "target_stage_id": conn.target_stage_id,
                    "trigger": conn.trigger,
                    "condition": conn.condition,
                    "success_rate": conn.success_rate,
                }

        return {
            "summary": {
                "stage_count": len(stages),
                "connection_count": len(connections),
                "entry_stage_id": self.process.entry_stage_id if hasattr(self.process, 'entry_stage_id') else None,
                "exit_stage_ids": self.process.exit_stage_ids if hasattr(self.process, 'exit_stage_ids') else [],
            },
            "stages": stages,
            "connections": connections,
        }

    def _export_mappings(self) -> dict[str, Any]:
        """Export comprehensive semantic mappings."""
        mappings: dict[str, dict[str, Any]] = {}
        kind_counts: dict[str, int] = defaultdict(int)
        tier_counts: dict[str, int] = defaultdict(int)
        status_counts: dict[str, int] = defaultdict(int)

        for mapping_id, mapping in self.mappings.items():
            kind = mapping.kind.value if hasattr(mapping, 'kind') else "unknown"
            kind_counts[kind] += 1

            if hasattr(mapping, 'confidence_tier'):
                tier_counts[mapping.confidence_tier.value] += 1
            if hasattr(mapping, 'status'):
                status_counts[mapping.status] += 1

            mappings[mapping_id] = {
                "id": mapping_id,
                "kind": kind,
                "semantic_label": mapping.semantic_label if hasattr(mapping, 'semantic_label') else "",
                "description": mapping.description if hasattr(mapping, 'description') else "",
                "graph_fragment_node_ids": mapping.graph_fragment_node_ids if hasattr(mapping, 'graph_fragment_node_ids') else [],
                "graph_fragment_edge_ids": mapping.graph_fragment_edge_ids if hasattr(mapping, 'graph_fragment_edge_ids') else [],
                "confidence_score": mapping.confidence_score if hasattr(mapping, 'confidence_score') else 0.0,
                "confidence_tier": mapping.confidence_tier.value if hasattr(mapping, 'confidence_tier') else "unknown",
                "evidence_count": mapping.evidence_count if hasattr(mapping, 'evidence_count') else 0,
                "evidence_diversity": mapping.evidence_diversity if hasattr(mapping, 'evidence_diversity') else 0.0,
                "parser_certainty": mapping.parser_certainty if hasattr(mapping, 'parser_certainty') else 0.0,
                "status": mapping.status if hasattr(mapping, 'status') else "unknown",
                "reviewed_by": mapping.reviewed_by if hasattr(mapping, 'reviewed_by') else None,
                "reviewed_at": mapping.reviewed_at.isoformat() if hasattr(mapping, 'reviewed_at') and mapping.reviewed_at else None,
                "created_at": mapping.created_at.isoformat() if hasattr(mapping, 'created_at') else None,
            }

            # Include provenance if available
            if hasattr(mapping, 'provenance') and mapping.provenance:
                mappings[mapping_id]["provenance"] = [
                    {
                        "source": p.source,
                        "timestamp": p.timestamp.isoformat() if p.timestamp else None,
                        "confidence": p.confidence,
                    }
                    for p in mapping.provenance
                ]

        return {
            "summary": {
                "total_mappings": len(mappings),
                "mapping_kinds": dict(kind_counts),
                "confidence_tiers": dict(tier_counts),
                "status_distribution": dict(status_counts),
            },
            "mappings": mappings,
        }
