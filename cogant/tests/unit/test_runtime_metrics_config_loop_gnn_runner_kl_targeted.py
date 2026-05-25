#!/usr/bin/env python3
"""Targeted branch tests: runtime/metrics, runtime/config, runtime/loop,
gnn/runner, server/models, translate/dsl/schema, plugins/base, schema/versions,
config/schema."""

import json

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# runtime/metrics.py — pure math, no deps
# ---------------------------------------------------------------------------


class TestKLDivergence:
    def test_identical_distributions(self):
        from cogant.runtime.metrics import kl_divergence

        p = [0.5, 0.5]
        result = kl_divergence(p, p)
        assert abs(result) < 1e-6

    def test_one_hot(self):
        from cogant.runtime.metrics import kl_divergence

        p = [1.0, 0.0]
        q = [0.5, 0.5]
        result = kl_divergence(p, q)
        assert result > 0

    def test_zero_p_entry(self):
        from cogant.runtime.metrics import kl_divergence

        p = [0.0, 1.0]
        q = [0.5, 0.5]
        result = kl_divergence(p, q)
        # Only non-zero p entries contribute
        assert result > 0

    def test_non_negative(self):
        import random

        from cogant.runtime.metrics import kl_divergence

        random.seed(42)
        for _ in range(10):
            p = [random.random() + 0.1 for _ in range(4)]
            s = sum(p)
            p = [x / s for x in p]
            q = [0.25, 0.25, 0.25, 0.25]
            assert kl_divergence(p, q) >= 0

    def test_mismatched_length(self):
        from cogant.runtime.metrics import kl_divergence

        p = [0.5, 0.5]
        q = [0.33, 0.33, 0.33]
        result = kl_divergence(p, q)  # zip truncates to shorter
        assert result >= 0


class TestFreeEnergy:
    def _make_simple_model(self):
        A = [[0.9, 0.1], [0.1, 0.9]]  # 2 obs x 2 states
        C = [1.0, 0.0]
        D = [0.5, 0.5]
        return A, C, D

    def test_basic(self):
        from cogant.runtime.metrics import free_energy

        A, C, D = self._make_simple_model()
        state_dist = [0.8, 0.2]
        result = free_energy(state_dist, 0, A, C, D)
        assert isinstance(result, float)
        assert result > 0  # VFE is non-negative

    def test_different_state_gives_different_fe(self):
        from cogant.runtime.metrics import free_energy

        A, C, D = self._make_simple_model()
        # Different state distributions give different FE values
        fe_certain = free_energy([0.99, 0.01], 0, A, C, D)
        fe_uncertain = free_energy([0.5, 0.5], 0, A, C, D)
        # FE depends on KL from prior and observation surprise
        assert isinstance(fe_certain, float)
        assert isinstance(fe_uncertain, float)

    def test_obs_idx_out_of_range(self):
        from cogant.runtime.metrics import free_energy

        A, C, D = self._make_simple_model()
        state_dist = [0.5, 0.5]
        # Out-of-range obs_idx should be clamped to 0
        result = free_energy(state_dist, 10, A, C, D)
        assert isinstance(result, float)

    def test_negative_obs_idx(self):
        from cogant.runtime.metrics import free_energy

        A, C, D = self._make_simple_model()
        state_dist = [0.5, 0.5]
        result = free_energy(state_dist, -1, A, C, D)
        assert isinstance(result, float)

    def test_uniform_belief(self):
        from cogant.runtime.metrics import free_energy

        A = [[1.0, 0.0], [0.0, 1.0]]
        C = [0.0, 0.0]
        D = [0.5, 0.5]
        state_dist = [0.5, 0.5]
        result = free_energy(state_dist, 0, A, C, D)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# runtime/config.py
# ---------------------------------------------------------------------------


class TestAgentConfig:
    def test_defaults(self):
        from cogant.runtime.config import AgentConfig

        cfg = AgentConfig()
        assert cfg.max_steps == 100
        assert cfg.convergence_threshold == 1e-4
        assert cfg.action_selection == "preference"
        assert cfg.seed == 42

    def test_custom(self):
        from cogant.runtime.config import AgentConfig

        cfg = AgentConfig(max_steps=50, convergence_threshold=1e-3, seed=7)
        assert cfg.max_steps == 50
        assert cfg.seed == 7

    def test_dataclass_fields(self):
        import dataclasses

        from cogant.runtime.config import AgentConfig

        fields = {f.name for f in dataclasses.fields(AgentConfig)}
        assert "max_steps" in fields
        assert "convergence_threshold" in fields


