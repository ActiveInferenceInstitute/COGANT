"""
JSON Schema export for COGANT data structures.

Generates JSON Schema (draft 7 / 2020-12 compliant) for GNN bundles,
program graphs, semantic mappings, and pipeline results with examples.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class JSONSchemaExporter:
    """Export JSON Schema definitions for COGANT data structures."""

    def __init__(self) -> None:
        """Initialize the JSONSchemaExporter."""
        pass

    def export_gnn_bundle_schema(self) -> dict[str, Any]:
        """
        Export JSON Schema for GNN bundle format.

        Returns:
            JSON Schema dict (draft 7 compatible) for the complete GNN bundle.
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "COGANT GNN Bundle",
            "description": "Complete GNN bundle with state space matrices and metadata",
            "type": "object",
            "required": ["metadata", "state_space", "matrices"],
            "properties": {
                "metadata": {
                    "type": "object",
                    "description": "Bundle metadata and provenance",
                    "required": ["id", "schema_name", "created_at"],
                    "properties": {
                        "id": {"type": "string", "description": "Unique bundle identifier"},
                        "schema_name": {
                            "type": "string",
                            "description": "Name of the Active Inference schema",
                        },
                        "created_at": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Bundle creation timestamp",
                        },
                        "version": {"type": "string", "description": "COGANT version"},
                    },
                },
                "state_space": {
                    "type": "object",
                    "description": "State space definition",
                    "required": ["hidden_states", "observations", "actions"],
                    "properties": {
                        "hidden_states": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of hidden state variables",
                        },
                        "observations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of observation variables",
                        },
                        "actions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of action variables",
                        },
                        "policies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of policy variables",
                        },
                    },
                },
                "matrices": {
                    "type": "object",
                    "description": "Active Inference matrices (A, B, C, D)",
                    "properties": {
                        "A": {
                            "type": "array",
                            "description": "Observation model (likelihood)",
                            "items": {
                                "type": "array",
                                "items": {"type": "number"},
                            },
                        },
                        "B": {
                            "type": "array",
                            "description": "Transition model",
                            "items": {
                                "type": "array",
                                "items": {"type": "number"},
                            },
                        },
                        "C": {
                            "type": "array",
                            "description": "Preference (goal) model",
                            "items": {"type": "number"},
                        },
                        "D": {
                            "type": "array",
                            "description": "Prior belief distribution",
                            "items": {"type": "number"},
                        },
                    },
                },
            },
            "example": {
                "metadata": {
                    "id": "bundle_12345",
                    "schema_name": "CalcAgent",
                    "created_at": "2026-04-13T12:00:00Z",
                    "version": "0.5.0",
                },
                "state_space": {
                    "hidden_states": ["user_input", "calc_state"],
                    "observations": ["display_value"],
                    "actions": ["compute", "display"],
                    "policies": ["eval_policy"],
                },
                "matrices": {
                    "A": [[0.95, 0.05], [0.05, 0.95]],
                    "B": [[0.9, 0.1], [0.1, 0.9]],
                    "C": [1.0, 0.0],
                    "D": [0.5, 0.5],
                },
            },
        }

    def export_program_graph_schema(self) -> dict[str, Any]:
        """
        Export JSON Schema for ProgramGraph serialization.

        Returns:
            JSON Schema dict for program graph format.
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "COGANT Program Graph",
            "description": "Typed program graph with nodes, edges, and metadata",
            "type": "object",
            "required": ["metadata", "nodes", "edges"],
            "properties": {
                "metadata": {
                    "type": "object",
                    "description": "Graph metadata",
                    "required": ["repo_uri", "version", "created_at"],
                    "properties": {
                        "repo_uri": {"type": "string", "description": "Repository URI"},
                        "languages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Detected programming languages",
                        },
                        "version": {"type": "string", "description": "Graph version"},
                        "created_at": {
                            "type": "string",
                            "format": "date-time",
                        },
                        "updated_at": {
                            "type": "string",
                            "format": "date-time",
                        },
                        "node_count": {"type": "integer", "minimum": 0},
                        "edge_count": {"type": "integer", "minimum": 0},
                    },
                },
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "kind", "name", "qualified_name"],
                        "properties": {
                            "id": {"type": "string", "description": "Unique node ID"},
                            "kind": {
                                "type": "string",
                                "enum": [
                                    "class",
                                    "function",
                                    "method",
                                    "module",
                                    "variable",
                                    "endpoint",
                                    "data_structure",
                                    "test",
                                    "policy",
                                    "action",
                                ],
                                "description": "Node type/role",
                            },
                            "name": {"type": "string", "description": "Node name"},
                            "qualified_name": {
                                "type": "string",
                                "description": "Fully qualified name",
                            },
                            "path": {"type": ["string", "null"]},
                            "language": {"type": ["string", "null"]},
                            "source_range": {"type": "object"},
                            "created_at": {"type": "string", "format": "date-time"},
                        },
                    },
                },
                "edges": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "source_id", "target_id", "kind"],
                        "properties": {
                            "id": {"type": "string"},
                            "source_id": {"type": "string"},
                            "target_id": {"type": "string"},
                            "kind": {"type": "string"},
                            "weight": {"type": "number", "default": 1.0},
                            "created_at": {"type": "string", "format": "date-time"},
                        },
                    },
                },
            },
        }

    def export_semantic_mappings_schema(self) -> dict[str, Any]:
        """
        Export JSON Schema for SemanticMappings serialization.

        Returns:
            JSON Schema dict for semantic mappings.
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "COGANT Semantic Mappings",
            "description": "Semantic role mappings from program graph to AII",
            "type": "object",
            "required": ["mappings"],
            "properties": {
                "mappings": {
                    "type": "object",
                    "description": "Node ID to semantic role mapping",
                    "additionalProperties": {
                        "type": "object",
                        "required": ["role", "confidence"],
                        "properties": {
                            "role": {
                                "type": "string",
                                "enum": [
                                    "HIDDEN_STATE",
                                    "OBSERVATION",
                                    "ACTION",
                                    "POLICY",
                                    "CONTEXT",
                                    "CONFIG",
                                    "UTILITY",
                                    "CONSTRAINT",
                                ],
                                "description": "Semantic role in AII",
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Confidence score",
                            },
                            "evidence": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Evidence supporting the mapping",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Additional mapping metadata",
                            },
                        },
                    },
                }
            },
            "example": {
                "mappings": {
                    "node_calc_state": {
                        "role": "HIDDEN_STATE",
                        "confidence": 0.92,
                        "evidence": ["state_variable", "type_analysis"],
                        "metadata": {"inferred_by": "structural_rule"},
                    }
                }
            },
        }

    def export_pipeline_result_schema(self) -> dict[str, Any]:
        """
        Export JSON Schema for PipelineResult serialization.

        Returns:
            JSON Schema dict for pipeline results.
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "COGANT Pipeline Result",
            "description": "Complete pipeline execution result with all artifacts",
            "type": "object",
            "required": ["id", "status", "program_graph", "semantic_mappings"],
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Pipeline execution ID",
                },
                "status": {
                    "type": "string",
                    "enum": ["success", "failure", "partial"],
                    "description": "Pipeline execution status",
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Execution timestamp",
                },
                "duration_seconds": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Total execution time",
                },
                "program_graph": {
                    "$ref": "#/definitions/program_graph_ref",
                    "description": "Serialized program graph",
                },
                "semantic_mappings": {
                    "$ref": "#/definitions/semantic_mappings_ref",
                    "description": "Node semantic role mappings",
                },
                "state_space_model": {
                    "type": "object",
                    "description": "Compiled Active Inference state space",
                },
                "gnn_bundle": {
                    "$ref": "#/definitions/gnn_bundle_ref",
                    "description": "GNN bundle with matrices",
                },
                "validation_results": {
                    "type": "object",
                    "description": "Validation and scoring results",
                    "properties": {
                        "passed": {"type": "boolean"},
                        "findings": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "severity": {
                                        "type": "string",
                                        "enum": ["error", "warning", "info"],
                                    },
                                    "message": {"type": "string"},
                                },
                            },
                        },
                        "score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                        },
                    },
                },
                "config": {
                    "type": "object",
                    "description": "Pipeline configuration used",
                },
            },
            "definitions": {
                "program_graph_ref": {"type": "object"},
                "semantic_mappings_ref": {"type": "object"},
                "gnn_bundle_ref": {"type": "object"},
            },
        }
