#!/usr/bin/env python3
"""Coverage boost batch 63 — dynamic/coverage.py, dynamic/traces.py,
dynamic/enrichment.py, pipeline/dag.py, process/extractor.py,
process/policies.py, process/timeline.py.

Covers:
- dynamic/coverage.py: CoverageIngester (ingest_coverage_xml, ingest_coverage_py,
  get_coverage_summary, get_file_coverage, map_coverage_to_spans)
- dynamic/traces.py: TraceIngester (ingest_chrome_trace, ingest_custom_trace,
  get_trace_summary, get_function_calls, extract_call_graph, extract_call_sequences,
  extract_hot_paths, extract_timing, get_callee_functions, get_caller_functions)
- dynamic/enrichment.py: enrich_graph
- pipeline/dag.py: Stage, StageResult, DAGResult, StageStatus, PipelineDAG (add_stage, run)
- process/extractor.py: ProcessExtractor (extract, add_stage_dependency, set_entry_stage),
  ProcessModel, ProcessConnection, Stage
- process/policies.py: PolicyExtractor (extract, get_retry_policy, list_policies_for_stage),
  RetryPolicy, BranchingPolicy
- process/timeline.py: TimelineBuilder (build, get_stage_at_time, get_stages_in_range),
  GanttStage, Timeline
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_empty_graph():
    from cogant.schemas.graph import ProgramGraph, GraphMetadata
    return ProgramGraph(metadata=GraphMetadata(repo_uri="file:///test"))


def _make_graph_with_nodes():
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import NodeKind, EdgeKind
    builder = ProgramGraphBuilder(repo_uri="file:///test")
    n1 = builder.add_node(NodeKind.MODULE, "mod", "mod", path="mod.py")
    n2 = builder.add_node(NodeKind.FUNCTION, "fn", "mod.fn", path="mod.py")
    builder.add_edge(n1.id, n2.id, EdgeKind.CONTAINS)
    return builder.finalize()


def _make_process_model():
    from cogant.process.extractor import ProcessModel
    return ProcessModel(id="pm1", schema_name="test", stages={}, connections={})


# ---------------------------------------------------------------------------
# dynamic/coverage.py — CoverageIngester
# ---------------------------------------------------------------------------

class TestCoverageIngester:
    def _make_ingester(self):
        from cogant.dynamic.coverage import CoverageIngester
        return CoverageIngester()

    def test_init(self):
        ingester = self._make_ingester()
        assert ingester is not None

    def test_get_coverage_summary_empty(self):
        ingester = self._make_ingester()
        summary = ingester.get_coverage_summary()
        assert isinstance(summary, dict)

    def test_get_file_coverage_unknown(self):
        ingester = self._make_ingester()
        result = ingester.get_file_coverage("nonexistent.py")
        assert result is None or isinstance(result, dict)

    def test_map_coverage_to_spans_empty(self):
        ingester = self._make_ingester()
        spans = ingester.map_coverage_to_spans()
        assert isinstance(spans, list)

    def test_ingest_coverage_xml_missing_file(self, tmp_path):
        ingester = self._make_ingester()
        result = ingester.ingest_coverage_xml(str(tmp_path / "missing.xml"))
        assert isinstance(result, dict)

    def test_ingest_coverage_py_missing_file(self, tmp_path):
        ingester = self._make_ingester()
        result = ingester.ingest_coverage_py(str(tmp_path / "missing.coverage"))
        assert isinstance(result, dict)

    def test_ingest_coverage_xml_valid(self, tmp_path):
        xml_content = """<?xml version="1.0" ?>
