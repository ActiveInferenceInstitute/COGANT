"""Targeted unit tests for cogant.markov.blanket.

Targets the dataclass methods that the existing tests don't exercise:

* ``MarkovBlanket.get_sensory_states`` / ``get_active_states`` (lines 141, 153)
* ``MarkovBlanket.visualize`` (line 171)
* ``MarkovBlanket.validate`` (lines 196-224) — including the three failure paths
* ``MarkovBlanket.to_mermaid`` (lines 240-267) — both empty-role and populated paths
* ``MarkovBlanket.merge`` (lines 286-298)
* ``MarkovBlanket.blanket_summary`` (lines 314-326)
* ``_bidirectional_adjacency`` self-loop ``continue`` branch (line 348)

All tests use real ProgramGraph instances and the public partition_by_seeds
helper to construct realistic blanket inputs.
"""

from __future__ import annotations

from cogant.markov.blanket import (
    BlanketRole,
    MarkovBlanket,
    _bidirectional_adjacency,
    partition_by_seeds,
)
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _node(nid: str, kind: NodeKind = NodeKind.FUNCTION) -> Node:
    return Node(
        id=nid,
        kind=kind,
        name=nid,
        qualified_name=f"pkg.{nid}",
        path=f"pkg/{nid}.py",
    )


def _edge(eid: str, src: str, tgt: str, kind: EdgeKind = EdgeKind.CALLS) -> Edge:
    return Edge(id=eid, source_id=src, target_id=tgt, kind=kind)


def _graph_with_boundary() -> tuple[ProgramGraph, set[str]]:
    """Return a graph with internal/sensory/active/external nodes."""
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///targeted"))
    for nid in ["i1", "i2", "s1", "a1", "ext1", "ext2"]:
        g.add_node(_node(nid))

    # Internal-internal edges (so i1, i2 stay internal)
    g.add_edge(_edge("e_ii", "i1", "i2"))

    # Edge from external INTO s1 → s1 is sensory
    g.add_edge(_edge("e_ext_s", "ext1", "s1"))

    # Edge from a1 OUT to external → a1 is active
    g.add_edge(_edge("e_a_ext", "a1", "ext2"))

    # Connect internal to boundary so they're related (still internal because
    # all neighbours are inside the seed set).
    g.add_edge(_edge("e_i_s", "i1", "s1"))
    g.add_edge(_edge("e_i_a", "i2", "a1"))

    seeds = {"i1", "i2", "s1", "a1"}
    return g, seeds


# --------------------------------------------------------------------------- #
# get_sensory_states / get_active_states (line 141, 153)
# --------------------------------------------------------------------------- #


def test_get_sensory_states_returns_sorted_list():
    g, seeds = _graph_with_boundary()
    blanket = partition_by_seeds(g, seeds)
    sensory = blanket.get_sensory_states()
    assert sensory == sorted(blanket.sensory_ids)
    assert isinstance(sensory, list)


def test_get_active_states_returns_sorted_list():
    g, seeds = _graph_with_boundary()
    blanket = partition_by_seeds(g, seeds)
    active = blanket.get_active_states()
    assert active == sorted(blanket.active_ids)
    assert isinstance(active, list)


def test_get_sensory_states_empty_when_no_sensory_nodes():
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///empty"))
    g.add_node(_node("only"))
    blanket = partition_by_seeds(g, {"only"})
    assert blanket.get_sensory_states() == []
    assert blanket.get_active_states() == []


# --------------------------------------------------------------------------- #
# visualize() (line 171)
# --------------------------------------------------------------------------- #


def test_visualize_returns_lists_per_role():
    g, seeds = _graph_with_boundary()
    blanket = partition_by_seeds(g, seeds)
    vis = blanket.visualize()
    assert set(vis.keys()) == {"internal", "sensory", "active", "external", "edges"}
    assert vis["internal"] == sorted(blanket.internal_ids)
    assert vis["sensory"] == sorted(blanket.sensory_ids)
    assert vis["active"] == sorted(blanket.active_ids)
    assert vis["external"] == sorted(blanket.external_ids)
    # Edges placeholder is empty list per the docstring contract
    assert vis["edges"] == []


# --------------------------------------------------------------------------- #
# validate() — happy path + each issue branch (lines 196-224)
# --------------------------------------------------------------------------- #


def test_validate_clean_blanket_returns_no_issues():
    g, seeds = _graph_with_boundary()
    blanket = partition_by_seeds(g, seeds)
    issues = blanket.validate()
    assert issues == []


