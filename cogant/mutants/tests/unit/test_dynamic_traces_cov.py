"""Behavioral tests for cogant.dynamic.traces.TraceIngester.

Feeds the ingester real Chrome DevTools trace JSON and exercises every
public method.
"""

from __future__ import annotations

import json
from pathlib import Path

from cogant.dynamic.traces import TraceIngester

# --------------------------- fixtures ----------------------------------- #


def _write_chrome_trace(tmp_path: Path, events: list[dict]) -> str:
    """Write a Chrome trace JSON with the standard wrapper."""
    path = tmp_path / "trace.json"
    path.write_text(json.dumps({"traceEvents": events}))
    return str(path)


def _sample_events() -> list[dict]:
    """Return a representative event stream:
      t=0: B main (pid=1,tid=1)
      t=100: B helper
      t=150: E helper (helper took 50us)
      t=200: X complete_fn dur=25
      t=300: E main (main took 300us)
    """
    return [
        {"name": "main", "ph": "B", "ts": 0, "pid": 1, "tid": 1},
        {"name": "helper", "ph": "B", "ts": 100, "pid": 1, "tid": 1},
        {"name": "helper", "ph": "E", "ts": 150, "pid": 1, "tid": 1},
        {"name": "complete_fn", "ph": "X", "ts": 200, "dur": 25, "pid": 1, "tid": 1},
        {"name": "main", "ph": "E", "ts": 300, "pid": 1, "tid": 1},
    ]


# --------------------------- ingest_chrome_trace ------------------------ #


def test_ingest_chrome_trace_wrapped_format(tmp_path):
    """Wrapped Chrome trace format is parsed into normalized events."""
    path = _write_chrome_trace(tmp_path, _sample_events())
    ingester = TraceIngester()
    result = ingester.ingest_chrome_trace(path)

    assert len(result) == 1
    trace = result[0]
    assert trace["format"] == "chrome"
    assert len(trace["events"]) == 5
    assert trace["duration_ms"] > 0


def test_ingest_chrome_trace_bare_list_format(tmp_path):
    """A bare-list Chrome trace (no {traceEvents: ...} wrapper) also works."""
    path = tmp_path / "bare.json"
    path.write_text(json.dumps(_sample_events()))
    result = TraceIngester().ingest_chrome_trace(str(path))
    assert result[0]["events"]
    assert len(result[0]["events"]) == 5


def test_ingest_chrome_trace_missing_file_returns_empty_trace(tmp_path):
    """A missing trace path produces an empty-events placeholder."""
    ingester = TraceIngester()
    result = ingester.ingest_chrome_trace(str(tmp_path / "nope.json"))
    assert result[0]["events"] == []
    assert result[0]["duration_ms"] == 0


def test_ingest_chrome_trace_malformed_json_returns_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json")
    result = TraceIngester().ingest_chrome_trace(str(path))
    assert result[0]["events"] == []


def test_ingest_chrome_trace_unexpected_format_returns_empty(tmp_path):
    """A JSON number at the top level is not recognized and logs a warning."""
    path = tmp_path / "weird.json"
    path.write_text("42")
    result = TraceIngester().ingest_chrome_trace(str(path))
    assert result[0]["events"] == []


def test_ingest_chrome_trace_filters_non_dict_entries(tmp_path):
    """Non-dict entries in the events list are silently dropped."""
    path = tmp_path / "mixed.json"
    path.write_text(
        json.dumps({"traceEvents": [{"name": "ok", "ph": "X"}, "not-a-dict", 42]})
    )
    result = TraceIngester().ingest_chrome_trace(str(path))
    assert len(result[0]["events"]) == 1
    assert result[0]["events"][0]["name"] == "ok"


# --------------------------- ingest_custom_trace ------------------------ #


def test_ingest_custom_trace_returns_placeholder(tmp_path):
    """Custom trace parser is currently a placeholder."""
    ingester = TraceIngester()
    result = ingester.ingest_custom_trace(str(tmp_path / "foo.perf"), "perf")
    assert result[0]["format"] == "perf"
    assert result[0]["events"] == []


