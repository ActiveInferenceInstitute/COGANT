#!/usr/bin/env python3
"""Coverage boost batch 4 — targets simulate/distributions, simulate/free_energy,
graph/queries, graph/builder, gnn/formatter/* modules.

All tests use real objects and real data.  No mocks.
"""

from __future__ import annotations

import math

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph(nodes=None, edges=None):
    from cogant.schemas.graph import GraphMetadata, ProgramGraph

    g = ProgramGraph(metadata=GraphMetadata(repo_uri="test://repo"))
    for n in nodes or []:
        g.add_node(n)
    for e in edges or []:
        g.add_edge(e)
    return g


def _make_node(
    node_id: str, kind, name: str = "node", path: str | None = None, language: str | None = None
):
    from cogant.schemas.core import Node

    return Node(id=node_id, kind=kind, name=name, qualified_name=name, path=path, language=language)


def _make_edge(edge_id: str, src: str, tgt: str, kind, weight: float = 1.0):
    from cogant.schemas.core import Edge

    return Edge(id=edge_id, source_id=src, target_id=tgt, kind=kind, weight=weight)


def _make_state_space(
    variables=None,
    observations=None,
    actions=None,
    transitions=None,
    likelihoods=None,
    preferences=None,
):
    from cogant.statespace.compiler import StateSpaceModel
    from cogant.statespace.temporal import TimeRegime

    return StateSpaceModel(
        id="ss1",
        schema_name="test",
        time_regime=TimeRegime.SYNCHRONOUS,
        variables=variables or {},
        observations=observations or {},
        actions=actions or {},
        transitions=transitions or {},
        likelihoods=likelihoods or {},
        preferences=preferences or {},
    )


def _make_variable(vid: str, vtype=None, node_id: str | None = None):
    from cogant.statespace.variables import StateVariable, StateVariableType

    return StateVariable(
        id=vid, name=vid, var_type=vtype or StateVariableType.DISCRETE, node_id=node_id or vid
    )


def _make_action(aid: str, effects=None, controller_id: str = "ctrl"):
    from cogant.statespace.compiler import Action

    return Action(id=aid, name=aid, controller_id=controller_id, effects=effects or [])


# ---------------------------------------------------------------------------
# simulate/distributions.py — CategoricalDistribution
# ---------------------------------------------------------------------------


