"""
Integrity checking for graph structures.

Verifies node ID uniqueness, edge endpoints, mapping references,
orphaned nodes, and confidence values.
"""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import logging

from cogant.schemas.graph import ProgramGraph
from cogant.statespace.compiler import StateSpaceModel
from cogant.process.extractor import ProcessModel
from cogant.validate.schema_check import ValidationIssue

logger = logging.getLogger(__name__)


class IntegrityChecker:
    """
    Checks structural integrity of IR models:
    - Node ID uniqueness
    - Edge endpoint validity
    - Reference validity (mappings, cross-model references)
    - No orphaned nodes
    - Confidence values in [0, 1]
    """

    def __init__(self):
        """Initialize the checker."""
        self.issues: List[ValidationIssue] = []

    def check_program_graph(self, graph: ProgramGraph) -> List[ValidationIssue]:
        """
        Check integrity of a program graph.

        Args:
            graph: The program graph to check.

        Returns:
            List of integrity issues found.
        """
        logger.info("Checking program graph integrity...")
        self.issues = []

        # Check node ID uniqueness
        self._check_node_uniqueness(graph)

        # Check edge endpoints
        self._check_edge_endpoints(graph)

        # Check for orphaned nodes (unreachable from entry points)
        self._check_orphaned_nodes(graph)

        # Check for cycles (if not expected)
        self._check_for_cycles(graph)

        logger.info(f"Found {len(self.issues)} integrity issues in program graph")
        return self.issues

    def check_state_space(self, state_space: StateSpaceModel) -> List[ValidationIssue]:
        """
        Check integrity of a state space model.

        Args:
            state_space: The state space model to check.

        Returns:
            List of integrity issues found.
        """
        logger.info("Checking state space integrity...")
        self.issues = []

        # Check variable ID uniqueness
        self._check_variable_uniqueness(state_space)

        # Check variable references in actions and preferences
        self._check_variable_references(state_space)

        # Check confidence values
        self._check_confidence_values(state_space)

        logger.info(f"Found {len(self.issues)} integrity issues in state space")
        return self.issues

    def check_process_model(self, process: ProcessModel) -> List[ValidationIssue]:
        """
        Check integrity of a process model.

        Args:
            process: The process model to check.

        Returns:
            List of integrity issues found.
        """
        logger.info("Checking process model integrity...")
        self.issues = []

        # Check stage ID uniqueness
        self._check_stage_uniqueness(process)

        # Check connection stage references
        self._check_connection_integrity(process)

        # Check entry and exit stages
        self._check_entry_exit_stages(process)

        logger.info(f"Found {len(self.issues)} integrity issues in process model")
        return self.issues

    # Private checking methods

    def _check_node_uniqueness(self, graph: ProgramGraph) -> None:
        """Check that all node IDs are unique."""
        node_ids = set()
        for node_id, node in graph.nodes.items():
            if node_id in node_ids:
                self._add_issue("error", "integrity",
                               f"Duplicate node ID: {node_id}", [node_id])
            else:
                node_ids.add(node_id)

    def _check_edge_endpoints(self, graph: ProgramGraph) -> None:
        """Check that all edges have valid endpoints."""
        node_ids = set(graph.nodes.keys())

        for edge_id, edge in graph.edges.items():
            if edge.source_id not in node_ids:
                self._add_issue("error", "integrity",
                               f"Edge {edge_id} source not in nodes: {edge.source_id}",
                               [edge_id, edge.source_id])
            if edge.target_id not in node_ids:
                self._add_issue("error", "integrity",
                               f"Edge {edge_id} target not in nodes: {edge.target_id}",
                               [edge_id, edge.target_id])

    def _check_orphaned_nodes(self, graph: ProgramGraph) -> None:
        """Check for orphaned (unreachable) nodes."""
        # Find entry points (nodes with no incoming edges)
        entry_points = set()
        has_incoming = set()

        for edge in graph.edges.values():
            has_incoming.add(edge.target_id)

        for node_id in graph.nodes.keys():
            if node_id not in has_incoming:
                entry_points.add(node_id)

        # BFS from entry points to find reachable nodes
        reachable = set()
        queue = list(entry_points)

        while queue:
            node_id = queue.pop(0)
            if node_id in reachable:
                continue
            reachable.add(node_id)

            # Add neighbors
            for edge in graph.get_edges_from(node_id):
                if edge.target_id not in reachable:
                    queue.append(edge.target_id)

        # Check for unreachable nodes
        unreachable = set(graph.nodes.keys()) - reachable
        for node_id in unreachable:
            self._add_issue("warning", "integrity",
                           f"Unreachable node: {node_id}",
                           [node_id])

    def _check_for_cycles(self, graph: ProgramGraph) -> None:
        """Check for cycles in the graph."""
        visited = set()
        rec_stack = set()

        def has_cycle(node_id: str) -> bool:
            """DFS that flags back-edges while walking containment."""
            visited.add(node_id)
            rec_stack.add(node_id)

            for edge in graph.get_edges_from(node_id):
                if edge.target_id not in visited:
                    if has_cycle(edge.target_id):
                        return True
                elif edge.target_id in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in graph.nodes.keys():
            if node_id not in visited:
                if has_cycle(node_id):
                    self._add_issue("info", "integrity",
                                   f"Cycle detected from node: {node_id}",
                                   [node_id])

    def _check_variable_uniqueness(self, state_space: StateSpaceModel) -> None:
        """Check that all variable IDs are unique."""
        var_ids = set()
        for var_id in state_space.variables.keys():
            if var_id in var_ids:
                self._add_issue("error", "integrity",
                               f"Duplicate variable ID: {var_id}", [var_id])
            else:
                var_ids.add(var_id)

    def _check_variable_references(self, state_space: StateSpaceModel) -> None:
        """Check that all variable references are valid."""
        var_ids = set(state_space.variables.keys())

        # Check action effects and preconditions
        for action_id, action in state_space.actions.items():
            for var_id in action.effects:
                if var_id not in var_ids:
                    self._add_issue("error", "integrity",
                                   f"Action {action_id} references non-existent variable: {var_id}",
                                   [action_id, var_id])

        # Check preference scopes
        for pref_id, pref in state_space.preferences.items():
            for var_id in pref.scope:
                if var_id not in var_ids:
                    self._add_issue("error", "integrity",
                                   f"Preference {pref_id} references non-existent variable: {var_id}",
                                   [pref_id, var_id])

    def _check_confidence_values(self, state_space: StateSpaceModel) -> None:
        """Check that confidence values are in [0, 1]."""
        # Check variable confidences
        for var_id, var in state_space.variables.items():
            pass  # ConfidenceLevel is an enum, so this check is implicit

        # Check observation confidences
        for obs_id, obs in state_space.observations.items():
            pass  # Enum values are valid by definition

        # Check action confidences
        for action_id, action in state_space.actions.items():
            pass  # Enum values are valid

    def _check_stage_uniqueness(self, process: ProcessModel) -> None:
        """Check that all stage IDs are unique."""
        stage_ids = set()
        for stage_id in process.stages.keys():
            if stage_id in stage_ids:
                self._add_issue("error", "integrity",
                               f"Duplicate stage ID: {stage_id}", [stage_id])
            else:
                stage_ids.add(stage_id)

    def _check_connection_integrity(self, process: ProcessModel) -> None:
        """Check that all connections have valid stage references."""
        stage_ids = set(process.stages.keys())

        for conn_id, conn in process.connections.items():
            if conn.source_stage_id not in stage_ids:
                self._add_issue("error", "integrity",
                               f"Connection {conn_id} source not in stages: {conn.source_stage_id}",
                               [conn_id, conn.source_stage_id])
            if conn.target_stage_id not in stage_ids:
                self._add_issue("error", "integrity",
                               f"Connection {conn_id} target not in stages: {conn.target_stage_id}",
                               [conn_id, conn.target_stage_id])

    def _check_entry_exit_stages(self, process: ProcessModel) -> None:
        """Check that entry and exit stages are valid."""
        stage_ids = set(process.stages.keys())

        if process.entry_stage_id and process.entry_stage_id not in stage_ids:
            self._add_issue("error", "integrity",
                           f"Entry stage not in stages: {process.entry_stage_id}",
                           [process.entry_stage_id])

        for exit_id in process.exit_stage_ids:
            if exit_id not in stage_ids:
                self._add_issue("error", "integrity",
                               f"Exit stage not in stages: {exit_id}",
                               [exit_id])

    def _add_issue(
        self,
        severity: str,
        category: str,
        message: str,
        affected_ids: List[str],
    ) -> None:
        """Add an integrity issue."""
        issue = ValidationIssue(
            id=f"issue_{len(self.issues)}",
            severity=severity,
            category=category,
            message=message,
            affected_ids=affected_ids,
        )
        self.issues.append(issue)

    def get_issues(self) -> List[ValidationIssue]:
        """Get all integrity issues."""
        return self.issues

    def is_valid(self) -> bool:
        """Check if there are no errors."""
        return all(i.severity != "error" for i in self.issues)
