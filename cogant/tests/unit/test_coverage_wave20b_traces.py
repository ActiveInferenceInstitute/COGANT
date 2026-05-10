"""Wave-20b coverage boost: ``cogant.dynamic.traces`` perf / flamegraph paths.

Targets the lines that the existing ``test_dynamic_traces_cov.py`` skips:

* ``ingest_custom_trace`` chrome dispatch (line 148)
* ``ingest_custom_trace`` perf parser (lines 154-179, 192-244)
* ``ingest_custom_trace`` flamegraph parser (lines 256-285)
* ``ingest_custom_trace`` invalid format
* ``extract_timing`` zero-duration short-circuit (line 432)

Real files only, no mocks. Each parser fixture is a hand-written sample
that mirrors the real-world output of ``perf script`` and Brendan Gregg's
``stackcollapse`` tools.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cogant.dynamic.traces import TraceIngester

# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


def _write_perf_script(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "sample.perf"
    p.write_text(body, encoding="utf-8")
    return p


def _write_folded(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "sample.folded"
    p.write_text(body, encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# ingest_custom_trace dispatch
# --------------------------------------------------------------------------- #


def test_ingest_custom_trace_dispatches_to_chrome(tmp_path: Path) -> None:
    """``format='chrome'`` delegates to ``ingest_chrome_trace``."""
    chrome_path = tmp_path / "trace.json"
    chrome_path.write_text(
        json.dumps(
            {
                "traceEvents": [
                    {"name": "main", "ph": "X", "ts": 100, "dur": 50, "pid": 1, "tid": 1},
                ]
            }
        )
    )
    ingester = TraceIngester()
    result = ingester.ingest_custom_trace(str(chrome_path), "chrome")
    assert result[0]["format"] == "chrome"
    assert len(result[0]["events"]) == 1
    assert result[0]["events"][0]["name"] == "main"


def test_ingest_custom_trace_dispatches_to_chrome_uppercase(tmp_path: Path) -> None:
    """Format string is normalized via ``.lower().strip()``."""
    chrome_path = tmp_path / "trace.json"
    chrome_path.write_text(json.dumps({"traceEvents": []}))
    ingester = TraceIngester()
    # Mixed-case + whitespace should still dispatch
    result = ingester.ingest_custom_trace(str(chrome_path), "  CHROME  ")
    assert result[0]["format"] == "chrome"


def test_ingest_custom_trace_unsupported_format_raises(tmp_path: Path) -> None:
    """Unknown format produces a ValueError with a helpful message."""
    sample = tmp_path / "sample.bin"
    sample.write_text("anything")
    with pytest.raises(ValueError, match="unsupported trace format"):
        TraceIngester().ingest_custom_trace(str(sample), "ftrace")


# --------------------------------------------------------------------------- #
# perf script parser
# --------------------------------------------------------------------------- #


PERF_SAMPLE = """\
myapp 12345/12345 1234.567890: cycles:
\t7fff8a 0x00007fff8a foo+0x10 (/usr/lib/libc.so)
\t7fff8b 0x00007fff8b bar+0x20 (/usr/lib/libc.so)
\t7fff8c 0x00007fff8c main+0x30 (/usr/lib/libc.so)