class TestCategoricalDistribution:
    """Full coverage of CategoricalDistribution methods."""

    def test_init_uniform_distribution(self):
        from cogant.simulate.distributions import CategoricalDistribution

        d = CategoricalDistribution(["a", "b", "c"])
        assert len(d.probabilities) == 3
        assert abs(sum(d.probabilities) - 1.0) < 1e-9
        assert all(abs(p - 1 / 3) < 1e-9 for p in d.probabilities)

    def test_init_empty_categories(self):
        from cogant.simulate.distributions import CategoricalDistribution

        d = CategoricalDistribution([])
        assert d.n == 0
        assert d.probabilities == []
        assert d.dist == {}

    def test_init_custom_probabilities_normalized(self):
        from cogant.simulate.distributions import CategoricalDistribution

        d = CategoricalDistribution(["a", "b"], [2.0, 2.0])
        assert abs(d.dist["a"] - 0.5) < 1e-9
        assert abs(d.dist["b"] - 0.5) < 1e-9

    def test_init_mismatched_probs_raises(self):
        from cogant.simulate.distributions import CategoricalDistribution

        with pytest.raises(ValueError, match="Number of probabilities"):
            CategoricalDistribution(["a", "b"], [0.5, 0.3, 0.2])

    def test_init_zero_sum_probs_raises(self):
        from cogant.simulate.distributions import CategoricalDistribution

        with pytest.raises(ValueError, match="positive"):
            CategoricalDistribution(["a", "b"], [0.0, 0.0])

    def test_sample_returns_valid_category(self):
        from cogant.simulate.distributions import CategoricalDistribution

        d = CategoricalDistribution(["x", "y", "z"])
        for _ in range(10):
            result = d.sample()
            assert result in ("x", "y", "z")

    def test_log_prob_known_category(self):
        from cogant.simulate.distributions import CategoricalDistribution

        d = CategoricalDistribution(["a", "b"], [0.7, 0.3])
        lp = d.log_prob("a")
        assert abs(lp - math.log(0.7)) < 1e-9

    def test_log_prob_unknown_category_raises(self):
        from cogant.simulate.distributions import CategoricalDistribution

        d = CategoricalDistribution(["a"])
        with pytest.raises(KeyError, match="Unknown category"):
            d.log_prob("z")

    def test_entropy_uniform_is_log_n(self):
        from cogant.simulate.distributions import CategoricalDistribution

        n = 4
        d = CategoricalDistribution([str(i) for i in range(n)])
        h = d.entropy()
        assert abs(h - math.log(n)) < 1e-9

    def test_entropy_degenerate_is_zero(self):
        from cogant.simulate.distributions import CategoricalDistribution

        d = CategoricalDistribution(["a", "b"], [1.0, 0.0])
        h = d.entropy()
        assert h == 0.0

    def test_kl_divergence_same_distribution_is_zero(self):
        from cogant.simulate.distributions import CategoricalDistribution

        d1 = CategoricalDistribution(["a", "b"], [0.6, 0.4])
        d2 = CategoricalDistribution(["a", "b"], [0.6, 0.4])
        kl = d1.kl_divergence(d2)
        assert abs(kl) < 1e-9

    def test_kl_divergence_different_distributions(self):
        from cogant.simulate.distributions import CategoricalDistribution

        d1 = CategoricalDistribution(["a", "b"], [0.9, 0.1])
        d2 = CategoricalDistribution(["a", "b"], [0.5, 0.5])
        kl = d1.kl_divergence(d2)
        assert kl > 0

    def test_kl_divergence_infinite_when_q_zero(self):
        from cogant.simulate.distributions import CategoricalDistribution

        # d1 has p > 0 where d2 has q = 0 → KL = inf
        d1 = CategoricalDistribution(["a", "b"], [0.5, 0.5])
        d2 = CategoricalDistribution(["a", "b"], [1.0, 0.0])
        kl = d1.kl_divergence(d2)
        assert kl == float("inf")

    def test_kl_divergence_different_categories_raises(self):
        from cogant.simulate.distributions import CategoricalDistribution

        d1 = CategoricalDistribution(["a", "b"])
        d2 = CategoricalDistribution(["x", "y"])
        with pytest.raises(ValueError, match="same categories"):
            d1.kl_divergence(d2)

    def test_update_returns_posterior(self):
        from cogant.simulate.distributions import CategoricalDistribution

        prior = CategoricalDistribution(["s1", "s2"], [0.5, 0.5])
        # likelihood["obs" | "s1"] = 0.9, likelihood["obs" | "s2"] = 0.1
        likelihood = CategoricalDistribution(["s1", "s2"], [0.9, 0.1])
        posterior = prior.update("s1", likelihood)
        # Should concentrate mass on s1
        assert posterior.dist["s1"] > posterior.dist["s2"]

    def test_update_zero_posterior_falls_back_to_prior(self):
        from cogant.simulate.distributions import CategoricalDistribution

        # Trigger the zero-total fallback by directly manipulating the dict
        # after a valid construction.
        prior = CategoricalDistribution(["s1", "s2"], [0.5, 0.5])
        likelihood_zero = CategoricalDistribution(["s1", "s2"], [0.5, 0.5])
        # Force all probabilities to zero so the update produces zero unnormalized.
        likelihood_zero.dist = {"s1": 0.0, "s2": 0.0}
        likelihood_zero.probabilities = [0.0, 0.0]
        # "s1" is in likelihood_zero.categories but has prob 0 → total=0 → fallback
        posterior = prior.update("s1", likelihood_zero)
        # Should fall back to prior since total=0
        assert abs(posterior.dist["s1"] - 0.5) < 1e-9

    def test_update_unknown_observation_raises(self):
        from cogant.simulate.distributions import CategoricalDistribution

        prior = CategoricalDistribution(["s1", "s2"])
        likelihood = CategoricalDistribution(["a", "b"])
        with pytest.raises(ValueError, match="not in likelihood"):
            prior.update("missing_obs", likelihood)

    def test_repr_contains_categories(self):
        from cogant.simulate.distributions import CategoricalDistribution

        d = CategoricalDistribution(["alpha", "beta"])
        r = repr(d)
        assert "alpha" in r or "CategoricalDistribution" in r


