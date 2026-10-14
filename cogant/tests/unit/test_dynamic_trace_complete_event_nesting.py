"""Complete ('X') trace events nest by time containment on the same thread.

In the Chrome Trace Event format an ``X`` event spans ``[ts, ts + dur)``;
an event that starts inside that span on the same pid/tid is its callee.
Tracers such as viztracer, Perfetto exports and torch.profiler emit almost
only ``X`` events, so the call graph must be built from that containment,
not just from ``B``/``E`` pairs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cogant.dynamic.enrichment import enrich_graph
from cogant.dynamic.traces import TraceIngester
from cogant.schemas.core import EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph


def _x(name: str, ts: float, dur: float, tid: int = 1) -> dict[str, object]:
    return {"name": name, "ph": "X", "ts": ts, "dur": dur, "pid": 1, "tid": tid}


def _write_trace(tmp_path: Path, events: list[dict[str, object]]) -> Path:
    path = tmp_path / "trace.json"
    path.write_text(json.dumps({"traceEvents": events}))
    return path


@pytest.mark.unit
def test_contained_complete_event_is_a_callee(tmp_path: Path) -> None:
    """``mul`` [10, 30) inside ``add`` [0, 100) is called by ``add``."""
    ingester = TraceIngester()
    ingester.ingest_chrome_trace(
        str(_write_trace(tmp_path, [_x("add", 5e9, 100), _x("mul", 5e9 + 10, 20)]))
    )

    assert ingester.extract_call_graph() == {"add": ["mul"]}


@pytest.mark.unit
def test_sequential_and_cross_thread_complete_events_are_not_nested(tmp_path: Path) -> None:
    """Events after a span ends, or on another thread, are not its callees."""
    ingester = TraceIngester()
    ingester.ingest_chrome_trace(
        str(
            _write_trace(
                tmp_path,
                [
                    _x("main", 0, 100),
                    _x("load", 10, 20),
                    _x("parse", 15, 5),
                    _x("save", 40, 10),
                    _x("after", 100, 5),
                    _x("worker", 20, 10, tid=2),
                ],
            )
        )
    )

    assert ingester.extract_call_graph() == {"load": ["parse"], "main": ["load", "save"]}


@pytest.mark.unit
def test_complete_events_nest_inside_begin_end_spans(tmp_path: Path) -> None:
    """An ``X`` callee of a ``B``/``E`` span can itself parent another ``X``."""
    ingester = TraceIngester()
    ingester.ingest_chrome_trace(
        str(
            _write_trace(
                tmp_path,
                [
                    {"name": "run", "ph": "B", "ts": 0, "pid": 1, "tid": 1},
                    _x("step", 10, 50),
                    _x("inner", 20, 5),
                    {"name": "run", "ph": "E", "ts": 100, "pid": 1, "tid": 1},
                ],
            )
        )
    )

    assert ingester.extract_call_graph() == {"run": ["step"], "step": ["inner"]}


@pytest.mark.unit
def test_complete_event_trace_adds_dynamic_calls_edge(tmp_path: Path) -> None:
    """enrich_graph adds the CALLS edge observed in an X-only trace."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="test://repo"))
    for node_id in ("add", "mul"):
        graph.add_node(
            Node(id=node_id, kind=NodeKind.FUNCTION, name=node_id, qualified_name=node_id)
        )
    trace = _write_trace(tmp_path, [_x("add", 5e9, 100), _x("mul", 5e9 + 10, 20)])

    enrich_graph(graph, trace_path=str(trace))

    calls = [(e.source_id, e.target_id) for e in graph.edges.values() if e.kind == EdgeKind.CALLS]
    assert calls == [("add", "mul")]