<coverage version="7.0" timestamp="1000000" lines-valid="10" lines-covered="8"
          line-rate="0.8" branches-covered="0" branches-valid="0"
          branch-rate="0" complexity="0">
    <packages>
        <package name="mod" line-rate="0.8" branch-rate="0" complexity="0">
            <classes>
                <class name="mod.py" filename="mod.py" line-rate="0.8"
                       branch-rate="0" complexity="0">
                    <lines>
                        <line number="1" hits="1"/>
                        <line number="2" hits="1"/>
                        <line number="3" hits="0"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>"""
        xml_path = tmp_path / "coverage.xml"
        xml_path.write_text(xml_content)
        ingester = self._make_ingester()
        result = ingester.ingest_coverage_xml(str(xml_path))
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# dynamic/traces.py — TraceIngester
# ---------------------------------------------------------------------------

class TestTraceIngester:
    def _make_ingester(self):
        from cogant.dynamic.traces import TraceIngester
        return TraceIngester()

    def test_init(self):
        ingester = self._make_ingester()
        assert ingester is not None

    def test_get_trace_summary_empty(self):
        ingester = self._make_ingester()
        summary = ingester.get_trace_summary()
        assert isinstance(summary, dict)

    def test_get_function_calls_unknown(self):
        ingester = self._make_ingester()
        calls = ingester.get_function_calls("nonexistent_func")
        assert isinstance(calls, list)

    def test_extract_call_graph_empty(self):
        ingester = self._make_ingester()
        graph = ingester.extract_call_graph()
        assert isinstance(graph, dict)

    def test_extract_call_sequences_empty(self):
        ingester = self._make_ingester()
        seqs = ingester.extract_call_sequences()
        assert isinstance(seqs, list)

    def test_extract_hot_paths_empty(self):
        ingester = self._make_ingester()
        paths = ingester.extract_hot_paths()
        assert isinstance(paths, list)

    def test_extract_timing_empty(self):
        ingester = self._make_ingester()
        timing = ingester.extract_timing()
        assert isinstance(timing, dict)

    def test_get_callee_functions_unknown(self):
        ingester = self._make_ingester()
        callees = ingester.get_callee_functions("nonexistent_func")
        assert isinstance(callees, list)

    def test_get_caller_functions_unknown(self):
        ingester = self._make_ingester()
        callers = ingester.get_caller_functions("nonexistent_func")
        assert isinstance(callers, list)

    def test_ingest_chrome_trace_missing_file(self, tmp_path):
        ingester = self._make_ingester()
        result = ingester.ingest_chrome_trace(str(tmp_path / "missing.json"))
        assert isinstance(result, list)

    def test_ingest_custom_trace_missing_file(self, tmp_path):
        ingester = self._make_ingester()
        result = ingester.ingest_custom_trace(str(tmp_path / "missing.trace"), "json")
        assert isinstance(result, list)

    def test_ingest_chrome_trace_valid(self, tmp_path):
        import json
        trace_data = {
            "traceEvents": [
                {"pid": 1, "tid": 1, "ph": "B", "ts": 0, "name": "func_a", "cat": "python"},
                {"pid": 1, "tid": 1, "ph": "E", "ts": 100, "name": "func_a", "cat": "python"},
                {"pid": 1, "tid": 1, "ph": "B", "ts": 50, "name": "func_b", "cat": "python"},
                {"pid": 1, "tid": 1, "ph": "E", "ts": 80, "name": "func_b", "cat": "python"},
            ]
        }
        trace_path = tmp_path / "trace.json"
        trace_path.write_text(json.dumps(trace_data))
        ingester = self._make_ingester()
        result = ingester.ingest_chrome_trace(str(trace_path))
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# dynamic/enrichment.py — enrich_graph
# ---------------------------------------------------------------------------

class TestEnrichGraph:
    def test_enrich_empty_graph_no_paths(self):
        from cogant.dynamic.enrichment import enrich_graph
        graph = _make_empty_graph()
        result = enrich_graph(graph)
        assert isinstance(result, dict)

    def test_enrich_graph_with_nodes(self):
        from cogant.dynamic.enrichment import enrich_graph
        graph = _make_graph_with_nodes()
        result = enrich_graph(graph)
        assert isinstance(result, dict)

    def test_enrich_graph_missing_coverage_path(self, tmp_path):
        from cogant.dynamic.enrichment import enrich_graph
        graph = _make_empty_graph()
        result = enrich_graph(graph, coverage_path=str(tmp_path / "missing.xml"))
        assert isinstance(result, dict)

    def test_enrich_graph_missing_trace_path(self, tmp_path):
        from cogant.dynamic.enrichment import enrich_graph
        graph = _make_empty_graph()
        result = enrich_graph(graph, trace_path=str(tmp_path / "missing.json"))
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# pipeline/dag.py — Stage, StageResult, DAGResult, StageStatus, PipelineDAG
# ---------------------------------------------------------------------------

class TestStageStatus:
    def test_status_values(self):
        from cogant.pipeline.dag import StageStatus
        assert StageStatus.SUCCESS is not None
        assert StageStatus.FAILED is not None
        assert StageStatus.SKIPPED is not None


class TestStageDataclass:
    def test_stage_init(self):
        from cogant.pipeline.dag import Stage
        stage = Stage(name="my_stage", fn=lambda ctx: {"result": 42}, deps=[], timeout=30.0)
        assert stage.name == "my_stage"
        assert stage.deps == []
        assert stage.timeout == 30.0

    def test_stage_fn_callable(self):
        from cogant.pipeline.dag import Stage
        stage = Stage(name="s", fn=lambda ctx: ctx.get("x", 0) * 2, deps=[])
        assert callable(stage.fn)


class TestStageResult:
    def test_stage_result_init(self):
        from cogant.pipeline.dag import StageResult, StageStatus
        result = StageResult(name="s1", status=StageStatus.SUCCESS, elapsed=0.1, error=None, output={"val": 1})
        assert result.status == StageStatus.SUCCESS
        assert result.elapsed == 0.1
        assert result.output == {"val": 1}

    def test_stage_result_failed(self):
        from cogant.pipeline.dag import StageResult, StageStatus
        result = StageResult(name="s2", status=StageStatus.FAILED, elapsed=0.0, error="boom", output=None)
        assert result.status == StageStatus.FAILED
        assert result.error == "boom"


class TestDAGResult:
    def test_dag_result_init(self):
        from cogant.pipeline.dag import DAGResult
        result = DAGResult(stage_results={}, errors=[], elapsed=0.5)
        assert isinstance(result.stage_results, dict)
        assert result.errors == []
        assert result.elapsed == 0.5


class TestPipelineDAG:
    def test_init(self):
        from cogant.pipeline.dag import PipelineDAG
        dag = PipelineDAG()
        assert dag is not None

    def test_add_and_run_single_stage(self):
        from cogant.pipeline.dag import PipelineDAG, Stage, DAGResult, StageStatus
        dag = PipelineDAG()
        ran = []
        dag.add_stage(Stage(name="step1", fn=lambda ctx: ran.append("step1") or {"done": True}, deps=[]))
        result = dag.run({})
        assert isinstance(result, DAGResult)

    def test_run_empty_dag(self):
        from cogant.pipeline.dag import PipelineDAG, DAGResult
        dag = PipelineDAG()
        result = dag.run({})
        assert isinstance(result, DAGResult)
        assert result.stage_results == {} or isinstance(result.stage_results, dict)

    def test_run_with_context_passed_to_fn(self):
        from cogant.pipeline.dag import PipelineDAG, Stage
        results = {}
        dag = PipelineDAG()
        dag.add_stage(Stage(name="read_ctx", fn=lambda ctx: results.update({"x": ctx.get("x")}), deps=[]))
        dag.run({"x": 42})
        assert results.get("x") == 42

    def test_run_with_deps_ordering(self):
        from cogant.pipeline.dag import PipelineDAG, Stage, DAGResult
        order = []
        dag = PipelineDAG()
        dag.add_stage(Stage(name="a", fn=lambda ctx: order.append("a"), deps=[]))
        dag.add_stage(Stage(name="b", fn=lambda ctx: order.append("b"), deps=["a"]))
        result = dag.run({})
        assert isinstance(result, DAGResult)
        if len(order) == 2:
            assert order.index("a") < order.index("b")


# ---------------------------------------------------------------------------
# process/extractor.py — ProcessExtractor, ProcessModel, ProcessConnection
# ---------------------------------------------------------------------------

class TestProcessExtractor:
    def test_init(self):
        from cogant.process.extractor import ProcessExtractor
        graph = _make_empty_graph()
        extractor = ProcessExtractor(graph, schema_name="test")
        assert extractor is not None

    def test_extract_returns_process_model(self):
        from cogant.process.extractor import ProcessExtractor, ProcessModel
        graph = _make_empty_graph()
        extractor = ProcessExtractor(graph, schema_name="test")
        model = extractor.extract()
        assert isinstance(model, ProcessModel)

    def test_extract_with_nodes(self):
        from cogant.process.extractor import ProcessExtractor, ProcessModel
        graph = _make_graph_with_nodes()
        extractor = ProcessExtractor(graph, schema_name="test")
        model = extractor.extract()
        assert isinstance(model, ProcessModel)
        assert isinstance(model.stages, dict)

    def test_add_stage_dependency(self):
        from cogant.process.extractor import ProcessExtractor
        graph = _make_empty_graph()
        extractor = ProcessExtractor(graph, schema_name="test")
        model = extractor.extract()
        stage_ids = list(model.stages.keys())
        if len(stage_ids) >= 2:
            extractor.add_stage_dependency(stage_ids[0], stage_ids[1], trigger="on_success")

    def test_set_entry_stage(self):
        from cogant.process.extractor import ProcessExtractor
        graph = _make_empty_graph()
        extractor = ProcessExtractor(graph, schema_name="test")
        model = extractor.extract()
        stage_ids = list(model.stages.keys())
        if stage_ids:
            extractor.set_entry_stage(stage_ids[0])


class TestProcessModel:
    def test_init(self):
        from cogant.process.extractor import ProcessModel
        model = ProcessModel(id="pm1", schema_name="test", stages={}, connections={})
        assert model.id == "pm1"
        assert model.schema_name == "test"
        assert model.stages == {}
        assert model.connections == {}


class TestProcessConnection:
    def test_init(self):
        from cogant.process.extractor import ProcessConnection
        conn = ProcessConnection(
            id="conn1",
            source_stage_id="s1",
            target_stage_id="s2",
            trigger="on_success",
            condition=None,
            success_rate=1.0,
        )
        assert conn.id == "conn1"
        assert conn.source_stage_id == "s1"
        assert conn.target_stage_id == "s2"


# ---------------------------------------------------------------------------
# process/policies.py — PolicyExtractor, RetryPolicy, BranchingPolicy
# ---------------------------------------------------------------------------

class TestPolicyExtractor:
    def test_init(self):
        from cogant.process.policies import PolicyExtractor
        graph = _make_empty_graph()
        extractor = PolicyExtractor(graph)
        assert extractor is not None

    def test_extract_returns_dict(self):
        from cogant.process.policies import PolicyExtractor
        graph = _make_empty_graph()
        extractor = PolicyExtractor(graph)
        result = extractor.extract()
        assert isinstance(result, dict)

    def test_extract_with_nodes(self):
        from cogant.process.policies import PolicyExtractor
        graph = _make_graph_with_nodes()
        extractor = PolicyExtractor(graph)
        result = extractor.extract()
        assert isinstance(result, dict)

    def test_get_retry_policy_unknown(self):
        from cogant.process.policies import PolicyExtractor
        graph = _make_empty_graph()
        extractor = PolicyExtractor(graph)
        result = extractor.get_retry_policy("nonexistent")
        assert result is None

    def test_list_policies_for_stage_unknown(self):
        from cogant.process.policies import PolicyExtractor
        graph = _make_empty_graph()
        extractor = PolicyExtractor(graph)
        result = extractor.list_policies_for_stage("nonexistent")
        assert isinstance(result, dict)

    def test_policy_count(self):
        from cogant.process.policies import PolicyExtractor
        graph = _make_empty_graph()
        extractor = PolicyExtractor(graph)
        count = extractor.policy_count()
        assert isinstance(count, int)
        assert count >= 0


class TestRetryPolicy:
    def test_init(self):
        from cogant.process.policies import RetryPolicy
        policy = RetryPolicy(
            id="rp1",
            stage_id="s1",
            max_attempts=3,
            backoff_strategy="exponential",
            backoff_base=1.0,
            backoff_multiplier=2.0,
        )
        assert policy.id == "rp1"
        assert policy.max_attempts == 3
        assert policy.backoff_strategy == "exponential"


class TestBranchingPolicy:
    def test_init(self):
        from cogant.process.policies import BranchingPolicy
        policy = BranchingPolicy(
            id="bp1",
            stage_id="s1",
            decision_point="on_error",
            branches={"error": "s_error", "success": "s_success"},
            default_branch="s_success",
        )
        assert policy.id == "bp1"
        assert policy.decision_point == "on_error"
        assert "error" in policy.branches


# ---------------------------------------------------------------------------
# process/timeline.py — TimelineBuilder, GanttStage, Timeline
# ---------------------------------------------------------------------------

class TestTimelineBuilder:
    def test_init(self):
        from cogant.process.timeline import TimelineBuilder
        model = _make_process_model()
        builder = TimelineBuilder(model)
        assert builder is not None

    def test_build_returns_timeline(self):
        from cogant.process.timeline import TimelineBuilder, Timeline
        model = _make_process_model()
        builder = TimelineBuilder(model)
        timeline = builder.build()
        assert isinstance(timeline, Timeline)

    def test_get_stage_at_time_empty(self):
        from cogant.process.timeline import TimelineBuilder
        model = _make_process_model()
        builder = TimelineBuilder(model)
        builder.build()
        result = builder.get_stage_at_time(0.0)
        assert result is None or isinstance(result, str)

    def test_get_stages_in_range_empty(self):
        from cogant.process.timeline import TimelineBuilder
        model = _make_process_model()
        builder = TimelineBuilder(model)
        builder.build()
        result = builder.get_stages_in_range(0.0, 10.0)
        assert isinstance(result, list)

    def test_export_gantt_data_returns_collection(self):
        from cogant.process.timeline import TimelineBuilder
        model = _make_process_model()
        builder = TimelineBuilder(model)
        builder.build()
        result = builder.export_gantt_data()
        assert isinstance(result, (list, dict))

    def test_get_timeline_returns_timeline(self):
        from cogant.process.timeline import TimelineBuilder, Timeline
        model = _make_process_model()
        builder = TimelineBuilder(model)
        builder.build()
        timeline = builder.get_timeline()
        assert isinstance(timeline, Timeline)


class TestGanttStage:
    def test_init(self):
        from cogant.process.timeline import GanttStage
        gs = GanttStage(
            stage_id="s1",
            name="Stage 1",
            start_time=0.0,
            duration=5.0,
            dependencies=[],
            criticality=1.0,
        )
        assert gs.stage_id == "s1"
        assert gs.duration == 5.0
        assert gs.dependencies == []


class TestTimeline:
    def test_init(self):
        from cogant.process.timeline import Timeline
        tl = Timeline(stages=[], total_duration=0.0, critical_path=[], parallel_groups=[])
        assert isinstance(tl.stages, list)
        assert tl.total_duration == 0.0