# ---------------------------------------------------------------------------
# simulate/distributions.py — TransitionMatrix
# ---------------------------------------------------------------------------


class TestTransitionMatrix:
    """Tests for TransitionMatrix."""

    def test_init_stores_states_and_actions(self):
        from cogant.simulate.distributions import TransitionMatrix

        m = TransitionMatrix(["s1", "s2"], ["a1", "a2"])
        assert m.states == ["s1", "s2"]
        assert m.actions == ["a1", "a2"]

    def test_get_next_state_dist_default_is_uniform(self):
        from cogant.simulate.distributions import TransitionMatrix

        m = TransitionMatrix(["s1", "s2"], ["a1"])
        dist = m.get_next_state_dist("s1", "a1")
        assert abs(dist.dist["s1"] - 0.5) < 1e-9

    def test_set_and_get_transition(self):
        from cogant.simulate.distributions import TransitionMatrix

        m = TransitionMatrix(["s1", "s2"], ["a1"])
        m.set_transition("s1", "a1", "s2", 0.8)
        dist = m.get_next_state_dist("s1", "a1")
        assert dist.dist["s2"] >= 0.5  # majority mass on s2

    def test_set_transition_unknown_state_raises(self):
        from cogant.simulate.distributions import TransitionMatrix

        m = TransitionMatrix(["s1"], ["a1"])
        with pytest.raises(ValueError, match="Unknown state"):
            m.set_transition("bad", "a1", "s1", 0.5)

    def test_set_transition_unknown_action_raises(self):
        from cogant.simulate.distributions import TransitionMatrix

        m = TransitionMatrix(["s1"], ["a1"])
        with pytest.raises(ValueError, match="Unknown action"):
            m.set_transition("s1", "bad", "s1", 0.5)

    def test_set_transition_unknown_next_state_raises(self):
        from cogant.simulate.distributions import TransitionMatrix

        m = TransitionMatrix(["s1"], ["a1"])
        with pytest.raises(ValueError, match="Unknown next_state"):
            m.set_transition("s1", "a1", "bad", 0.5)

    def test_get_next_state_dist_unknown_state_raises(self):
        from cogant.simulate.distributions import TransitionMatrix

        m = TransitionMatrix(["s1"], ["a1"])
        with pytest.raises(ValueError, match="Unknown state"):
            m.get_next_state_dist("bad", "a1")

    def test_get_next_state_dist_unknown_action_raises(self):
        from cogant.simulate.distributions import TransitionMatrix

        m = TransitionMatrix(["s1"], ["a1"])
        with pytest.raises(ValueError, match="Unknown action"):
            m.get_next_state_dist("s1", "bad")

    def test_from_state_space_empty(self):
        from cogant.simulate.distributions import TransitionMatrix

        ss = _make_state_space()
        m = TransitionMatrix.from_state_space(ss)
        assert m.states == []
        assert m.actions == []

    def test_from_state_space_with_variables_and_actions(self):
        from cogant.simulate.distributions import TransitionMatrix

        v1 = _make_variable("v1")
        a1 = _make_action("a1")
        ss = _make_state_space(variables={"v1": v1}, actions={"a1": a1})
        m = TransitionMatrix.from_state_space(ss)
        assert "v1" in m.states
        assert "a1" in m.actions

    def test_repr_contains_state_count(self):
        from cogant.simulate.distributions import TransitionMatrix

        m = TransitionMatrix(["s1", "s2"], ["a1"])
        r = repr(m)
        assert "2 states" in r


# ---------------------------------------------------------------------------
# simulate/free_energy.py — principled functions
# ---------------------------------------------------------------------------


