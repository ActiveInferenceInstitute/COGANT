"""Wave-20 coverage boost: cogant.statespace.temporal.

Drives ``TemporalAnalyzer`` end-to-end with real ``ProgramGraph``
fixtures hand-built from ``Node`` / ``Edge`` dataclasses (no mocks).

Coverage targets in ``py/cogant/statespace/temporal.py``:
  * Async detection by metadata flag (line 129) and event detection by
    NodeKind / metadata (149, 154).
  * Parallel-edge ordering branch (195-196) and parallel-edge counter
    (266) inside ``_compute_metrics``.
  * Event-pattern construction with handlers / triggers (227-243).
  * Loop detection edge cases — dangling edges (319, 321).
  * HYBRID regime when events + async coexist (347-350).
  * ``get_critical_path`` dangling-edge guard (425) and entry filter (413).
  * ``get_markov_order`` (451-456).
  * ``find_feedback_loops`` cycle path (473-508).
  * ``to_mermaid`` happy path + the empty-graph fallback (527-547).
"""

from __future__ import annotations

import pytest

from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.statespace.temporal import (
    EventPattern,
    TemporalAnalyzer,
    TemporalMetrics,
    TemporalOrdering,
    TimeRegime,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers — real graphs, no mocks
# ---------------------------------------------------------------------------


def _empty_graph() -> ProgramGraph:
    return ProgramGraph(metadata=GraphMetadata(repo_uri="test://empty"))


def _node(
    nid: str,
    *,
    name: str | None = None,
    kind: NodeKind = NodeKind.FUNCTION,
    metadata: dict | None = None,
) -> Node:
    return Node(
        id=nid,
        kind=kind,
        name=name or nid,
        qualified_name=name or nid,
        metadata=metadata or {},
    )


def _edge(
    eid: str,
    src: str,
    tgt: str,
    *,
    kind: EdgeKind = EdgeKind.CALLS,
    weight: float = 1.0,
) -> Edge:
    return Edge(id=eid, source_id=src, target_id=tgt, kind=kind, weight=weight)


# ---------------------------------------------------------------------------
# Async / event detection branches
# ---------------------------------------------------------------------------


class TestAsyncDetection:
    def test_metadata_async_flag_detected(self) -> None:
        # Covers line 129 (metadata.get('is_async') / .get('async') branch).
        g = _empty_graph()
        g.add_node(_node("a", metadata={"async": True}))
        g.add_node(_node("b", metadata={"is_async": True}))
        g.add_node(_node("c", name="run_async"))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        assert analyzer.metrics is not None
        assert analyzer.metrics.async_fraction == pytest.approx(1.0)

    def test_async_name_pattern_detected(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a", name="callback_handler"))
        g.add_node(_node("b", name="future_thing"))
        g.add_node(_node("c", name="promise_x"))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        # All three names contain async patterns.
        assert analyzer.metrics is not None
        assert analyzer.metrics.async_fraction == pytest.approx(1.0)


class TestEventDetection:
    def test_event_node_kind_detected(self) -> None:
        # Covers line 149 (NodeKind.EVENT branch).
        g = _empty_graph()
        g.add_node(_node("evt", kind=NodeKind.EVENT, name="evt"))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        assert analyzer.metrics is not None
        assert analyzer.metrics.has_event_triggers

    def test_event_metadata_flag_detected(self) -> None:
        # Covers line 154 (metadata.get('is_event') / .get('event') branch).
        g = _empty_graph()
        g.add_node(_node("e", metadata={"is_event": True}))
        g.add_node(_node("f", metadata={"event": True}))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        assert analyzer.metrics is not None
        assert analyzer.metrics.has_event_triggers

    def test_event_name_pattern_detected(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a", name="event_bus"))
        g.add_node(_node("b", name="my_listener"))
        g.add_node(_node("c", name="trigger_func"))
        g.add_node(_node("d", name="evt_handler"))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        assert analyzer.metrics is not None
        assert analyzer.metrics.has_event_triggers


# ---------------------------------------------------------------------------
# Ordering — parallel branch (lines 195-196)
# ---------------------------------------------------------------------------


class TestOrderings:
    def test_async_endpoint_yields_parallel_ordering(self) -> None:
        g = _empty_graph()
        g.add_node(_node("caller"))
        g.add_node(_node("worker", metadata={"is_async": True}))
        g.add_edge(_edge("e1", "caller", "worker", kind=EdgeKind.CALLS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        orderings = analyzer.get_ordering_constraints()
        assert len(orderings) == 1
        assert orderings[0].constraint_type == "parallel"
        assert orderings[0].confidence == pytest.approx(0.7)

    def test_sync_edge_yields_sequential_ordering(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_edge(_edge("e1", "a", "b", kind=EdgeKind.CALLS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        orderings = analyzer.get_ordering_constraints()
        assert len(orderings) == 1
        assert orderings[0].constraint_type == "sequential"
        assert orderings[0].confidence == pytest.approx(0.95)

    def test_non_calls_triggers_edges_skipped(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_edge(_edge("e1", "a", "b", kind=EdgeKind.READS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        assert analyzer.get_ordering_constraints() == []


# ---------------------------------------------------------------------------
# Event patterns (lines 227-243)
# ---------------------------------------------------------------------------


class TestEventPatterns:
    def test_event_with_triggers_and_handlers(self) -> None:
        g = _empty_graph()
        # Use names that don't trigger event-pattern detection.
        g.add_node(_node("src1", name="produce_a"))
        g.add_node(_node("src2", name="produce_b"))
        g.add_node(_node("ev", kind=NodeKind.EVENT, name="ev"))
        g.add_node(_node("dst1", name="consume_x"))
        # Triggers point INTO the event; handlers point OUT.
        g.add_edge(_edge("t1", "src1", "ev", kind=EdgeKind.TRIGGERS))
        g.add_edge(_edge("t2", "src2", "ev", kind=EdgeKind.TRIGGERS))
        g.add_edge(_edge("h1", "ev", "dst1", kind=EdgeKind.TRIGGERS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        patterns = analyzer.get_event_patterns()
        # Only the EVENT-kind node 'ev' is detected as event; others are plain
        # functions and so produce no pattern.
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.event_node_id == "ev"
        assert set(pattern.trigger_nodes) == {"src1", "src2"}
        assert pattern.handler_nodes == ["dst1"]
        # ASYNC_HANDLER kind is not present in the schema → is_async is False.
        assert pattern.is_async is False

    def test_event_with_only_handlers_creates_pattern(self) -> None:
        g = _empty_graph()
        g.add_node(_node("ev", kind=NodeKind.EVENT, name="ev"))
        g.add_node(_node("dst", name="consume"))
        g.add_edge(_edge("h", "ev", "dst", kind=EdgeKind.TRIGGERS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        assert len(analyzer.get_event_patterns()) == 1

    def test_event_with_no_links_creates_no_pattern(self) -> None:
        g = _empty_graph()
        g.add_node(_node("ev", kind=NodeKind.EVENT, name="ev"))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        # Lone event with no edges — no pattern created.
        assert analyzer.get_event_patterns() == []


# ---------------------------------------------------------------------------
# Compute metrics — parallel edge counter (line 266)
# ---------------------------------------------------------------------------


class TestComputeMetrics:
    def test_parallel_edge_counter_increments_for_async_endpoints(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a", metadata={"is_async": True}))
        g.add_node(_node("b"))
        g.add_node(_node("c"))
        g.add_edge(_edge("e1", "a", "b", kind=EdgeKind.CALLS))
        g.add_edge(_edge("e2", "b", "c", kind=EdgeKind.CALLS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        assert analyzer.metrics is not None
        assert analyzer.metrics.parallel_edges_count == 1  # e1 has async endpoint
        assert analyzer.metrics.sequential_edges_count == 1  # e2 is fully sync

    def test_empty_graph_yields_zero_fractions(self) -> None:
        analyzer = TemporalAnalyzer(_empty_graph())
        analyzer.analyze()
        assert analyzer.metrics is not None
        assert analyzer.metrics.async_fraction == 0.0
        assert analyzer.metrics.event_driven_fraction == 0.0


# ---------------------------------------------------------------------------
# Loop detection edge cases (lines 319, 321)
# ---------------------------------------------------------------------------


class TestLoopDetection:
    def test_dangling_edge_does_not_crash(self) -> None:
        # Edge target_id refers to a node that doesn't exist in graph.nodes.
        # In ProgramGraph.add_edge this is rejected unless we hack the dict
        # directly — bypass the validation to drive the dangling branch.
        g = _empty_graph()
        g.add_node(_node("a"))
        # Inject a dangling edge directly into the dict.
        dangling = Edge(
            id="dangle", source_id="a", target_id="ghost", kind=EdgeKind.CALLS
        )
        g.edges["dangle"] = dangling
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        # Loop detection should swallow the dangling edge without raising.
        assert analyzer.metrics is not None
        assert analyzer.metrics.has_loops is False

    def test_simple_cycle_detected(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_edge(_edge("e1", "a", "b", kind=EdgeKind.CALLS))
        g.add_edge(_edge("e2", "b", "a", kind=EdgeKind.CALLS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        assert analyzer.metrics is not None
        assert analyzer.metrics.has_loops is True

    def test_no_cycle_when_dag(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_node(_node("c"))
        g.add_edge(_edge("e1", "a", "b", kind=EdgeKind.CALLS))
        g.add_edge(_edge("e2", "b", "c", kind=EdgeKind.CALLS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        assert analyzer.metrics is not None
        assert analyzer.metrics.has_loops is False


# ---------------------------------------------------------------------------
# Regime determination — HYBRID branch (lines 347-350)
# ---------------------------------------------------------------------------


class TestRegimeDetermination:
    def test_hybrid_when_events_and_async_present(self) -> None:
        g = _empty_graph()
        g.add_node(_node("async1", metadata={"is_async": True}))
        g.add_node(_node("evt", kind=NodeKind.EVENT))
        g.add_node(_node("handler"))
        g.add_edge(_edge("h", "evt", "handler", kind=EdgeKind.TRIGGERS))
        analyzer = TemporalAnalyzer(g)
        regime = analyzer.analyze()
        assert regime is TimeRegime.HYBRID

    def test_event_driven_when_only_events(self) -> None:
        g = _empty_graph()
        g.add_node(_node("evt", kind=NodeKind.EVENT))
        g.add_node(_node("handler"))
        g.add_edge(_edge("h", "evt", "handler", kind=EdgeKind.TRIGGERS))
        analyzer = TemporalAnalyzer(g)
        regime = analyzer.analyze()
        assert regime is TimeRegime.EVENT_DRIVEN

    def test_asynchronous_when_high_async_fraction(self) -> None:
        # 2/3 async > 0.3 threshold.
        g = _empty_graph()
        g.add_node(_node("a", metadata={"is_async": True}))
        g.add_node(_node("b", metadata={"is_async": True}))
        g.add_node(_node("c"))
        analyzer = TemporalAnalyzer(g)
        regime = analyzer.analyze()
        assert regime is TimeRegime.ASYNCHRONOUS

    def test_synchronous_default(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        analyzer = TemporalAnalyzer(g)
        regime = analyzer.analyze()
        assert regime is TimeRegime.SYNCHRONOUS


# ---------------------------------------------------------------------------
# Critical path — dangling edge guard (lines 413, 425)
# ---------------------------------------------------------------------------


class TestCriticalPath:
    def test_critical_path_walks_outgoing_edges(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_node(_node("c"))
        g.add_edge(_edge("e1", "a", "b", weight=1.0))
        g.add_edge(_edge("e2", "b", "c", weight=2.0))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        path = analyzer.get_critical_path()
        # 'a' is the only entry (no incoming edges).
        assert path == ["a", "b", "c"]

    def test_critical_path_dangling_edge_terminates(self) -> None:
        # Outgoing edge whose target_id is missing from ``graph.nodes``
        # → covers the dangling guard at line 425.
        g = _empty_graph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_edge(_edge("e1", "a", "b"))
        # Inject dangling edge bypassing validation.
        g.edges["e2"] = Edge(
            id="e2", source_id="b", target_id="ghost", kind=EdgeKind.CALLS, weight=99.0
        )
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        path = analyzer.get_critical_path()
        # Must stop at b — the dangling target is unreachable.
        assert path[0] == "a"
        assert "ghost" not in path

    def test_critical_path_with_cycle_terminates(self) -> None:
        # Cycle hits the visited guard at line 413.
        g = _empty_graph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_edge(_edge("e1", "a", "b"))
        g.add_edge(_edge("e2", "b", "a"))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        # No entry node (every node has an incoming edge).
        path = analyzer.get_critical_path()
        assert isinstance(path, list)

    def test_critical_path_revisit_guard_two_entries_share_target(self) -> None:
        # Two entries (a, x) both flow into 'b'. The second DFS run starts
        # at 'x', walks into 'b' which is already in ``visited`` from the
        # first run → covers the visited-set guard at line 413.
        g = _empty_graph()
        g.add_node(_node("a"))
        g.add_node(_node("x"))
        g.add_node(_node("b"))
        g.add_node(_node("c"))
        g.add_edge(_edge("e1", "a", "b", weight=1.0))
        g.add_edge(_edge("e2", "b", "c", weight=1.0))
        g.add_edge(_edge("e3", "x", "b", weight=2.0))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        path = analyzer.get_critical_path()
        # Whichever entry runs first records ['<entry>', 'b', 'c'];
        # the second entry's DFS hits 'b' in visited and returns early.
        assert "b" in path
        assert "c" in path


# ---------------------------------------------------------------------------
# Markov order (lines 451-456)
# ---------------------------------------------------------------------------


class TestMarkovOrder:
    def test_markov_order_chain_length_minus_one(self) -> None:
        g = _empty_graph()
        for nid in ("a", "b", "c", "d"):
            g.add_node(_node(nid))
        g.add_edge(_edge("e1", "a", "b"))
        g.add_edge(_edge("e2", "b", "c"))
        g.add_edge(_edge("e3", "c", "d"))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        order = analyzer.get_markov_order()
        assert order == 3  # 4-node chain → max(1, 4-1) = 3

    def test_markov_order_at_least_one(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a"))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        # Single-node graph → max(1, 1-1) = 1.
        assert analyzer.get_markov_order() == 1


# ---------------------------------------------------------------------------
# Feedback loops (lines 473-508)
# ---------------------------------------------------------------------------


class TestFeedbackLoops:
    def test_simple_cycle_yields_loop(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_edge(_edge("e1", "a", "b", kind=EdgeKind.CALLS))
        g.add_edge(_edge("e2", "b", "a", kind=EdgeKind.CALLS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        loops = analyzer.find_feedback_loops()
        assert len(loops) >= 1
        # Cycle should contain both nodes.
        flat = {n for loop in loops for n in loop}
        assert {"a", "b"} <= flat

    def test_no_cycle_yields_empty_loops(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a"))
        g.add_node(_node("b"))
        g.add_edge(_edge("e1", "a", "b", kind=EdgeKind.CALLS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        assert analyzer.find_feedback_loops() == []

    def test_data_flow_cycle_detected(self) -> None:
        # Cycle through READS/WRITES edges should also be caught.
        g = _empty_graph()
        g.add_node(_node("v"))
        g.add_node(_node("f"))
        g.add_edge(_edge("e1", "f", "v", kind=EdgeKind.WRITES))
        g.add_edge(_edge("e2", "v", "f", kind=EdgeKind.READS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        loops = analyzer.find_feedback_loops()
        assert len(loops) >= 1


# ---------------------------------------------------------------------------
# Mermaid export (lines 527-547)
# ---------------------------------------------------------------------------


class TestMermaidExport:
    def test_mermaid_renders_nodes_and_edges(self) -> None:
        g = _empty_graph()
        g.add_node(_node("a", name="alpha"))
        g.add_node(_node("b", name="beta"))
        g.add_edge(_edge("e1", "a", "b", kind=EdgeKind.CALLS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        diagram = analyzer.to_mermaid()
        assert diagram.startswith("graph TD")
        assert "alpha" in diagram
        assert "beta" in diagram
        assert "calls" in diagram

    def test_mermaid_empty_graph_uses_placeholder(self) -> None:
        g = _empty_graph()
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        diagram = analyzer.to_mermaid()
        # Empty graph → placeholder text on line 545.
        assert "No dependencies detected" in diagram

    def test_mermaid_truncates_to_node_and_edge_caps(self) -> None:
        # Build > 20 nodes and > 30 edges to force truncation.
        g = _empty_graph()
        for i in range(25):
            g.add_node(_node(f"n{i}", name=f"node{i}"))
        for i in range(33):
            src = f"n{i % 25}"
            tgt = f"n{(i + 1) % 25}"
            g.add_edge(_edge(f"e{i}", src, tgt, kind=EdgeKind.CALLS))
        analyzer = TemporalAnalyzer(g)
        analyzer.analyze()
        diagram = analyzer.to_mermaid()
        # Mermaid header always present; truncation caps don't crash.
        assert diagram.startswith("graph TD")


# ---------------------------------------------------------------------------
# Accessor smoke tests
# ---------------------------------------------------------------------------


class TestAccessors:
    def test_get_metrics_none_before_analyze(self) -> None:
        analyzer = TemporalAnalyzer(_empty_graph())
        # No analyze() call → metrics is None.
        assert analyzer.get_metrics() is None

    def test_get_metrics_returns_metrics_after_analyze(self) -> None:
        analyzer = TemporalAnalyzer(_empty_graph())
        analyzer.analyze()
        metrics = analyzer.get_metrics()
        assert isinstance(metrics, TemporalMetrics)

    def test_get_orderings_default_empty(self) -> None:
        analyzer = TemporalAnalyzer(_empty_graph())
        assert analyzer.get_ordering_constraints() == []

    def test_get_event_patterns_default_empty(self) -> None:
        analyzer = TemporalAnalyzer(_empty_graph())
        assert analyzer.get_event_patterns() == []


# ---------------------------------------------------------------------------
# Dataclass smokes — module-level types
# ---------------------------------------------------------------------------


class TestDataclassSmokes:
    def test_temporal_ordering_construction(self) -> None:
        o = TemporalOrdering(
            predecessor_id="a",
            successor_id="b",
            constraint_type="sequential",
            confidence=0.9,
        )
        assert o.predecessor_id == "a"

    def test_event_pattern_construction(self) -> None:
        p = EventPattern(
            event_node_id="evt",
            trigger_nodes=["t"],
            handler_nodes=["h"],
            is_async=True,
        )
        assert p.is_async is True

    def test_temporal_metrics_construction(self) -> None:
        m = TemporalMetrics(
            async_fraction=0.5,
            event_driven_fraction=0.0,
            parallel_edges_count=1,
            sequential_edges_count=2,
            event_patterns_count=0,
            has_async_handlers=True,
            has_event_triggers=False,
        )
        # Defaults applied.
        assert m.has_loops is False
        assert m.is_discrete is True

    def test_time_regime_str_enum(self) -> None:
        assert TimeRegime.SYNCHRONOUS == "synchronous"
        assert TimeRegime.HYBRID == "hybrid"