def test_validate_detects_role_dict_size_mismatch():
    blanket = MarkovBlanket(
        roles={"a": BlanketRole.INTERNAL},  # missing 'b'
        seeds={"a", "b"},
        internal_ids={"a", "b"},
    )
    issues = blanket.validate()
    assert any("Role dict size" in issue for issue in issues)


def test_validate_detects_overlap_between_role_sets():
    blanket = MarkovBlanket(
        roles={
            "x": BlanketRole.INTERNAL,
            "y": BlanketRole.SENSORY,
        },
        seeds={"x", "y"},
        internal_ids={"x", "y"},  # 'y' also in sensory below
        sensory_ids={"y"},
    )
    issues = blanket.validate()
    assert any("Overlap between internal/sensory" in issue for issue in issues)


def test_validate_detects_external_seeds():
    blanket = MarkovBlanket(
        roles={"a": BlanketRole.INTERNAL, "ext": BlanketRole.EXTERNAL},
        seeds={"a", "ext"},  # 'ext' is external — not in system
        internal_ids={"a"},
        external_ids={"ext"},
    )
    issues = blanket.validate()
    assert any("seed(s) are external" in issue for issue in issues)


def test_validate_detects_multiple_overlap_pairs():
    """Several overlap pairs are reported separately."""
    blanket = MarkovBlanket(
        roles={
            "p": BlanketRole.INTERNAL,
            "q": BlanketRole.SENSORY,
            "r": BlanketRole.ACTIVE,
            "s": BlanketRole.EXTERNAL,
        },
        seeds=set(),
        internal_ids={"p"},
        sensory_ids={"q", "p"},  # overlap with internal
        active_ids={"r", "q"},  # overlap with sensory
        external_ids={"s"},
    )
    issues = blanket.validate()
    overlap_msgs = [i for i in issues if "Overlap" in i]
    assert len(overlap_msgs) >= 2


# --------------------------------------------------------------------------- #
# to_mermaid() (lines 240-267)
# --------------------------------------------------------------------------- #


def test_to_mermaid_includes_all_role_subgraphs_when_populated():
    g, seeds = _graph_with_boundary()
    blanket = partition_by_seeds(g, seeds)
    diagram = blanket.to_mermaid()
    assert diagram.startswith("graph LR")
    # All four role subgraphs should be present given _graph_with_boundary
    assert "subgraph internal" in diagram
    assert "subgraph sensory" in diagram
    assert "subgraph active" in diagram
    assert "subgraph external" in diagram
    # Each subgraph must be closed with 'end'
    assert diagram.count("    end") == 4


def test_to_mermaid_with_empty_blanket_only_graph_header():
    blanket = MarkovBlanket(roles={}, seeds=set())
    diagram = blanket.to_mermaid()
    assert diagram == "graph LR"


def test_to_mermaid_caps_nodes_at_five_per_subgraph():
    """The mermaid renderer truncates each role to first 5 sorted ids."""
    # Build a graph with 7 internal nodes
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///big"))
    seed_ids = {f"n{i:02d}" for i in range(7)}
    for nid in seed_ids:
        g.add_node(_node(nid))
    # Connect them all internally so they stay internal
    g.add_edge(_edge("e", "n00", "n01"))
    blanket = partition_by_seeds(g, seed_ids)
    diagram = blanket.to_mermaid()
    # First 5 sorted ids appear
    for i in range(5):
        assert f"n0{i}[n0{i}]" in diagram
    # 6th and 7th are clipped
    assert "n05[n05]" not in diagram
    assert "n06[n06]" not in diagram


# --------------------------------------------------------------------------- #
# merge() (lines 286-298)
# --------------------------------------------------------------------------- #


def test_merge_two_blankets_unions_seed_sets_and_role_sets():
    g, seeds = _graph_with_boundary()
    b1 = partition_by_seeds(g, {"i1"})
    b2 = partition_by_seeds(g, {"i2"})
    merged = b1.merge(b2)
    # Seeds are union
    assert merged.seeds == {"i1", "i2"}
    # Internal_ids contain both i1 and i2 from their respective partitions
    assert "i1" in merged.internal_ids or "i1" in merged.sensory_ids or "i1" in merged.active_ids
    assert "i2" in merged.internal_ids or "i2" in merged.sensory_ids or "i2" in merged.active_ids
    # Returned object is independent (a new MarkovBlanket)
    assert isinstance(merged, MarkovBlanket)
    assert merged is not b1
    assert merged is not b2


