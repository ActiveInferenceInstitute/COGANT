"""
Provenance validation and coverage checking.

Checks provenance coverage and verifies every node has evidence.
Flags gaps in provenance.
"""

import logging
from dataclasses import dataclass
from typing import Any

from cogant.schemas.graph import ProgramGraph
from cogant.statespace.compiler import StateSpaceModel

logger = logging.getLogger(__name__)


@dataclass
class ProvenanceGap:
    """A gap in provenance coverage."""

    element_id: str
    element_type: str  # "node", "edge", "variable", etc.
    message: str
    severity: str  # "error", "warning"


class ProvenanceChecker:
    """
    Checks provenance coverage and ensures every extracted element has evidence.
    Flags gaps in provenance that might indicate low-confidence extractions.
    """

    def __init__(self, provenance_records: dict[str, list[object]] | None = None):
        """
        Initialize the checker.

        Args:
            provenance_records: Dictionary of element IDs to provenance records.
        """
        self.provenance_records = provenance_records or {}
        self.gaps: list[ProvenanceGap] = []

    def check_graph_provenance(self, graph: ProgramGraph) -> list[ProvenanceGap]:
        """
        Check provenance coverage for a program graph.

        Args:
            graph: The program graph to check.

        Returns:
            List of provenance gaps found.
        """
        logger.info("Checking program graph provenance...")
        self.gaps = []

        # Check node provenance
        for node_id, node in graph.nodes.items():
            self._check_node_provenance(node_id, node)

        # Check edge provenance
        for edge_id, edge in graph.edges.items():
            self._check_edge_provenance(edge_id, edge)

        logger.info(f"Found {len(self.gaps)} provenance gaps in program graph")
        return self.gaps

    def check_state_space_provenance(self, state_space: StateSpaceModel) -> list[ProvenanceGap]:
        """
        Check provenance coverage for a state space model.

        Args:
            state_space: The state space model to check.

        Returns:
            List of provenance gaps found.
        """
        logger.info("Checking state space provenance...")
        self.gaps = []

        # Check variable provenance
        for var_id, var in state_space.variables.items():
            self._check_variable_provenance(var_id, var)

        # Check observation provenance
        for obs_id, obs in state_space.observations.items():
            self._check_observation_provenance(obs_id, obs)

        # Check action provenance
        for action_id, action in state_space.actions.items():
            self._check_action_provenance(action_id, action)

        logger.info(f"Found {len(self.gaps)} provenance gaps in state space")
        return self.gaps

    # Private checking methods

    def _check_node_provenance(self, node_id: str, node: Any) -> None:
        """Check provenance for a single node."""
        if node_id not in self.provenance_records or not self.provenance_records[node_id]:
            self._add_gap(node_id, "node", f"Node {node_id} has no provenance records", "warning")

    def _check_edge_provenance(self, edge_id: str, edge: Any) -> None:
        """Check provenance for a single edge."""
        if edge_id not in self.provenance_records or not self.provenance_records[edge_id]:
            self._add_gap(edge_id, "edge", f"Edge {edge_id} has no provenance records", "warning")

    def _check_variable_provenance(self, var_id: str, var: Any) -> None:
        """Check provenance for a state variable."""
        if var_id not in self.provenance_records or not self.provenance_records[var_id]:
            # Check if derived from a node
            if var.node_id not in self.provenance_records:
                self._add_gap(
                    var_id,
                    "variable",
                    f"State variable {var_id} has no provenance (nor its source node)",
                    "warning",
                )

    def _check_observation_provenance(self, obs_id: str, obs: Any) -> None:
        """Check provenance for an observation."""
        if obs_id not in self.provenance_records or not self.provenance_records[obs_id]:
            # Check if derived from a node
            if obs.source_node_id not in self.provenance_records:
                self._add_gap(
                    obs_id,
                    "observation",
                    f"Observation {obs_id} has no provenance (nor its source node)",
                    "warning",
                )

    def _check_action_provenance(self, action_id: str, action: Any) -> None:
        """Check provenance for an action."""
        if action_id not in self.provenance_records or not self.provenance_records[action_id]:
            # Check if derived from a node
            if action.controller_id not in self.provenance_records:
                self._add_gap(
                    action_id,
                    "action",
                    f"Action {action_id} has no provenance (nor its controller node)",
                    "warning",
                )

    def _add_gap(
        self,
        element_id: str,
        element_type: str,
        message: str,
        severity: str,
    ) -> None:
        """Add a provenance gap."""
        gap = ProvenanceGap(
            element_id=element_id,
            element_type=element_type,
            message=message,
            severity=severity,
        )
        self.gaps.append(gap)

    def get_gaps(self) -> list[ProvenanceGap]:
        """Get all provenance gaps."""
        return self.gaps

    def get_coverage_percentage(self, total_elements: int) -> float:
        """
        Calculate provenance coverage percentage.

        Args:
            total_elements: Total number of elements.

        Returns:
            Coverage percentage (0-100).
        """
        if total_elements == 0:
            return 100.0

        missing_count = len([g for g in self.gaps if g.severity == "warning"])
        return ((total_elements - missing_count) / total_elements) * 100.0

    def merge_records(self, other_records: dict[str, list[object]]) -> None:
        """
        Merge additional provenance records.

        Args:
            other_records: Additional provenance records to merge.
        """
        for element_id, records in other_records.items():
            if element_id not in self.provenance_records:
                self.provenance_records[element_id] = records
            else:
                self.provenance_records[element_id].extend(records)

    def add_record(self, element_id: str, record: object) -> None:
        """
        Add a single provenance record.

        Args:
            element_id: ID of the element.
            record: Provenance record.
        """
        if element_id not in self.provenance_records:
            self.provenance_records[element_id] = []
        self.provenance_records[element_id].append(record)
