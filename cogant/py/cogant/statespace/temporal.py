"""
Temporal analysis and time regime extraction.

Determines execution model (synchronous/asynchronous/event-driven) and
extracts temporal ordering from process flow and event patterns.
"""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from cogant.schemas.core import Node, NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)


class TimeRegime(str, Enum):
    """Temporal execution model."""
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    EVENT_DRIVEN = "event_driven"
    HYBRID = "hybrid"


@dataclass
class TemporalOrdering:
    """Temporal ordering constraint between nodes."""
    predecessor_id: str
    successor_id: str
    constraint_type: str  # "sequential", "parallel", "conditional"
    confidence: float  # 0-1


@dataclass
class EventPattern:
    """Pattern of event-driven execution."""
    event_node_id: str
    trigger_nodes: List[str]
    handler_nodes: List[str]
    is_async: bool = False


@dataclass
class TemporalMetrics:
    """Metrics about temporal characteristics."""
    async_fraction: float  # Fraction of async nodes
    event_driven_fraction: float  # Fraction of event-driven nodes
    parallel_edges_count: int
    sequential_edges_count: int
    event_patterns_count: int
    has_async_handlers: bool
    has_event_triggers: bool
    has_loops: bool = False
    """True when a cycle was detected among CALLS/TRIGGERS edges, indicating
    iterative execution (loops, recursion, or event-handler cycles)."""
    is_discrete: bool = True
    """True when the execution model is discrete-time (the default); set to
    False only for purely continuous-time signal processing flows."""