def test_merge_preserves_metadata_and_rationale():
    g, seeds = _graph_with_boundary()
    b1 = partition_by_seeds(g, {"i1", "i2"})
    b2 = partition_by_seeds(g, {"s1"})
    merged = b1.merge(b2)
    # Rationale is the union of both
    assert set(merged.rationale.keys()) >= set(b1.rationale.keys())
    # Stats and metadata are merged dicts (latter overrides on conflict)
    assert "total_nodes" in merged.stats


# --------------------------------------------------------------------------- #
# blanket_summary() (lines 314-326)
# --------------------------------------------------------------------------- #


def test_blanket_summary_returns_expected_keys_and_values():
    g, seeds = _graph_with_boundary()
    blanket = partition_by_seeds(g, seeds)
    summary = blanket.blanket_summary()
    expected_keys = {
        "n_internal",
        "n_sensory",
        "n_active",
        "n_external",
        "blanket_size",
        "system_size",
        "key_nodes",
    }
    assert set(summary.keys()) == expected_keys
    # blanket_size = sensory + active
    assert summary["blanket_size"] == summary["n_sensory"] + summary["n_active"]
    # system_size = internal + blanket
    assert summary["system_size"] == summary["n_internal"] + summary["blanket_size"]
    assert isinstance(summary["key_nodes"], list)
    assert len(summary["key_nodes"]) <= 5


def test_blanket_summary_key_nodes_truncation():
    """Key nodes pulls 2 internal + 3 boundary, capped at 5 total."""
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///big"))
    # 5 internal nodes, 4 sensory boundary nodes
    for nid in ["i1", "i2", "i3", "i4", "i5"]:
        g.add_node(_node(nid))
    for nid in ["s1", "s2", "s3", "s4"]:
        g.add_node(_node(nid))
    g.add_node(_node("ext1"))

    # internals connected only to other internals
    g.add_edge(_edge("e_ii_1", "i1", "i2"))
    g.add_edge(_edge("e_ii_2", "i2", "i3"))
    # All boundary nodes have an edge from external → sensory
    for s in ["s1", "s2", "s3", "s4"]:
        g.add_edge(_edge(f"e_ext_{s}", "ext1", s))

    seeds = {"i1", "i2", "i3", "i4", "i5", "s1", "s2", "s3", "s4"}
    blanket = partition_by_seeds(g, seeds)
    summary = blanket.blanket_summary()
    assert len(summary["key_nodes"]) == 5


# --------------------------------------------------------------------------- #
# _bidirectional_adjacency self-loop continue branch (line 348)
# --------------------------------------------------------------------------- #


def test_bidirectional_adjacency_skips_self_loops():
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///self-loop"))
    g.add_node(_node("a"))
    g.add_node(_node("b"))
    # Self-loop on 'a' — must not appear in adjacency sets
    g.add_edge(_edge("e_self", "a", "a"))
    # Normal edge
    g.add_edge(_edge("e_ab", "a", "b"))

    adj = _bidirectional_adjacency(g)
    in_a, out_a = adj["a"]
    in_b, out_b = adj["b"]
    # 'a' should not have itself in its neighbour sets
    assert "a" not in in_a
    assert "a" not in out_a
    # 'b' is the target of 'a' — present
    assert "b" in out_a
    assert "a" in in_b
    assert "b" not in out_b


def test_partition_by_seeds_works_with_self_loop_graph():
    """End-to-end partition with a self-loop edge in the graph."""
    g = ProgramGraph(metadata=GraphMetadata(repo_uri="file:///self-loop"))
    g.add_node(_node("a"))
    g.add_edge(_edge("e_self", "a", "a"))
    blanket = partition_by_seeds(g, {"a"})
    # Self-loop alone leaves 'a' as internal
    assert "a" in blanket.internal_ids


# --------------------------------------------------------------------------- #
# role_of / ids_by_role helper accessors
# --------------------------------------------------------------------------- #


def test_role_of_unknown_node_returns_external():
    blanket = MarkovBlanket(roles={}, seeds=set())
    assert blanket.role_of("not_in_graph") is BlanketRole.EXTERNAL


def test_ids_by_role_each_role():
    g, seeds = _graph_with_boundary()
    blanket = partition_by_seeds(g, seeds)
    assert blanket.ids_by_role(BlanketRole.INTERNAL) == blanket.internal_ids
    assert blanket.ids_by_role(BlanketRole.SENSORY) == blanket.sensory_ids
    assert blanket.ids_by_role(BlanketRole.ACTIVE) == blanket.active_ids
    assert blanket.ids_by_role(BlanketRole.EXTERNAL) == blanket.external_ids
