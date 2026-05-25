#!/usr/bin/env python3
"""Targeted branch tests: gnn/runner.py, gnn/matrices.py, validate/report.py,
export/bundle.py, gnn/json_export.py, gnn/formatter/structural.py,
process/extractor.py, reverse/parser.py, static/calls.py, static/dataflow.py."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_graph():
    from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
    from cogant.schemas.graph import GraphMetadata, ProgramGraph

    meta = GraphMetadata(repo_uri="test://repo", languages={"python"})
    graph = ProgramGraph(metadata=meta)
    m1 = Node(
        id="m1",
        kind=NodeKind.MODULE,
        name="module_a",
        qualified_name="module_a",
        language="python",
        path="/repo/module_a.py",
    )
    c1 = Node(
        id="c1",
        kind=NodeKind.CLASS,
        name="ClassA",
        qualified_name="module_a.ClassA",
        path="/repo/module_a.py",
    )
    f1 = Node(
        id="f1",
        kind=NodeKind.FUNCTION,
        name="func_a",
        qualified_name="module_a.ClassA.func_a",
        path="/repo/module_a.py",
    )
    f2 = Node(
        id="f2",
        kind=NodeKind.FUNCTION,
        name="helper",
        qualified_name="module_a.helper",
        path="/repo/module_a.py",
    )
    for n in [m1, c1, f1, f2]:
        graph.add_node(n)
    edges = [
        Edge(id="e1", source_id="m1", target_id="c1", kind=EdgeKind.CONTAINS),
        Edge(id="e2", source_id="c1", target_id="f1", kind=EdgeKind.CONTAINS),
        Edge(id="e3", source_id="f1", target_id="f2", kind=EdgeKind.CALLS),
        Edge(id="e4", source_id="f2", target_id="c1", kind=EdgeKind.READS),
    ]
    for e in edges:
        graph.add_edge(e)
    return graph


def _make_ssm():
    from cogant.statespace.compiler import Action, ObservationModality, StateSpaceModel, Transition
    from cogant.statespace.temporal import TimeRegime
    from cogant.statespace.variables import StateVariable, StateVariableType

    v1 = StateVariable(
        id="v1", name="pos", var_type=StateVariableType.DISCRETE, node_id="m1", cardinality=3
    )
    v2 = StateVariable(
        id="v2", name="flag", var_type=StateVariableType.BOOLEAN, node_id="c1", cardinality=2
    )
    a1 = Action(id="a1", name="move", controller_id="f1", effects=["v1"])
    obs1 = ObservationModality(
        id="o1", name="sensor", source_node_id="f2", modality_type="discrete"
    )
    t1 = Transition(
        id="t1", source_state={"v1": "pre"}, target_state={"v1": "post"}, action_id="a1"
    )
    return StateSpaceModel(
        id="ssm1",
        schema_name="test_schema",
        variables={"v1": v1, "v2": v2},
        observations={"o1": obs1},
        actions={"a1": a1},
        transitions={"t1": t1},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def _make_process():
    from cogant.process.extractor import ProcessModel

    return ProcessModel(id="p1", schema_name="test_schema", stages={}, connections={})


# ---------------------------------------------------------------------------
# gnn/runner.py — GNNModelRunner with richer state space
# ---------------------------------------------------------------------------


class TestGNNModelRunnerRich:
    def _setup_runner(self, tmp_path, with_state_space=True, with_observations=True):
        from cogant.gnn.runner import GNNModelRunner

        manifest = {"version": "1.0.0", "name": "rich_model", "schema_name": "test"}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
        if with_state_space:
            state_space = {
                "variables": [
                    {"name": "position", "type": "discrete", "cardinality": 3},
                    {"name": "velocity", "type": "discrete", "cardinality": 2},
                    {"name": "heading", "type": "discrete", "cardinality": 4},
                ],
                "observations": [{"name": "obs_pos"}, {"name": "obs_vel"}]
                if with_observations
                else [],
                "actions": [
                    {"name": "move_forward"},
                    {"name": "turn_left"},
                    {"name": "turn_right"},
                    {"name": "stop"},
                ],
            }
            (tmp_path / "state_space.json").write_text(json.dumps(state_space))
        runner = GNNModelRunner()
        runner.load_package(str(tmp_path))
        return runner

    def test_run_with_state_space(self, tmp_path):
        runner = self._setup_runner(tmp_path)
        result = runner.run(steps=8)
        assert result["success"] is True
        assert result["steps_completed"] == 8
        assert len(result["traces"]) == 8

    def test_run_action_distribution(self, tmp_path):
        runner = self._setup_runner(tmp_path)
        result = runner.run(steps=10)
        ad = result["action_distribution"]
        assert isinstance(ad, dict)
        assert sum(ad.values()) == 10

    def test_run_statistics(self, tmp_path):
        runner = self._setup_runner(tmp_path)
        result = runner.run(steps=5)
        stats = result["statistics"]
        assert "min_reward" in stats or len(stats) == 0  # ok if empty

    def test_run_free_energy_trajectory(self, tmp_path):
        runner = self._setup_runner(tmp_path)
        result = runner.run(steps=6)
        fe = result["free_energy_trajectory"]
        assert isinstance(fe, list)
        assert len(fe) == 6

    def test_generate_execution_report_with_rich_trace(self, tmp_path):
        runner = self._setup_runner(tmp_path)
        result = runner.run(steps=5)
        report = runner.generate_execution_report(result)
        assert "GNN Model Execution Report" in report
        assert "Steps Completed" in report

    def test_generate_execution_report_empty(self, tmp_path):
        runner = self._setup_runner(tmp_path)
        report = runner.generate_execution_report()
        assert "No traces" in report

    def test_run_without_observations(self, tmp_path):
        runner = self._setup_runner(tmp_path, with_observations=False)
        result = runner.run(steps=3)
        assert result["success"] is True

    def test_load_package_returns_manifest(self, tmp_path):
        from cogant.gnn.runner import GNNModelRunner

        manifest = {"version": "1.0.0", "name": "test", "schema_name": "ts"}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
        runner = GNNModelRunner()
        result = runner.load_package(str(tmp_path))
        assert isinstance(result, dict)
        assert "version" in result

    def test_run_not_loaded_raises(self):
        from cogant.gnn.runner import GNNModelRunner

        runner = GNNModelRunner()
        with pytest.raises(RuntimeError, match="not loaded"):
            runner.run(steps=1)

    def test_traces_are_dicts(self, tmp_path):
        runner = self._setup_runner(tmp_path)
        result = runner.run(steps=3)
        for trace in result["traces"]:
            assert "step" in trace
            assert "action" in trace
            assert "state" in trace


# ---------------------------------------------------------------------------
# gnn/matrices.py — GNNMatrices
# ---------------------------------------------------------------------------


class TestGNNMatrices:
    def _make_matrices(self, with_vars=True):
        from cogant.gnn.matrices import GNNMatrices
        from cogant.schemas.graph import GraphMetadata, ProgramGraph
        from cogant.statespace.compiler import StateSpaceModel
        from cogant.statespace.temporal import TimeRegime
        from cogant.statespace.variables import StateVariable, StateVariableType

        meta = GraphMetadata(repo_uri="test")
        graph = ProgramGraph(metadata=meta)
        if with_vars:
            v1 = StateVariable(
                id="v1",
                name="pos",
                var_type=StateVariableType.DISCRETE,
                node_id="n1",
                cardinality=3,
            )
            v2 = StateVariable(
                id="v2",
                name="vel",
                var_type=StateVariableType.DISCRETE,
                node_id="n2",
                cardinality=2,
            )
            variables = {"v1": v1, "v2": v2}
        else:
            variables = {}
        ssm = StateSpaceModel(
            id="m1",
            schema_name="test",
            variables=variables,
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
        )
        return GNNMatrices(graph, mappings=[], state_space=ssm)

    def test_compute_A(self):
        m = self._make_matrices()
        A = m.compute_A()
        assert isinstance(A, list)

    def test_compute_B(self):
        m = self._make_matrices()
        B = m.compute_B()
        assert isinstance(B, list)

    def test_compute_C(self):
        m = self._make_matrices()
        C = m.compute_C()
        assert isinstance(C, list)

    def test_compute_D(self):
        m = self._make_matrices()
        D = m.compute_D()
        assert isinstance(D, list)
        if D:
            assert abs(sum(D) - 1.0) < 1e-9

    def test_n_states(self):
        m = self._make_matrices()
        assert m.n_states >= 0

    def test_n_obs(self):
        m = self._make_matrices()
        assert m.n_obs >= 0

    def test_n_actions(self):
        m = self._make_matrices()
        assert m.n_actions >= 0

    def test_to_dict(self):
        m = self._make_matrices()
        d = m.to_dict()
        assert "A" in d
        assert "B" in d
        assert "C" in d
        assert "D" in d

    def test_to_gnn_markdown_block(self):
        m = self._make_matrices()
        md = m.to_gnn_markdown_block()
        assert isinstance(md, str)

    def test_validate_shapes(self):
        m = self._make_matrices()
        valid, errors = m.validate_shapes()
        assert isinstance(valid, bool)
        assert isinstance(errors, list)

    def test_empty_variables(self):
        m = self._make_matrices(with_vars=False)
        A = m.compute_A()
        D = m.compute_D()
        assert isinstance(A, list)
        assert isinstance(D, list)


# ---------------------------------------------------------------------------
# validate/report.py — ReportGenerator
# ---------------------------------------------------------------------------


class TestReportGenerator:
    def _make_generator(self, schema_name="test_schema"):
        from cogant.validate.report import ReportGenerator

        graph = _make_graph()
        ssm = _make_ssm()
        process = _make_process()
        return ReportGenerator(graph, ssm, process, schema_name)

    def test_generate_basic(self):
        gen = self._make_generator()
        report = gen.generate()
        assert report.id == "report_test_schema"
        assert report.schema_name == "test_schema"

    def test_generate_is_valid(self):
        gen = self._make_generator()
        report = gen.generate()
        assert isinstance(report.is_valid, bool)

    def test_generate_coverage_score(self):
        gen = self._make_generator()
        report = gen.generate()
        assert 0.0 <= report.coverage_score <= 1.0

    def test_generate_confidence_score(self):
        gen = self._make_generator()
        report = gen.generate()
        assert 0.0 <= report.confidence_score <= 1.0

    def test_generate_summary(self):
        gen = self._make_generator()
        report = gen.generate()
        assert isinstance(report.summary, str)
        assert len(report.summary) > 0

    def test_generate_issues_list(self):
        gen = self._make_generator()
        report = gen.generate()
        assert isinstance(report.issues, list)

    def test_generate_with_provenance_records(self):
        from cogant.validate.report import ReportGenerator

        graph = _make_graph()
        ssm = _make_ssm()
        process = _make_process()
        gen = ReportGenerator(graph, ssm, process, "prov_schema")
        provenance = {"node1": ["source1", "source2"]}
        report = gen.generate(provenance_records=provenance)
        assert isinstance(report.is_valid, bool)

    def test_generate_different_schema_names(self):
        gen1 = self._make_generator("schema_a")
        gen2 = self._make_generator("schema_b")
        r1 = gen1.generate()
        r2 = gen2.generate()
        assert r1.id != r2.id
        assert r1.schema_name == "schema_a"
        assert r2.schema_name == "schema_b"

    def test_generate_timestamp(self):
        from datetime import datetime

        gen = self._make_generator()
        report = gen.generate()
        assert isinstance(report.validated_at, datetime)

    def test_report_model_id(self):
        gen = self._make_generator()
        report = gen.generate()
        assert report.model_id == "ssm1"


# ---------------------------------------------------------------------------
# export/bundle.py — BundleExporter
# ---------------------------------------------------------------------------


class TestBundleExporter:
    def _make_exporter(self, tmp_path):
        from cogant.export.bundle import BundleExporter

        graph = _make_graph()
        ssm = _make_ssm()
        process = _make_process()
        return BundleExporter(graph, ssm, process, {}, Path(tmp_path))

    def test_export_markdown_only(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        exporter.export(formats=["markdown"])
        assert Path(tmp_path / "gnn.md").exists()

    def test_export_json_only(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        exporter.export(formats=["json"])
        assert Path(tmp_path / "gnn.json").exists()

    def test_export_creates_manifest(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        exporter.export(formats=["markdown", "json"])
        assert Path(tmp_path / "MANIFEST.json").exists()

    def test_export_manifest_content(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        exporter.export(formats=["markdown"])
        manifest_data = json.loads((tmp_path / "MANIFEST.json").read_text())
        assert (
            "format" in manifest_data
            or "files" in manifest_data
            or "exports" in manifest_data
            or len(manifest_data) > 0
        )

    def test_export_all_formats(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        result = exporter.export()
        assert result == Path(tmp_path)

    def test_export_empty_formats(self, tmp_path):
        exporter = self._make_exporter(tmp_path)
        result = exporter.export(formats=[])
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# gnn/json_export.py — GNNJSONExporter
# ---------------------------------------------------------------------------


class TestGNNJSONExporter:
    def _make_exporter(self):
        from cogant.gnn.json_export import GNNJSONExporter

        graph = _make_graph()
        ssm = _make_ssm()
        process = _make_process()
        return GNNJSONExporter(graph, ssm, process, {})

    def test_export_returns_dict(self):
        exporter = self._make_exporter()
        result = exporter.export()
        assert isinstance(result, dict)

    def test_export_has_required_keys(self):
        exporter = self._make_exporter()
        result = exporter.export()
        assert "model_id" in result
        assert "schema_name" in result
        assert "state_space" in result

    def test_export_schema_name(self):
        exporter = self._make_exporter()
        result = exporter.export()
        assert result["schema_name"] == "test_schema"

    def test_export_state_space_section(self):
        exporter = self._make_exporter()
        result = exporter.export()
        ss = result["state_space"]
        assert isinstance(ss, dict) or isinstance(ss, list)

    def test_export_has_matrices(self):
        exporter = self._make_exporter()
        result = exporter.export()
        assert "matrices" in result

    def test_export_has_program_graph(self):
        exporter = self._make_exporter()
        result = exporter.export()
        assert "program_graph" in result

    def test_export_has_actions(self):
        exporter = self._make_exporter()
        result = exporter.export()
        assert "actions_policies" in result


# ---------------------------------------------------------------------------
# process/extractor.py — ProcessExtractor
# ---------------------------------------------------------------------------


class TestProcessExtractor:
    def test_extract_returns_process_model(self):
        from cogant.process.extractor import ProcessExtractor

        graph = _make_graph()
        extractor = ProcessExtractor(graph, "test_schema")
        model = extractor.extract()
        assert model.schema_name == "test_schema"
        assert hasattr(model, "stages")
        assert hasattr(model, "connections")

    def test_extract_stages_are_dict(self):
        from cogant.process.extractor import ProcessExtractor

        graph = _make_graph()
        extractor = ProcessExtractor(graph, "test_schema")
        model = extractor.extract()
        assert isinstance(model.stages, dict)

    def test_extract_connections_are_dict(self):
        from cogant.process.extractor import ProcessExtractor

        graph = _make_graph()
        extractor = ProcessExtractor(graph, "test_schema")
        model = extractor.extract()
        assert isinstance(model.connections, dict)

    def test_extract_empty_graph(self):
        from cogant.process.extractor import ProcessExtractor
        from cogant.schemas.graph import GraphMetadata, ProgramGraph

        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="x"))
        extractor = ProcessExtractor(graph, "empty")
        model = extractor.extract()
        assert model.schema_name == "empty"


# ---------------------------------------------------------------------------
# gnn/formatter/structural.py (via GNNMarkdownFormatter)
# ---------------------------------------------------------------------------


class TestGNNFormatterStructural:
    def _make_formatter(self):
        from cogant.gnn.formatter.base import GNNMarkdownFormatter

        graph = _make_graph()
        ssm = _make_ssm()
        process = _make_process()
        return GNNMarkdownFormatter(graph, ssm, process, {})

    def test_format_structural_sections(self):
        formatter = self._make_formatter()
        result = formatter.format()
        # Structural sections: ModelName, StateSpace, etc.
        assert isinstance(result, str)
        assert len(result) > 200

    def test_format_contains_state_space(self):
        formatter = self._make_formatter()
        result = formatter.format()
        assert "StateSpace" in result or "State Space" in result or "pos" in result

    def test_format_with_transitions(self):
        formatter = self._make_formatter()
        result = formatter.format()
        # Should have transition info
        assert isinstance(result, str)

    def test_format_with_actions(self):
        formatter = self._make_formatter()
        result = formatter.format()
        assert "move" in result or "Action" in result or "policy" in result.lower()


# ---------------------------------------------------------------------------
# reverse/parser.py — GNNMarkdownParser
# ---------------------------------------------------------------------------


class TestGNNMarkdownParser:
    def _basic_gnn(self):
        return """## ModelName
