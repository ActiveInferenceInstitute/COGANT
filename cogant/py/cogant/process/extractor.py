"""
Process model extraction from call graphs and control flow.

Identifies workflow stages, predecessors/successors, triggers, and side effects.
"""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from cogant.schemas.core import EdgeKind, Node, NodeKind
from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)


@dataclass
class Stage:
    """A workflow stage."""

    id: str
    name: str
    description: str | None = None
    node_ids: list[str] = field(default_factory=list)  # Program nodes involved
    entry_points: list[str] = field(default_factory=list)  # Predecessor stage IDs
    exit_points: list[str] = field(default_factory=list)  # Successor stage IDs
    side_effects: list[str] = field(default_factory=list)  # State mutations
    expected_duration: float | None = None  # Seconds
    confidence: float = 0.5
    pattern_type: str | None = None  # "sequential", "fan_out", "fan_in", "loop_member"


@dataclass
class ProcessConnection:
    """Connection between workflow stages."""

    id: str
    source_stage_id: str
    target_stage_id: str
    trigger: str | None = None
    condition: str | None = None
    success_rate: float | None = None


@dataclass
class ProcessModel:
    """Workflow model extracted from call graph."""

    id: str
    schema_name: str
    stages: dict[str, Stage]
    connections: dict[str, ProcessConnection]
    entry_stage_id: str | None = None
    exit_stage_ids: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


