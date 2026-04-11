"""Unit tests for :mod:`cogant.process.timeline` and
:mod:`cogant.process.policies`.

All tests build real :class:`ProgramGraph` / :class:`ProcessModel`
instances — no mocks. Two flavours of fixtures are used:

- Hand-crafted :class:`Stage` / :class:`ProcessConnection` graphs that
  exercise timeline sequencing and parallel-group detection.
- Real :class:`ProcessExtractor` output on a small program graph so we
  can validate the integration between the timeline builder and the
  process extractor.
"""

from __future__ import annotations

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.process.extractor import (
    ProcessConnection,
    ProcessExtractor,
    ProcessModel,
    Stage,
)
from cogant.process.policies import (
    BranchingPolicy,
    CircuitBreakerPolicy,
    PolicyExtractor,
    RetryPolicy,
)
from cogant.process.timeline import (
    GanttStage,
    Timeline,
    TimelineBuilder,
)
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------- helpers


def _make_stage(
    stage_id: str,
    name: str,
    *,
    duration: float = 2.0,
    entry_points=None,
    exit_points=None,
) -> Stage:
    return Stage(
        id=stage_id,
        name=name,
        expected_duration=duration,
        entry_points=list(entry_points or []),
        exit_points=list(exit_points or []),
    )


def _linear_process_model() -> ProcessModel:
    """Sequential A -> B -> C with matching connections."""
    stages = {
        "a": _make_stage("a", "A", duration=1.0, exit_points=["b"]),
        "b": _make_stage("b", "B", duration=2.0, entry_points=["a"], exit_points=["c"]),
        "c": _make_stage("c", "C", duration=3.0, entry_points=["b"]),
    }
    conns = {
        "c_ab": ProcessConnection(id="c_ab", source_stage_id="a", target_stage_id="b"),
        "c_bc": ProcessConnection(id="c_bc", source_stage_id="b", target_stage_id="c"),
    }
    return ProcessModel(
        id="proc_linear",
        schema_name="linear",
        stages=stages,
        connections=conns,
        entry_stage_id="a",
        exit_stage_ids=["c"],
    )


def _parallel_process_model() -> ProcessModel:
    """Fan-out from A to (B, C) both feeding D."""
    stages = {
        "a": _make_stage("a", "A", duration=1.0, exit_points=["b", "c"]),
        "b": _make_stage("b", "B", duration=2.0, entry_points=["a"], exit_points=["d"]),
        "c": _make_stage("c", "C", duration=2.0, entry_points=["a"], exit_points=["d"]),
        "d": _make_stage("d", "D", duration=1.5, entry_points=["b", "c"]),
    }
    conns = {
        "c_ab": ProcessConnection(id="c_ab", source_stage_id="a", target_stage_id="b"),
        "c_ac": ProcessConnection(id="c_ac", source_stage_id="a", target_stage_id="c"),
        "c_bd": ProcessConnection(id="c_bd", source_stage_id="b", target_stage_id="d"),
        "c_cd": ProcessConnection(id="c_cd", source_stage_id="c", target_stage_id="d"),
    }
    return ProcessModel(
        id="proc_parallel",
        schema_name="parallel",
        stages=stages,
        connections=conns,
        entry_stage_id="a",
        exit_stage_ids=["d"],
    )


# ---------------------------------------------------------- TimelineBuilder