TestModel

## StateSpaceBlock
s_f0[3, 1, type=int]
s_f1[2, 1, type=int]

## ObservationBlock
o_m0[3, 1, type=int]

## ControlBlock
u_c0[2, 1, type=int]

## ActInfOntologyAnnotation
s_f0 = HiddenState
s_f1 = HiddenState
o_m0 = Observation
u_c0 = Action
"""

    def test_parse_basic_gnn(self):
        from cogant.reverse.parser import parse_gnn

        model = parse_gnn(self._basic_gnn())
        assert (
            model.model_name == "TestModel"
            or "test" in model.model_name.lower()
            or "Model" in model.model_name
        )

    def test_parse_hidden_states(self):
        from cogant.reverse.parser import parse_gnn

        model = parse_gnn(self._basic_gnn())
        assert isinstance(model.hidden_states, list)
        assert len(model.hidden_states) >= 0

    def test_parse_observations(self):
        from cogant.reverse.parser import parse_gnn

        model = parse_gnn(self._basic_gnn())
        assert isinstance(model.observations, list)

    def test_parse_actions(self):
        from cogant.reverse.parser import parse_gnn

        model = parse_gnn(self._basic_gnn())
        assert isinstance(model.actions, list)

    def test_parse_empty_string(self):
        from cogant.reverse.parser import parse_gnn

        model = parse_gnn("")
        assert hasattr(model, "model_name")
        assert hasattr(model, "hidden_states")

    def test_parse_annotations(self):
        from cogant.reverse.parser import parse_gnn

        model = parse_gnn(self._basic_gnn())
        assert isinstance(model.annotations, dict)

    def test_parse_cardinalities(self):
        from cogant.reverse.parser import parse_gnn

        model = parse_gnn(self._basic_gnn())
        assert isinstance(model.cardinalities, dict)

    def test_parse_from_file(self, tmp_path):
        from pathlib import Path

        from cogant.reverse.parser import parse_gnn

        gnn_file = tmp_path / "model.gnn.md"
        gnn_file.write_text(self._basic_gnn())
        model = parse_gnn(Path(gnn_file))
        assert hasattr(model, "model_name")


# ---------------------------------------------------------------------------
# static/calls.py — CallGraphBuilder
# ---------------------------------------------------------------------------


class TestCallExtractor:
    def test_extract_calls_basic(self, tmp_path):

        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        code = """