class ProcessExtractor:
    """
    Identifies workflow stages from call graph and control flow.
    Extracts predecessors/successors, triggers, and side effects.
    """

    def __init__(self, program_graph: ProgramGraph, schema_name: str):
        """
        Initialize the extractor.

        Args:
            program_graph: The program graph to analyze.
            schema_name: Name of the schema.
        """
        self.graph = program_graph
        self.schema_name = schema_name
        self.stages: dict[str, Stage] = {}
        self.connections: dict[str, ProcessConnection] = {}

    def extract(self) -> ProcessModel:
        """
        Extract process model from the program graph.

        Returns:
            Extracted ProcessModel.
        """
        logger.info(f"Extracting process model for '{self.schema_name}'")

        # Identify workflow stages from strongly connected components or call chains
        self._identify_stages()

        # Build connections between stages
        self._build_connections()

        # Topologically sort stages by dependency
        self._topological_sort_stages()

        # Detect workflow patterns and annotate stages
        patterns = self._detect_patterns()

        # Identify entry and exit stages
        entry_stage_id = self._find_entry_stage()
        exit_stage_ids = self._find_exit_stages()

        model = ProcessModel(
            id=f"process_{self.schema_name}",
            schema_name=self.schema_name,
            stages=self.stages,
            connections=self.connections,
            entry_stage_id=entry_stage_id,
            exit_stage_ids=exit_stage_ids,
            metadata={"patterns": patterns},
        )

        logger.info(f"Extracted {len(self.stages)} stages and {len(self.connections)} connections")
        return model

    def _identify_stages(self) -> None:
        """
        Identify workflow stages from the call graph.

        First pass: group nodes by module path.
        Second pass: split module groups into sub-stages when they contain
        disconnected components (nodes that don't call each other).
        Each stage is named after the primary function/method within it.
        """
        # First pass: group by module/class
        module_groups: dict[str, list[str]] = {}

        for node in self.graph.nodes.values():
            module = node.path.split("/")[0] if node.path else "root"
            if module not in module_groups:
                module_groups[module] = []
            module_groups[module].append(node.id)

        # Second pass: split each module group into connected components
        # using intra-group call-chain analysis
        for module, node_ids in module_groups.items():
            components = self._find_connected_components(node_ids)

            for comp_idx, component_ids in enumerate(components):
                # Find primary node (method/function) for stage naming
                primary_node = self._find_primary_node(component_ids)
                primary_name = primary_node.name if primary_node else module

                if len(components) == 1:
                    stage_id = f"stage_{primary_name}_{module}"
                    stage_name = f"{primary_name} ({module})"
                else:
                    stage_id = f"stage_{primary_name}_{module}_{comp_idx}"
                    stage_name = f"{primary_name} ({module} component {comp_idx})"

                side_effects = self._find_side_effects(component_ids)

                # Confidence 0.6 — principled default. Stage
                # identification is a heuristic clustering step
                # (connected components over CALLS edges within a
                # module) and cannot claim the precision of the
                # static translation rules. 0.6 sits just below the
                # lowest translation-rule band (0.65) to signal
                # "derived, not directly extracted" to downstream
                # consumers. TODO(calibration): compare extracted
                # stages against human-labelled process maps on the
                # 20-repo corpus and re-fit the confidence.
                stage = Stage(
                    id=stage_id,
                    name=stage_name,
                    node_ids=component_ids,
                    side_effects=side_effects,
                    confidence=0.6,  # principled default (below rule bands)
                )
                self.stages[stage_id] = stage

        logger.debug(f"Identified {len(self.stages)} stages")

    def _find_primary_node(self, node_ids: list[str]) -> Node | None:
        """
        Find the primary (most significant) node in a component.

        Priority: method > function > class > module

        Args:
            node_ids: Node IDs in the component.

        Returns:
            The primary Node or None.
        """
        if not node_ids:
            return None

        # Rank by NodeKind (prefer methods/functions)
        ranked = []
        for nid in node_ids:
            node = self.graph.nodes.get(nid)
            if not node:
                continue
            # Higher priority = larger tuple value
            if node.kind == NodeKind.METHOD:
                priority = (4, node.name)
            elif node.kind == NodeKind.FUNCTION:
                priority = (3, node.name)
            elif node.kind == NodeKind.CLASS:
                priority = (2, node.name)
            elif node.kind == NodeKind.MODULE:
                priority = (1, node.name)
            else:
                priority = (0, node.name)
            ranked.append((priority, node))

        if not ranked:
            return None
        # Sort by priority tuple (first element of tuple), keeping node as second
        ranked.sort(key=lambda x: x[0], reverse=True)
        return ranked[0][1]

    def _find_connected_components(self, node_ids: list[str]) -> list[list[str]]:
        """
        Find connected components within a set of nodes using call/control-flow edges.

        Two nodes are connected if there is a CALLS, CONTROL_FLOW, or TRIGGERS
        edge between them (in either direction) and both endpoints are in the
        given node set.

        Args:
            node_ids: Node IDs to partition.

        Returns:
            List of connected components (each a list of node IDs).
        """
        if not node_ids:
            return []

        node_set = set(node_ids)
        call_edge_kinds = {EdgeKind.CALLS, EdgeKind.TRIGGERS}
        if hasattr(EdgeKind, "CONTROL_FLOW"):
            call_edge_kinds.add(EdgeKind.CONTROL_FLOW)  # type: ignore[attr-defined,unused-ignore]

        # Build adjacency within the node set
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in self.graph.edges.values():
            if edge.kind not in call_edge_kinds:
                continue
            if edge.source_id in node_set and edge.target_id in node_set:
                adjacency[edge.source_id].add(edge.target_id)
                adjacency[edge.target_id].add(edge.source_id)

        # BFS to find components
        visited: set[str] = set()
        components: list[list[str]] = []

        for nid in node_ids:
            if nid in visited:
                continue
            component: list[str] = []
            queue = deque([nid])
            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)
                for neighbor in adjacency.get(current, []):
                    if neighbor not in visited:
                        queue.append(neighbor)
            components.append(component)

        return components

    def _topological_sort_stages(self) -> None:
        """
        Order stages by dependency using connections (Kahn's algorithm).

        Stages involved in cycles are placed after all acyclic stages,
        preserving their relative insertion order. Updates self.stages
        to an ordered dict reflecting the topological order.
        """
        if not self.stages:
            return

        # Build adjacency and in-degree from connections
        in_degree: dict[str, int] = dict.fromkeys(self.stages, 0)
        successors: dict[str, list[str]] = defaultdict(list)

        seen_edges: set[tuple[str, str]] = set()
        for conn in self.connections.values():
            pair = (conn.source_stage_id, conn.target_stage_id)
            if pair in seen_edges:
                continue
            seen_edges.add(pair)
            if conn.source_stage_id in self.stages and conn.target_stage_id in self.stages:
                successors[conn.source_stage_id].append(conn.target_stage_id)
                in_degree[conn.target_stage_id] = in_degree.get(conn.target_stage_id, 0) + 1

        # Kahn's algorithm
        queue = deque([sid for sid, deg in in_degree.items() if deg == 0])
        sorted_ids: list[str] = []

        while queue:
            current = queue.popleft()
            sorted_ids.append(current)
            for succ in successors.get(current, []):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        # Append any remaining (cyclic) stages
        for sid in self.stages:
            if sid not in sorted_ids:
                sorted_ids.append(sid)

        # Rebuild stages dict in sorted order
        self.stages = {sid: self.stages[sid] for sid in sorted_ids}

    def _detect_patterns(self) -> dict[str, list[str]]:
        """
        Detect workflow patterns in the stage connection graph.

        Detected patterns:
        - sequential: chains A->B->C with no branching at each node
        - fan_out: one stage calling multiple downstream stages
        - fan_in: multiple stages feeding into one stage
        - loop: cycles among stages

        Returns:
            Dictionary mapping pattern names to lists of stage IDs involved.
            Also sets pattern_type on each Stage and stores results in
            ProcessModel metadata (via the caller).
        """
        patterns: dict[str, list[str]] = {
            "sequential": [],
            "fan_out": [],
            "fan_in": [],
            "loop": [],
        }

        if not self.stages:
            return patterns

        # Build out-degree and in-degree per stage from connections
        out_targets: dict[str, set[str]] = defaultdict(set)
        in_sources: dict[str, set[str]] = defaultdict(set)

        for conn in self.connections.values():
            src, tgt = conn.source_stage_id, conn.target_stage_id
            if src in self.stages and tgt in self.stages:
                out_targets[src].add(tgt)
                in_sources[tgt].add(src)

        # Detect fan-out: stages with >1 distinct downstream target
        for sid, targets in out_targets.items():
            if len(targets) > 1:
                patterns["fan_out"].append(sid)
                if self.stages[sid].pattern_type is None:
                    self.stages[sid].pattern_type = "fan_out"

        # Detect fan-in: stages with >1 distinct upstream source
        for sid, sources in in_sources.items():
            if len(sources) > 1:
                patterns["fan_in"].append(sid)
                if self.stages[sid].pattern_type is None:
                    self.stages[sid].pattern_type = "fan_in"

        # Detect loops via DFS cycle detection
        loop_members: set[str] = set()
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def _dfs_cycle(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in out_targets.get(node, []):
                if neighbor not in visited:
                    _dfs_cycle(neighbor)
                elif neighbor in rec_stack:
                    # Found a cycle -- trace it
                    loop_members.add(neighbor)
                    loop_members.add(node)
            rec_stack.discard(node)

        for sid in self.stages:
            if sid not in visited:
                _dfs_cycle(sid)

        patterns["loop"] = list(loop_members)
        for sid in loop_members:
            self.stages[sid].pattern_type = "loop_member"

        # Detect sequential chains: stages with exactly one outgoing and
        # the target has exactly one incoming (and the stage itself has <= 1 incoming)
        for sid in self.stages:
            targets = out_targets.get(sid, set())
            sources = in_sources.get(sid, set())
            if len(targets) == 1 and len(sources) <= 1 and sid not in loop_members:
                target = next(iter(targets))
                if len(in_sources.get(target, set())) == 1 and target not in loop_members:
                    if self.stages[sid].pattern_type is None:
                        self.stages[sid].pattern_type = "sequential"
                    if self.stages[target].pattern_type is None:
                        self.stages[target].pattern_type = "sequential"
                    if sid not in patterns["sequential"]:
                        patterns["sequential"].append(sid)
                    if target not in patterns["sequential"]:
                        patterns["sequential"].append(target)

        return patterns

    def _build_connections(self) -> None:
        """
        Build connections between stages based on inter-stage edges.
        Also populate stage entry_points and exit_points.
        """
        connection_count = 0

        # Track which stages are sources/targets
        stage_exits: dict[str, set[str]] = defaultdict(set)
        stage_entries: dict[str, set[str]] = defaultdict(set)

        for edge in self.graph.edges.values():
            # Find stages containing the endpoints
            source_stage = self._find_stage_for_node(edge.source_id)
            target_stage = self._find_stage_for_node(edge.target_id)

            # Skip intra-stage edges
            if not source_stage or not target_stage or source_stage == target_stage:
                continue

            # Create connection
            conn_id = f"conn_{source_stage}_{target_stage}_{connection_count}"
            trigger = self._infer_trigger(edge)

            connection = ProcessConnection(
                id=conn_id,
                source_stage_id=source_stage,
                target_stage_id=target_stage,
                trigger=trigger,
            )
            self.connections[conn_id] = connection
            connection_count += 1

            # Track entry/exit points
            stage_exits[source_stage].add(target_stage)
            stage_entries[target_stage].add(source_stage)

        # Populate entry/exit points on stages
        for stage_id, stage in self.stages.items():
            stage.entry_points = list(stage_entries.get(stage_id, []))
            stage.exit_points = list(stage_exits.get(stage_id, []))

        logger.debug(f"Built {len(self.connections)} inter-stage connections")

    def _find_stage_for_node(self, node_id: str) -> str | None:
        """
        Find the stage ID containing a given node.

        Args:
            node_id: The node ID.

        Returns:
            Stage ID if found, None otherwise.
        """
        for stage_id, stage in self.stages.items():
            if node_id in stage.node_ids:
                return stage_id
        return None

    def _find_entry_stage(self) -> str | None:
        """
        Find the entry stage (stage with no incoming inter-stage edges).

        Returns:
            Entry stage ID or None.
        """
        # Find stage with no incoming connections
        incoming_stages = {c.source_stage_id for c in self.connections.values()}

        for stage_id in self.stages.keys():
            if stage_id not in incoming_stages:
                return stage_id

        # Fallback: return first stage
        return next(iter(self.stages.keys())) if self.stages else None

    def _find_exit_stages(self) -> list[str]:
        """
        Find exit stages (stages with no outgoing inter-stage edges).

        Returns:
            List of exit stage IDs.
        """
        outgoing_stages = {c.target_stage_id for c in self.connections.values()}
        exit_stages = [sid for sid in self.stages.keys() if sid not in outgoing_stages]
        return exit_stages if exit_stages else []

    def _find_side_effects(self, node_ids: list[str]) -> list[str]:
        """
        Find state mutations (side effects) in a set of nodes.

        Args:
            node_ids: List of node IDs.

        Returns:
            List of affected state variable/node IDs.
        """
        side_effects = []

        for node_id in node_ids:
            # Find WRITES edges from this node
            for edge in self.graph.get_edges_from(node_id):
                if edge.kind == EdgeKind.WRITES:
                    side_effects.append(edge.target_id)

        return side_effects

    def _infer_trigger(self, edge: Any) -> str | None:
        """
        Infer the trigger for an inter-stage connection.

        Maps edge kinds to meaningful trigger types:
        - CALLS: function_call (direct invocation)
        - TRIGGERS: event (async/event-driven)
        - READS: data_access (read dependency)
        - WRITES: state_mutation (write dependency)
        - RETURNS: return_value (returns from previous call)
        - THROWS: exception (exception propagation)
        - YIELDS: generator_yield (generator protocol)

        Args:
            edge: The edge representing the connection.

        Returns:
            Trigger description or None.
        """
        trigger_map = {
            EdgeKind.CALLS: "function_call",
            EdgeKind.TRIGGERS: "event",
            EdgeKind.READS: "data_access",
            EdgeKind.WRITES: "state_mutation",
            EdgeKind.RETURNS: "return_value",
            EdgeKind.THROWS: "exception",
            EdgeKind.YIELDS: "generator_yield",
        }

        # Check if the edge kind is in the map
        if hasattr(edge.kind, "value"):
            kind_val = edge.kind.value
            for ek, trigger in trigger_map.items():
                if ek.value == kind_val:
                    return trigger

        return trigger_map.get(edge.kind, None)

    def set_entry_stage(self, stage_id: str) -> None:
        """
        Manually set the entry stage.

        Args:
            stage_id: The ID of the entry stage.
        """
        if stage_id in self.stages:
            # Find current entry and update
            current_entry = self._find_entry_stage()
            if current_entry and current_entry != stage_id:
                logger.info(f"Changing entry stage from {current_entry} to {stage_id}")

    def add_stage_dependency(
        self, source_stage_id: str, target_stage_id: str, trigger: str | None = None
    ) -> None:
        """
        Manually add a dependency between stages.

        Args:
            source_stage_id: Source stage ID.
            target_stage_id: Target stage ID.
            trigger: Optional trigger description.
        """
        if source_stage_id not in self.stages or target_stage_id not in self.stages:
            logger.warning(
                f"Invalid stage IDs for dependency: {source_stage_id} -> {target_stage_id}"
            )
            return

        conn_id = f"conn_{source_stage_id}_{target_stage_id}"
        connection = ProcessConnection(
            id=conn_id,
            source_stage_id=source_stage_id,
            target_stage_id=target_stage_id,
            trigger=trigger,
        )
        self.connections[conn_id] = connection
        logger.info(f"Added stage dependency: {source_stage_id} -> {target_stage_id}")