# --------------------------- extract_call_sequences --------------------- #


def test_extract_call_sequences_from_bemix(tmp_path):
    """B/E pairs and X events both contribute to the call sequence."""
    path = _write_chrome_trace(tmp_path, _sample_events())
    ingester = TraceIngester()
    ingester.ingest_chrome_trace(path)
    sequences = ingester.extract_call_sequences()
    assert len(sequences) == 1
    # main -> helper -> complete_fn
    seq = sequences[0]
    assert "main" in seq
    assert "helper" in seq
    assert "complete_fn" in seq


def test_extract_call_sequences_empty_when_no_traces():
    """No traces means no sequences."""
    assert TraceIngester().extract_call_sequences() == []


# --------------------------- extract_call_graph ------------------------- #


def test_extract_call_graph_captures_parent_child(tmp_path):
    """A nested B/E pair registers the caller -> callee edge."""
    path = _write_chrome_trace(tmp_path, _sample_events())
    ingester = TraceIngester()
    ingester.ingest_chrome_trace(path)
    graph = ingester.extract_call_graph()
    # 'main' is on the stack when 'helper' and 'complete_fn' are seen
    assert "main" in graph
    assert "helper" in graph["main"]
    assert "complete_fn" in graph["main"]


# --------------------------- extract_timing ----------------------------- #


def test_extract_timing_from_bemix_pairs(tmp_path):
    """Timing extracts per-function mean/min/max/count."""
    path = _write_chrome_trace(tmp_path, _sample_events())
    ingester = TraceIngester()
    ingester.ingest_chrome_trace(path)
    timing = ingester.extract_timing()
    assert "helper" in timing
    # 150 - 100 = 50us = 0.05ms
    assert timing["helper"]["mean"] > 0
    assert timing["helper"]["count"] == 1.0
    assert "complete_fn" in timing
    # X event with dur=25 → 0.025ms
    assert timing["complete_fn"]["mean"] > 0


# --------------------------- extract_hot_paths -------------------------- #


def test_extract_hot_paths_returns_requested_count(tmp_path):
    """hot_paths respects the count cap."""
    path = _write_chrome_trace(tmp_path, _sample_events())
    ingester = TraceIngester()
    ingester.ingest_chrome_trace(path)
    hot = ingester.extract_hot_paths(count=5)
    assert len(hot) <= 5
    assert all(isinstance(path_seq, list) for path_seq, _ in hot)


# --------------------------- summary / queries -------------------------- #


def test_get_trace_summary_reports_counts(tmp_path):
    path = _write_chrome_trace(tmp_path, _sample_events())
    ingester = TraceIngester()
    ingester.ingest_chrome_trace(path)
    ingester.extract_call_graph()
    summary = ingester.get_trace_summary()
    assert summary["trace_count"] == 1
    assert summary["total_events"] == 5
    assert summary["call_graph_size"] >= 1


def test_get_function_calls_returns_matching_events(tmp_path):
    """Calls to a specific function are located by name + B/X phase."""
    path = _write_chrome_trace(tmp_path, _sample_events())
    ingester = TraceIngester()
    ingester.ingest_chrome_trace(path)
    helper_calls = ingester.get_function_calls("helper")
    assert len(helper_calls) == 1
    assert helper_calls[0]["name"] == "helper"


def test_get_caller_and_callee_lookups(tmp_path):
    """Caller and callee lookups derive from the extracted graph."""
    path = _write_chrome_trace(tmp_path, _sample_events())
    ingester = TraceIngester()
    ingester.ingest_chrome_trace(path)
    # get_caller_functions lazily builds the graph
    callers = ingester.get_caller_functions("helper")
    assert "main" in callers
    # callee lookup uses the populated graph
    callees = ingester.get_callee_functions("main")
    assert "helper" in callees
    assert "complete_fn" in callees
    # Unknown function returns an empty list
    assert ingester.get_callee_functions("nope") == []