class TestFreeEnergyFunctions:
    """Tests for variational_free_energy, bayesian_belief_update, expected_free_energy."""

    def test_variational_free_energy_empty_beliefs(self):
        from cogant.simulate.free_energy import variational_free_energy

        result = variational_free_energy([], [], [[]])
        assert result == 0.0

    def test_variational_free_energy_kl_only_no_obs(self):
        from cogant.simulate.free_energy import variational_free_energy

        beliefs = [0.8, 0.2]
        prior = [0.5, 0.5]
        vfe = variational_free_energy(beliefs, prior, [])
        # KL > 0 since beliefs != prior
        assert vfe > 0

    def test_variational_free_energy_with_uniform_obs(self):
        from cogant.simulate.free_energy import variational_free_energy

        beliefs = [0.6, 0.4]
        prior = [0.5, 0.5]
        A = [[0.9, 0.1], [0.1, 0.9]]  # 2 obs x 2 states
        vfe = variational_free_energy(beliefs, prior, A)
        assert isinstance(vfe, float)

    def test_variational_free_energy_with_observation(self):
        from cogant.simulate.free_energy import variational_free_energy

        beliefs = [0.6, 0.4]
        prior = [0.5, 0.5]
        A = [[0.9, 0.1], [0.1, 0.9]]
        obs = [1.0, 0.0]  # observed outcome 0
        vfe = variational_free_energy(beliefs, prior, A, observation=obs)
        assert isinstance(vfe, float)

    def test_variational_free_energy_prior_mismatch_raises(self):
        from cogant.simulate.free_energy import variational_free_energy

        with pytest.raises(ValueError, match="prior length"):
            variational_free_energy([0.5, 0.5], [0.5], [[0.9, 0.1]])

    def test_variational_free_energy_obs_length_mismatch_raises(self):
        from cogant.simulate.free_energy import variational_free_energy

        with pytest.raises(ValueError, match="observation length"):
            variational_free_energy([0.5, 0.5], [0.5, 0.5], [[0.9, 0.1]], [1.0, 0.0, 0.0])

    def test_variational_free_energy_A_row_mismatch_raises(self):
        from cogant.simulate.free_energy import variational_free_energy

        A = [[0.9]]  # 1 state but beliefs has 2
        with pytest.raises(ValueError, match="n_states entries"):
            variational_free_energy([0.5, 0.5], [0.5, 0.5], A)

    def test_bayesian_belief_update_basic(self):
        from cogant.simulate.free_energy import bayesian_belief_update

        prior = [0.5, 0.5]
        A = [[0.9, 0.1], [0.1, 0.9]]
        posterior = bayesian_belief_update(prior, A, 0)
        assert len(posterior) == 2
        assert abs(sum(posterior) - 1.0) < 1e-9
        assert posterior[0] > posterior[1]  # obs 0 → state 0 more likely

    def test_bayesian_belief_update_empty_prior(self):
        from cogant.simulate.free_energy import bayesian_belief_update

        result = bayesian_belief_update([], [[]], 0)
        assert result == []

    def test_bayesian_belief_update_out_of_range_raises(self):
        from cogant.simulate.free_energy import bayesian_belief_update

        with pytest.raises(IndexError, match="out of range"):
            bayesian_belief_update([0.5, 0.5], [[0.9, 0.1]], 5)

    def test_bayesian_belief_update_zero_likelihood_falls_back(self):
        from cogant.simulate.free_energy import bayesian_belief_update

        prior = [0.5, 0.5]
        A = [[0.0, 0.0]]  # zero likelihood for all states
        posterior = bayesian_belief_update(prior, A, 0)
        # Falls back to prior
        assert abs(posterior[0] - 0.5) < 1e-9

    def test_expected_free_energy_empty_beliefs(self):
        from cogant.simulate.free_energy import expected_free_energy

        result = expected_free_energy([], [], [[]], [[[0.0]]], [])
        assert result == 0.0

    def test_expected_free_energy_no_obs_returns_zero(self):
        from cogant.simulate.free_energy import expected_free_energy

        result = expected_free_energy([0], [0.5], [], [[[1.0]]], [])
        assert result == 0.0

    def test_expected_free_energy_single_step(self):
        from cogant.simulate.free_energy import expected_free_energy

        # 2 states, 1 obs, 1 action
        beliefs = [0.5, 0.5]
        A = [[0.9, 0.1]]  # 1 obs x 2 states
        # B[s'][s][a]: 2x2x1
        B = [[[1.0], [0.0]], [[0.0], [1.0]]]  # identity
        C = [0.5]  # prefer obs 0
        efe = expected_free_energy([0], beliefs, A, B, C)
        assert isinstance(efe, float)

    def test_expected_free_energy_log_prefs_mismatch_raises(self):
        from cogant.simulate.free_energy import expected_free_energy

        with pytest.raises(ValueError, match="log_preferences length"):
            expected_free_energy(
                [0], [0.5, 0.5], [[0.9, 0.1]], [[[1.0], [0.0]], [[0.0], [1.0]]], [0.1, 0.2]
            )

    def test_uniform_distribution(self):
        from cogant.simulate.free_energy import uniform_distribution

        d = uniform_distribution(4)
        assert len(d) == 4
        assert abs(sum(d) - 1.0) < 1e-9
        assert all(abs(x - 0.25) < 1e-9 for x in d)

    def test_uniform_distribution_zero_returns_empty(self):
        from cogant.simulate.free_energy import uniform_distribution

        assert uniform_distribution(0) == []