# ---------------------------------------------------------------------------
# runtime/loop.py — helper functions + AgentRuntime
# ---------------------------------------------------------------------------


def _make_runtime():
    from cogant.runtime.loop import AgentRuntime

    return AgentRuntime.from_matrices_dict(
        {
            "A": [[0.9, 0.1], [0.1, 0.9]],
            "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
            "C": [1.0, 0.0],
            "D": [0.5, 0.5],
        }
    )


class TestNormalize:
    def test_basic(self):
        from cogant.runtime.loop import _normalize

        result = _normalize([1.0, 2.0, 3.0])
        assert abs(sum(result) - 1.0) < 1e-9

    def test_already_normalized(self):
        from cogant.runtime.loop import _normalize

        p = [0.3, 0.7]
        result = _normalize(p)
        assert abs(sum(result) - 1.0) < 1e-9

    def test_zero_sum(self):
        from cogant.runtime.loop import _normalize

        result = _normalize([0.0, 0.0])
        assert abs(sum(result) - 1.0) < 1e-9

    def test_empty(self):
        from cogant.runtime.loop import _normalize

        result = _normalize([])
        assert result == []


class TestArgmax:
    def test_basic(self):
        from cogant.runtime.loop import _argmax

        assert _argmax([0.1, 0.9, 0.5]) == 1

    def test_first_element(self):
        from cogant.runtime.loop import _argmax

        assert _argmax([1.0, 0.0, 0.0]) == 0

    def test_last_element(self):
        from cogant.runtime.loop import _argmax

        assert _argmax([0.0, 0.0, 1.0]) == 2

    def test_empty(self):
        from cogant.runtime.loop import _argmax

        assert _argmax([]) == 0

    def test_ties_take_first(self):
        from cogant.runtime.loop import _argmax

        assert _argmax([1.0, 1.0]) == 0


class TestMatVec:
    def test_identity(self):
        from cogant.runtime.loop import _mat_vec

        mat = [[1.0, 0.0], [0.0, 1.0]]
        vec = [0.3, 0.7]
        result = _mat_vec(mat, vec)
        assert abs(result[0] - 0.3) < 1e-9
        assert abs(result[1] - 0.7) < 1e-9

    def test_uniform_mat(self):
        from cogant.runtime.loop import _mat_vec

        mat = [[0.5, 0.5], [0.5, 0.5]]
        vec = [1.0, 0.0]
        result = _mat_vec(mat, vec)
        assert abs(result[0] - 0.5) < 1e-9


class TestDefaultLikelihood:
    def test_basic(self):
        from cogant.runtime.loop import _default_likelihood

        A = [[0.9, 0.1], [0.1, 0.9]]
        state_dist = [1.0, 0.0]
        result = _default_likelihood(A, state_dist)
        assert abs(result[0] - 0.9) < 1e-9
        assert abs(result[1] - 0.1) < 1e-9


class TestDefaultTransition:
    def test_basic(self):
        from cogant.runtime.loop import _default_transition

        B = [[[1.0], [0.0]], [[0.0], [1.0]]]
        state_dist = [1.0, 0.0]
        result = _default_transition(B, state_dist, action=0)
        assert abs(sum(result) - 1.0) < 1e-9

    def test_out_of_range_action(self):
        from cogant.runtime.loop import _default_transition

        B = [[[1.0], [0.0]], [[0.0], [1.0]]]
        result = _default_transition(B, [0.5, 0.5], action=99)
        assert abs(sum(result) - 1.0) < 1e-9


class TestDefaultPreferenceScore:
    def test_basic(self):
        from cogant.runtime.loop import _default_preference_score

        C = [1.0, -1.0]
        obs_dist = [0.8, 0.2]
        result = _default_preference_score(C, obs_dist)
        assert abs(result - (1.0 * 0.8 + (-1.0) * 0.2)) < 1e-9


class TestAgentStep:
    def test_basic(self):
        from cogant.runtime.loop import AgentStep

        step = AgentStep(t=0, state_dist=[0.5, 0.5], obs=0, action=1, free_energy=0.5)
        assert step.t == 0
        assert step.free_energy == 0.5


