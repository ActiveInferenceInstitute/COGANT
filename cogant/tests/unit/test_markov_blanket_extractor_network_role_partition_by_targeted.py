#!/usr/bin/env python3
"""Targeted branch tests — markov/blanket.py, markov/extractor.py,
markov/network.py.

Covers:
- markov/blanket.py: BlanketRole enum, MarkovBlanket dataclass (boundary_ids,
  role_of, ids_by_role), partition_by_seeds (empty graph, with nodes),
  serialize_blanket, _bidirectional_adjacency
- markov/extractor.py: MarkovBlanketExtractor (init, extract with empty graph)
- markov/network.py: BlanketNetwork (to_dict, to_mermaid), build_blanket_network
"""

import pytest

pytestmark = pytest.mark.unit


def _make_empty_graph():
    from cogant.schemas.graph import GraphMetadata, ProgramGraph

    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))


def _make_graph_with_nodes():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
    n2 = builder.add_node(NodeKind.CLASS, "Cls", "mod.Cls", path="mod.py")
    n3 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn", path="mod.py")
    builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
    builder.add_edge(n1.id, n3.id, EdgeKind.CONTAINS)
    return builder.finalize(), [n1.id, n2.id, n3.id]


# ---------------------------------------------------------------------------
# markov/blanket.py — BlanketRole enum
# ---------------------------------------------------------------------------


class TestBlanketRole:
    def test_blanket_role_values(self):
        from cogant.markov.blanket import BlanketRole

        assert BlanketRole.INTERNAL is not None
        assert BlanketRole.SENSORY is not None
        assert BlanketRole.ACTIVE is not None
        assert BlanketRole.EXTERNAL is not None

    def test_blanket_role_is_str(self):
        from cogant.markov.blanket import BlanketRole

        assert isinstance(BlanketRole.INTERNAL, str)


# ---------------------------------------------------------------------------
# markov/blanket.py — MarkovBlanket dataclass
# ---------------------------------------------------------------------------


class TestMarkovBlanket:
    def _make_blanket(self):
        from cogant.markov.blanket import BlanketRole, MarkovBlanket

        return MarkovBlanket(
            roles={
                "n0": BlanketRole.INTERNAL,
                "n1": BlanketRole.SENSORY,
                "n2": BlanketRole.EXTERNAL,
            },
            seeds={"n0"},
            internal_ids={"n0"},
            sensory_ids={"n1"},
            active_ids=set(),
            external_ids={"n2"},
        )

    def test_boundary_ids_union(self):
        blanket = self._make_blanket()
        boundary = blanket.boundary_ids
        assert "n1" in boundary
        assert "n0" not in boundary  # internal is not boundary

    def test_role_of_known(self):
        from cogant.markov.blanket import BlanketRole

        blanket = self._make_blanket()
        assert blanket.role_of("n0") == BlanketRole.INTERNAL
        assert blanket.role_of("n1") == BlanketRole.SENSORY

    def test_role_of_unknown_defaults_external(self):
        from cogant.markov.blanket import BlanketRole

        blanket = self._make_blanket()
        assert blanket.role_of("nonexistent") == BlanketRole.EXTERNAL

    def test_ids_by_role_internal(self):
        from cogant.markov.blanket import BlanketRole

        blanket = self._make_blanket()
        ids = blanket.ids_by_role(BlanketRole.INTERNAL)
        assert "n0" in ids

    def test_ids_by_role_sensory(self):
        from cogant.markov.blanket import BlanketRole

        blanket = self._make_blanket()
        ids = blanket.ids_by_role(BlanketRole.SENSORY)
        assert "n1" in ids

    def test_ids_by_role_external(self):
        from cogant.markov.blanket import BlanketRole

        blanket = self._make_blanket()
        ids = blanket.ids_by_role(BlanketRole.EXTERNAL)
        assert "n2" in ids


# ---------------------------------------------------------------------------
# markov/blanket.py — partition_by_seeds and serialize_blanket
# ---------------------------------------------------------------------------