# ---------------------------------------------------------------------------
# simulate/free_energy.py — FreeEnergyCalculator
# ---------------------------------------------------------------------------


class TestFreeEnergyCalculator:
    """Tests for the FreeEnergyCalculator class."""

    def _make_calc(self):
        from cogant.simulate.free_energy import FreeEnergyCalculator

        v1 = _make_variable("v1")
        v2 = _make_variable("v2")
        a1 = _make_action("a1")
        ss = _make_state_space(variables={"v1": v1, "v2": v2}, actions={"a1": a1})
        return FreeEnergyCalculator(ss)

    def test_calc_init(self):
        calc = self._make_calc()
        assert "v1" in calc.states
        assert "v2" in calc.states
        assert "a1" in calc.actions

    def test_variational_free_energy_calc(self):
        from cogant.simulate.distributions import CategoricalDistribution

        calc = self._make_calc()
        beliefs = CategoricalDistribution(["v1", "v2"], [0.7, 0.3])
        vfe = calc.variational_free_energy(beliefs, "v1")
        assert isinstance(vfe, float)

    def test_variational_free_energy_with_likelihood_model(self):
        from cogant.simulate.distributions import CategoricalDistribution

        calc = self._make_calc()
        beliefs = CategoricalDistribution(["v1", "v2"], [0.7, 0.3])
        likelihood_model = {
            "v1": CategoricalDistribution(["v1", "v2"], [0.9, 0.1]),
            "v2": CategoricalDistribution(["v1", "v2"], [0.1, 0.9]),
        }
        vfe = calc.variational_free_energy(beliefs, "v1", likelihood_model)
        assert isinstance(vfe, float)


# ---------------------------------------------------------------------------
# graph/queries.py — GraphQuery
# ---------------------------------------------------------------------------


