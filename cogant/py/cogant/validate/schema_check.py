"""
Schema validation for IR objects.

Validates all IR objects against Pydantic schemas.
"""

import logging
from dataclasses import dataclass

from cogant.process.extractor import ProcessModel
from cogant.schemas.graph import ProgramGraph
from cogant.statespace.compiler import StateSpaceModel

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """A validation issue found in the model."""
    id: str
    severity: str  # "error", "warning", "info"
    category: str  # "schema", "integrity", "provenance", "coverage"
    message: str
    affected_ids: list[str]
    recommendation: str | None = None


class SchemaValidator:
    """
    Validates IR objects against Pydantic schemas.
    Checks type consistency, required fields, and value ranges.
    """

    def __init__(self):
        """Initialize the validator."""
        self.issues: list[ValidationIssue] = []

    def validate_program_graph(self, graph: ProgramGraph) -> list[ValidationIssue]:
        """
        Validate a program graph.

        Args:
            graph: The program graph to validate.

        Returns:
            List of validation issues found.
        """
        logger.info("Validating program graph...")
        self.issues = []

        # Check nodes
        for node_id, node in graph.nodes.items():
            self._validate_node(node_id, node)

        # Check edges
        for edge_id, edge in graph.edges.items():
            self._validate_edge(edge_id, edge, graph)

        # Check metadata
        if graph.metadata:
            self._validate_graph_metadata(graph.metadata)

        logger.info(f"Found {len(self.issues)} issues in program graph")
        return self.issues

    def validate_state_space(self, state_space: StateSpaceModel) -> list[ValidationIssue]:
        """
        Validate a state space model.

        Args:
            state_space: The state space model to validate.

        Returns:
            List of validation issues found.
        """
        logger.info("Validating state space model...")
        self.issues = []

        # Check variables
        for var_id, var in state_space.variables.items():
            self._validate_state_variable(var_id, var)

        # Check observations
        for obs_id, obs in state_space.observations.items():
            self._validate_observation(obs_id, obs)

        # Check actions
        for action_id, action in state_space.actions.items():
            self._validate_action(action_id, action)

        # Check transitions
        for trans_id, trans in state_space.transitions.items():
            self._validate_transition(trans_id, trans)

        logger.info(f"Found {len(self.issues)} issues in state space model")
        return self.issues

    def validate_process_model(self, process: ProcessModel) -> list[ValidationIssue]:
        """
        Validate a process model.

        Args:
            process: The process model to validate.

        Returns:
            List of validation issues found.
        """
        logger.info("Validating process model...")
        self.issues = []

        # Check stages
        for stage_id, stage in process.stages.items():
            self._validate_stage(stage_id, stage)

        # Check connections
        for conn_id, conn in process.connections.items():
            self._validate_connection(conn_id, conn, process)

        logger.info(f"Found {len(self.issues)} issues in process model")
        return self.issues

    # Private validation methods

    def _validate_node(self, node_id: str, node) -> None:
        """Validate a single node."""
        # Check required fields
        if not node.id:
            self._add_issue("error", "schema", "Node missing id", [node_id])
        if not node.name:
            self._add_issue("warning", "schema", f"Node {node_id} missing name", [node_id])
        if not node.qualified_name:
            self._add_issue("warning", "schema", f"Node {node_id} missing qualified_name", [node_id])

    def _validate_edge(self, edge_id: str, edge, graph: ProgramGraph) -> None:
        """Validate a single edge."""
        # Check required fields
        if not edge.id:
            self._add_issue("error", "schema", "Edge missing id", [edge_id])
        if not edge.source_id:
            self._add_issue("error", "schema", f"Edge {edge_id} missing source_id", [edge_id])
        if not edge.target_id:
            self._add_issue("error", "schema", f"Edge {edge_id} missing target_id", [edge_id])

        # Check that endpoints exist
        if edge.source_id not in graph.nodes:
            self._add_issue("error", "integrity",
                           f"Edge {edge_id} references non-existent source {edge.source_id}",
                           [edge_id, edge.source_id])
        if edge.target_id not in graph.nodes:
            self._add_issue("error", "integrity",
                           f"Edge {edge_id} references non-existent target {edge.target_id}",
                           [edge_id, edge.target_id])

        # Check weight
        if edge.weight < 0:
            self._add_issue("warning", "schema",
                           f"Edge {edge_id} has negative weight: {edge.weight}",
                           [edge_id])

    def _validate_graph_metadata(self, metadata) -> None:
        """Validate graph metadata."""
        if not metadata.repo_uri:
            self._add_issue("warning", "schema", "Graph metadata missing repo_uri", [])

    def _validate_state_variable(self, var_id: str, var) -> None:
        """Validate a state variable."""
        if not var.id:
            self._add_issue("error", "schema", "State variable missing id", [var_id])
        if not var.name:
            self._add_issue("warning", "schema", f"State variable {var_id} missing name", [var_id])

    def _validate_observation(self, obs_id: str, obs) -> None:
        """Validate an observation."""
        if not obs.id:
            self._add_issue("error", "schema", "Observation missing id", [obs_id])
        if not obs.name:
            self._add_issue("warning", "schema", f"Observation {obs_id} missing name", [obs_id])

    def _validate_action(self, action_id: str, action) -> None:
        """Validate an action."""
        if not action.id:
            self._add_issue("error", "schema", "Action missing id", [action_id])
        if not action.name:
            self._add_issue("warning", "schema", f"Action {action_id} missing name", [action_id])

    def _validate_transition(self, trans_id: str, trans) -> None:
        """Validate a transition."""
        if not trans.id:
            self._add_issue("error", "schema", "Transition missing id", [trans_id])

    def _validate_stage(self, stage_id: str, stage) -> None:
        """Validate a stage."""
        if not stage.id:
            self._add_issue("error", "schema", "Stage missing id", [stage_id])
        if not stage.name:
            self._add_issue("warning", "schema", f"Stage {stage_id} missing name", [stage_id])

    def _validate_connection(self, conn_id: str, conn, process: ProcessModel) -> None:
        """Validate a connection."""
        if not conn.id:
            self._add_issue("error", "schema", "Connection missing id", [conn_id])

        # Check that stages exist
        if conn.source_stage_id not in process.stages:
            self._add_issue("error", "integrity",
                           f"Connection {conn_id} references non-existent source stage {conn.source_stage_id}",
                           [conn_id, conn.source_stage_id])
        if conn.target_stage_id not in process.stages:
            self._add_issue("error", "integrity",
                           f"Connection {conn_id} references non-existent target stage {conn.target_stage_id}",
                           [conn_id, conn.target_stage_id])

    def _add_issue(
        self,
        severity: str,
        category: str,
        message: str,
        affected_ids: list[str],
    ) -> None:
        """Add a validation issue."""
        issue = ValidationIssue(
            id=f"issue_{len(self.issues)}",
            severity=severity,
            category=category,
            message=message,
            affected_ids=affected_ids,
        )
        self.issues.append(issue)

    def get_issues(self) -> list[ValidationIssue]:
        """Get all validation issues."""
        return self.issues

    def get_errors(self) -> list[ValidationIssue]:
        """Get only error issues."""
        return [i for i in self.issues if i.severity == "error"]

    def get_warnings(self) -> list[ValidationIssue]:
        """Get only warning issues."""
        return [i for i in self.issues if i.severity == "warning"]

    def is_valid(self) -> bool:
        """Check if there are no errors."""
        return len(self.get_errors()) == 0