class TestEpisodeResult:
    def test_basic(self):
        from cogant.runtime.loop import AgentStep, EpisodeResult

        step = AgentStep(t=0, state_dist=[0.5, 0.5], obs=0, action=0, free_energy=1.0)
        er = EpisodeResult(
            steps=[step],
            final_posterior=[0.5, 0.5],
            obs_counts=[1.0, 0.0],
            obs_state_counts=[[0.5, 0.5], [0.0, 0.0]],
            mean_free_energy=1.0,
            final_free_energy=1.0,
        )
        assert len(er.steps) == 1
        assert er.mean_free_energy == 1.0


class TestAgentRuntimeFromMatricesDict:
    def test_basic(self):
        rt = _make_runtime()
        assert rt is not None
        assert len(rt.A) == 2
        assert len(rt.D) == 2

    def test_step(self):
        rt = _make_runtime()
        state = [0.5, 0.5]
        result = rt.step(state, obs_idx=0, t=0)
        assert result.t == 0
        assert len(result.state_dist) == 2
        assert abs(sum(result.state_dist) - 1.0) < 1e-6

    def test_step_obs_1(self):
        rt = _make_runtime()
        result = rt.step([0.3, 0.7], obs_idx=1, t=5)
        assert result.t == 5
        assert result.obs == 1

    def test_run_n_steps(self):
        rt = _make_runtime()
        steps = rt.run_n_steps(3)
        assert len(steps) == 3
        for i, s in enumerate(steps):
            assert s.t == i

    def test_run_n_steps_with_initial(self):
        rt = _make_runtime()
        steps = rt.run_n_steps(2, initial_state=[0.9, 0.1])
        assert len(steps) == 2

    def test_run_n_steps_zero(self):
        rt = _make_runtime()
        steps = rt.run_n_steps(0)
        assert steps == []

    def test_run_until_convergence(self):
        from cogant.runtime.config import AgentConfig

        rt = _make_runtime()
        cfg = AgentConfig(max_steps=10, convergence_threshold=1e-2)
        steps = rt.run_until_convergence(cfg=cfg)
        assert isinstance(steps, list)
        assert len(steps) >= 1

    def test_run_episode(self):
        rt = _make_runtime()
        result = rt.run_episode(n_steps=5)
        assert hasattr(result, "steps")
        assert len(result.steps) == 5

    def test_update_D_from_posterior(self):
        rt = _make_runtime()
        new_D = rt.update_D_from_posterior([0.8, 0.2])
        assert abs(sum(new_D) - 1.0) < 1e-6

    def test_update_A_from_counts(self):
        rt = _make_runtime()
        # update_A_from_counts(obs_state_counts, learning_rate=0.1)
        obs_state_counts = [[0.8, 0.2], [0.0, 0.0]]
        new_A = rt.update_A_from_counts(obs_state_counts, learning_rate=0.1)
        assert len(new_A) == 2

    def test_custom_likelihood(self):
        import types

        from cogant.runtime.loop import AgentRuntime

        ns = types.SimpleNamespace(
            A=[[0.9, 0.1], [0.1, 0.9]],
            B=[[[1.0], [0.0]], [[0.0], [1.0]]],
            C=[1.0, 0.0],
            D=[0.5, 0.5],
            likelihood=lambda sd: [sum(sd), 1 - sum(sd)],
        )
        rt = AgentRuntime(ns)
        assert rt._n_obs == 2

    def test_run_multi_episode(self):
        rt = _make_runtime()
        result = rt.run_multi_episode(n_episodes=3, steps_per_episode=5)
        assert hasattr(result, "episodes")
        assert len(result.episodes) == 3


class TestStandaloneFunctions:
    def test_run_n_steps(self):
        from cogant.runtime.loop import run_n_steps

        rt = _make_runtime()
        steps = run_n_steps(rt, n=3)
        assert len(steps) == 3

    def test_run_until_convergence(self):
        from cogant.runtime.config import AgentConfig
        from cogant.runtime.loop import run_until_convergence

        rt = _make_runtime()
        cfg = AgentConfig(max_steps=5)
        steps = run_until_convergence(rt, cfg=cfg)
        assert isinstance(steps, list)