class TestTimelineBuilderLinear:
    """Linear A -> B -> C chain."""

    def test_build_returns_timeline(self) -> None:
        builder = TimelineBuilder(_linear_process_model())
        timeline = builder.build()
        assert isinstance(timeline, Timeline)
        assert builder.get_timeline() is timeline

    def test_all_stages_created(self) -> None:
        builder = TimelineBuilder(_linear_process_model())
        builder.build()
        assert set(builder.gantt_stages.keys()) == {"a", "b", "c"}
        for gs in builder.gantt_stages.values():
            assert isinstance(gs, GanttStage)

    def test_sequential_timing(self) -> None:
        builder = TimelineBuilder(_linear_process_model())
        builder.build()
        a = builder.gantt_stages["a"]
        b = builder.gantt_stages["b"]
        c = builder.gantt_stages["c"]
        assert a.start_time == pytest.approx(0.0)
        assert b.start_time == pytest.approx(a.start_time + a.duration)
        assert c.start_time == pytest.approx(b.start_time + b.duration)

    def test_total_duration_is_sum(self) -> None:
        builder = TimelineBuilder(_linear_process_model())
        timeline = builder.build()
        # Durations: 1 + 2 + 3 = 6
        assert timeline.total_duration == pytest.approx(6.0)

    def test_critical_path_visits_all_stages(self) -> None:
        builder = TimelineBuilder(_linear_process_model())
        timeline = builder.build()
        assert timeline.critical_path == ["a", "b", "c"]

    def test_critical_stages_marked(self) -> None:
        builder = TimelineBuilder(_linear_process_model())
        builder.build()
        for stage_id in ("a", "b", "c"):
            assert builder.gantt_stages[stage_id].criticality == pytest.approx(1.0)

    def test_no_parallel_groups(self) -> None:
        builder = TimelineBuilder(_linear_process_model())
        timeline = builder.build()
        assert timeline.parallel_groups == []

    def test_get_stage_at_time(self) -> None:
        builder = TimelineBuilder(_linear_process_model())
        builder.build()
        assert builder.get_stage_at_time(0.5) == "a"
        assert builder.get_stage_at_time(1.5) == "b"
        assert builder.get_stage_at_time(4.0) == "c"
        assert builder.get_stage_at_time(100.0) is None

    def test_get_stages_in_range(self) -> None:
        builder = TimelineBuilder(_linear_process_model())
        builder.build()
        # Range [0, 3) should contain a and b
        stages = set(builder.get_stages_in_range(0.0, 3.0))
        assert "a" in stages and "b" in stages
        # Range [3, 6) should contain b (ending at 3) and c
        stages_late = set(builder.get_stages_in_range(3.5, 6.0))
        assert "c" in stages_late

    def test_export_gantt_data(self) -> None:
        builder = TimelineBuilder(_linear_process_model())
        builder.build()
        data = builder.export_gantt_data()
        assert data["total_duration"] == pytest.approx(6.0)
        assert data["critical_path"] == ["a", "b", "c"]
        # stages should be a list of dicts with expected keys
        stage_dicts = {s["id"]: s for s in data["stages"]}
        assert set(stage_dicts.keys()) == {"a", "b", "c"}
        assert stage_dicts["b"]["start"] == pytest.approx(1.0)
        assert stage_dicts["c"]["duration"] == pytest.approx(3.0)


class TestTimelineBuilderParallel:
    """Fan-out / fan-in process."""

    def test_parallel_stages_have_same_start(self) -> None:
        builder = TimelineBuilder(_parallel_process_model())
        builder.build()
        b = builder.gantt_stages["b"]
        c = builder.gantt_stages["c"]
        assert b.start_time == pytest.approx(c.start_time)

    def test_parallel_groups_detected(self) -> None:
        builder = TimelineBuilder(_parallel_process_model())
        timeline = builder.build()
        # At least one group containing {b, c}
        assert timeline.parallel_groups, "Expected at least one parallel group"
        combined = {sid for group in timeline.parallel_groups for sid in group}
        assert "b" in combined and "c" in combined

    def test_fanin_waits_for_longest_branch(self) -> None:
        builder = TimelineBuilder(_parallel_process_model())
        builder.build()
        builder.gantt_stages["a"]
        b = builder.gantt_stages["b"]
        d = builder.gantt_stages["d"]
        # d must start at or after b's end
        assert d.start_time >= b.start_time + b.duration - 1e-9

    def test_critical_path_goes_through_parallel_branch(self) -> None:
        builder = TimelineBuilder(_parallel_process_model())
        timeline = builder.build()
        assert timeline.critical_path[0] == "a"
        assert timeline.critical_path[-1] == "d"
        # The middle of the critical path is one of b / c.
        assert set(timeline.critical_path) & {"b", "c"}

    def test_export_gantt_data_has_parallel_groups(self) -> None:
        builder = TimelineBuilder(_parallel_process_model())
        builder.build()
        data = builder.export_gantt_data()
        assert data["parallel_groups"]


