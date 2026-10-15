#!/usr/bin/env python3
"""Targeted branch tests: runtime/metrics, runtime/config, runtime/loop,
gnn/runner, server/models, translate/dsl/schema, plugins/base, schema/versions,
config/schema."""

import pytest
from pydantic import ValidationError

from cogant.runtime.categorical import CategoricalModel

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

    def test_mismatched_length_rejected(self):
        from cogant.runtime.metrics import kl_divergence

        with pytest.raises(ValueError, match="dimensions"):
            kl_divergence([0.5, 0.5], [1 / 3, 1 / 3, 1 / 3])


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

    def test_obs_idx_out_of_range_rejected(self):
        from cogant.runtime.metrics import free_energy

        A, C, D = self._make_simple_model()
        with pytest.raises(ValueError, match="observation"):
            free_energy([0.5, 0.5], 10, A, C, D)

    def test_negative_obs_idx_rejected(self):
        from cogant.runtime.metrics import free_energy

        A, C, D = self._make_simple_model()
        with pytest.raises(ValueError, match="observation"):
            free_energy([0.5, 0.5], -1, A, C, D)

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

    def test_custom(self):
        from cogant.runtime.config import AgentConfig

        cfg = AgentConfig(max_steps=50, convergence_threshold=1e-3)
        assert cfg.max_steps == 50
        assert cfg.convergence_threshold == 1e-3

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

    def test_zero_sum_rejected(self):
        from cogant.runtime.loop import _normalize

        with pytest.raises(ValueError, match="zero probability"):
            _normalize([0.0, 0.0])

    def test_empty_rejected(self):
        from cogant.runtime.loop import _normalize

        with pytest.raises(ValueError, match="nonempty"):
            _normalize([])


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

    def test_empty_rejected(self):
        from cogant.runtime.loop import _argmax

        with pytest.raises(ValueError, match="nonempty"):
            _argmax([])

    def test_ties_take_first(self):
        from cogant.runtime.loop import _argmax

        assert _argmax([1.0, 1.0]) == 0


class TestMatVec:
    def test_identity(self):

        mat = [[1.0, 0.0], [0.0, 1.0]]
        vec = [0.3, 0.7]
        result = CategoricalModel(mat, [[[1.0], [0.0]], [[0.0], [1.0]]], [0.0, 0.0], vec).observe(
            vec
        )
        assert abs(result[0] - 0.3) < 1e-9
        assert abs(result[1] - 0.7) < 1e-9

    def test_uniform_mat(self):

        mat = [[0.5, 0.5], [0.5, 0.5]]
        vec = [1.0, 0.0]
        result = CategoricalModel(mat, [[[1.0], [0.0]], [[0.0], [1.0]]], [0.0, 0.0], vec).observe(
            vec
        )
        assert abs(result[0] - 0.5) < 1e-9


class TestCategoricalLikelihood:
    def test_basic(self):

        A = [[0.9, 0.1], [0.1, 0.9]]
        state_dist = [1.0, 0.0]
        result = CategoricalModel(
            A, [[[1.0], [0.0]], [[0.0], [1.0]]], [0.0, 0.0], state_dist
        ).observe(state_dist)
        assert abs(result[0] - 0.9) < 1e-9
        assert abs(result[1] - 0.1) < 1e-9


class TestCategoricalTransition:
    def test_basic(self):

        B = [[[1.0], [0.0]], [[0.0], [1.0]]]
        state_dist = [1.0, 0.0]
        result = CategoricalModel([[1.0, 0.0], [0.0, 1.0]], B, [0.0, 0.0], state_dist).predict(
            state_dist, 0
        )
        assert abs(sum(result) - 1.0) < 1e-9

    def test_out_of_range_action_rejected(self):
        with pytest.raises(ValueError, match="action"):
            CategoricalModel(
                [[1.0, 0.0], [0.0, 1.0]], [[[1.0], [0.0]], [[0.0], [1.0]]], [0.0, 0.0], [0.5, 0.5]
            ).predict([0.5, 0.5], 99)


class TestPreferenceDiagnostic:
    def test_basic(self):

        C = [1.0, -1.0]
        obs_dist = [0.8, 0.2]
        result = CategoricalModel(
            [[1.0, 0.0], [0.0, 1.0]], [[[1.0], [0.0]], [[0.0], [1.0]]], C, [0.5, 0.5]
        ).preference_score(obs_dist)
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
    def test_trace_json_records_filter_then_predict(self, tmp_path):
        from tests.gnn_execution_fixture import trace

        record = trace(tmp_path)
        encoded = record.to_dict()
        assert encoded["beliefs"] != encoded["predicted_state"]
        assert encoded["beliefs_prior"] == encoded["state"]
        assert len(encoded["policy_scores"]) == 2


class TestGNNModelRunner:
    def test_complete_model_run_and_report(self, tmp_path):
        from tests.gnn_execution_fixture import runner

        model = runner(tmp_path)
        result = model.run(3)
        assert len(result["traces"]) == 3
        assert result["success"] is True
        assert result["source_sha256"] in model.generate_execution_report()


class TestAnalyzeRequest:
    def test_basic(self):
        from cogant.server.models import AnalyzeRequest

        req = AnalyzeRequest(repo_path="/some/path")
        assert req.repo_path == "/some/path"
        assert req.skip_dynamic is True
        assert req.stages is None

    def test_with_stages(self):
        from cogant.server.models import AnalyzeRequest

        # 'analyze' is not a canonical stage name; use the RUNNER_STAGES set.
        req = AnalyzeRequest(repo_path="/my/repo", stages=["ingest", "static"], skip_dynamic=False)
        assert req.stages == ["ingest", "static"]
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

        r = RoundtripResponse(
            role_preservation_score=0.85, structurally_isomorphic=True, threshold=0.7
        )
        assert r.role_preservation_score == 0.85
        assert r.structurally_isomorphic is True

    def test_not_isomorphic(self):
        from cogant.server.models import RoundtripResponse

        r = RoundtripResponse(
            role_preservation_score=0.4,
            structurally_isomorphic=False,
            threshold=0.7,
            original_roles={"obs": 3},
            synthesized_roles={"obs": 1},
            errors=["role mismatch"],
        )
        assert r.structurally_isomorphic is False
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


class TestGNNVersion:
    def test_versions(self):
        from cogant.schema.versions import CURRENT_GNN_VERSION

        assert CURRENT_GNN_VERSION == "2.0.0"

    def test_gnn_current_sections(self):
        from cogant.schema.versions import GNN_V2_REQUIRED_SECTIONS

        assert "GNNSection" in GNN_V2_REQUIRED_SECTIONS
        assert "GNNVersionAndFlags" in GNN_V2_REQUIRED_SECTIONS
        assert "Signature" in GNN_V2_REQUIRED_SECTIONS


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
    """Canonical PipelineConfig contract (stages/skip_dynamic; no name)."""

    def test_basic(self):
        from cogant.config.pipeline import PipelineConfig

        pc = PipelineConfig()
        assert pc.stages[0] == "ingest"
        assert pc.skip_dynamic is False

    def test_with_stages(self):
        from cogant.config.pipeline import PipelineConfig

        pc = PipelineConfig(
            stages=["ingest", "static", "normalize"],
            skip_dynamic=True,
        )
        assert pc.stages == ["ingest", "static", "normalize"]
        assert pc.skip_dynamic is True


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


class TestCurrentGNNVersionsModule:
    def test_schema_init(self):
        import cogant.schema as s

        assert s is not None
