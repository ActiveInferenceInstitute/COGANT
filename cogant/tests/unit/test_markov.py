"""Unit tests for :mod:`cogant.markov`.

These tests exercise the full Markov blanket API surface that COGANT
relies on for its Active Inference export: the low-level partitioner,
every seed strategy supported by :class:`MarkovBlanketExtractor`, the
two-tier auto fallback, the collapsed :class:`BlanketNetwork` view, and
the JSON serializer used by the GNN bundle.

The tests deliberately build small, hand-constructed graphs rather than
parsing fixtures so that partition expectations are exact — there is no
ambiguity about which nodes should land in which role.
"""

from __future__ import annotations

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.markov import (
    BlanketNetwork,
    BlanketRole,
    MarkovBlanket,
    MarkovBlanketExtractor,
    build_blanket_network,
    partition_by_seeds,
    serialize_blanket,
)
from cogant.schemas.core import EdgeKind, NodeKind


# ---------------------------------------------------------------- fixtures --

def _two_module_graph():
    """Build a deterministic two-module graph with a known boundary.

    Layout::

        core (MODULE)                 util (MODULE)
          ├── Engine (CLASS)             ├── Logger (CLASS)
          │     ├── run (METHOD)         │     └── emit (METHOD)
          │     └── step (METHOD)        └── Config (CLASS)
          └── helper (FUNCTION)                └── load (METHOD)

    Cross-module edges (these are what make ``Engine.run`` a *boundary*
    node rather than purely internal):

        Engine.run --CALLS-->  Logger.emit
        Engine.step --READS--> Config.load
    """
    b = ProgramGraphBuilder(repo_uri="test://two_module")

    core = b.add_node(NodeKind.MODULE, "core", "core", path="core.py")
    util = b.add_node(NodeKind.MODULE, "util", "util", path="util.py")

    engine = b.add_node(NodeKind.CLASS, "Engine", "core.Engine", path="core.py")
    helper = b.add_node(NodeKind.FUNCTION, "helper", "core.helper", path="core.py")
    run = b.add_node(NodeKind.METHOD, "run", "core.Engine.run", path="core.py")
    step = b.add_node(NodeKind.METHOD, "step", "core.Engine.step", path="core.py")

    logger_cls = b.add_node(NodeKind.CLASS, "Logger", "util.Logger", path="util.py")
    emit = b.add_node(NodeKind.METHOD, "emit", "util.Logger.emit", path="util.py")
    config = b.add_node(NodeKind.CLASS, "Config", "util.Config", path="util.py")
    load = b.add_node(NodeKind.METHOD, "load", "util.Config.load", path="util.py")

    # Containment (CORE)
    b.add_edge(core.id, engine.id, EdgeKind.CONTAINS)
    b.add_edge(core.id, helper.id, EdgeKind.CONTAINS)
    b.add_edge(engine.id, run.id, EdgeKind.CONTAINS)
    b.add_edge(engine.id, step.id, EdgeKind.CONTAINS)

    # Containment (UTIL)
    b.add_edge(util.id, logger_cls.id, EdgeKind.CONTAINS)
    b.add_edge(logger_cls.id, emit.id, EdgeKind.CONTAINS)
    b.add_edge(util.id, config.id, EdgeKind.CONTAINS)
    b.add_edge(config.id, load.id, EdgeKind.CONTAINS)

    # Intra-core cohesion (keeps "core" above "util" on the cohesion score)
    b.add_edge(run.id, step.id, EdgeKind.CALLS)
    b.add_edge(run.id, helper.id, EdgeKind.CALLS)

    # Cross-module edges: engine→logger is OUT (active), engine→config is IN-facing
    b.add_edge(run.id, emit.id, EdgeKind.CALLS)
    b.add_edge(step.id, load.id, EdgeKind.READS)
    # And one external-to-internal edge so sensory has something to latch onto
    b.add_edge(load.id, helper.id, EdgeKind.CALLS)

    graph = b.finalize()
    return graph, {
        "core": core.id,
        "util": util.id,
        "engine": engine.id,
        "helper": helper.id,
        "run": run.id,
        "step": step.id,
        "logger": logger_cls.id,
        "emit": emit.id,
        "config": config.id,
        "load": load.id,
    }