class TestTimelineBuilderEdgeCases:
    def test_export_before_build_returns_empty(self) -> None:
        builder = TimelineBuilder(_linear_process_model())
        # build not yet called
        assert builder.export_gantt_data() == {}
        assert builder.get_timeline() is None

    def test_empty_process_model(self) -> None:
        model = ProcessModel(
            id="empty",
            schema_name="empty",
            stages={},
            connections={},
            entry_stage_id=None,
            exit_stage_ids=[],
        )
        builder = TimelineBuilder(model)
        timeline = builder.build()
        assert timeline.total_duration == 0.0
        assert timeline.critical_path == []
        assert timeline.parallel_groups == []
        assert timeline.stages == []

    def test_dependencies_derived_from_connections_when_entry_points_empty(self) -> None:
        # Build a process model where entry_points are not populated
        # but connections exist — timeline should still sequence correctly.
        stages = {
            "a": _make_stage("a", "A", duration=1.0),
            "b": _make_stage("b", "B", duration=2.0),
        }
        conns = {
            "c_ab": ProcessConnection(id="c_ab", source_stage_id="a", target_stage_id="b"),
        }
        model = ProcessModel(
            id="derived",
            schema_name="derived",
            stages=stages,
            connections=conns,
            entry_stage_id="a",
            exit_stage_ids=["b"],
        )
        builder = TimelineBuilder(model)
        builder.build()
        assert builder.gantt_stages["b"].start_time == pytest.approx(1.0)

    def test_timeline_with_single_stage(self) -> None:
        stages = {"only": _make_stage("only", "Only", duration=4.0)}
        model = ProcessModel(
            id="single",
            schema_name="single",
            stages=stages,
            connections={},
            entry_stage_id="only",
            exit_stage_ids=["only"],
        )
        builder = TimelineBuilder(model)
        timeline = builder.build()
        assert timeline.critical_path == ["only"]
        assert timeline.total_duration == pytest.approx(4.0)


# --------------------------------------------------------- PolicyExtractor


def _policy_graph() -> ProgramGraph:
    """Build a graph with retry, branching and circuit-breaker patterns."""
    builder = ProgramGraphBuilder(repo_uri="test://policies")

    module = builder.add_node(
        kind=NodeKind.MODULE,
        name="svc",
        qualified_name="svc",
        path="svc.py",
        language="python",
    )

    # Retry by metadata
    retry_meta = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="send_with_retries",
        qualified_name="svc.send_with_retries",
        path="svc.py",
        language="python",
        metadata={"max_retries": 4, "backoff_strategy": "linear", "backoff_base": 0.5},
    )
    # Retry by structure: self-call
    retry_struct = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="retry_self_call",
        qualified_name="svc.retry_self_call",
        path="svc.py",
        language="python",
    )
    builder.add_edge(retry_struct.id, retry_struct.id, EdgeKind.CALLS)

    # Branching by name hint
    branch_name = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="route_request",
        qualified_name="svc.route_request",
        path="svc.py",
        language="python",
    )
    # Branching by fan-out structure
    branch_struct = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="handle",
        qualified_name="svc.handle",
        path="svc.py",
        language="python",
    )
    tgt_a = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="handler_a",
        qualified_name="svc.handler_a",
        path="svc.py",
        language="python",
    )
    tgt_b = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="handler_b",
        qualified_name="svc.handler_b",
        path="svc.py",
        language="python",
    )
    builder.add_edge(branch_struct.id, tgt_a.id, EdgeKind.CALLS)
    builder.add_edge(branch_struct.id, tgt_b.id, EdgeKind.CALLS)

    # Circuit breaker by metadata
    cb_meta = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="safe_call",
        qualified_name="svc.safe_call",
        path="svc.py",
        language="python",
        metadata={
            "is_circuit_breaker": True,
            "failure_threshold": 10,
            "success_threshold": 3,
            "timeout": 45.0,
        },
    )
    # Circuit breaker by name
    cb_name = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="circuit_guard",
        qualified_name="svc.circuit_guard",
        path="svc.py",
        language="python",
    )

    # A plain stage that is not a policy at all
    plain = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="just_work",
        qualified_name="svc.just_work",
        path="svc.py",
        language="python",
    )

    # Containment
    for child in (retry_meta, retry_struct, branch_name, branch_struct,
                  tgt_a, tgt_b, cb_meta, cb_name, plain):
        builder.add_edge(module.id, child.id, EdgeKind.CONTAINS)

    return builder.finalize()