class TestPartitionBySeeds:
    def test_partition_empty_graph_empty_seeds(self):
        from cogant.markov.blanket import partition_by_seeds

        graph = _make_empty_graph()
        blanket = partition_by_seeds(graph, seeds=set())
        assert isinstance(blanket.roles, dict)
        assert blanket.boundary_ids == set()

    def test_partition_with_graph_and_seeds(self):
        from cogant.markov.blanket import partition_by_seeds

        graph, node_ids = _make_graph_with_nodes()
        seeds = {node_ids[0]}  # MODULE as seed
        blanket = partition_by_seeds(graph, seeds=seeds)
        assert isinstance(blanket.roles, dict)
        # All nodes should be classified
        assert len(blanket.roles) == len(graph.nodes)

    def test_partition_empty_seeds_all_external(self):
        from cogant.markov.blanket import BlanketRole, partition_by_seeds

        graph, node_ids = _make_graph_with_nodes()
        blanket = partition_by_seeds(graph, seeds=set())
        # With no seeds, every node should be EXTERNAL
        for node_id in graph.nodes:
            assert blanket.role_of(node_id) == BlanketRole.EXTERNAL


class TestSerializeBlanket:
    def test_serialize_empty_blanket(self):
        from cogant.markov.blanket import partition_by_seeds, serialize_blanket

        graph = _make_empty_graph()
        blanket = partition_by_seeds(graph, seeds=set())
        result = serialize_blanket(blanket, graph)
        assert isinstance(result, dict)

    def test_serialize_with_nodes(self):
        from cogant.markov.blanket import partition_by_seeds, serialize_blanket

        graph, node_ids = _make_graph_with_nodes()
        blanket = partition_by_seeds(graph, seeds={node_ids[0]})
        result = serialize_blanket(blanket, graph)
        assert isinstance(result, dict)
        # Should have role sections
        assert (
            "internal" in result or "sensory" in result or "external" in result or "roles" in result
        )


# ---------------------------------------------------------------------------
# markov/extractor.py — MarkovBlanketExtractor
# ---------------------------------------------------------------------------


class TestMarkovBlanketExtractor:
    def test_init(self):
        from cogant.markov.extractor import MarkovBlanketExtractor

        graph = _make_empty_graph()
        extractor = MarkovBlanketExtractor(graph)
        assert extractor is not None

    def test_extract_empty_graph(self):
        from cogant.markov.blanket import MarkovBlanket
        from cogant.markov.extractor import MarkovBlanketExtractor

        graph = _make_empty_graph()
        extractor = MarkovBlanketExtractor(graph)
        blanket = extractor.extract()
        assert isinstance(blanket, MarkovBlanket)

    def test_extract_with_seeds(self):
        from cogant.markov.blanket import MarkovBlanket
        from cogant.markov.extractor import MarkovBlanketExtractor

        graph, node_ids = _make_graph_with_nodes()
        extractor = MarkovBlanketExtractor(graph)
        blanket = extractor.extract(seeds={node_ids[0]})
        assert isinstance(blanket, MarkovBlanket)
        assert len(blanket.roles) >= 1


# ---------------------------------------------------------------------------
# markov/network.py — BlanketNetwork and build_blanket_network
# ---------------------------------------------------------------------------


class TestBlanketNetwork:
    def _make_network(self):
        from cogant.markov.extractor import MarkovBlanketExtractor
        from cogant.markov.network import build_blanket_network

        graph, node_ids = _make_graph_with_nodes()
        extractor = MarkovBlanketExtractor(graph)
        blanket = extractor.extract()
        return build_blanket_network(graph, blanket), graph, blanket

    def test_build_network(self):
        from cogant.markov.network import BlanketNetwork

        network, _, _ = self._make_network()
        assert isinstance(network, BlanketNetwork)

    def test_to_dict(self):
        network, _, _ = self._make_network()
        result = network.to_dict()
        assert isinstance(result, dict)

    def test_to_mermaid(self):
        network, _, _ = self._make_network()
        mermaid = network.to_mermaid()
        assert isinstance(mermaid, str)
        assert len(mermaid) > 0