def _single_module_graph():
    """Single-module graph that would produce a degenerate auto partition."""
    b = ProgramGraphBuilder(repo_uri="test://single_module")
    mod = b.add_node(NodeKind.MODULE, "app", "app", path="app.py")
    big = b.add_node(NodeKind.CLASS, "Big", "app.Big", path="app.py")
    small = b.add_node(NodeKind.CLASS, "Small", "app.Small", path="app.py")
    big_m1 = b.add_node(NodeKind.METHOD, "m1", "app.Big.m1", path="app.py")
    big_m2 = b.add_node(NodeKind.METHOD, "m2", "app.Big.m2", path="app.py")
    small_m = b.add_node(NodeKind.METHOD, "s", "app.Small.s", path="app.py")

    b.add_edge(mod.id, big.id, EdgeKind.CONTAINS)
    b.add_edge(mod.id, small.id, EdgeKind.CONTAINS)
    b.add_edge(big.id, big_m1.id, EdgeKind.CONTAINS)
    b.add_edge(big.id, big_m2.id, EdgeKind.CONTAINS)
    b.add_edge(small.id, small_m.id, EdgeKind.CONTAINS)
    b.add_edge(big_m1.id, small_m.id, EdgeKind.CALLS)

    return b.finalize(), {
        "mod": mod.id,
        "big": big.id,
        "small": small.id,
        "big_m1": big_m1.id,
        "big_m2": big_m2.id,
        "small_m": small_m.id,
    }


# ------------------------------------------------- partition_by_seeds tests --

class TestPartitionBySeeds:
    def test_every_node_gets_exactly_one_role(self):
        graph, ids = _two_module_graph()
        seeds = {ids["core"], ids["engine"], ids["run"], ids["step"], ids["helper"]}
        blanket = partition_by_seeds(graph, seeds)

        # Partition is exhaustive and mutually exclusive.
        all_ids = (
            blanket.internal_ids
            | blanket.sensory_ids
            | blanket.active_ids
            | blanket.external_ids
        )
        assert all_ids == set(graph.nodes)
        assert len(all_ids) == len(blanket.roles)

    def test_internal_nodes_have_no_external_neighbours(self):
        graph, ids = _two_module_graph()
        seeds = {ids["engine"], ids["step"]}  # small internal island
        blanket = partition_by_seeds(graph, seeds)

        for nid in blanket.internal_ids:
            for edge in graph.get_edges_from(nid):
                assert edge.target_id in seeds
            for edge in graph.get_edges_to(nid):
                assert edge.source_id in seeds

    def test_empty_seeds_produces_all_external(self):
        graph, _ = _two_module_graph()
        blanket = partition_by_seeds(graph, set())
        assert blanket.internal_ids == set()
        assert blanket.sensory_ids == set()
        assert blanket.active_ids == set()
        assert blanket.external_ids == set(graph.nodes)
        assert all(r is BlanketRole.EXTERNAL for r in blanket.roles.values())

    def test_stats_sum_to_total(self):
        graph, ids = _two_module_graph()
        seeds = {ids["core"], ids["engine"], ids["run"]}
        blanket = partition_by_seeds(graph, seeds)
        s = blanket.stats
        assert (
            s["internal_count"]
            + s["sensory_count"]
            + s["active_count"]
            + s["external_count"]
            == s["total_nodes"]
        )
        assert 0.0 <= s["internal_ratio"] <= 1.0
        assert 0.0 <= s["boundary_ratio"] <= 1.0

    def test_rationale_populated_for_every_node(self):
        graph, ids = _two_module_graph()
        blanket = partition_by_seeds(graph, {ids["engine"], ids["run"]})
        assert set(blanket.rationale.keys()) == set(graph.nodes)
        for text in blanket.rationale.values():
            assert isinstance(text, str) and text

    def test_role_of_defaults_to_external(self):
        graph, ids = _two_module_graph()
        blanket = partition_by_seeds(graph, {ids["engine"]})
        assert blanket.role_of("does-not-exist") is BlanketRole.EXTERNAL

    def test_ids_by_role(self):
        graph, ids = _two_module_graph()
        blanket = partition_by_seeds(graph, {ids["engine"], ids["run"], ids["step"]})
        assert blanket.ids_by_role(BlanketRole.INTERNAL) is blanket.internal_ids
        assert blanket.ids_by_role(BlanketRole.SENSORY) is blanket.sensory_ids
        assert blanket.ids_by_role(BlanketRole.ACTIVE) is blanket.active_ids
        assert blanket.ids_by_role(BlanketRole.EXTERNAL) is blanket.external_ids

    def test_boundary_property(self):
        graph, ids = _two_module_graph()
        blanket = partition_by_seeds(graph, {ids["engine"], ids["run"], ids["step"]})
        assert blanket.boundary_ids == blanket.sensory_ids | blanket.active_ids


