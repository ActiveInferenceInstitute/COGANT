"""
Integrity checking for graph structures.

Verifies node ID uniqueness, edge endpoints, mapping references,
orphaned nodes, and confidence values.
"""

import logging

from cogant.process.extractor import ProcessModel
from cogant.schemas.graph import ProgramGraph
from cogant.statespace.compiler import StateSpaceModel
from cogant.validate._mixin import ValidationIssue, _ValidatorMixin

logger = logging.getLogger(__name__)


class IntegrityChecker(_ValidatorMixin):
    """
    Checks structural integrity of IR models:
    - Node ID uniqueness
    - Edge endpoint validity
    - Reference validity (mappings, cross-model references)
    - No orphaned nodes
    - Confidence values in [0, 1]
    """

    def __init__(self) -> None:
        """Initialize the checker."""
        super().__init__()

    def check_program_graph(self, graph: ProgramGraph) -> list[ValidationIssue]:
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

    def check_state_space(self, state_space: StateSpaceModel) -> list[ValidationIssue]:
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

    def check_process_model(self, process: ProcessModel) -> list[ValidationIssue]:
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
        for node_id, _node in graph.nodes.items():
            if node_id in node_ids:
                self._add_issue("error", "integrity", f"Duplicate node ID: {node_id}", [node_id])
            else:
                node_ids.add(node_id)

    def _check_edge_endpoints(self, graph: ProgramGraph) -> None:
        """Check that all edges have valid endpoints."""
        node_ids = set(graph.nodes.keys())

        for edge_id, edge in graph.edges.items():
            if edge.source_id not in node_ids:
                self._add_issue(
                    "error",
                    "integrity",
                    f"Edge {edge_id} source not in nodes: {edge.source_id}",
                    [edge_id, edge.source_id],
                )
            if edge.target_id not in node_ids:
                self._add_issue(
                    "error",
                    "integrity",
                    f"Edge {edge_id} target not in nodes: {edge.target_id}",
                    [edge_id, edge.target_id],
                )

    def _check_orphaned_nodes(self, graph: ProgramGraph) -> None:
        """Check for orphaned (unreachable) nodes."""
        from collections import defaultdict, deque

        # Find entry points (nodes with no incoming edges).
        has_incoming: set[str] = set()
        for edge in graph.edges.values():
            has_incoming.add(edge.target_id)

        entry_points = {nid for nid in graph.nodes if nid not in has_incoming}

        # Build out-edge adjacency once (O(|E|)) so the BFS below runs in
        # O(|V| + |E|) rather than O(|V| * |E|) from re-scanning all edges
        # per node via ``get_edges_from``.
        adj: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges.values():
            adj[edge.source_id].append(edge.target_id)

        reachable: set[str] = set()
        queue: deque[str] = deque(entry_points)

        while queue:
            node_id = queue.popleft()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            for target_id in adj.get(node_id, []):
                if target_id not in reachable:
                    queue.append(target_id)

        # Check for unreachable nodes
        unreachable = set(graph.nodes.keys()) - reachable
        for node_id in unreachable:
            self._add_issue("warning", "integrity", f"Unreachable node: {node_id}", [node_id])

    def _check_for_cycles(self, graph: ProgramGraph) -> None:
        """Check for cycles in the graph.

        Iterative DFS with an explicit stack so that very deep graphs
        (containment chains > ~1000) do not overflow Python's default
        recursion limit. A cycle is reported once per starting root that
        first encounters a back-edge.
        """
        from collections import defaultdict

        # Build out-edge adjacency once.
        adj: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges.values():
            adj[edge.source_id].append(edge.target_id)

        visited: set[str] = set()
        on_stack: set[str] = set()

        for root in graph.nodes:
            if root in visited:
                continue

            # Each frame is (node_id, iter_over_neighbors). When a frame's
            # iterator is exhausted we pop it off and remove from on_stack.
            stack: list[tuple[str, object]] = [(root, iter(adj.get(root, [])))]
            visited.add(root)
            on_stack.add(root)
            cycle_found = False

            while stack:
                node_id, it = stack[-1]
                next_target: str | None = next(it, None)  # type: ignore[arg-type]
                if next_target is None:
                    on_stack.discard(node_id)
                    stack.pop()
                    continue
                if next_target in on_stack:
                    cycle_found = True
                    self._add_issue(
                        "info",
                        "integrity",
                        f"Cycle detected from node: {root}",
                        [root],
                    )
                    break
                if next_target not in visited:
                    visited.add(next_target)
                    on_stack.add(next_target)
                    stack.append((next_target, iter(adj.get(next_target, []))))

            if cycle_found:
                # Drain remaining frames so on_stack is consistent for the
                # next root iteration.
                for nid, _ in stack:
                    on_stack.discard(nid)
                stack.clear()

    def _check_variable_uniqueness(self, state_space: StateSpaceModel) -> None:
        """Check that all variable IDs are unique."""
        var_ids = set()
        for var_id in state_space.variables.keys():
            if var_id in var_ids:
                self._add_issue("error", "integrity", f"Duplicate variable ID: {var_id}", [var_id])
            else:
                var_ids.add(var_id)

    def _check_variable_references(self, state_space: StateSpaceModel) -> None:
        """Check that all variable references are valid."""
        var_ids = set(state_space.variables.keys())

        # Check action effects and preconditions
        for action_id, action in state_space.actions.items():
            for var_id in action.effects:
                if var_id not in var_ids:
                    self._add_issue(
                        "error",
                        "integrity",
                        f"Action {action_id} references non-existent variable: {var_id}",
                        [action_id, var_id],
                    )

        # Check preference scopes
        for pref_id, pref in state_space.preferences.items():
            for var_id in pref.scope:
                if var_id not in var_ids:
                    self._add_issue(
                        "error",
                        "integrity",
                        f"Preference {pref_id} references non-existent variable: {var_id}",
                        [pref_id, var_id],
                    )

    def _check_confidence_values(self, state_space: StateSpaceModel) -> None:
        """Check that confidence values are in [0, 1].

        Currently a no-op: variable, observation, and action confidence
        levels are represented by the :class:`ConfidenceLevel` enum, so
        their values are constrained at construction time. This hook is
        kept so future schemas with raw float confidences can be
        validated here without changing the public surface of
        :meth:`check_state_space`.
        """
        # Intentionally empty — see docstring.
        del state_space

    def _check_stage_uniqueness(self, process: ProcessModel) -> None:
        """Check that all stage IDs are unique."""
        stage_ids = set()
        for stage_id in process.stages.keys():
            if stage_id in stage_ids:
                self._add_issue("error", "integrity", f"Duplicate stage ID: {stage_id}", [stage_id])
            else:
                stage_ids.add(stage_id)

    def _check_connection_integrity(self, process: ProcessModel) -> None:
        """Check that all connections have valid stage references."""
        stage_ids = set(process.stages.keys())

        for conn_id, conn in process.connections.items():
            if conn.source_stage_id not in stage_ids:
                self._add_issue(
                    "error",
                    "integrity",
                    f"Connection {conn_id} source not in stages: {conn.source_stage_id}",
                    [conn_id, conn.source_stage_id],
                )
            if conn.target_stage_id not in stage_ids:
                self._add_issue(
                    "error",
                    "integrity",
                    f"Connection {conn_id} target not in stages: {conn.target_stage_id}",
                    [conn_id, conn.target_stage_id],
                )

    def _check_entry_exit_stages(self, process: ProcessModel) -> None:
        """Check that entry and exit stages are valid."""
        stage_ids = set(process.stages.keys())

        if process.entry_stage_id and process.entry_stage_id not in stage_ids:
            self._add_issue(
                "error",
                "integrity",
                f"Entry stage not in stages: {process.entry_stage_id}",
                [process.entry_stage_id],
            )

        for exit_id in process.exit_stage_ids:
            if exit_id not in stage_ids:
                self._add_issue(
                    "error", "integrity", f"Exit stage not in stages: {exit_id}", [exit_id]
                )