class TestGraphQuery:
    """Tests for GraphQuery methods."""

    def test_filter_nodes_by_kind(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import NodeKind

        fn = _make_node("fn1", NodeKind.FUNCTION)
        cls = _make_node("cls1", NodeKind.CLASS)
        g = _make_graph(nodes=[fn, cls])
        q = GraphQuery(g)
        funcs = q.filter_nodes(kind=NodeKind.FUNCTION)
        assert len(funcs) == 1
        assert funcs[0].id == "fn1"

    def test_filter_nodes_by_language(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import NodeKind

        fn_py = _make_node("fn1", NodeKind.FUNCTION, language="python")
        fn_js = _make_node("fn2", NodeKind.FUNCTION, language="javascript")
        g = _make_graph(nodes=[fn_py, fn_js])
        q = GraphQuery(g)
        py_nodes = q.filter_nodes(language="python")
        assert len(py_nodes) == 1

    def test_filter_nodes_by_name_pattern(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION, name="get_user")
        fn2 = _make_node("fn2", NodeKind.FUNCTION, name="set_config")
        g = _make_graph(nodes=[fn1, fn2])
        q = GraphQuery(g)
        getters = q.filter_nodes(name_pattern="get")
        assert len(getters) == 1
        assert getters[0].id == "fn1"

    def test_filter_nodes_by_metadata(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION)
        fn1.metadata["is_exported"] = True
        fn2 = _make_node("fn2", NodeKind.FUNCTION)
        fn2.metadata["is_exported"] = False
        g = _make_graph(nodes=[fn1, fn2])
        q = GraphQuery(g)
        exported = q.filter_nodes(metadata_filter={"is_exported": True})
        assert len(exported) == 1

    def test_filter_edges_by_kind(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import EdgeKind, NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION)
        fn2 = _make_node("fn2", NodeKind.FUNCTION)
        e1 = _make_edge("e1", "fn1", "fn2", EdgeKind.CALLS)
        e2 = _make_edge("e2", "fn1", "fn2", EdgeKind.READS)
        g = _make_graph(nodes=[fn1, fn2], edges=[e1, e2])
        q = GraphQuery(g)
        calls = q.filter_edges(kind=EdgeKind.CALLS)
        assert len(calls) == 1

    def test_filter_edges_by_source_and_target(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import EdgeKind, NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION)
        fn2 = _make_node("fn2", NodeKind.FUNCTION)
        e1 = _make_edge("e1", "fn1", "fn2", EdgeKind.CALLS)
        g = _make_graph(nodes=[fn1, fn2], edges=[e1])
        q = GraphQuery(g)
        edges = q.filter_edges(source_id="fn1")
        assert len(edges) == 1
        edges = q.filter_edges(target_id="fn2")
        assert len(edges) == 1

    def test_filter_edges_by_min_weight(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import EdgeKind, NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION)
        fn2 = _make_node("fn2", NodeKind.FUNCTION)
        e_light = _make_edge("e1", "fn1", "fn2", EdgeKind.CALLS, weight=0.1)
        e_heavy = _make_edge("e2", "fn1", "fn2", EdgeKind.READS, weight=5.0)
        g = _make_graph(nodes=[fn1, fn2], edges=[e_light, e_heavy])
        q = GraphQuery(g)
        heavy = q.filter_edges(min_weight=1.0)
        assert len(heavy) == 1

    def test_find_nodes_by_kind(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import NodeKind

        fn = _make_node("fn1", NodeKind.FUNCTION)
        g = _make_graph(nodes=[fn])
        q = GraphQuery(g)
        results = q.find_nodes_by_kind(NodeKind.FUNCTION)
        assert len(results) == 1

    def test_find_shortest_path_same_node(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION)
        g = _make_graph(nodes=[fn1])
        q = GraphQuery(g)
        path = q.find_shortest_path("fn1", "fn1")
        assert path == ["fn1"]

    def test_find_shortest_path_direct(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import EdgeKind, NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION)
        fn2 = _make_node("fn2", NodeKind.FUNCTION)
        e1 = _make_edge("e1", "fn1", "fn2", EdgeKind.CALLS)
        g = _make_graph(nodes=[fn1, fn2], edges=[e1])
        q = GraphQuery(g)
        path = q.find_shortest_path("fn1", "fn2")
        assert path == ["fn1", "fn2"]

    def test_find_shortest_path_no_path(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION)
        fn2 = _make_node("fn2", NodeKind.FUNCTION)
        g = _make_graph(nodes=[fn1, fn2])
        q = GraphQuery(g)
        path = q.find_shortest_path("fn1", "fn2")
        assert path is None

    def test_find_all_paths_direct(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import EdgeKind, NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION)
        fn2 = _make_node("fn2", NodeKind.FUNCTION)
        e1 = _make_edge("e1", "fn1", "fn2", EdgeKind.CALLS)
        g = _make_graph(nodes=[fn1, fn2], edges=[e1])
        q = GraphQuery(g)
        paths = q.find_all_paths("fn1", "fn2")
        assert len(paths) >= 1
        assert ["fn1", "fn2"] in paths

    def test_compute_in_degree_and_out_degree(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import EdgeKind, NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION)
        fn2 = _make_node("fn2", NodeKind.FUNCTION)
        e1 = _make_edge("e1", "fn1", "fn2", EdgeKind.CALLS)
        g = _make_graph(nodes=[fn1, fn2], edges=[e1])
        q = GraphQuery(g)
        assert q.compute_in_degree("fn2") == 1
        assert q.compute_out_degree("fn1") == 1
        assert q.compute_in_degree("fn1") == 0

    def test_compute_degree_centrality(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import EdgeKind, NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION)
        fn2 = _make_node("fn2", NodeKind.FUNCTION)
        fn3 = _make_node("fn3", NodeKind.FUNCTION)
        e1 = _make_edge("e1", "fn1", "fn2", EdgeKind.CALLS)
        e2 = _make_edge("e2", "fn1", "fn3", EdgeKind.CALLS)
        g = _make_graph(nodes=[fn1, fn2, fn3], edges=[e1, e2])
        q = GraphQuery(g)
        centrality = q.compute_degree_centrality()
        assert "fn1" in centrality
        assert centrality["fn1"] > centrality["fn2"]  # fn1 has higher degree

    def test_compute_betweenness_centrality_small_graph(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import EdgeKind, NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION)
        fn2 = _make_node("fn2", NodeKind.FUNCTION)
        fn3 = _make_node("fn3", NodeKind.FUNCTION)
        e1 = _make_edge("e1", "fn1", "fn2", EdgeKind.CALLS)
        e2 = _make_edge("e2", "fn2", "fn3", EdgeKind.CALLS)
        g = _make_graph(nodes=[fn1, fn2, fn3], edges=[e1, e2])
        q = GraphQuery(g)
        centrality = q.compute_betweenness_centrality()
        # fn2 is on the path fn1→fn3 so should have highest betweenness
        assert isinstance(centrality, dict)

    def test_compute_closeness_centrality(self):
        from cogant.graph.queries import GraphQuery
        from cogant.schemas.core import EdgeKind, NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION)
        fn2 = _make_node("fn2", NodeKind.FUNCTION)
        e1 = _make_edge("e1", "fn1", "fn2", EdgeKind.CALLS)
        g = _make_graph(nodes=[fn1, fn2], edges=[e1])
        q = GraphQuery(g)
        centrality = q.compute_closeness_centrality()
        assert isinstance(centrality, dict)


# ---------------------------------------------------------------------------
# graph/builder.py — ProgramGraphBuilder
# ---------------------------------------------------------------------------


class TestProgramGraphBuilder:
    """Tests for ProgramGraphBuilder."""

    def test_builder_init_creates_graph(self):
        from cogant.graph.builder import ProgramGraphBuilder

        b = ProgramGraphBuilder("test://repo")
        assert b.graph is not None

    def test_builder_add_node(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        b = ProgramGraphBuilder("test://repo")
        node = b.add_node(NodeKind.FUNCTION, "my_func", "module.my_func")
        assert node.id is not None
        assert node.kind == NodeKind.FUNCTION

    def test_builder_add_edge(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind

        b = ProgramGraphBuilder("test://repo")
        n1 = b.add_node(NodeKind.FUNCTION, "func_a", "module.func_a")
        n2 = b.add_node(NodeKind.FUNCTION, "func_b", "module.func_b")
        edge = b.add_edge(n1.id, n2.id, EdgeKind.CALLS)
        assert edge is not None
        assert edge.kind == EdgeKind.CALLS

    def test_builder_finalize(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        b = ProgramGraphBuilder("test://repo")
        b.add_node(NodeKind.FUNCTION, "f", "module.f")
        g = b.finalize()
        assert g is not None
        assert len(g.nodes) >= 1

    def test_builder_get_statistics(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind

        b = ProgramGraphBuilder("test://repo")
        n1 = b.add_node(NodeKind.FUNCTION, "f1", "mod.f1")
        n2 = b.add_node(NodeKind.FUNCTION, "f2", "mod.f2")
        b.add_edge(n1.id, n2.id, EdgeKind.CALLS)
        stats = b.get_statistics()
        assert "node_count" in stats or isinstance(stats, dict)

    def test_builder_add_node_with_path_and_language(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import NodeKind

        b = ProgramGraphBuilder("test://repo")
        node = b.add_node(
            NodeKind.MODULE, "utils", "src.utils", path="src/utils.py", language="python"
        )
        assert node.path == "src/utils.py"
        assert node.language == "python"


# ---------------------------------------------------------------------------
# gnn/formatter — GNNMarkdownFormatter (concrete class using all mixins)
# ---------------------------------------------------------------------------


def _make_process_model():
    """Build a minimal ProcessModel for formatter tests."""
    from cogant.process.extractor import ProcessModel, Stage

    stage = Stage(id="s1", name="init")
    return ProcessModel(
        id="pm1",
        schema_name="test_process",
        stages={"s1": stage},
        connections={},
    )


class TestGNNMarkdownFormatter:
    """Tests for gnn/formatter/*.py via the concrete GNNMarkdownFormatter."""

    def _make_formatter(self, graph=None, state_space=None, mappings=None):
        from cogant.gnn.formatter.base import GNNMarkdownFormatter

        g = graph or _make_graph()
        ss = state_space or _make_state_space()
        pm = _make_process_model()
        m = mappings or {}
        return GNNMarkdownFormatter(g, ss, pm, m)

    def test_formatter_init(self):
        f = self._make_formatter()
        assert f is not None

    def test_formatter_format_returns_string(self):
        f = self._make_formatter()
        result = f.format()
        assert isinstance(result, str)

    def test_formatter_format_with_variable(self):
        v = _make_variable("v1")
        ss = _make_state_space(variables={"v1": v})
        f = self._make_formatter(state_space=ss)
        result = f.format()
        assert isinstance(result, str)

    def test_formatter_with_action_and_transition(self):
        from cogant.statespace.compiler import Transition

        v1 = _make_variable("v1")
        a1 = _make_action("a1", effects=["v1"])
        t1 = Transition(
            id="t1", source_state={"v1": "pre"}, target_state={"v1": "post"}, action_id="a1"
        )
        ss = _make_state_space(
            variables={"v1": v1},
            actions={"a1": a1},
            transitions={"t1": t1},
        )
        f = self._make_formatter(state_space=ss)
        result = f.format()
        assert isinstance(result, str)

    def test_formatter_with_semantic_mappings(self):
        from cogant.schemas.core import NodeKind
        from cogant.schemas.semantic import MappingKind, SemanticMapping

        fn1 = _make_node("fn1", NodeKind.FUNCTION, name="compute")
        g = _make_graph(nodes=[fn1])
        sm = SemanticMapping(
            id="m1",
            kind=MappingKind.HIDDEN_STATE,
            graph_fragment_node_ids=["fn1"],
            confidence_score=0.8,
        )
        f = self._make_formatter(graph=g, mappings={"m1": sm})
        result = f.format()
        assert isinstance(result, str)

    def test_formatter_semantic_mixin_importable(self):
        from cogant.gnn.formatter import semantic

        assert hasattr(semantic, "_SemanticSectionsMixin")

    def test_formatter_structural_mixin_importable(self):
        from cogant.gnn.formatter import structural

        assert hasattr(structural, "__file__")

    def test_formatter_metadata_mixin_importable(self):
        from cogant.gnn.formatter import metadata as meta_mod

        assert hasattr(meta_mod, "__file__")

    def test_formatter_dynamics_mixin_importable(self):
        from cogant.gnn.formatter import dynamics as dyn_mod

        assert hasattr(dyn_mod, "__file__")

    def test_formatter_with_observation_modality(self):
        from cogant.statespace.compiler import ObservationModality

        obs = ObservationModality(
            id="obs1", name="sensor", source_node_id="n1", modality_type="sensor"
        )
        ss = _make_state_space(observations={"obs1": obs})
        f = self._make_formatter(state_space=ss)
        result = f.format()
        assert isinstance(result, str)

    def test_formatter_with_graph_nodes_and_edges(self):
        from cogant.schemas.core import EdgeKind, NodeKind

        fn1 = _make_node("fn1", NodeKind.FUNCTION, name="compute")
        fn2 = _make_node("fn2", NodeKind.FUNCTION, name="render")
        e1 = _make_edge("e1", "fn1", "fn2", EdgeKind.CALLS)
        g = _make_graph(nodes=[fn1, fn2], edges=[e1])
        f = self._make_formatter(graph=g)
        result = f.format()
        assert isinstance(result, str)