# ---------------------------------------------- MarkovBlanketExtractor tests --

class TestExtractorExplicitStrategy:
    def test_explicit_seeds_respected(self):
        graph, ids = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        blanket = ex.extract(
            strategy="explicit",
            seeds=[ids["engine"], ids["run"], ids["step"]],
        )
        assert blanket.seeds == {ids["engine"], ids["run"], ids["step"]}
        assert blanket.metadata["strategy"] == "explicit"

    def test_explicit_requires_seeds(self):
        graph, _ = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        with pytest.raises(ValueError, match="explicit"):
            ex.extract(strategy="explicit")


class TestExtractorModuleStrategy:
    def test_module_strategy_descends_contains(self):
        graph, ids = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        blanket = ex.extract(strategy="module", module_names=["core"])
        # Every contains-closure member of "core" must be in the seed set.
        expected = {ids["core"], ids["engine"], ids["helper"],
                    ids["run"], ids["step"]}
        assert expected <= blanket.seeds
        assert blanket.metadata["module_names"] == ["core"]

    def test_module_strategy_requires_names(self):
        graph, _ = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        with pytest.raises(ValueError, match="module_names"):
            ex.extract(strategy="module")


class TestExtractorKindStrategy:
    def test_kind_strategy_collects_all_classes(self):
        graph, ids = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        blanket = ex.extract(strategy="kind", kinds=[NodeKind.CLASS])
        class_ids = {ids["engine"], ids["logger"], ids["config"]}
        assert class_ids <= blanket.seeds
        assert blanket.metadata["kinds"] == ["class"]

    def test_kind_strategy_requires_kinds(self):
        graph, _ = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        with pytest.raises(ValueError, match="kinds"):
            ex.extract(strategy="kind")


class TestExtractorAutoStrategy:
    def test_auto_on_two_module_graph_picks_module_tier(self):
        graph, _ = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        blanket = ex.extract(strategy="auto")
        assert blanket.metadata["auto_tier"] == "module"
        assert blanket.metadata["chosen_module_id"]
        assert isinstance(blanket.metadata["scoreboard"], list)
        # Boundary must be non-empty (there IS a cross-module edge).
        assert blanket.boundary_ids, "auto should find a real boundary in two-module graph"

    def test_auto_on_single_module_graph_falls_back_to_class(self):
        graph, _ = _single_module_graph()
        ex = MarkovBlanketExtractor(graph)
        blanket = ex.extract(strategy="auto")
        assert blanket.metadata["auto_tier"] in {"class", "class_aggregate"}
        assert "fell back" in blanket.metadata["auto_reason"].lower() or \
               blanket.metadata["auto_tier"] == "class_aggregate"

    def test_auto_on_empty_graph(self):
        b = ProgramGraphBuilder(repo_uri="test://empty")
        graph = b.finalize()
        ex = MarkovBlanketExtractor(graph)
        blanket = ex.extract(strategy="auto")
        assert blanket.internal_ids == set()
        assert blanket.boundary_ids == set()
        assert blanket.external_ids == set()


