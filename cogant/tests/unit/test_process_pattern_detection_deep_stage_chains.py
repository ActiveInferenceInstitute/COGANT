"""Loop detection over the stage graph must not recurse once per stage.

``ProcessExtractor._detect_patterns`` used a recursive DFS, so any stage
graph with a path longer than the interpreter recursion limit (about 1000
stages, e.g. a long import chain across modules) made ``extract()`` raise
``RecursionError`` and the whole process stage fail. The iterative walk
must succeed on deep chains and report exactly what the recursive walk did.
"""

from __future__ import annotations

import random
import sys
from collections import defaultdict

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.process.extractor import ProcessExtractor
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph

pytestmark = pytest.mark.unit


def _import_chain(length: int, *, close_cycle: bool) -> ProgramGraph:
    builder = ProgramGraphBuilder(repo_uri="test://deep-import-chain")
    modules = [
        builder.add_node(
            kind=NodeKind.MODULE,
            name=f"m{index}",
            qualified_name=f"pkg.m{index}",
            path=f"pkg/m{index}.py",
            language="python",
        )
        for index in range(length)
    ]
    for current, following in zip(modules, modules[1:], strict=False):
        builder.add_edge(current.id, following.id, EdgeKind.IMPORTS)
    if close_cycle:
        builder.add_edge(modules[-1].id, modules[0].id, EdgeKind.IMPORTS)
    return builder.finalize()


def test_extract_succeeds_on_a_stage_chain_deeper_than_the_recursion_limit() -> None:
    length = sys.getrecursionlimit() + 500
    model = ProcessExtractor(_import_chain(length, close_cycle=False), "chain").extract()

    assert len(model.stages) == length
    assert model.metadata["patterns"]["loop"] == []
    assert len(model.metadata["patterns"]["sequential"]) == length


def test_deep_cycle_is_reported_as_a_loop() -> None:
    length = sys.getrecursionlimit() + 500
    model = ProcessExtractor(_import_chain(length, close_cycle=True), "cycle").extract()

    loop = set(model.metadata["patterns"]["loop"])
    assert loop == {"stage_m0_pkg_0", f"stage_m{length - 1}_pkg_{length - 1}"}


class _RecursiveLoopReference(ProcessExtractor):
    """The previous recursive loop detection, kept as the reference oracle."""

    def recursive_loop_members(self) -> list[str]:
        out_targets: dict[str, set[str]] = defaultdict(set)
        for conn in self.connections.values():
            if conn.source_stage_id in self.stages and conn.target_stage_id in self.stages:
                out_targets[conn.source_stage_id].add(conn.target_stage_id)
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
                    loop_members.add(neighbor)
                    loop_members.add(node)
            rec_stack.discard(node)

        for sid in self.stages:
            if sid not in visited:
                _dfs_cycle(sid)
        return list(loop_members)


@pytest.mark.parametrize("seed", range(6))
def test_iterative_loop_detection_matches_recursive_reference(seed: int) -> None:
    rng = random.Random(seed)
    builder = ProgramGraphBuilder(repo_uri=f"test://loop-reference-{seed}")
    nodes = [
        builder.add_node(
            kind=NodeKind.MODULE,
            name=f"m{index}",
            qualified_name=f"m{index}",
            path=f"p{rng.randrange(3)}/m{index}.py",
            language="python",
        )
        for index in range(120)
    ]
    for _ in range(260):
        builder.add_edge(rng.choice(nodes).id, rng.choice(nodes).id, EdgeKind.IMPORTS)
    graph = builder.finalize()

    reference = _RecursiveLoopReference(graph, "reference")
    reference._identify_stages()
    reference._build_connections()
    reference._topological_sort_stages()
    expected_loop = reference.recursive_loop_members()

    model = ProcessExtractor(graph, "reference").extract()

    assert model.metadata["patterns"]["loop"] == expected_loop
    assert expected_loop, "fixture should contain at least one cycle"