class TestPolicyExtractor:
    """Exercise :class:`PolicyExtractor` on a hand-built graph."""

    @pytest.fixture
    def extractor(self) -> PolicyExtractor:
        extractor = PolicyExtractor(_policy_graph())
        extractor.extract()
        return extractor

    def test_extract_returns_dict_structure(self) -> None:
        extractor = PolicyExtractor(_policy_graph())
        policies = extractor.extract()
        assert set(policies.keys()) == {
            "retry_policies",
            "branching_policies",
            "circuit_breaker_policies",
        }

    def test_retry_by_metadata(self, extractor: PolicyExtractor) -> None:
        retry_policies = list(extractor.retry_policies.values())
        # The metadata-driven retry and the structural self-call should both appear
        assert len(retry_policies) >= 2
        {p.stage_id: p for p in retry_policies}
        metadata_policy = next(
            p for p in retry_policies if p.max_attempts == 4
        )
        assert isinstance(metadata_policy, RetryPolicy)
        assert metadata_policy.backoff_strategy == "linear"
        assert metadata_policy.backoff_base == pytest.approx(0.5)

    def test_branching_detection_names_and_fanout(self, extractor: PolicyExtractor) -> None:
        branching = list(extractor.branching_policies.values())
        # At least the name-hit branch (route_request) and the structural
        # fan-out (handle) should be found.
        assert len(branching) >= 2
        for p in branching:
            assert isinstance(p, BranchingPolicy)
        # Fan-out branch should have 2 branches recorded
        fanout_branch = next(p for p in branching if len(p.branches) >= 2)
        assert fanout_branch.default_branch is None

    def test_circuit_breakers_by_metadata_and_name(self, extractor: PolicyExtractor) -> None:
        cbs = list(extractor.circuit_breaker_policies.values())
        assert len(cbs) >= 2
        metadata_cb = next(p for p in cbs if p.failure_threshold == 10)
        assert isinstance(metadata_cb, CircuitBreakerPolicy)
        assert metadata_cb.success_threshold == 3
        assert metadata_cb.timeout == pytest.approx(45.0)

    def test_list_policies_for_stage(self, extractor: PolicyExtractor) -> None:
        retry = next(iter(extractor.retry_policies.values()))
        result = extractor.list_policies_for_stage(retry.stage_id)
        assert retry in result["retry"]
        assert isinstance(result["branching"], list)
        assert isinstance(result["circuit_breaker"], list)

    def test_policy_count(self, extractor: PolicyExtractor) -> None:
        expected = (
            len(extractor.retry_policies)
            + len(extractor.branching_policies)
            + len(extractor.circuit_breaker_policies)
        )
        assert extractor.policy_count() == expected

    def test_getters_return_none_for_missing(self, extractor: PolicyExtractor) -> None:
        assert extractor.get_retry_policy("does-not-exist") is None
        assert extractor.get_branching_policy("does-not-exist") is None
        assert extractor.get_circuit_breaker_policy("does-not-exist") is None

    def test_getters_return_objects_for_known_ids(self, extractor: PolicyExtractor) -> None:
        if extractor.retry_policies:
            pid, pol = next(iter(extractor.retry_policies.items()))
            assert extractor.get_retry_policy(pid) is pol
        if extractor.branching_policies:
            pid, pol = next(iter(extractor.branching_policies.items()))
            assert extractor.get_branching_policy(pid) is pol
        if extractor.circuit_breaker_policies:
            pid, pol = next(iter(extractor.circuit_breaker_policies.items()))
            assert extractor.get_circuit_breaker_policy(pid) is pol

    def test_retry_structural_detection_from_throws_catches(self) -> None:
        """A node with both THROWS and CATCHES edges should be detected
        as retry-shaped even without name/metadata hints."""
        builder = ProgramGraphBuilder(repo_uri="test://retry-struct")
        module = builder.add_node(
            kind=NodeKind.MODULE,
            name="m",
            qualified_name="m",
            path="m.py",
            language="python",
        )
        worker = builder.add_node(
            kind=NodeKind.FUNCTION,
            name="do_work",
            qualified_name="m.do_work",
            path="m.py",
            language="python",
        )
        err = builder.add_node(
            kind=NodeKind.FUNCTION,
            name="error",
            qualified_name="m.error",
            path="m.py",
            language="python",
        )
        builder.add_edge(module.id, worker.id, EdgeKind.CONTAINS)
        builder.add_edge(module.id, err.id, EdgeKind.CONTAINS)
        builder.add_edge(worker.id, err.id, EdgeKind.THROWS)
        builder.add_edge(worker.id, err.id, EdgeKind.CATCHES)

        graph = builder.finalize()
        extractor = PolicyExtractor(graph)
        extractor.extract()
        retry_stage_ids = {p.stage_id for p in extractor.retry_policies.values()}
        assert worker.id in retry_stage_ids


