"""TraceIngester: Parse runtime traces and extract call sequences."""

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TraceIngester:
    """
    Parse runtime trace files and extract execution data.

    Supports:
      - Chrome DevTools traces (JSON)
      - Custom trace formats
      - Function call sequences
      - Timing and performance data
    """

    def __init__(self) -> None:
        """Initialize trace ingester."""
        self.traces: list[dict[str, Any]] = []
        self.call_graph: dict[str, list[str]] = {}

    def ingest_chrome_trace(self, json_path: str) -> list[dict[str, Any]]:
        """
        Parse Chrome DevTools trace JSON.

        Args:
            json_path: Path to trace JSON file.

        Returns:
            List of trace events.
        """
        logger.info(f"Parsing Chrome trace from {json_path}")

        path = Path(json_path)
        if not path.exists():
            logger.error(f"Trace file not found: {json_path}")
            self.traces = [
                {
                    "type": "trace",
                    "format": "chrome",
                    "events": [],
                    "duration_ms": 0,
                }
            ]
            return self.traces

        try:
            with open(json_path, encoding="utf-8") as fh:
                raw = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(f"Failed to parse trace file {json_path}: {exc}")
            self.traces = [
                {
                    "type": "trace",
                    "format": "chrome",
                    "events": [],
                    "duration_ms": 0,
                }
            ]
            return self.traces

        # Chrome trace format: either {"traceEvents": [...]} or bare [...]
        if isinstance(raw, dict):
            events = raw.get("traceEvents", [])
        elif isinstance(raw, list):
            events = raw
        else:
            logger.warning(f"Unexpected trace format in {json_path}")
            events = []

        # Normalize events: ensure each has the expected keys
        normalized: list[dict[str, Any]] = []
        for evt in events:
            if not isinstance(evt, dict):
                continue
            normalized.append(
                {
                    "name": evt.get("name", ""),
                    "cat": evt.get("cat", ""),
                    "ph": evt.get("ph", ""),
                    "ts": evt.get("ts", 0),
                    "dur": evt.get("dur", 0),
                    "pid": evt.get("pid", 0),
                    "tid": evt.get("tid", 0),
                    "args": evt.get("args", {}),
                }
            )

        # Compute total duration from event timestamps
        if normalized:
            min_ts = min(e["ts"] for e in normalized)
            max_ts = max(e["ts"] + e.get("dur", 0) for e in normalized)
            duration_ms = (max_ts - min_ts) / 1000.0
        else:
            duration_ms = 0.0

        logger.info(f"Parsed {len(normalized)} trace events, duration={duration_ms:.1f}ms")

        self.traces = [
            {
                "type": "trace",
                "format": "chrome",
                "events": normalized,
                "duration_ms": duration_ms,
            }
        ]

        return self.traces

    def ingest_custom_trace(self, trace_path: str, format: str) -> list[dict[str, Any]]:
        """Parse a non-Chrome runtime trace file.

        Dispatches on ``format``:

        * ``"chrome"`` — delegates to :meth:`ingest_chrome_trace`.
        * ``"perf"`` — Linux ``perf script`` text output, where each
          sample is an indented stack of ``address symbol+offset (dso)``
          lines separated by blank lines (see ``man perf-script``).
          Every leaf-frame symbol becomes one ``"X"`` (complete) event
          with synthetic timestamps.
        * ``"flamegraph"`` — Brendan Gregg "folded stack" format, where
          each line is ``"frame1;frame2;…;leaf <count>"``. Each line
          becomes ``count`` ``"X"`` events for the leaf frame.

        Args:
            trace_path: Filesystem path to the trace file.
            format: One of the formats above.

        Returns:
            ``self.traces``, a single-element list with the parsed
            events normalised to the same shape used by
            :meth:`ingest_chrome_trace`.

        Raises:
            FileNotFoundError: If ``trace_path`` does not exist.
            ValueError: If ``format`` is unknown.
        """
        logger.info(f"Parsing {format} trace from {trace_path}")

        format_key = format.lower().strip()
        if format_key == "chrome":
            return self.ingest_chrome_trace(trace_path)

        path = Path(trace_path)
        if not path.exists():
            raise FileNotFoundError(f"trace file not found: {trace_path}")

        if format_key == "perf":
            events = self._parse_perf_script(path)
        elif format_key == "flamegraph":
            events = self._parse_folded_stacks(path)
        else:
            raise ValueError(
                f"unsupported trace format: {format!r} (supported: chrome, perf, flamegraph)"
            )

        if events:
            duration_ms = (
                max(e["ts"] + e.get("dur", 0) for e in events) - min(e["ts"] for e in events)
            ) / 1000.0
        else:
            duration_ms = 0.0

        self.traces = [
            {
                "type": "trace",
                "format": format_key,
                "events": events,
                "duration_ms": duration_ms,
            }
        ]
        logger.info(f"Parsed {len(events)} {format_key} events from {trace_path}")
        return self.traces

    @staticmethod
    def _parse_perf_script(path: Path) -> list[dict[str, Any]]:
        """Parse ``perf script`` text output into Chrome-style ``X`` events.

        ``perf script`` separates samples with a blank line. The first
        line of each sample carries the comm/pid/tid/timestamp; the
        following lines are indented stack frames whose symbol is the
        second whitespace-separated token. We emit one event per
        sample using the leaf (top) frame's symbol with a 1µs duration
        so downstream timing extraction has stable values.
        """
        events: list[dict[str, Any]] = []
        text = path.read_text(encoding="utf-8", errors="replace")
        ts_counter = 0
        for raw_sample in text.split("\n\n"):
            sample = raw_sample.strip("\n")
            if not sample.strip():
                continue
            lines = sample.splitlines()
            header = lines[0].split()
            pid = tid = 0
            for tok in header:
                if "/" in tok and tok.replace("/", "").isdigit():
                    p, t = tok.split("/", 1)
                    pid, tid = int(p), int(t)
                    break
            stack_symbols: list[str] = []
            for line in lines[1:]:
                stripped = line.strip()
                if not stripped:
                    continue
                parts = stripped.split()
                # Skip leading hex-address tokens; the symbol+offset is
                # the first token containing "+0x" (or, failing that,
                # the first non-pure-hex token after the leading addr).
                sym: str | None = None
                for tok in parts:
                    if "+0x" in tok:
                        sym = tok.split("+", 1)[0]
                        break
                if sym is None:
                    for tok in parts[1:]:
                        if not all(c in "0123456789abcdefABCDEF" for c in tok):
                            sym = tok.split("+", 1)[0].lstrip("(").rstrip(")")
                            break
                if sym:
                    stack_symbols.append(sym)
            if not stack_symbols:
                continue
            leaf = stack_symbols[0]
            ts_counter += 1
            events.append(
                {
                    "name": leaf,
                    "cat": "perf",
                    "ph": "X",
                    "ts": ts_counter,
                    "dur": 1,
                    "pid": pid,
                    "tid": tid,
                    "args": {"stack": stack_symbols},
                }
            )
        return events

    @staticmethod
    def _parse_folded_stacks(path: Path) -> list[dict[str, Any]]:
        """Parse Brendan Gregg folded-stack format into ``X`` events.

        Each non-empty, non-comment line has the shape
        ``frame1;frame2;...;leaf <count>``. We emit ``count`` events
        for the leaf with synthetic ascending timestamps so multiple
        samples of the same leaf show up as multiple calls in
        :meth:`extract_timing`.
        """
        events: list[dict[str, Any]] = []
        ts_counter = 0
        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                stack_part, count_part = line.rsplit(" ", 1)
                count = int(count_part)
            except ValueError:
                continue
            frames = [f for f in stack_part.split(";") if f]
            if not frames or count <= 0:
                continue
            leaf = frames[-1]
            for _ in range(count):
                ts_counter += 1
                events.append(
                    {
                        "name": leaf,
                        "cat": "flamegraph",
                        "ph": "X",
                        "ts": ts_counter,
                        "dur": 1,
                        "pid": 0,
                        "tid": 0,
                        "args": {"stack": frames},
                    }
                )
        return events

    def _all_events(self) -> list[dict[str, Any]]:
        """Collect all events from all ingested traces."""
        events: list[dict[str, Any]] = []
        for trace in self.traces:
            events.extend(trace.get("events", []))
        return events

    def extract_call_sequences(self) -> list[list[str]]:
        """
        Extract function call sequences from traces.

        Returns:
            List of call sequences (each sequence is a list of function names).
        """
        logger.debug("Extracting call sequences from traces")

        sequences: list[list[str]] = []

        # Group events by thread (pid, tid) to track per-thread call stacks
        thread_events: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        for evt in self._all_events():
            ph = evt.get("ph", "")
            if ph in ("B", "E", "X"):
                key = (evt.get("pid", 0), evt.get("tid", 0))
                thread_events[key].append(evt)

        for _thread_key, events in thread_events.items():
            # Sort by timestamp, then B before E for same timestamp
            phase_order = {"B": 0, "X": 1, "E": 2}
            events.sort(key=lambda e: (e["ts"], phase_order.get(e.get("ph", ""), 1)))

            stack: list[str] = []
            sequence: list[str] = []

            for evt in events:
                ph = evt.get("ph", "")
                name = evt.get("name", "")

                if ph == "B":
                    stack.append(name)
                    sequence.append(name)
                elif ph == "E":
                    if stack:
                        stack.pop()
                elif ph == "X":
                    # Complete event: represents both begin and end
                    sequence.append(name)

            if sequence:
                sequences.append(sequence)

        logger.debug(f"Extracted {len(sequences)} call sequences")
        return sequences

    def extract_call_graph(self) -> dict[str, list[str]]:
        """
        Build call graph from traces.

        Returns:
            Dict mapping function names to list of functions they call.
        """
        logger.debug("Extracting call graph from traces")

        # Track caller->callee relationships using adjacency sets
        adjacency: dict[str, set[str]] = defaultdict(set)

        # Group events by thread
        thread_events: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        for evt in self._all_events():
            ph = evt.get("ph", "")
            if ph in ("B", "E", "X"):
                key = (evt.get("pid", 0), evt.get("tid", 0))
                thread_events[key].append(evt)

        for _thread_key, events in thread_events.items():
            phase_order = {"B": 0, "X": 1, "E": 2}
            events.sort(key=lambda e: (e["ts"], phase_order.get(e.get("ph", ""), 1)))

            stack: list[str] = []

            for evt in events:
                ph = evt.get("ph", "")
                name = evt.get("name", "")

                if ph == "B":
                    if stack:
                        adjacency[stack[-1]].add(name)
                    stack.append(name)
                elif ph == "E":
                    if stack:
                        stack.pop()
                elif ph == "X":
                    if stack:
                        adjacency[stack[-1]].add(name)

        self.call_graph = {caller: sorted(callees) for caller, callees in adjacency.items()}

        logger.debug(f"Built call graph with {len(self.call_graph)} callers")
        return self.call_graph

    def extract_timing(self) -> dict[str, dict[str, float]]:
        """
        Extract timing information for functions.

        Returns:
            Dict mapping function names to timing stats (min, max, mean, count).
        """
        logger.debug("Extracting timing data")

        # Collect durations per function name
        durations: dict[str, list[float]] = defaultdict(list)

        # Build duration data from B/E pairs and X events
        thread_stacks: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)

        for evt in self._all_events():
            ph = evt.get("ph", "")
            name = evt.get("name", "")

            if ph == "X":
                # Complete event has explicit duration in microseconds
                dur = evt.get("dur", 0)
                durations[name].append(dur / 1000.0)  # convert to ms
            elif ph in ("B", "E"):
                key = (evt.get("pid", 0), evt.get("tid", 0))
                thread_stacks[key].append(evt)

        # Match B/E pairs per thread
        for _thread_key, events in thread_stacks.items():
            events.sort(key=lambda e: e["ts"])
            stack: list[dict[str, Any]] = []

            for evt in events:
                ph = evt.get("ph", "")
                if ph == "B":
                    stack.append(evt)
                elif ph == "E" and stack:
                    begin_evt = stack.pop()
                    name = begin_evt.get("name", "")
                    dur_us = evt["ts"] - begin_evt["ts"]
                    durations[name].append(dur_us / 1000.0)  # convert to ms

        timing_stats: dict[str, dict[str, float]] = {}
        for name, durs in durations.items():
            if not durs:
                continue
            timing_stats[name] = {
                "min": min(durs),
                "max": max(durs),
                "mean": sum(durs) / len(durs),
                "count": float(len(durs)),
            }

        logger.debug(f"Computed timing for {len(timing_stats)} functions")
        return timing_stats

    def extract_hot_paths(self, count: int = 10) -> list[tuple[list[str], int]]:
        """
        Extract most frequently executed code paths.

        Args:
            count: Number of hot paths to return.

        Returns:
            List of (path, count) tuples.
        """
        logger.debug(f"Extracting {count} hottest paths")

        sequences = self.extract_call_sequences()

        # Count path frequencies using tuple keys for hashability
        path_counts: dict[tuple[str, ...], int] = defaultdict(int)
        for seq in sequences:
            # Use the full sequence as a path
            key = tuple(seq)
            path_counts[key] += 1

            # Also count sub-paths (sliding windows of length 2..len)
            for window_size in range(2, min(len(seq) + 1, 8)):
                for i in range(len(seq) - window_size + 1):
                    sub = tuple(seq[i : i + window_size])
                    path_counts[sub] += 1

        # Sort by frequency descending
        sorted_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)

        result = [(list(path), freq) for path, freq in sorted_paths[:count]]

        logger.debug(f"Found {len(result)} hot paths")
        return result

    def get_trace_summary(self) -> dict[str, Any]:
        """Get summary of trace data."""
        return {
            "trace_count": len(self.traces),
            "total_events": sum(len(t.get("events", [])) for t in self.traces),
            "call_graph_size": len(self.call_graph),
        }

    def get_function_calls(self, function_name: str) -> list[dict[str, Any]]:
        """Get all calls to a specific function."""
        matches: list[dict[str, Any]] = []
        for evt in self._all_events():
            if evt.get("name") == function_name and evt.get("ph") in (
                "B",
                "X",
            ):
                matches.append(evt)
        return matches

    def get_caller_functions(self, function_name: str) -> list[str]:
        """Get list of functions that call the given function."""
        # Ensure call graph is populated
        if not self.call_graph:
            self.extract_call_graph()

        callers: list[str] = []
        for caller, callees in self.call_graph.items():
            if function_name in callees:
                callers.append(caller)
        return sorted(callers)

    def get_callee_functions(self, function_name: str) -> list[str]:
        """Get list of functions called by the given function."""
        return self.call_graph.get(function_name, [])