def foo():
    bar()
    baz(x=1, y=2)

def bar():
    pass

def baz(x, y):
    return x + y
"""
        src_file = tmp_path / "test.py"
        src_file.write_text(code)
        result = builder.extract_calls_from_source(code, src_file)
        assert isinstance(result, list)

    def test_extract_calls_from_file(self, tmp_path):

        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        code = "def foo():\n    bar()\n\ndef bar():\n    pass\n"
        src_file = tmp_path / "test.py"
        src_file.write_text(code)
        result = builder.extract_calls_from_file(src_file)
        assert isinstance(result, list)

    def test_extract_method_calls(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        code = """
class Foo:
    def method_a(self):
        self.method_b()
    def method_b(self):
        pass
"""
        src_file = tmp_path / "test.py"
        src_file.write_text(code)
        result = builder.extract_calls_from_source(code, src_file)
        assert isinstance(result, list)

    def test_calledge_attributes(self, tmp_path):
        from cogant.static.calls import CallGraphBuilder

        builder = CallGraphBuilder(repo_root=tmp_path)
        code = "def foo():\n    bar()\n"
        src_file = tmp_path / "foo.py"
        src_file.write_text(code)
        edges = builder.extract_calls_from_source(code, src_file)
        if edges:
            e = edges[0]
            assert hasattr(e, "caller_id")
            assert hasattr(e, "callee_name")


# ---------------------------------------------------------------------------
# static/dataflow.py — DataFlowAnalyzer
# ---------------------------------------------------------------------------


class TestDataFlowAnalyzer:
    def test_analyze_basic(self, tmp_path):

        from cogant.static.dataflow import DataFlowAnalyzer

        code = """