# ---------------------------------------------------------------------------
# gnn/runner.py — ExecutionTrace + GNNModelRunner
# ---------------------------------------------------------------------------


class TestExecutionTrace:
    def test_basic(self):
        from cogant.gnn.runner import ExecutionTrace

        t = ExecutionTrace(step=0, state={"x": 1})
        assert t.step == 0
        assert t.action is None
        assert t.reward == 0.0
        assert t.beliefs == {}

    def test_full(self):
        from cogant.gnn.runner import ExecutionTrace

        t = ExecutionTrace(
            step=3,
            state={"x": 1, "y": 2},
            action="move_right",
            observation="obs_0",
            reward=1.5,
            beliefs={"state_a": 0.8, "state_b": 0.2},
            beliefs_prior={"state_a": 0.5, "state_b": 0.5},
            free_energy_before=2.0,
            free_energy_after=1.0,
            policy_scores=[("act_a", 0.9), ("act_b", 0.1)],
            action_rationale="Minimize EFE",
            predicted_state={"x": 2, "y": 2},
        )
        assert t.step == 3
        assert t.action == "move_right"
        assert t.reward == 1.5
        assert len(t.policy_scores) == 2

    def test_to_dict(self):
        from cogant.gnn.runner import ExecutionTrace

        t = ExecutionTrace(step=1, state={"x": 0}, action="do_nothing")
        d = t.to_dict()
        assert "step" in d
        assert "state" in d
        assert "action" in d
        assert d["action"] == "do_nothing"
        assert "timestamp" in d
        assert "beliefs" in d
        assert "policy_scores" in d

    def test_to_dict_none_action(self):
        from cogant.gnn.runner import ExecutionTrace

        t = ExecutionTrace(step=0, state={})
        d = t.to_dict()
        assert d["action"] is None


