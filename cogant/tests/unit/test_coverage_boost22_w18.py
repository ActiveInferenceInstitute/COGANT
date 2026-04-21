#!/usr/bin/env python3
"""Coverage boost batch 22 — GNNPackageBuilder helpers, PipelineConfig, and api/pipeline.

Covers:
- gnn/package.py: GNNPackageBuilder private helpers (_count_graph_nodes/edges/by_kind,
  _count_state_space_elements, _count_nodes_by_kind, _count_mappings_by_tier,
  _fallback_chart, _is_deterministic, _is_markovian, _extract_state_variables,
  _extract_observation_space, _extract_action_space, _extract_observation_modalities,
  _extract_actions, _extract_policies, _extract_constraints, _extract_objectives,
  _extract_relationships, _extract_classes, _extract_ontology_mappings,
  _extract_source_evidence, _extract_factorization, _extract_factor_list,
  _generate_dashboard_html, _checksum, _checksum_dict, _state_var_object,
  _action_object, _enum_value)
- api/pipeline.py: PipelineConfig defaults, PipelineRunner initialization,
  skip_stages / skip_dynamic logic
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers — lightweight graph + state space stubs
# ---------------------------------------------------------------------------


def _make_graph():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test_repo")
    mod = builder.add_node(
        NodeKind.MODULE, "mymodule", "mymodule", path="mymodule.py", language="python"
    )
    cls = builder.add_node(NodeKind.CLASS, "MyClass", "mymodule.MyClass", path="mymodule.py")
    func = builder.add_node(NodeKind.FUNCTION, "my_func", "mymodule.my_func", path="mymodule.py")
    builder.add_edge(mod.id, cls.id, EdgeKind.CONTAINS)
    builder.add_edge(cls.id, func.id, EdgeKind.CONTAINS)
    return builder.finalize()


class _FakeStateSpace:
    """Minimal duck-type substitute for StateSpaceModel."""

    def __init__(
        self,
        variables=None,
        observations=None,
        actions=None,
        transitions=None,
        likelihoods=None,
        preferences=None,
    ):
        self.variables = variables or []
        self.observations = observations or {}
        self.actions = actions or {}
        self.transitions = transitions or {}
        self.likelihoods = likelihoods or []
        self.preferences = preferences or {}
        self._state_var_objects: dict = {}


class _FakeProcessModel:
    def __init__(self):
        self.connections = []
        self.stages = []
        self.policies = []
        self.timelines = []


def _make_builder(graph=None, state_space=None, mappings=None):
    from cogant.gnn.package import GNNPackageBuilder

    if graph is None:
        graph = _make_graph()
    if state_space is None:
        state_space = _FakeStateSpace()
    if mappings is None:
        mappings = {}
    return GNNPackageBuilder(
        graph=graph,
        state_space=state_space,
        process_model=_FakeProcessModel(),
        mappings=mappings,
    )


# ---------------------------------------------------------------------------
# gnn/package.py — _enum_value module-level helper
# ---------------------------------------------------------------------------


class TestEnumValue:
    def test_enum_with_value(self):
        from cogant.gnn.package import _enum_value

        class FakeEnum:
            value = "HIDDEN_STATE"

        assert _enum_value(FakeEnum()) == "HIDDEN_STATE"

    def test_plain_string(self):
        from cogant.gnn.package import _enum_value

        assert _enum_value("raw_string") == "raw_string"

    def test_none(self):
        from cogant.gnn.package import _enum_value

        assert _enum_value(None) is None

    def test_integer(self):
        from cogant.gnn.package import _enum_value

        assert _enum_value(42) == 42


# ---------------------------------------------------------------------------
# GNNPackageBuilder — graph counting helpers
# ---------------------------------------------------------------------------


class TestGraphCounting:
    def test_count_nodes(self):
        b = _make_builder()
        # graph has 3 nodes (module, class, function)
        assert b._count_graph_nodes() == 3

    def test_count_edges(self):
        b = _make_builder()
        # graph has 2 edges (CONTAINS × 2)
        assert b._count_graph_edges() == 2

    def test_count_edges_by_kind(self):
        b = _make_builder()
        counts = b._count_edges_by_kind()
        assert isinstance(counts, dict)
        assert len(counts) >= 1

    def test_count_nodes_by_kind(self):
        b = _make_builder()
        counts = b._count_nodes_by_kind()
        assert isinstance(counts, dict)
        # Should have MODULE, CLASS, FUNCTION entries
        total = sum(counts.values())
        assert total == 3

    def test_count_mappings_by_tier_empty(self):
        b = _make_builder()
        result = b._count_mappings_by_tier()
        assert result == {}

    def test_count_mappings_by_tier_non_dict_mappings(self):
        b = _make_builder(mappings="invalid")
        result = b._count_mappings_by_tier()
        assert result == {}

    def test_count_state_space_elements_empty(self):
        b = _make_builder()
        counts = b._count_state_space_elements()
        assert counts["variables"] == 0
        assert counts["observations"] == 0
        assert counts["actions"] == 0

    def test_count_state_space_with_items(self):
        ss = _FakeStateSpace(
            variables=["v1", "v2"],
            observations={"o1": object()},
            actions={"a1": object()},
        )
        b = _make_builder(state_space=ss)
        counts = b._count_state_space_elements()
        assert counts["variables"] == 2
        assert counts["observations"] == 1
        assert counts["actions"] == 1


# ---------------------------------------------------------------------------
# GNNPackageBuilder — _checksum helpers
# ---------------------------------------------------------------------------


class TestChecksumHelpers:
    def test_checksum_string(self):
        b = _make_builder()
        h = b._checksum("hello world")
        assert isinstance(h, str)
        assert len(h) > 0

    def test_checksum_stable(self):
        b = _make_builder()
        assert b._checksum("abc") == b._checksum("abc")

    def test_checksum_dict(self):
        b = _make_builder()
        h = b._checksum_dict({"a": 1, "b": 2})
        assert isinstance(h, str)
        assert len(h) > 0

    def test_checksum_dict_stable(self):
        b = _make_builder()
        d = {"key": "value", "num": 42}
        assert b._checksum_dict(d) == b._checksum_dict(d)


# ---------------------------------------------------------------------------
# GNNPackageBuilder — _fallback_chart
# ---------------------------------------------------------------------------


class TestFallbackChart:
    def test_returns_html_string(self):
        b = _make_builder()
        html = b._fallback_chart("My Chart", {"A": 5, "B": 3})
        assert "<!DOCTYPE html>" in html
        assert "My Chart" in html
        assert "<svg" in html

    def test_empty_counts(self):
        b = _make_builder()
        html = b._fallback_chart("Empty", {})
        assert "<!DOCTYPE html>" in html
        assert "Empty" in html

    def test_single_category(self):
        b = _make_builder()
        html = b._fallback_chart("Single", {"OnlyOne": 10})
        assert "<!DOCTYPE html>" in html
        assert "10" in html


# ---------------------------------------------------------------------------
# GNNPackageBuilder — _is_deterministic, _is_markovian
# ---------------------------------------------------------------------------


class TestDeterministicMarkovian:
    def test_deterministic_empty_transitions(self):
        b = _make_builder()
        assert b._is_deterministic() is True

    def test_markovian_empty_transitions(self):
        b = _make_builder()
        assert b._is_markovian() is True

    def test_non_deterministic_multiple_to_states(self):
        class Trans:
            to_states = ["s1", "s2"]  # multiple successors → non-deterministic

        ss = _FakeStateSpace(transitions=[Trans()])
        b = _make_builder(state_space=ss)
        assert b._is_deterministic() is False

    def test_non_deterministic_multiple_observations(self):
        class Likelihood:
            observations = ["obs1", "obs2"]

        ss = _FakeStateSpace(likelihoods=[Likelihood()])
        b = _make_builder(state_space=ss)
        assert b._is_deterministic() is False

    def test_non_markovian_multiple_from_states(self):
        class Trans:
            from_states = ["s1", "s2"]  # multiple predecessors → non-Markovian

        ss = _FakeStateSpace(transitions=[Trans()])
        b = _make_builder(state_space=ss)
        assert b._is_markovian() is False

    def test_deterministic_single_to_state(self):
        class Trans:
            to_states = ["s1"]

        ss = _FakeStateSpace(transitions=[Trans()])
        b = _make_builder(state_space=ss)
        assert b._is_deterministic() is True

    def test_markovian_single_from_state(self):
        class Trans:
            from_states = ["s1"]

        ss = _FakeStateSpace(transitions=[Trans()])
        b = _make_builder(state_space=ss)
        assert b._is_markovian() is True


# ---------------------------------------------------------------------------
# GNNPackageBuilder — state variable / action object lookups
# ---------------------------------------------------------------------------


class TestObjectLookups:
    def test_state_var_object_returns_none_when_no_store(self):
        b = _make_builder()
        assert b._state_var_object("nonexistent") is None

    def test_state_var_object_returns_from_store(self):
        ss = _FakeStateSpace(variables=["v1"])
        ss._state_var_objects = {"v1": "var_object"}
        b = _make_builder(state_space=ss)
        assert b._state_var_object("v1") == "var_object"

    def test_action_object_returns_none_no_actions(self):
        b = _make_builder()
        assert b._action_object("nonexistent") is None

    def test_action_object_returns_from_actions_dict(self):
        class FakeAction:
            name = "my_action"

        ss = _FakeStateSpace(actions={"a1": FakeAction()})
        b = _make_builder(state_space=ss)
        result = b._action_object("a1")
        assert result is not None
        assert result.name == "my_action"


# ---------------------------------------------------------------------------
# GNNPackageBuilder — extraction helpers
# ---------------------------------------------------------------------------


class TestExtractionHelpers:
    def test_extract_state_variables_empty(self):
        b = _make_builder()
        result = b._extract_state_variables()
        assert result == []

    def test_extract_state_variables_no_obj(self):
        ss = _FakeStateSpace(variables=["v1", "v2"])
        b = _make_builder(state_space=ss)
        result = b._extract_state_variables()
        # Falls back to id/name/type dict when no _state_var_objects
        assert len(result) == 2
        assert result[0]["type"] == "variable"

    def test_extract_state_variables_with_obj(self):
        class FakeVar:
            id = "v1"
            name = "myvar"
            var_type = None
            cardinality = 3
            domain = None
            factor = "f1"
            description = "test var"
            source_node_ids = ["node1"]
            confidence = None

        ss = _FakeStateSpace(variables=["v1"])
        ss._state_var_objects = {"v1": FakeVar()}
        b = _make_builder(state_space=ss)
        result = b._extract_state_variables()
        assert len(result) == 1
        assert result[0]["name"] == "myvar"
        assert result[0]["cardinality"] == 3

    def test_extract_observation_space_empty(self):
        b = _make_builder()
        result = b._extract_observation_space()
        assert result == []

    def test_extract_observation_space_with_dict(self):
        class FakeObs:
            id = "obs1"
            name = "myobs"
            modality = "symbolic"
            values = None
            source_channels = []
            description = "test obs"
            confidence = None

        ss = _FakeStateSpace(observations={"o1": FakeObs()})
        b = _make_builder(state_space=ss)
        result = b._extract_observation_space()
        assert len(result) == 1
        assert result[0]["name"] == "myobs"

    def test_extract_observation_space_string_items(self):
        ss = _FakeStateSpace(observations={"o1": "plain_obs"})
        b = _make_builder(state_space=ss)
        result = b._extract_observation_space()
        assert len(result) == 1
        assert result[0]["name"] == "plain_obs"

    def test_extract_action_space_empty(self):
        b = _make_builder()
        result = b._extract_action_space()
        assert result == []

    def test_extract_action_space_with_objects(self):
        class FakeAction:
            id = "a1"
            name = "myaction"
            controller_id = None
            parameters = []
            effects = []
            preconditions = []
            description = "do something"
            confidence = None

        ss = _FakeStateSpace(actions={"a1": FakeAction()})
        b = _make_builder(state_space=ss)
        result = b._extract_action_space()
        assert len(result) == 1
        assert result[0]["name"] == "myaction"

    def test_extract_action_space_plain_strings(self):
        ss = _FakeStateSpace(actions={"a1": "plain_action"})
        b = _make_builder(state_space=ss)
        result = b._extract_action_space()
        assert len(result) == 1
        assert result[0]["name"] == "plain_action"

    def test_extract_observation_modalities_empty(self):
        b = _make_builder()
        modalities = b._extract_observation_modalities()
        # Default modality when none found
        assert modalities == ["symbolic"]

    def test_extract_observation_modalities_with_obs(self):
        class FakeObs:
            modality = "continuous"

        ss = _FakeStateSpace(observations={"o1": FakeObs()})
        b = _make_builder(state_space=ss)
        modalities = b._extract_observation_modalities()
        assert "continuous" in modalities

    def test_extract_observation_modalities_deduplication(self):
        class FakeObs:
            def __init__(self, m):
                self.modality = m

        ss = _FakeStateSpace(
            observations={
                "o1": FakeObs("symbolic"),
                "o2": FakeObs("symbolic"),
            }
        )
        b = _make_builder(state_space=ss)
        modalities = b._extract_observation_modalities()
        assert modalities.count("symbolic") == 1

    def test_extract_actions_empty(self):
        b = _make_builder()
        result = b._extract_actions()
        assert result == []

    def test_extract_actions_with_objects(self):
        class FakeAction:
            id = "a1"
            name = "do_something"
            controller_id = "ctrl"
            parameters = ["p1"]
            effects = ["var1"]
            preconditions = []
            description = "test action"
            confidence = None

        ss = _FakeStateSpace(actions={"a1": FakeAction()})
        b = _make_builder(state_space=ss)
        result = b._extract_actions()
        assert len(result) == 1
        assert result[0]["name"] == "do_something"
        assert result[0]["effects"] == ["var1"]

    def test_extract_actions_plain_string(self):
        ss = _FakeStateSpace(actions={"a1": "plain_str_action"})
        b = _make_builder(state_space=ss)
        result = b._extract_actions()
        assert len(result) == 1
        assert result[0]["name"] == "plain_str_action"

    def test_extract_policies_default_stub(self):
        b = _make_builder()
        result = b._extract_policies()
        # No POLICY mappings → default stub
        assert len(result) == 1
        assert result[0]["id"] == "policy:default"

    def test_extract_policies_with_policy_mapping(self):
        from cogant.schemas.semantic import MappingKind

        class FakeMapping:
            kind = MappingKind.POLICY
            semantic_label = "my_policy"
            description = "test"
            graph_fragment_node_ids = ["n1"]
            confidence_score = 0.9
            confidence_tier = None

        b = _make_builder(mappings={"m1": FakeMapping()})
        result = b._extract_policies()
        assert len(result) == 1
        assert result[0]["label"] == "my_policy"

    def test_extract_constraints_empty(self):
        b = _make_builder()
        result = b._extract_constraints()
        assert result == []

    def test_extract_constraints_with_constraint_mapping(self):
        from cogant.schemas.semantic import MappingKind

        class FakeMapping:
            kind = MappingKind.CONSTRAINT
            semantic_label = "my_constraint"
            description = "must not exceed"
            graph_fragment_node_ids = ["n1"]
            confidence_score = 0.8
            confidence_tier = None

        b = _make_builder(mappings={"m1": FakeMapping()})
        result = b._extract_constraints()
        assert len(result) == 1
        assert result[0]["label"] == "my_constraint"

    def test_extract_objectives_empty(self):
        b = _make_builder()
        result = b._extract_objectives()
        assert result == []

    def test_extract_objectives_with_preference_mapping(self):
        from cogant.schemas.semantic import MappingKind

        class FakeMapping:
            kind = MappingKind.PREFERENCE
            semantic_label = "minimize_cost"
            description = "keep low"
            graph_fragment_node_ids = []
            confidence_score = 0.7
            confidence_tier = None

        b = _make_builder(mappings={"m1": FakeMapping()})
        result = b._extract_objectives()
        assert len(result) == 1
        assert result[0]["label"] == "minimize_cost"

    def test_extract_relationships(self):
        b = _make_builder()
        rels = b._extract_relationships()
        assert isinstance(rels, list)
        # graph has 2 edges
        assert len(rels) == 2
        assert "source" in rels[0]
        assert "target" in rels[0]
        assert "kind" in rels[0]

    def test_extract_classes(self):
        b = _make_builder()
        classes = b._extract_classes()
        assert isinstance(classes, list)
        assert "MyClass" in classes

    def test_extract_ontology_mappings_empty(self):
        b = _make_builder()
        result = b._extract_ontology_mappings()
        assert result == []

    def test_extract_ontology_mappings_with_mappings(self):
        from cogant.schemas.semantic import MappingKind

        class FakeMapping:
            kind = MappingKind.HIDDEN_STATE
            semantic_label = "state_var"
            description = "internal state"
            graph_fragment_node_ids = ["n1"]
            graph_fragment_edge_ids = []
            confidence_score = 0.85
            confidence_tier = None
            evidence_count = 3

        b = _make_builder(mappings={"m1": FakeMapping()})
        result = b._extract_ontology_mappings()
        assert len(result) == 1
        assert result[0]["semantic_label"] == "state_var"
        assert result[0]["evidence_count"] == 3

    def test_extract_source_evidence(self):
        b = _make_builder()
        evidence = b._extract_source_evidence()
        assert "graph_nodes" in evidence
        assert "graph_edges" in evidence
        assert "timestamp" in evidence
        assert evidence["graph_nodes"] == 3

    def test_extract_factorization_empty(self):
        b = _make_builder()
        result = b._extract_factorization()
        assert result["type"] == "none"
        assert result["factor_count"] == 0

    def test_extract_factorization_with_vars_no_factor(self):
        ss = _FakeStateSpace(variables=["v1", "v2"])
        b = _make_builder(state_space=ss)
        result = b._extract_factorization()
        # No factor attribute → grouped into "default"
        assert result["type"] == "factor_partition"
        assert "default" in [f["id"] for f in result["factors"]]

    def test_extract_factorization_with_factor_attr(self):
        class FakeVar:
            factor = "f1"

        ss = _FakeStateSpace(variables=["v1"])
        ss._state_var_objects = {"v1": FakeVar()}
        b = _make_builder(state_space=ss)
        result = b._extract_factorization()
        assert result["factor_count"] == 1
        assert result["factors"][0]["id"] == "f1"

    def test_extract_factor_list(self):
        b = _make_builder()
        result = b._extract_factor_list()
        assert isinstance(result, list)

    def test_generate_dashboard_html(self):
        b = _make_builder()
        html = b._generate_dashboard_html()
        assert "<!DOCTYPE html>" in html or "<html" in html or "<div" in html
        # Just check it returns a non-empty string
        assert len(html) > 100


# ---------------------------------------------------------------------------
# api/pipeline.py — PipelineConfig defaults
# ---------------------------------------------------------------------------


class TestPipelineConfig:
    def test_default_stages(self):
        from cogant.api.pipeline import PipelineConfig

        cfg = PipelineConfig()
        assert "ingest" in cfg.stages
        assert "graph" in cfg.stages
        assert "validate" in cfg.stages

    def test_default_skip_stages_empty(self):
        from cogant.api.pipeline import PipelineConfig

        cfg = PipelineConfig()
        assert cfg.skip_stages == []

    def test_default_verbose_false(self):
        from cogant.api.pipeline import PipelineConfig

        cfg = PipelineConfig()
        assert cfg.verbose is False

    def test_default_dry_run_false(self):
        from cogant.api.pipeline import PipelineConfig

        cfg = PipelineConfig()
        assert cfg.dry_run is False

    def test_default_skip_dynamic_false(self):
        from cogant.api.pipeline import PipelineConfig

        cfg = PipelineConfig()
        assert cfg.skip_dynamic is False

    def test_custom_skip_stages(self):
        from cogant.api.pipeline import PipelineConfig

        cfg = PipelineConfig(skip_stages=["static", "dynamic"])
        assert "static" in cfg.skip_stages

    def test_incremental_since_default_none(self):
        from cogant.api.pipeline import PipelineConfig

        cfg = PipelineConfig()
        assert cfg.incremental_since is None

    def test_coverage_path_default_none(self):
        from cogant.api.pipeline import PipelineConfig

        cfg = PipelineConfig()
        assert cfg.coverage_path is None

    def test_cache_dir_default_none(self):
        from cogant.api.pipeline import PipelineConfig

        cfg = PipelineConfig()
        assert cfg.cache_dir is None


# ---------------------------------------------------------------------------
# api/pipeline.py — PipelineRunner initialization
# ---------------------------------------------------------------------------


class TestPipelineRunner:
    def test_initialization(self):
        from cogant.api.pipeline import PipelineRunner

        runner = PipelineRunner()
        assert hasattr(runner, "stage_handlers")

    def test_has_all_expected_stage_handlers(self):
        from cogant.api.pipeline import PipelineRunner

        runner = PipelineRunner()
        expected_stages = [
            "ingest",
            "static",
            "normalize",
            "graph",
            "dynamic",
            "translate",
            "statespace",
            "process",
            "export",
            "validate",
        ]
        for stage in expected_stages:
            assert stage in runner.stage_handlers

    def test_run_dry_all_skipped(self):
        """All stages skipped → no errors, bundle returns."""
        from cogant.api.pipeline import PipelineConfig, PipelineRunner

        runner = PipelineRunner()
        cfg = PipelineConfig(
            stages=["ingest"],
            skip_stages=["ingest"],
        )
        bundle = runner.run(".", cfg)
        # No errors from skipped stages
        assert isinstance(bundle.errors, list)

    def test_skip_dynamic_adds_to_effective_skip(self):
        """skip_dynamic=True should skip dynamic stage."""
        from cogant.api.pipeline import PipelineConfig, PipelineRunner

        runner = PipelineRunner()
        cfg = PipelineConfig(
            stages=["dynamic"],
            skip_dynamic=True,
        )
        bundle = runner.run(".", cfg)
        # dynamic stage should be in stage_results as skipped
        assert "dynamic" in bundle.stage_results
        assert bundle.stage_results["dynamic"].get("skipped") is True

    def test_unknown_stage_generates_error(self):
        """An unknown stage name should add an error but not raise."""
        from cogant.api.pipeline import PipelineConfig, PipelineRunner

        runner = PipelineRunner()
        cfg = PipelineConfig(stages=["nonexistent_stage_xyz"])
        bundle = runner.run(".", cfg)
        # Check that error was recorded
        assert any("Unknown stage" in e or "nonexistent_stage_xyz" in e for e in bundle.errors)