class TestExtractorUnknownStrategy:
    def test_unknown_strategy_raises(self):
        graph, _ = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        with pytest.raises(ValueError, match="Unknown"):
            ex.extract(strategy="bogus")  # type: ignore[arg-type]


class TestExtractorDeterminism:
    def test_same_graph_produces_same_blanket(self):
        graph, _ = _two_module_graph()
        ex1 = MarkovBlanketExtractor(graph)
        ex2 = MarkovBlanketExtractor(graph)
        b1 = ex1.extract(strategy="auto")
        b2 = ex2.extract(strategy="auto")
        assert b1.internal_ids == b2.internal_ids
        assert b1.boundary_ids == b2.boundary_ids
        assert b1.external_ids == b2.external_ids


# ------------------------------------------------------- BlanketNetwork tests --

class TestBlanketNetwork:
    def test_build_and_serialize(self):
        graph, ids = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        blanket = ex.extract(strategy="auto")
        net = build_blanket_network(graph, blanket)
        assert isinstance(net, BlanketNetwork)
        data = net.to_dict()
        assert set(data["role_counts"].keys()) == {
            "internal", "sensory", "active", "external"
        }
        # Sum of role counts equals total nodes.
        assert sum(data["role_counts"].values()) == len(graph.nodes)

    def test_mermaid_contains_four_roles(self):
        graph, _ = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        blanket = ex.extract(strategy="auto")
        net = build_blanket_network(graph, blanket)
        text = net.to_mermaid()
        assert text.startswith("graph LR")
        for role in ("internal", "sensory", "active", "external"):
            assert role in text

    def test_role_counts_match_blanket(self):
        graph, ids = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        blanket = ex.extract(strategy="kind", kinds=[NodeKind.CLASS])
        net = build_blanket_network(graph, blanket)
        assert net.role_counts["internal"] == len(blanket.internal_ids)
        assert net.role_counts["sensory"] == len(blanket.sensory_ids)
        assert net.role_counts["active"] == len(blanket.active_ids)
        assert net.role_counts["external"] == len(blanket.external_ids)


# ----------------------------------------------------- serialize_blanket tests --

class TestSerializeBlanket:
    def test_default_payload_shape(self):
        graph, ids = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        blanket = ex.extract(strategy="module", module_names=["core"])
        payload = serialize_blanket(blanket, graph)

        assert payload["schema_version"] == "1.0.0"
        assert set(payload["roles"].keys()) == {
            "internal", "sensory", "active", "external"
        }
        assert "stats" in payload and "metadata" in payload
        # Every node in every role has the four canonical fields.
        for role_members in payload["roles"].values():
            for record in role_members:
                assert set(record.keys()) >= {"id", "kind", "name", "path"}

    def test_suppress_rationale(self):
        graph, ids = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        blanket = ex.extract(strategy="module", module_names=["core"])
        payload = serialize_blanket(blanket, graph, include_rationale=False)
        for role_members in payload["roles"].values():
            for record in role_members:
                assert "rationale" not in record

    def test_max_nodes_per_role_caps_list(self):
        graph, _ = _two_module_graph()
        ex = MarkovBlanketExtractor(graph)
        blanket = ex.extract(strategy="kind", kinds=[NodeKind.METHOD])
        payload = serialize_blanket(blanket, graph, max_nodes_per_role=1)
        for role_members in payload["roles"].values():
            assert len(role_members) <= 1