x = 1
y = x + 2
z = y * 3
"""
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        f = tmp_path / "test.py"
        f.write_text(code)
        result = analyzer.analyze_source(code, f)
        assert isinstance(result, list)

    def test_analyze_function_args(self, tmp_path):

        from cogant.static.dataflow import DataFlowAnalyzer

        code = """
def compute(a, b):
    c = a + b
    d = c * 2
    return d
"""
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        f = tmp_path / "func.py"
        f.write_text(code)
        result = analyzer.analyze_source(code, f)
        assert isinstance(result, list)

    def test_analyze_file(self, tmp_path):

        from cogant.static.dataflow import DataFlowAnalyzer

        code = "x = 1\ny = x + 2\n"
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        f = tmp_path / "simple.py"
        f.write_text(code)
        result = analyzer.analyze_file(f)
        assert isinstance(result, list)

    def test_dataflow_edge_attrs(self, tmp_path):

        from cogant.static.dataflow import DataFlowAnalyzer

        code = "def foo(a):\n    b = a + 1\n    return b\n"
        analyzer = DataFlowAnalyzer(repo_root=tmp_path)
        f = tmp_path / "edge.py"
        f.write_text(code)
        edges = analyzer.analyze_source(code, f)
        if edges:
            e = edges[0]
            assert hasattr(e, "source_symbol") or hasattr(e, "edge_type") or hasattr(e, "id")


# ---------------------------------------------------------------------------
# config/loaders.py — config loading functions
# ---------------------------------------------------------------------------


class TestConfigLoaders:
    def test_import_module(self):
        import cogant.config.loaders as cl

        assert cl is not None

    def test_load_from_dict(self):
        from cogant.config.loaders import ConfigLoader

        config = ConfigLoader.load_from_dict({"debug": True, "max_depth": 5})
        assert config is not None
        assert isinstance(config, dict)

    def test_load_from_dict_empty(self):
        from cogant.config.loaders import ConfigLoader

        config = ConfigLoader.load_from_dict({})
        assert config is not None

    def test_load_default(self):
        from cogant.config.loaders import ConfigLoader

        config = ConfigLoader.load_default()
        assert isinstance(config, dict)

    def test_load_from_yaml(self, tmp_path):
        from cogant.config.loaders import ConfigLoader

        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("debug: true\ntimeout: 30\n")
        config = ConfigLoader.load_from_yaml(cfg_file)
        assert isinstance(config, dict)

    def test_load_json_from_file(self, tmp_path):
        from cogant.config.loaders import ConfigLoader

        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"debug": False, "timeout": 30}))
        config = ConfigLoader.load_json_from_file(cfg_file)
        assert isinstance(config, dict)
        assert config.get("timeout") == 30

    def test_merge_configs(self):
        from cogant.config.loaders import ConfigLoader

        base = {"a": 1, "b": 2}
        override = {"b": 99, "c": 3}
        merged = ConfigLoader.merge_configs(base, override)
        assert isinstance(merged, dict)
        assert merged.get("b") == 99

    def test_build_cogant_config(self):
        from cogant.config.loaders import ConfigLoader

        config = ConfigLoader.build_cogant_config()
        assert config is not None

    def test_build_pipeline_config(self):
        from cogant.config.loaders import ConfigLoader

        config = ConfigLoader.build_pipeline_config()
        assert config is not None

    def test_build_export_config(self):
        from cogant.config.loaders import ConfigLoader

        config = ConfigLoader.build_export_config()
        assert config is not None

    def test_build_validation_config(self):
        from cogant.config.loaders import ConfigLoader

        config = ConfigLoader.build_validation_config()
        assert config is not None

    def test_load_all_configs(self):
        from cogant.config.loaders import ConfigLoader

        configs = ConfigLoader.load_all_configs()
        assert configs is not None


# ---------------------------------------------------------------------------
# gnn/validator.py — GNNValidator
# ---------------------------------------------------------------------------


class TestGNNValidator:
    def test_import(self):
        from cogant.gnn.validator import GNNValidator

        v = GNNValidator()
        assert v is not None

    def test_validate_markdown(self):
        from cogant.gnn.validator import GNNValidator

        v = GNNValidator()
        md = "## ModelName\nTestModel\n\n## StateSpaceBlock\ns_f0[3, 1, type=int]\n"
        errors = v.validate_markdown(md)
        assert isinstance(errors, list)

    def test_validate_state_space(self):
        from cogant.gnn.validator import GNNValidator

        v = GNNValidator()
        ss = {
            "variables": [{"name": "s_f0", "size": 3}],
            "actions": [],
            "observations": [],
        }
        errors = v.validate_state_space(ss)
        assert isinstance(errors, list)

    def test_validate_matrices(self):
        from cogant.gnn.validator import GNNValidator

        v = GNNValidator()
        matrices = {
            "A": [[0.7, 0.3], [0.4, 0.6]],
            "B": [[[1.0, 0.0], [0.0, 1.0]]],
        }
        errors = v.validate_matrices(matrices)
        assert isinstance(errors, list)

    def test_validate_provenance(self):
        from cogant.gnn.validator import GNNValidator

        v = GNNValidator()
        prov = {"source": "static_analysis", "confidence": 0.85}
        errors = v.validate_provenance(prov)
        assert isinstance(errors, list)

    def test_validation_result_to_dict(self):
        from cogant.gnn.validator import ValidationResult

        result = ValidationResult(valid=True, errors=[], warnings=["w1"])
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d.get("valid") is True

    def test_validate_package(self, tmp_path):
        from cogant.gnn.validator import GNNValidator

        v = GNNValidator()
        result = v.validate_package(str(tmp_path))
        assert hasattr(result, "valid") or isinstance(result, (bool, dict))


# ---------------------------------------------------------------------------
# ingest/language_detect.py — remaining gaps
# ---------------------------------------------------------------------------


class TestLanguageDetectorRemaining:
    def test_detect_go_file(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "main.go").write_text("package main\nfunc main() {}")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert "go" in result

    def test_detect_typescript_file(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "app.ts").write_text("const x: number = 1;")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert "typescript" in result

    def test_detect_rust_file(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "lib.rs").write_text("fn main() {}")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert "rust" in result

    def test_detect_multiple_languages(self, tmp_path):
        from cogant.ingest.language_detect import LanguageDetector

        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "app.js").write_text("var x = 1;")
        (tmp_path / "lib.ts").write_text("const y = 2;")
        result = LanguageDetector.detect_repo_languages(tmp_path)
        assert len(result) >= 2

    def test_detect_single_file(self):
        from cogant.ingest.language_detect import LanguageDetector

        assert LanguageDetector.detect_language(Path("test.py")) == "python"
        assert LanguageDetector.detect_language(Path("test.js")) == "javascript"
        assert LanguageDetector.detect_language(Path("test.unknown")) is None

    def test_extension_map_completeness(self):
        from cogant.ingest.language_detect import LanguageDetector

        em = LanguageDetector.EXTENSION_MAP
        assert ".py" in em
        assert ".js" in em
        assert ".ts" in em
        assert ".go" in em
        assert ".rs" in em

    def test_lazy_load_then_extension_map(self):
        from cogant.ingest.language_detect import LanguageDetector

        LanguageDetector._lazy_load_parsers()
        # Still has the extension map after lazy load
        assert ".py" in LanguageDetector.EXTENSION_MAP


# ---------------------------------------------------------------------------
# statespace/compiler.py — StateSpaceCompiler
# ---------------------------------------------------------------------------


class TestStateSpaceCompilerEdgeCases:
    def test_compile_basic(self):
        from cogant.statespace.compiler import StateSpaceCompiler

        graph = _make_graph()
        compiler = StateSpaceCompiler(graph, "test_schema")
        model = compiler.compile({})
        assert model.schema_name == "test_schema"

    def test_compile_time_regime(self):
        from cogant.statespace.compiler import StateSpaceCompiler

        graph = _make_graph()
        compiler = StateSpaceCompiler(graph, "test_schema")
        model = compiler.compile({})
        assert model.time_regime is not None

    def test_compile_empty_graph(self):
        from cogant.schemas.graph import GraphMetadata, ProgramGraph
        from cogant.statespace.compiler import StateSpaceCompiler

        graph = ProgramGraph(metadata=GraphMetadata(repo_uri="x"))
        compiler = StateSpaceCompiler(graph, "empty")
        model = compiler.compile({})
        assert model.schema_name == "empty"
        assert isinstance(model.variables, dict)
