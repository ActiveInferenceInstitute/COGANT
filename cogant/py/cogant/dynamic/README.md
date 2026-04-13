# Dynamic — Runtime Analysis and Coverage Integration

The dynamic module ingests runtime traces and code coverage data, extracting execution-informed facts to enrich the program graph.

## Module Overview

TraceIngester parses runtime trace files and extracts execution sequences. It supports Chrome DevTools JSON trace format (traceEvents array with name, cat, ph, ts, dur, pid, tid, args) and custom trace formats. It computes total duration from timestamps, normalizes events, and optionally builds a call graph from trace events. Returns a list of normalized trace dicts with duration_ms, event count, and optional call_graph.

CoverageIngester parses code coverage data and maps it to source code spans. It supports coverage.py (.coverage SQLite database) and Cobertura (coverage.xml) formats. For coverage.py, it decodes numbits blobs (compressed line number bitmaps) to extract executed lines. For coverage.xml, it parses packages and files with line and branch coverage rates. Returns coverage_data dict with per-file coverage metrics.

enrich_graph is the integration function. It takes a ProgramGraph and paths to coverage and/or trace files, ingests them, and annotates matching graph nodes with coverage_hits (number of covered lines within node) and branch_coverage rates. It also extracts dynamic CALLS edges from trace call graphs and merges them into the graph. Returns the number of nodes enriched.

## API Reference

TraceIngester class with methods:
- ingest_chrome_trace(json_path) — Parse Chrome DevTools trace JSON and return list of trace dicts
- ingest_custom_trace(json_path) — Parse custom JSON trace format (implementation-dependent)
- extract_call_graph() — Extract call sequences from currently ingested traces and return dict

CoverageIngester class with methods:
- ingest_coverage_py(db_path) — Parse coverage.py SQLite database and return coverage data
- ingest_coverage_xml(xml_path) — Parse Cobertura coverage.xml and return coverage data
- map_coverage_to_spans() — Map coverage data to source code spans and return list of span dicts

Function:
- enrich_graph(graph, coverage_path=None, trace_path=None) — Annotate graph nodes with runtime data and return count of nodes enriched

Data classes (implicit from ingest results):
- Trace event dict: name, cat, ph, ts, dur, pid, tid, args, normalized form
- Coverage span dict: file, line_start, line_end, hit_count (per-line execution count or 0/1)