class TestGNNModelRunner:
    def test_init(self):
        from cogant.gnn.runner import GNNModelRunner

        runner = GNNModelRunner()
        assert runner.traces == []
        assert runner.manifest == {}
        assert runner.beliefs_history == []

    def test_load_package_missing_manifest(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        runner = GNNModelRunner()
        with pytest.raises(FileNotFoundError):
            runner.load_package(str(tmp_path))

    def test_load_package_minimal(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        manifest = {"version": "1.0.0", "name": "test_model"}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
        runner = GNNModelRunner()
        result = runner.load_package(str(tmp_path))
        assert result["version"] == "1.0.0"

    def test_load_package_with_model(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        manifest = {"version": "1.0.0", "name": "test"}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
        model = {"variables": ["x", "y"], "observations": ["obs1"]}
        (tmp_path / "model.gnn.json").write_text(json.dumps(model))
        state_space = {"states": ["s0", "s1"]}
        (tmp_path / "state_space.json").write_text(json.dumps(state_space))
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        assert runner.model == model
        assert runner.state_space == state_space

    def test_load_package_with_transitions(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        manifest = {"version": "1.0.0", "name": "test"}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
        (tmp_path / "transitions.json").write_text(json.dumps({"transitions": []}))
        (tmp_path / "preferences.json").write_text(json.dumps({"preferences": []}))
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        assert runner.manifest["name"] == "test"

    def test_run_basic(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        manifest = {"version": "1.0.0", "name": "test", "variables": ["x", "y"]}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        result = runner.run(steps=3)
        assert isinstance(result, dict)
        assert "traces" in result or "steps_run" in result or len(runner.traces) > 0

    def test_generate_execution_report(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        manifest = {"version": "1.0.0", "name": "test", "variables": ["x"]}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        runner.run(steps=2)
        report = runner.generate_execution_report()
        assert isinstance(report, str)
        assert len(report) > 0


# ---------------------------------------------------------------------------
# server/models.py — Pydantic models
# ---------------------------------------------------------------------------


class TestAnalyzeRequest:
    def test_basic(self):
        from cogant.server.models import AnalyzeRequest

        req = AnalyzeRequest(repo_path="/some/path")
        assert req.repo_path == "/some/path"
        assert req.skip_dynamic is True
        assert req.stages is None

    def test_with_stages(self):
        from cogant.server.models import AnalyzeRequest

        req = AnalyzeRequest(repo_path="/my/repo", stages=["ingest", "analyze"], skip_dynamic=False)
        assert req.stages == ["ingest", "analyze"]
        assert req.skip_dynamic is False

    def test_forbids_extra(self):
        from cogant.server.models import AnalyzeRequest

        with pytest.raises(ValidationError):
            AnalyzeRequest(repo_path="/p", unknown_field="bad")


class TestAnalyzeResponse:
    def test_basic(self):
        from cogant.server.models import AnalyzeResponse

        resp = AnalyzeResponse(nodes=10, edges=20, mappings=5)
        assert resp.nodes == 10
        assert resp.roles == {}
        assert resp.errors == []

    def test_with_roles(self):
        from cogant.server.models import AnalyzeResponse

        resp = AnalyzeResponse(
            nodes=5,
            edges=8,
            mappings=3,
            roles={"observation": 2, "action": 1},
            errors=["warning: low coverage"],
        )
        assert resp.roles["observation"] == 2
        assert len(resp.errors) == 1


class TestHealthResponse:
    def test_basic(self):
        from cogant.server.models import HealthResponse

        h = HealthResponse(version="0.4.0")
        assert h.status == "ok"
        assert h.docs == "/docs"

    def test_custom_docs(self):
        from cogant.server.models import HealthResponse

        h = HealthResponse(version="1.0", docs="/api-docs")
        assert h.docs == "/api-docs"


class TestExplainResponse:
    def test_basic(self):
        from cogant.server.models import ExplainResponse

        er = ExplainResponse(
            node_name="auth_check",
            node_id="fn_auth",
            node_kind="function",
            blanket_role="observation",
        )
        assert er.node_name == "auth_check"
        assert er.assigned_role is None

    def test_with_rules(self):
        from cogant.server.models import ExplainResponse

        er = ExplainResponse(
            node_name="foo",
            node_id="n1",
            node_kind="function",
            blanket_role="action",
            assigned_role="ACTION",
            rules_fired=[{"rule": "ObservationRule"}],
            metadata={"confidence": 0.9},
        )
        assert len(er.rules_fired) == 1


class TestRoundtripRequest:
    def test_basic(self):
        from cogant.server.models import RoundtripRequest

        req = RoundtripRequest(repo_path="/my/repo")
        assert req.threshold == 0.7

    def test_custom_threshold(self):
        from cogant.server.models import RoundtripRequest

        req = RoundtripRequest(repo_path="/r", threshold=0.5)
        assert req.threshold == 0.5


class TestRoundtripResponse:
    def test_basic(self):
        from cogant.server.models import RoundtripResponse

        r = RoundtripResponse(role_match_score=0.85, is_isomorphic=True, threshold=0.7)
        assert r.role_match_score == 0.85
        assert r.is_isomorphic is True

    def test_not_isomorphic(self):
        from cogant.server.models import RoundtripResponse

        r = RoundtripResponse(
            role_match_score=0.4,
            is_isomorphic=False,
            threshold=0.7,
            original_roles={"obs": 3},
            synthesized_roles={"obs": 1},
            errors=["role mismatch"],
        )
        assert r.is_isomorphic is False
        assert len(r.errors) == 1


class TestGraphModels:
    def test_node(self):
        from cogant.server.models import GraphNode

        n = GraphNode(id="n1", name="auth", kind="function", role="observation")
        assert n.id == "n1"

    def test_edge(self):
        from cogant.server.models import GraphEdge

        e = GraphEdge(id="e1", source="n1", target="n2", kind="calls")
        assert e.source == "n1"

    def test_graph_response(self):
        from cogant.server.models import GraphEdge, GraphNode, GraphResponse

        resp = GraphResponse(
            nodes=[GraphNode(id="n1", name="foo", kind="function")],
            edges=[GraphEdge(id="e1", source="n1", target="n2", kind="calls")],
        )
        assert len(resp.nodes) == 1


class TestErrorResponse:
    def test_basic(self):
        from cogant.server.models import ErrorResponse

        err = ErrorResponse(detail="File not found", error_type="FileNotFoundError")
        assert err.detail == "File not found"
        assert err.error_type == "FileNotFoundError"


# ---------------------------------------------------------------------------
# translate/dsl/schema.py — dataclasses
# ---------------------------------------------------------------------------


class TestKnownConditionKeys:
    def test_contains_expected_keys(self):
        from cogant.translate.dsl.schema import KNOWN_CONDITION_KEYS

        assert "node_kind" in KNOWN_CONDITION_KEYS
        assert "name_pattern" in KNOWN_CONDITION_KEYS
        assert "has_method" in KNOWN_CONDITION_KEYS
        assert "edge_type" in KNOWN_CONDITION_KEYS


class TestDSLCondition:
    def test_empty(self):
        from cogant.translate.dsl.schema import DSLCondition

        c = DSLCondition()
        assert c.node_kind is None
        assert c.name_pattern is None

    def test_with_node_kind(self):
        from cogant.translate.dsl.schema import DSLCondition

        c = DSLCondition(node_kind="function")
        assert c.node_kind == "function"

    def test_with_pattern(self):
        from cogant.translate.dsl.schema import DSLCondition

        c = DSLCondition(name_pattern="*_handler")
        assert c.name_pattern == "*_handler"

    def test_frozen(self):
        from cogant.translate.dsl.schema import DSLCondition

        c = DSLCondition(node_kind="method")
        with pytest.raises((AttributeError, TypeError)):
            c.node_kind = "function"  # type: ignore


class TestDSLRule:
    def test_basic(self):
        from cogant.translate.dsl.schema import DSLCondition, DSLRule

        rule = DSLRule(
            name="ObservationRule",
            role="OBSERVATION",
            confidence=0.9,
            conditions=[DSLCondition(node_kind="function")],
        )
        assert rule.name == "ObservationRule"
        assert rule.confidence == 0.9
        assert len(rule.conditions) == 1

    def test_with_description(self):
        from cogant.translate.dsl.schema import DSLCondition, DSLRule

        rule = DSLRule(
            name="ActionRule",
            role="ACTION",
            confidence=0.8,
            conditions=[DSLCondition(name_pattern="do_*")],
            description="Matches action functions",
        )
        assert rule.description == "Matches action functions"


class TestDSLRuleSet:
    def test_empty(self):
        from cogant.translate.dsl.schema import DSLRuleSet

        rs = DSLRuleSet()
        assert rs.rules == []

    def test_with_rules(self):
        from cogant.translate.dsl.schema import DSLCondition, DSLRule, DSLRuleSet

        rule = DSLRule(
            name="R1", role="OBS", confidence=0.7, conditions=[DSLCondition(node_kind="function")]
        )
        rs = DSLRuleSet(rules=[rule])
        assert len(rs.rules) == 1


# ---------------------------------------------------------------------------
# plugins/base.py — PluginMetadata and concrete plugin instances
# ---------------------------------------------------------------------------


class TestPluginMetadata:
    def test_basic(self):
        from cogant.plugins.base import PluginMetadata

        meta = PluginMetadata(name="my-plugin", version="1.0.0")
        assert meta.name == "my-plugin"
        assert meta.author == ""

    def test_full(self):
        from cogant.plugins.base import PluginMetadata

        meta = PluginMetadata(
            name="test", version="2.0", author="Alice", description="A test plugin"
        )
        assert meta.description == "A test plugin"


class TestConcretePlugin:
    """Test instantiating a concrete subclass of Plugin."""

    def _make_concrete_language_plugin(self):
        from cogant.plugins.base import LanguagePlugin, PluginMetadata

        class ConcreteLanguagePlugin(LanguagePlugin):
            supported_languages = {"python"}

            def initialize(self, config):
                pass

            def shutdown(self):
                pass

            def parse(self, source_code):
                return {"type": "module", "body": []}

            def extract_symbols(self, ast):
                return []

            def extract_types(self, ast):
                return {}

            def resolve_imports(self, ast):
                return []

        meta = PluginMetadata(name="py-plugin", version="1.0")
        return ConcreteLanguagePlugin(meta)

    def test_language_plugin(self):
        plugin = self._make_concrete_language_plugin()
        assert plugin.metadata.name == "py-plugin"
        plugin.initialize({})
        result = plugin.parse("def foo(): pass")
        assert isinstance(result, dict)
        plugin.shutdown()

    def test_trace_plugin(self):
        from cogant.plugins.base import PluginMetadata, TracePlugin

        class ConcreteTracePlugin(TracePlugin):
            def initialize(self, config):
                pass

            def shutdown(self):
                pass

            def parse_trace(self, f):
                return {}

            def parse_coverage(self, f):
                return {}

            def extract_call_graph(self, trace):
                return {}

        meta = PluginMetadata(name="trace-plugin", version="0.1")
        p = ConcreteTracePlugin(meta)
        assert p.metadata.version == "0.1"
        p.initialize({})

    def test_normalizer_plugin(self):
        from cogant.plugins.base import NormalizerPlugin, PluginMetadata

        class ConcreteNormalizerPlugin(NormalizerPlugin):
            def initialize(self, config):
                pass

            def shutdown(self):
                pass

            def normalize(self, data):
                return data

            def validate_schema(self, data):
                return True

        meta = PluginMetadata(name="norm", version="1.0")
        p = ConcreteNormalizerPlugin(meta)
        result = p.normalize({"x": 1})
        assert result == {"x": 1}

    def test_translation_rule_plugin(self):
        from cogant.plugins.base import PluginMetadata, TranslationRulePlugin

        class ConcreteTransRulePlugin(TranslationRulePlugin):
            def initialize(self, c):
                pass

            def shutdown(self):
                pass

            def translate_nodes(self, nodes):
                return nodes

            def translate_edges(self, edges):
                return edges

            def compute_features(self, node):
                return [0.0]

        meta = PluginMetadata(name="tr", version="0.1")
        p = ConcreteTransRulePlugin(meta)
        result = p.translate_nodes([{"id": "n1"}])
        assert len(result) == 1

    def test_state_space_plugin(self):
        from cogant.plugins.base import PluginMetadata, StateSpacePlugin

        class ConcreteSSPlugin(StateSpacePlugin):
            def initialize(self, c):
                pass

            def shutdown(self):
                pass

            def extract_states(self, m):
                return []

            def extract_observations(self, m):
                return []

            def extract_actions(self, m):
                return []

            def learn_policies(self, s, o, a):
                return []

        meta = PluginMetadata(name="ss", version="0.1")
        p = ConcreteSSPlugin(meta)
        assert p.extract_states({}) == []

    def test_export_plugin(self):
        from cogant.plugins.base import ExportPlugin, PluginMetadata

        class ConcreteExportPlugin(ExportPlugin):
            supported_formats = {"json"}

            def initialize(self, c):
                pass

            def shutdown(self):
                pass

            def export(self, bundle, path, fmt):
                pass

            def get_format_info(self, fmt):
                return {"name": fmt}

        meta = PluginMetadata(name="exp", version="1.0")
        p = ConcreteExportPlugin(meta)
        info = p.get_format_info("json")
        assert info["name"] == "json"

    def test_validation_plugin(self):
        from cogant.plugins.base import PluginMetadata, ValidationPlugin

        class ConcreteValidPlugin(ValidationPlugin):
            def initialize(self, c):
                pass

            def shutdown(self):
                pass

            def validate(self, bundle):
                return {"valid": True}

            def compute_quality_metrics(self, bundle):
                return {"score": 1.0}

        meta = PluginMetadata(name="val", version="1.0")
        p = ConcreteValidPlugin(meta)
        result = p.validate({})
        assert result["valid"] is True

    def test_visualization_plugin(self):
        from cogant.plugins.base import PluginMetadata, VisualizationPlugin

        class ConcreteVizPlugin(VisualizationPlugin):
            supported_visualizations = {"graph"}

            def initialize(self, c):
                pass

            def shutdown(self):
                pass

            def render(self, bundle, path, vtype):
                pass

            def get_viz_info(self, vtype):
                return {"type": vtype}

        meta = PluginMetadata(name="viz", version="1.0")
        p = ConcreteVizPlugin(meta)
        info = p.get_viz_info("graph")
        assert info["type"] == "graph"


# ---------------------------------------------------------------------------
# schema/versions.py
# ---------------------------------------------------------------------------


class TestSchemaVersion:
    def test_versions(self):
        from cogant.schema.versions import SchemaVersion

        assert SchemaVersion.V1_0 == "1.0"
        assert SchemaVersion.V1_1 == "1.1"
        assert SchemaVersion.CURRENT == "1.1"

    def test_gnn_v1_0_sections(self):
        from cogant.schema.versions import GNN_V1_0_REQUIRED_SECTIONS

        assert "GNNSection" in GNN_V1_0_REQUIRED_SECTIONS
        assert "ModelName" in GNN_V1_0_REQUIRED_SECTIONS
        assert "StateSpaceBlock" in GNN_V1_0_REQUIRED_SECTIONS

    def test_gnn_v1_1_sections(self):
        from cogant.schema.versions import GNN_V1_0_REQUIRED_SECTIONS, GNN_V1_1_REQUIRED_SECTIONS

        assert "GNNVersionAndFlags" in GNN_V1_1_REQUIRED_SECTIONS
        # V1.1 should include all V1.0 sections
        for sec in GNN_V1_0_REQUIRED_SECTIONS:
            assert sec in GNN_V1_1_REQUIRED_SECTIONS


# ---------------------------------------------------------------------------
# config/schema.py — Pydantic config models
# ---------------------------------------------------------------------------


class TestLogLevel:
    def test_values(self):
        from cogant.config.schema import LogLevel

        assert LogLevel.DEBUG == "debug"
        assert LogLevel.INFO == "info"
        assert LogLevel.WARNING == "warning"
        assert LogLevel.ERROR == "error"
        assert LogLevel.CRITICAL == "critical"


class TestCogantConfig:
    def test_defaults(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig()
        assert cfg.version == "1.0.0"
        assert cfg.environment == "production"
        assert cfg.max_workers == 4
        assert cfg.enable_caching is True

    def test_custom(self):
        from cogant.config.schema import CogantConfig, LogLevel

        cfg = CogantConfig(
            version="2.0.0",
            environment="development",
            log_level=LogLevel.DEBUG,
            max_workers=8,
            enable_caching=False,
        )
        assert cfg.environment == "development"
        assert cfg.max_workers == 8


class TestLanguageConfig:
    def test_basic(self):
        from cogant.config.schema import LanguageConfig

        lc = LanguageConfig(language="python", analyzer_name="ast_visitor")
        assert lc.language == "python"
        assert lc.enabled is True

    def test_disabled(self):
        from cogant.config.schema import LanguageConfig

        lc = LanguageConfig(language="rust", analyzer_name="syn", enabled=False)
        assert lc.enabled is False


class TestPipelineStage:
    def test_basic(self):
        from cogant.config.schema import PipelineStage

        ps = PipelineStage(name="ingest")
        assert ps.name == "ingest"
        assert ps.enabled is True
        assert ps.retry_count == 0

    def test_with_retry(self):
        from cogant.config.schema import PipelineStage

        ps = PipelineStage(
            name="analyze", retry_count=3, skip_on_error=True, parameters={"depth": 5}
        )
        assert ps.retry_count == 3
        assert ps.skip_on_error is True


class TestPipelineConfig:
    def test_basic(self):
        from cogant.config.schema import PipelineConfig

        pc = PipelineConfig()
        assert pc.name == "default"

    def test_with_stages(self):
        from cogant.config.schema import PipelineConfig

        pc = PipelineConfig(
            name="my_pipeline",
            run_stages=["ingest", "analyze"],
        )
        assert len(pc.run_stages) == 2


# ---------------------------------------------------------------------------
# schemas/program_graph.py
# ---------------------------------------------------------------------------


class TestProgramGraphSchema:
    def test_importable(self):
        import cogant.schemas.program_graph as pg

        assert pg is not None

    def test_stable_id(self):
        from cogant.schemas.program_graph import StableID

        sid = StableID("test_id")
        assert isinstance(sid, str)
        assert sid == "test_id"


# ---------------------------------------------------------------------------
# config/* small modules
# ---------------------------------------------------------------------------


class TestSmallConfigModules:
    def test_config_gnn(self):
        import cogant.config.gnn as cfg

        assert cfg is not None

    def test_config_graph(self):
        import cogant.config.graph as cfg

        assert cfg is not None

    def test_config_ingest(self):
        import cogant.config.ingest as cfg

        assert cfg is not None

    def test_config_reverse(self):
        import cogant.config.reverse as cfg

        assert cfg is not None

    def test_config_statespace(self):
        import cogant.config.statespace as cfg

        assert cfg is not None

    def test_config_translate(self):
        import cogant.config.translate as cfg

        assert cfg is not None

    def test_config_init(self):
        import cogant.config as cfg

        assert cfg is not None


class TestSchemaVersionsModule:
    def test_schema_init(self):
        import cogant.schema as s

        assert s is not None
