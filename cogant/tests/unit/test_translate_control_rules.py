"""Targeted coverage tests for ``cogant.translate.rules.control``.

Drives ConfigRule, FeatureFlagRule, and ParameterRule against real
ProgramGraph instances (no mocks). Hits both ``matches`` and ``apply``
paths plus the unknown-node-id branch and the variable/class parameter
type branches.
"""

from cogant.graph.queries import GraphQuery
from cogant.schemas.core import Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.schemas.semantic import MappingKind
from cogant.translate.rules.control import (
    ConfigRule,
    FeatureFlagRule,
    ParameterRule,
)


def _make_graph(nodes: list[Node]) -> ProgramGraph:
    metadata = GraphMetadata(
        repo_uri="test://control", languages={"python"}, version="1.0"
    )
    graph = ProgramGraph(metadata=metadata)
    for n in nodes:
        graph.add_node(n)
    return graph


# ---------------------------------------------------------------------------
# ConfigRule
# ---------------------------------------------------------------------------


class TestConfigRule:
    def test_name_and_mapping_kind(self):
        rule = ConfigRule()
        assert rule.name == "config"
        assert rule.mapping_kind == MappingKind.CONTEXT

    def test_matches_returns_configuration_nodes(self):
        cfg = Node(
            id="config:settings",
            kind=NodeKind.CONFIGURATION,
            name="settings",
            qualified_name="settings",
            path="settings.yaml",
        )
        other = Node(
            id="module:main",
            kind=NodeKind.MODULE,
            name="main",
            qualified_name="main",
            path="main.py",
        )
        graph = _make_graph([cfg, other])
        rule = ConfigRule()
        matches = rule.matches(graph, GraphQuery(graph))
        assert len(matches) == 1
        assert matches[0]["node_id"] == "config:settings"

    def test_apply_returns_semantic_mapping(self):
        cfg = Node(
            id="config:db",
            kind=NodeKind.CONFIGURATION,
            name="database",
            qualified_name="database",
            path="db.toml",
        )
        graph = _make_graph([cfg])
        rule = ConfigRule()
        mapping = rule.apply(graph, {"node_id": "config:db"})
        assert mapping is not None
        assert mapping.kind == MappingKind.CONTEXT
        assert mapping.confidence_score == 0.9
        assert mapping.parser_certainty == 0.95
        assert "database" in mapping.semantic_label
        assert mapping.evidence_count == 1
        assert mapping.graph_fragment_node_ids == ["config:db"]

    def test_apply_returns_none_for_missing_node(self):
        graph = _make_graph([])
        rule = ConfigRule()
        result = rule.apply(graph, {"node_id": "config:missing"})
        assert result is None


# ---------------------------------------------------------------------------
# FeatureFlagRule
# ---------------------------------------------------------------------------


class TestFeatureFlagRule:
    def test_name_and_mapping_kind(self):
        rule = FeatureFlagRule()
        assert rule.name == "feature_flag"
        assert rule.mapping_kind == MappingKind.CONTEXT

    def test_matches_returns_feature_flag_nodes(self):
        ff = Node(
            id="flag:dark_mode",
            kind=NodeKind.FEATURE_FLAG,
            name="DARK_MODE",
            qualified_name="flags.DARK_MODE",
            path="flags.py",
        )
        cfg = Node(
            id="config:s",
            kind=NodeKind.CONFIGURATION,
            name="s",
            qualified_name="s",
            path="s.yaml",
        )
        graph = _make_graph([ff, cfg])
        rule = FeatureFlagRule()
        matches = rule.matches(graph, GraphQuery(graph))
        assert len(matches) == 1
        assert matches[0]["node_id"] == "flag:dark_mode"

    def test_apply_creates_mapping_with_high_band_confidence(self):
        ff = Node(
            id="flag:beta",
            kind=NodeKind.FEATURE_FLAG,
            name="BETA",
            qualified_name="flags.BETA",
            path="flags.py",
        )
        graph = _make_graph([ff])
        rule = FeatureFlagRule()
        mapping = rule.apply(graph, {"node_id": "flag:beta"})
        assert mapping is not None
        assert mapping.confidence_score == 0.85
        assert mapping.parser_certainty == 0.9
        assert "BETA" in mapping.semantic_label
        assert mapping.kind == MappingKind.CONTEXT

    def test_apply_returns_none_for_missing_node(self):
        graph = _make_graph([])
        rule = FeatureFlagRule()
        assert rule.apply(graph, {"node_id": "flag:nope"}) is None


# ---------------------------------------------------------------------------
# ParameterRule
# ---------------------------------------------------------------------------


