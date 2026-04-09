# Agents — py/cogant/dynamic

## Owner
Dynamic Analysis

## Responsibilities
TraceIngester parses Chrome DevTools and custom JSON traces, extracts normalized events with timestamps/duration/args, and optionally builds call graphs. CoverageIngester parses coverage.py (SQLite with numbits decoding) and Cobertura (XML), mapping coverage to source spans. enrich_graph() integrates both: loads coverage/trace data, matches to graph nodes by file path and source_range, and annotates with coverage_hits and dynamic CALLS edges.

## Coordination
Input: Optional trace files (JSON) and coverage files (.coverage SQLite or coverage.xml) provided by user. Output: Enriched ProgramGraph with coverage and dynamic execution annotations. Optional layer; pipeline works without it. No configuration.

## How to Extend
Add trace format: implement ingest_<format> method parsing JSON/binary and extracting events. Add coverage format: implement ingest_<format> parsing and returning coverage spans. Modify enrich_graph to handle new annotation types.