myapp 12345/12345 1234.567990: cycles:
\t7fff8a 0x00007fff8a foo+0x10 (/usr/lib/libc.so)
\t7fff8c 0x00007fff8c main+0x30 (/usr/lib/libc.so)
"""


def test_ingest_perf_script_parses_two_samples(tmp_path: Path) -> None:
    """Two-sample perf trace produces two leaf-frame X events."""
    perf_path = _write_perf_script(tmp_path, PERF_SAMPLE)
    ingester = TraceIngester()
    result = ingester.ingest_custom_trace(str(perf_path), "perf")
    trace = result[0]
    assert trace["format"] == "perf"
    events = trace["events"]
    assert len(events) == 2
    # First leaf frame is "foo" (top of the stack)
    for evt in events:
        assert evt["name"] == "foo"
        assert evt["ph"] == "X"
        assert evt["cat"] == "perf"
        assert evt["dur"] == 1
        assert evt["pid"] == 12345
        assert evt["tid"] == 12345
        # Stack symbols include all three frames
        assert "stack" in evt["args"]
        assert "main" in evt["args"]["stack"]


def test_ingest_perf_script_uppercase_format(tmp_path: Path) -> None:
    """``format='PERF'`` is case-insensitive."""
    perf_path = _write_perf_script(tmp_path, PERF_SAMPLE)
    result = TraceIngester().ingest_custom_trace(str(perf_path), "PERF")
    assert result[0]["format"] == "perf"
    assert len(result[0]["events"]) == 2


def test_ingest_perf_script_empty_file(tmp_path: Path) -> None:
    """Empty perf file yields zero events and zero duration."""
    perf_path = _write_perf_script(tmp_path, "")
    result = TraceIngester().ingest_custom_trace(str(perf_path), "perf")
    assert result[0]["events"] == []
    assert result[0]["duration_ms"] == 0.0


def test_ingest_perf_script_pure_hex_only_no_fallback(tmp_path: Path) -> None:
    """A frame with only pure-hex tokens (no +0x) yields no symbols.

    The parser scans for ``+0x`` first; if absent, it falls back to the
    first non-pure-hex token in ``parts[1:]``. With only addresses that
    are pure hex, no fallback symbol is found and the sample is dropped.
    """
    # All tokens (after addr) are pure hex digits → no fallback.
    body = "myapp 9/9 0.0: cycles:\n\tdeadbeef cafebabe\n\n"
    perf_path = _write_perf_script(tmp_path, body)
    result = TraceIngester().ingest_custom_trace(str(perf_path), "perf")
    assert result[0]["events"] == []


def test_ingest_perf_script_non_pure_hex_fallback(tmp_path: Path) -> None:
    """A frame without ``+0x`` falls back to the first non-hex token.

    Note: ``0x...`` tokens contain the letter ``x`` which is not a hex
    digit, so they qualify as "non-pure-hex" and are picked up by the
    fallback. The first such token after the leading address wins.
    """
    body = "myapp 7/7 0.0: cycles:\n\tdeadbe my_function (/lib/x.so)\n\n"
    perf_path = _write_perf_script(tmp_path, body)
    result = TraceIngester().ingest_custom_trace(str(perf_path), "perf")
    events = result[0]["events"]
    # Should fall back to "my_function" (first non-pure-hex token after addr).
    assert len(events) == 1
    assert events[0]["name"] == "my_function"


def test_ingest_perf_script_missing_pid_tid(tmp_path: Path) -> None:
    """Header without a pid/tid token still yields an event with pid=tid=0."""
    body = "noprocesstoken cycles:\n\t7fff foo+0x10 (/lib)\n\n"
    perf_path = _write_perf_script(tmp_path, body)
    result = TraceIngester().ingest_custom_trace(str(perf_path), "perf")
    events = result[0]["events"]
    # Sample resolves "foo" as leaf; default pid/tid = 0.
    assert len(events) == 1
    assert events[0]["pid"] == 0
    assert events[0]["tid"] == 0


# --------------------------------------------------------------------------- #
# folded-stack (flamegraph) parser
# --------------------------------------------------------------------------- #


FOLDED_SAMPLE = """\
# this is a comment
main;outer;leaf 3
main;outer;other_leaf 1
main 2
"""


def test_ingest_flamegraph_emits_one_event_per_count(tmp_path: Path) -> None:
    """Each ``count`` becomes one X event for the leaf frame."""
    folded_path = _write_folded(tmp_path, FOLDED_SAMPLE)
    ingester = TraceIngester()
    result = ingester.ingest_custom_trace(str(folded_path), "flamegraph")
    trace = result[0]
    assert trace["format"] == "flamegraph"
    # 3 + 1 + 2 = 6 events
    events = trace["events"]
    assert len(events) == 6
    leaf_names = [e["name"] for e in events]
    # Three "leaf", one "other_leaf", two "main" (single-frame stack)
    assert leaf_names.count("leaf") == 3
    assert leaf_names.count("other_leaf") == 1
    assert leaf_names.count("main") == 2
    # Synthetic ascending timestamps
    assert [e["ts"] for e in events] == [1, 2, 3, 4, 5, 6]
    # All events carry their stack
    for evt in events:
        assert evt["cat"] == "flamegraph"
        assert "stack" in evt["args"]


def test_ingest_flamegraph_skips_invalid_lines(tmp_path: Path) -> None:
    """Lines without a trailing integer count are skipped."""
    body = "main;leaf not_a_number\nempty 0\nfoo;bar 5\n"
    folded_path = _write_folded(tmp_path, body)
    result = TraceIngester().ingest_custom_trace(str(folded_path), "flamegraph")
    events = result[0]["events"]
    # Only "foo;bar 5" produces events; "empty 0" is skipped (count <= 0)
    assert len(events) == 5
    assert all(e["name"] == "bar" for e in events)


def test_ingest_flamegraph_empty_file(tmp_path: Path) -> None:
    """Empty file yields no events."""
    folded_path = _write_folded(tmp_path, "")
    result = TraceIngester().ingest_custom_trace(str(folded_path), "flamegraph")
    assert result[0]["events"] == []
    assert result[0]["duration_ms"] == 0.0


def test_ingest_flamegraph_skips_blank_frames(tmp_path: Path) -> None:
    """A line whose stack collapses to all-empty frames is dropped."""
    # Four trailing semicolons strip to an empty frames list.
    body = ";;;; 4\n"
    folded_path = _write_folded(tmp_path, body)
    result = TraceIngester().ingest_custom_trace(str(folded_path), "flamegraph")
    assert result[0]["events"] == []


# --------------------------------------------------------------------------- #
# missing custom-format files raise
# --------------------------------------------------------------------------- #


def test_ingest_perf_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        TraceIngester().ingest_custom_trace(str(tmp_path / "nope.perf"), "perf")


def test_ingest_flamegraph_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        TraceIngester().ingest_custom_trace(str(tmp_path / "nope.folded"), "flamegraph")


# --------------------------------------------------------------------------- #
# extract_timing edge case: durations dict with empty bucket
# --------------------------------------------------------------------------- #


def test_extract_timing_skips_empty_durations_bucket(tmp_path: Path) -> None:
    """Functions with no durations are skipped (line 432).

    A function name only appears in ``durations`` when an X event or a
    matched B/E pair contributes a duration. We assert the skip clause
    doesn't crash and that all returned entries have a non-empty count.
    """
    # Mix of B (no matching E), unmatched E (no matching B), and X events.
    # The unmatched B leaves an event on the per-thread stack but doesn't
    # contribute to durations[]; the X event does.
    chrome_path = tmp_path / "trace.json"
    chrome_path.write_text(
        json.dumps(
            {
                "traceEvents": [
                    {"name": "leaked_begin", "ph": "B", "ts": 10, "pid": 1, "tid": 1},
                    {"name": "complete_only", "ph": "X", "ts": 20, "dur": 5, "pid": 1, "tid": 1},
                ]
            }
        )
    )
    ingester = TraceIngester()
    ingester.ingest_chrome_trace(str(chrome_path))
    timing = ingester.extract_timing()
    # Only complete_only has a duration — leaked_begin is on the stack
    # but never popped, so it doesn't enter the durations dict.
    assert "complete_only" in timing
    assert timing["complete_only"]["count"] == 1.0
    # Every entry returned has a real positive count
    for stats in timing.values():
        assert stats["count"] > 0


def test_perf_trace_drives_call_sequences(tmp_path: Path) -> None:
    """A perf trace plugs into the same call-sequence machinery as Chrome.

    Cross-check that ingest_custom_trace(perf) populates self.traces such
    that downstream extract_call_sequences() / extract_timing() work.
    """
    perf_path = _write_perf_script(tmp_path, PERF_SAMPLE)
    ingester = TraceIngester()
    ingester.ingest_custom_trace(str(perf_path), "perf")
    sequences = ingester.extract_call_sequences()
    # Each X event becomes a single-name entry in its thread's sequence.
    # Both samples are pid=tid=12345, so they share one sequence.
    assert len(sequences) == 1
    assert sequences[0] == ["foo", "foo"]
    # Timing pulls dur from each X event
    timing = ingester.extract_timing()
    assert "foo" in timing
    assert timing["foo"]["count"] == 2.0