class TestParameterRule:
    def test_name_and_mapping_kind(self):
        rule = ParameterRule()
        assert rule.name == "parameter"
        assert rule.mapping_kind == MappingKind.CONTEXT

    def test_matches_variable_with_param_keyword(self):
        # Several keyword hits + one non-match
        nodes = [
            Node(
                id="var:learning_rate",
                kind=NodeKind.VARIABLE,
                name="learning_rate",
                qualified_name="model.learning_rate",
                path="model.py",
            ),
            Node(
                id="var:beta_decay",
                kind=NodeKind.VARIABLE,
                name="beta_decay",
                qualified_name="model.beta_decay",
                path="model.py",
            ),
            Node(
                id="var:weight_init",
                kind=NodeKind.VARIABLE,
                name="weight_init",
                qualified_name="model.weight_init",
                path="model.py",
            ),
            Node(
                id="var:not_a_param",
                kind=NodeKind.VARIABLE,
                name="user_count",
                qualified_name="model.user_count",
                path="model.py",
            ),
        ]
        graph = _make_graph(nodes)
        rule = ParameterRule()
        matches = rule.matches(graph, GraphQuery(graph))
        ids = {m["node_id"] for m in matches}
        assert "var:learning_rate" in ids
        assert "var:beta_decay" in ids
        assert "var:weight_init" in ids
        assert "var:not_a_param" not in ids
        for m in matches:
            assert m["parameter_type"] == "variable"

    def test_matches_class_with_config_keyword(self):
        nodes = [
            Node(
                id="class:HyperparameterConfig",
                kind=NodeKind.CLASS,
                name="HyperparameterConfig",
                qualified_name="model.HyperparameterConfig",
                path="model.py",
            ),
            Node(
                id="class:UserSettings",
                kind=NodeKind.CLASS,
                name="UserSettings",
                qualified_name="model.UserSettings",
                path="model.py",
            ),
            Node(
                id="class:Database",
                kind=NodeKind.CLASS,
                name="Database",
                qualified_name="model.Database",
                path="model.py",
            ),
        ]
        graph = _make_graph(nodes)
        rule = ParameterRule()
        matches = rule.matches(graph, GraphQuery(graph))
        cls_matches = [m for m in matches if m["parameter_type"] == "class"]
        ids = {m["node_id"] for m in cls_matches}
        # HyperparameterConfig contains both 'param' and 'config' & 'hyperparameter'
        assert "class:HyperparameterConfig" in ids
        assert "class:UserSettings" in ids  # 'settings'
        assert "class:Database" not in ids

    def test_matches_returns_empty_for_irrelevant_graph(self):
        graph = _make_graph(
            [
                Node(
                    id="module:m",
                    kind=NodeKind.MODULE,
                    name="m",
                    qualified_name="m",
                    path="m.py",
                ),
            ]
        )
        rule = ParameterRule()
        assert rule.matches(graph, GraphQuery(graph)) == []

    def test_apply_variable_uses_high_parser_certainty(self):
        var = Node(
            id="var:gamma_decay",
            kind=NodeKind.VARIABLE,
            name="gamma_decay",
            qualified_name="model.gamma_decay",
            path="model.py",
        )
        graph = _make_graph([var])
        rule = ParameterRule()
        mapping = rule.apply(
            graph, {"node_id": "var:gamma_decay", "parameter_type": "variable"}
        )
        assert mapping is not None
        assert mapping.confidence_score == 0.85
        # Variable branch -> 0.90 parser certainty
        assert mapping.parser_certainty == 0.9
        assert "Variable" in mapping.description

    def test_apply_class_uses_lower_parser_certainty(self):
        cls = Node(
            id="class:ParamConfig",
            kind=NodeKind.CLASS,
            name="ParamConfig",
            qualified_name="model.ParamConfig",
            path="model.py",
        )
        graph = _make_graph([cls])
        rule = ParameterRule()
        mapping = rule.apply(
            graph, {"node_id": "class:ParamConfig", "parameter_type": "class"}
        )
        assert mapping is not None
        # Class branch -> 0.85 parser certainty
        assert mapping.parser_certainty == 0.85
        assert "Class" in mapping.description

    def test_apply_default_parameter_type_is_variable(self):
        var = Node(
            id="var:alpha",
            kind=NodeKind.VARIABLE,
            name="alpha",
            qualified_name="model.alpha",
            path="model.py",
        )
        graph = _make_graph([var])
        rule = ParameterRule()
        # Omit parameter_type — falls back to "variable"
        mapping = rule.apply(graph, {"node_id": "var:alpha"})
        assert mapping is not None
        assert mapping.parser_certainty == 0.9

    def test_apply_returns_none_for_missing_node(self):
        graph = _make_graph([])
        rule = ParameterRule()
        assert (
            rule.apply(graph, {"node_id": "var:missing", "parameter_type": "variable"})
            is None
        )


class TestModuleExports:
    def test_all_exports_match(self):
        from cogant.translate.rules import control as mod

        assert set(mod.__all__) == {"ConfigRule", "FeatureFlagRule", "ParameterRule"}