# ---------------------------------------------- timeline + extractor integration


class TestTimelineWithProcessExtractor:
    """Feed the output of :class:`ProcessExtractor` into the timeline
    builder so we verify end-to-end integration, not just dict shapes."""

    @pytest.fixture
    def extracted_model(self) -> ProcessModel:
        builder = ProgramGraphBuilder(repo_uri="test://timeline-integration")
        module = builder.add_node(
            kind=NodeKind.MODULE,
            name="wf",
            qualified_name="wf",
            path="wf.py",
            language="python",
        )
        step1 = builder.add_node(
            kind=NodeKind.FUNCTION,
            name="step1",
            qualified_name="wf.step1",
            path="wf.py",
            language="python",
        )
        step2 = builder.add_node(
            kind=NodeKind.FUNCTION,
            name="step2",
            qualified_name="wf.step2",
            path="wf.py",
            language="python",
        )
        step3 = builder.add_node(
            kind=NodeKind.FUNCTION,
            name="step3",
            qualified_name="wf.step3",
            path="wf.py",
            language="python",
        )
        builder.add_edge(module.id, step1.id, EdgeKind.CONTAINS)
        builder.add_edge(module.id, step2.id, EdgeKind.CONTAINS)
        builder.add_edge(module.id, step3.id, EdgeKind.CONTAINS)
        builder.add_edge(step1.id, step2.id, EdgeKind.CALLS)
        builder.add_edge(step2.id, step3.id, EdgeKind.CALLS)

        graph = builder.finalize()
        extractor = ProcessExtractor(graph, schema_name="wf")
        return extractor.extract()

    def test_timeline_builds_from_extracted_model(self, extracted_model) -> None:
        builder = TimelineBuilder(extracted_model)
        timeline = builder.build()
        assert isinstance(timeline, Timeline)
        # At least as many Gantt stages as ProcessModel stages.
        assert len(timeline.stages) == len(extracted_model.stages)

    def test_timeline_has_positive_duration(self, extracted_model) -> None:
        builder = TimelineBuilder(extracted_model)
        timeline = builder.build()
        assert timeline.total_duration > 0.0
