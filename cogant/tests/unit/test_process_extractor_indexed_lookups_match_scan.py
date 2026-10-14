"""ProcessExtractor's indexed stage/edge lookups must match the scanning ones.

``ProcessExtractor`` used to find each edge endpoint's stage by scanning
every stage's ``node_ids`` list, re-scan every graph edge once per module
group to build connected components, and re-scan every edge per node to
collect WRITES side effects, i.e. O(edges x nodes) per extraction. The
indexed implementation must produce exactly the same ``ProcessModel``;
``ScanningProcessExtractor`` below keeps the previous scanning code as the
reference oracle.
"""

from __future__ import annotations

import random
from collections import defaultdict, deque
from dataclasses import asdict

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.process.extractor import ProcessConnection, ProcessExtractor, Stage
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph

pytestmark = pytest.mark.unit


class ScanningProcessExtractor(ProcessExtractor):
    """The pre-index implementation, kept verbatim as the reference."""

    def _identify_stages(self) -> None:
        module_groups: dict[str, list[str]] = {}
        for node in self.graph.nodes.values():
            module = node.path.split("/")[0] if node.path else "root"
            module_groups.setdefault(module, []).append(node.id)
        for module, node_ids in module_groups.items():
            components = self._scan_components(node_ids)
            for comp_idx, component_ids in enumerate(components):
                primary_node = self._find_primary_node(component_ids)
                primary_name = primary_node.name if primary_node else module
                if len(components) == 1:
                    stage_id = f"stage_{primary_name}_{module}"
                    stage_name = f"{primary_name} ({module})"
                else:
                    stage_id = f"stage_{primary_name}_{module}_{comp_idx}"
                    stage_name = f"{primary_name} ({module} component {comp_idx})"
                side_effects = [
                    edge.target_id
                    for node_id in component_ids
                    for edge in self.graph.get_edges_from(node_id)
                    if edge.kind == EdgeKind.WRITES
                ]
                self.stages[stage_id] = Stage(
                    id=stage_id,
                    name=stage_name,
                    node_ids=component_ids,
                    side_effects=side_effects,
                    confidence=0.6,
                )

    def _scan_components(self, node_ids: list[str]) -> list[list[str]]:
        node_set = set(node_ids)
        kinds = {EdgeKind.CALLS, EdgeKind.TRIGGERS}
        if hasattr(EdgeKind, "CONTROL_FLOW"):
            kinds.add(EdgeKind.CONTROL_FLOW)
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in self.graph.edges.values():
            if edge.kind not in kinds:
                continue
            if edge.source_id in node_set and edge.target_id in node_set:
                adjacency[edge.source_id].add(edge.target_id)
                adjacency[edge.target_id].add(edge.source_id)
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

    def _build_connections(self) -> None:
        connection_count = 0
        stage_exits: dict[str, set[str]] = defaultdict(set)
        stage_entries: dict[str, set[str]] = defaultdict(set)
        for edge in self.graph.edges.values():
            source_stage = self._scan_stage_for_node(edge.source_id)
            target_stage = self._scan_stage_for_node(edge.target_id)
            if not source_stage or not target_stage or source_stage == target_stage:
                continue
            conn_id = f"conn_{source_stage}_{target_stage}_{connection_count}"
            self.connections[conn_id] = ProcessConnection(
                id=conn_id,
                source_stage_id=source_stage,
                target_stage_id=target_stage,
                trigger=self._infer_trigger(edge),
            )
            connection_count += 1
            stage_exits[source_stage].add(target_stage)
            stage_entries[target_stage].add(source_stage)
        for stage_id, stage in self.stages.items():
            stage.entry_points = list(stage_entries.get(stage_id, []))
            stage.exit_points = list(stage_exits.get(stage_id, []))

    def _scan_stage_for_node(self, node_id: str) -> str | None:
        for stage_id, stage in self.stages.items():
            if node_id in stage.node_ids:
                return stage_id
        return None


_EDGE_KINDS = (
    EdgeKind.CALLS,
    EdgeKind.CALLS,
    EdgeKind.CALLS,
    EdgeKind.TRIGGERS,
    EdgeKind.WRITES,
    EdgeKind.READS,
    EdgeKind.IMPORTS,
    EdgeKind.CONTAINS,
)
_NODE_KINDS = (NodeKind.MODULE, NodeKind.CLASS, NodeKind.METHOD, NodeKind.FUNCTION)


def _random_graph(seed: int, node_count: int, edge_count: int) -> ProgramGraph:
    rng = random.Random(seed)
    builder = ProgramGraphBuilder(repo_uri=f"test://process-index-{seed}")
    packages = [f"pkg{i}" for i in range(5)] + [""]
    node_ids: list[str] = []
    for index in range(node_count):
        package = rng.choice(packages)
        path = f"{package}/mod{rng.randrange(4)}.py" if package else None
        node = builder.add_node(
            kind=rng.choice(_NODE_KINDS),
            # Duplicate simple names exercise stage-id collisions.
            name=f"n{rng.randrange(node_count // 3 + 1)}",
            qualified_name=f"q{index}",
            path=path,
            language="python",
        )
        node_ids.append(node.id)
    for _ in range(edge_count):
        builder.add_edge(rng.choice(node_ids), rng.choice(node_ids), rng.choice(_EDGE_KINDS))
    return builder.finalize()


@pytest.mark.parametrize(
    ("seed", "node_count", "edge_count"),
    [(0, 12, 20), (1, 60, 150), (2, 200, 600), (3, 400, 400), (4, 150, 1200)],
)
def test_indexed_extraction_matches_scanning_reference(
    seed: int, node_count: int, edge_count: int
) -> None:
    graph = _random_graph(seed, node_count, edge_count)

    expected = ScanningProcessExtractor(graph, "pinned").extract()
    actual = ProcessExtractor(graph, "pinned").extract()

    assert asdict(actual) == asdict(expected)
    assert list(actual.stages) == list(expected.stages)
    assert list(actual.connections) == list(expected.connections)