class TemporalAnalyzer:
    """
    Determines time regime (sync/async/event-driven) and extracts temporal
    ordering from process flow and event patterns.
    """

    def __init__(self, program_graph: ProgramGraph):
        """
        Initialize the analyzer.

        Args:
            program_graph: The program graph to analyze.
        """
        self.graph = program_graph
        self.time_regime = TimeRegime.SYNCHRONOUS
        self.orderings: List[TemporalOrdering] = []
        self.event_patterns: List[EventPattern] = []
        self.metrics: Optional[TemporalMetrics] = None

    def analyze(self) -> TimeRegime:
        """
        Analyze the temporal characteristics of the program.

        Returns:
            Determined TimeRegime.
        """
        logger.info("Analyzing temporal characteristics...")

        # Detect async nodes and handlers
        async_nodes = self._detect_async_nodes()
        event_nodes = self._detect_event_nodes()

        # Extract temporal orderings
        self._extract_orderings(async_nodes)

        # Detect event patterns
        self._detect_event_patterns(event_nodes)

        # Compute metrics
        self.metrics = self._compute_metrics(async_nodes, event_nodes)

        # Determine overall time regime
        self.time_regime = self._determine_regime(self.metrics)

        logger.info(f"Determined time regime: {self.time_regime}")
        logger.info(f"Found {len(self.orderings)} temporal orderings")
        logger.info(f"Found {len(self.event_patterns)} event patterns")

        return self.time_regime

    def _detect_async_nodes(self) -> Set[str]:
        """
        Detect asynchronous nodes from graph.

        Returns:
            Set of node IDs that are asynchronous.
        """
        async_nodes = set()

        for node in self.graph.nodes.values():
            # Check metadata for async indicators
            metadata = node.metadata or {}
            if metadata.get("is_async") or metadata.get("async"):
                async_nodes.add(node.id)

            # Check name for async patterns
            if any(p in node.name.lower() for p in ["async", "callback", "promise", "future"]):
                async_nodes.add(node.id)

        return async_nodes

    def _detect_event_nodes(self) -> Set[str]:
        """
        Detect event-related nodes.

        Returns:
            Set of node IDs that are event-related.
        """
        event_nodes = set()

        for node in self.graph.nodes.values():
            # Check node kind
            if node.kind == NodeKind.EVENT:
                event_nodes.add(node.id)

            # Check metadata
            metadata = node.metadata or {}
            if metadata.get("is_event") or metadata.get("event"):
                event_nodes.add(node.id)

            # Check name for event patterns
            if any(p in node.name.lower() for p in ["event", "handler", "listener", "trigger"]):
                event_nodes.add(node.id)

        return event_nodes

    def _extract_orderings(self, async_nodes: Set[str]) -> None:
        """
        Extract temporal orderings from control flow edges.

        Args:
            async_nodes: Set of asynchronous node IDs.
        """
        for edge in self.graph.edges.values():
            # Skip non-control flow edges
            if edge.kind not in (EdgeKind.CALLS, EdgeKind.TRIGGERS):
                continue

            # Determine constraint type
            if edge.source_id in async_nodes or edge.target_id in async_nodes:
                constraint_type = "parallel"
                confidence = 0.7
            else:
                constraint_type = "sequential"
                confidence = 0.95

            ordering = TemporalOrdering(
                predecessor_id=edge.source_id,
                successor_id=edge.target_id,
                constraint_type=constraint_type,
                confidence=confidence
            )
            self.orderings.append(ordering)

    def _detect_event_patterns(self, event_nodes: Set[str]) -> None:
        """
        Detect event-driven execution patterns.

        Args:
            event_nodes: Set of event node IDs.
        """
        for event_id in event_nodes:
            # Find trigger nodes (sources of event)
            trigger_edges = self.graph.get_edges_to(event_id)
            trigger_nodes = [e.source_id for e in trigger_edges if e.kind == EdgeKind.TRIGGERS]

            # Find handler nodes (targets of event)
            handler_edges = self.graph.get_edges_from(event_id)
            handler_nodes = [e.target_id for e in handler_edges if e.kind == EdgeKind.TRIGGERS]

            if trigger_nodes or handler_nodes:
                # Determine if async
                is_async = any(nid in self.graph.nodes and
                             self.graph.nodes[nid].kind == NodeKind.ASYNC_HANDLER
                             for nid in handler_nodes)

                pattern = EventPattern(
                    event_node_id=event_id,
                    trigger_nodes=trigger_nodes,
                    handler_nodes=handler_nodes,
                    is_async=is_async
                )
                self.event_patterns.append(pattern)

    def _compute_metrics(self, async_nodes: Set[str], event_nodes: Set[str]) -> TemporalMetrics:
        """
        Compute temporal metrics.

        Args:
            async_nodes: Set of async node IDs.
            event_nodes: Set of event node IDs.

        Returns:
            Computed TemporalMetrics.
        """
        total_nodes = len(self.graph.nodes)
        async_fraction = len(async_nodes) / total_nodes if total_nodes > 0 else 0.0
        event_fraction = len(event_nodes) / total_nodes if total_nodes > 0 else 0.0

        # Count edge types in a single pass. An edge is "parallel" if
        # either endpoint is an async node, and "sequential" otherwise.
        parallel_edges = 0
        sequential_edges = 0
        for e in self.graph.edges.values():
            if e.source_id in async_nodes or e.target_id in async_nodes:
                parallel_edges += 1
            else:
                sequential_edges += 1

        # Detect cycles among CALLS/TRIGGERS edges. A cycle indicates a loop
        # (iterative execution), recursion, or a handler feedback pattern.
        has_loops = self._detect_loops()

        return TemporalMetrics(
            async_fraction=async_fraction,
            event_driven_fraction=event_fraction,
            parallel_edges_count=parallel_edges,
            sequential_edges_count=sequential_edges,
            event_patterns_count=len(self.event_patterns),
            has_async_handlers=len(async_nodes) > 0,
            has_event_triggers=len(event_nodes) > 0,
            has_loops=has_loops,
            is_discrete=True,  # COGANT assumes discrete-time semantics.
        )

    def _detect_loops(self) -> bool:
        """
        Detect whether the CALLS/TRIGGERS subgraph contains a directed cycle.

        Uses iterative DFS with a recursion stack so it is robust against
        very deep or very wide call graphs (no Python recursion limits).

        Returns:
            True if any cycle is reachable via CALLS/TRIGGERS edges.
        """
        call_kinds = {EdgeKind.CALLS, EdgeKind.TRIGGERS}
        # Build adjacency for call-graph edges only.
        adj: Dict[str, List[str]] = {}
        for edge in self.graph.edges.values():
            if edge.kind in call_kinds:
                adj.setdefault(edge.source_id, []).append(edge.target_id)

        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {nid: WHITE for nid in self.graph.nodes}

        for start in list(color.keys()):
            if color[start] != WHITE:
                continue
            stack: List[Tuple[str, int]] = [(start, 0)]
            while stack:
                node_id, child_idx = stack[-1]
                if color[node_id] == WHITE:
                    color[node_id] = GRAY
                children = adj.get(node_id, [])
                if child_idx < len(children):
                    stack[-1] = (node_id, child_idx + 1)
                    next_id = children[child_idx]
                    if next_id not in color:
                        continue  # dangling edge
                    if color[next_id] == GRAY:
                        return True  # back edge -> cycle
                    if color[next_id] == WHITE:
                        stack.append((next_id, 0))
                else:
                    color[node_id] = BLACK
                    stack.pop()
        return False

    def _determine_regime(self, metrics: TemporalMetrics) -> TimeRegime:
        """
        Determine time regime from metrics.

        Args:
            metrics: Computed temporal metrics.

        Returns:
            Determined TimeRegime.
        """
        # Decision logic based on metrics
        if metrics.has_event_triggers and metrics.event_patterns_count > 0:
            if metrics.has_async_handlers:
                return TimeRegime.HYBRID
            else:
                return TimeRegime.EVENT_DRIVEN

        if metrics.async_fraction > 0.3 or metrics.has_async_handlers:
            return TimeRegime.ASYNCHRONOUS

        return TimeRegime.SYNCHRONOUS

    def get_ordering_constraints(self) -> List[TemporalOrdering]:
        """
        Get temporal ordering constraints.

        Returns:
            List of TemporalOrdering objects.
        """
        return self.orderings

    def get_event_patterns(self) -> List[EventPattern]:
        """
        Get detected event patterns.

        Returns:
            List of EventPattern objects.
        """
        return self.event_patterns

    def get_metrics(self) -> Optional[TemporalMetrics]:
        """
        Get computed temporal metrics.

        Returns:
            TemporalMetrics or None if not yet analyzed.
        """
        return self.metrics

    def get_critical_path(self) -> List[str]:
        """
        Compute the critical path through the execution.

        Returns:
            List of node IDs representing the critical path.
        """
        # Simple topological sort based on orderings
        # Find path from entry points to exit nodes
        entry_points = [n.id for n in self.graph.nodes.values()
                       if len(self.graph.get_edges_to(n.id)) == 0]

        critical_path = []
        visited = set()

        def dfs(node_id: str, path: List[str]) -> List[str]:
            """Walk outgoing edges greedily to extend the critical path."""
            if node_id in visited:
                return path
            visited.add(node_id)
            path.append(node_id)

            outgoing = self.graph.get_edges_from(node_id)
            if not outgoing:
                return path
            # Follow the edge with highest weight, but only if the target
            # node actually exists in the graph (defensive against dangling
            # edges).
            next_edge = max(outgoing, key=lambda e: e.weight)
            if next_edge.target_id not in self.graph.nodes:
                return path
            return dfs(next_edge.target_id, path)

        for entry in entry_points:
            path = dfs(entry, [])
            if len(path) > len(critical_path):
                critical_path = path

        return critical_path
