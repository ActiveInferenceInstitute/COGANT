# Agents — py/cogant/dynamic

## Owner
Dynamic Analysis / Runtime Instrumentation

## What Is the Dynamic Module

The `dynamic/` module **enriches a ProgramGraph with runtime execution data** by ingesting coverage reports and execution traces. It performs stage 1.5 (optional enrichment) of the 10-stage COGANT pipeline, augmenting static facts with dynamic observations:

- **Coverage data**: Which lines/branches were executed during test runs
- **Execution traces**: Call sequences, timing, performance metrics from Chrome DevTools or custom JSON
- **Call graphs**: Caller-callee edges derived from trace event sequences
- **Dynamic confidence**: Mark nodes and edges as RUNTIME_DYNAMIC vs. STATIC_ONLY

Dynamic analysis is **optional** — the pipeline works without it, producing valid GNN bundles with only static facts. When trace and coverage files are available, the enrichment layer:
1. Parses coverage.py SQLite databases or Cobertura XML
2. Parses Chrome DevTools JSON traces or custom trace formats
3. Maps coverage to graph nodes by file path + source_range (line numbers)
4. Adds dynamic CALLS edges where traces show explicit invocation
5. Annotates nodes with coverage_hits and branch_coverage metadata

## Pipeline Integration

```
stage 1: ingest/        → SourceFile, RepoSnapshot
    ↓
stage 2-3: static/, graph/  → ProgramGraph (nodes + static edges)
    ↓
stage 1.5: dynamic/      → enrich_graph(coverage_path, trace_path) [OPTIONAL]
           ├─ TraceIngester    → Chrome DevTools JSON or custom trace
           ├─ CoverageIngester → coverage.py SQLite or Cobertura XML
           └─ enrichment.py    → Match + annotate nodes with dynamic facts
    ↓
stage 4-10: translate, statespace, export, validate, ...
```

The dynamic module is **non-invasive** — it mutates the graph in-place, adding fields without breaking downstream consumers. Nodes without coverage/trace data simply have empty or None dynamic fields.

## Core Components

### TraceIngester — Parse Execution Traces

**Purpose**: Extract runtime call sequences and performance metrics from trace files.

**Key Methods**:
- **`ingest_chrome_trace(json_path: str) -> list[dict]`**
  - Parse Chrome DevTools trace JSON (format: `{"traceEvents": [...]}` or bare array)
  - Normalize events to {name, cat, ph, ts, dur, pid, tid, args}
  - Compute total trace duration in milliseconds
  - Graceful error handling: malformed JSON returns empty trace, not exception
  - Returns list with single normalized trace dict

- **`ingest_custom_trace(json_path: str) -> list[dict]`**
  - Parse custom JSON trace format with flexible schema
  - Expected fields: function, caller, callee, timestamp, duration
  - Transforms to canonical {source_id, target_id, kind, ts, dur}
  - Builds call_graph dict (caller → [callee, ...])

- **`extract_call_graph() -> dict[str, list[str]]`**
  - Return {function_name: [targets called by function]}
  - Built incrementally during ingestion
  - Used to add dynamic CALLS edges to graph

**Data Model**:
```python
@dataclass
class TraceEvent:
    name: str               # Function or event name
    cat: str               # Category (e.g., "function", "v8", "devtools")
    ph: str                # Phase ('B' begin, 'E' end, 'X' complete)
    ts: float              # Timestamp (microseconds since epoch or arbitrary reference)
    dur: float             # Duration (microseconds)
    pid: int               # Process ID
    tid: int               # Thread ID
    args: dict[str, Any]   # Additional metadata (arguments, return value, etc.)
```

### CoverageIngester — Parse Coverage Reports

**Purpose**: Extract per-file and per-line coverage data and map to graph nodes.

**Key Methods**:
- **`ingest_coverage_py(db_path: str) -> dict[str, Any]`**
  - Parse coverage.py SQLite database (.coverage file, Python built-in)
  - Decode line_bits.numbits bitmap (coverage.py's compression format)
  - Return {file: {lines_covered: [...], lines_missing: [...], branches: {...}}}
  - See `_decode_numbits()` for bitmap decompression (little-endian bit encoding)

- **`ingest_coverage_xml(xml_path: str) -> dict[str, Any]`**
  - Parse Cobertura coverage.xml (JaCoCo, OpenCover, etc.)
  - Extract per-file, per-class, and per-method coverage rates
  - Return {files: [...], summary: {line_rate, branch_rate, lines_valid, lines_covered, ...}}
  - Handles nested <package>, <class>, <line>, <branch> elements

- **`map_coverage_to_spans() -> list[dict]`**
  - Normalize coverage data to canonical spans: [{file, lines_covered, lines_missing, branches, ...}]
  - Used by enrich_graph to match against graph node source_range

**Data Model**:
```python
@dataclass
class CoverageSpan:
    file: str                      # File path (relative or absolute)
    lines_covered: set[int]        # Line numbers that executed
    lines_missing: set[int]        # Line numbers not executed
    branch_coverage: float | None  # 0.0-1.0 or None if no data
    covered_branches: int = 0
    total_branches: int = 0
```

### enrich_graph — Main Enrichment Function

**Purpose**: Orchestrate coverage and trace ingestion, then mutate graph in-place.

**Signature**:
```python
def enrich_graph(
    graph: ProgramGraph,
    coverage_path: str | None = None,
    trace_path: str | None = None,
) -> EnrichmentResult:
    """Enrich graph with runtime data.
    
    Mutates graph in-place:
    - Adds coverage_hits, branch_coverage metadata to matching nodes
    - Adds dynamic CALLS edges from trace call-graph
    - Sets confidence tier to RUNTIME_DYNAMIC for enriched nodes
    
    Returns:
        EnrichmentResult with stats and error list
    """
```

**Enrichment Workflow**:

1. **Coverage enrichment** (`_enrich_with_coverage`):
   - For each coverage span (file + line ranges):
     - Normalize file path (handle ./, backslashes, case-sensitivity)
     - Find all graph nodes whose path matches AND source_range overlaps lines
     - Increment coverage_hits count per node
     - Aggregate branch_coverage if available

2. **Trace enrichment** (`_enrich_with_traces`):
   - Parse trace events and build call_graph dict
   - For each (caller, callee) edge in call_graph:
     - Find graph nodes matching caller and callee by qualified_name
     - Create dynamic CALLS edge (kind = EdgeKind.CALLS_DYNAMIC)
     - Assign stable edge ID based on hash of source + target + kind

3. **Confidence scoring**:
   - Mark enriched nodes as RUNTIME_DYNAMIC (tier 2) vs. STATIC_ONLY (tier 1)
   - Nodes with zero coverage remain STATIC_ONLY
   - Used downstream by `statespace/` to weigh evidence

**Data Structures**:
```python
@dataclass
class EnrichmentResult:
    nodes_enriched: int        # Count of nodes that got coverage/trace data
    edges_added: int           # Count of dynamic CALLS edges added
    coverage_spans_matched: int # Spans that found matching nodes
    trace_calls_matched: int   # Call-graph edges matched to nodes
    errors: list[str]          # Warnings/diagnostics (non-fatal)
    confidence_tier_distribution: dict[str, int]  # {tier: count}
```

### Helper Functions

**`_normalize_path(raw: str) -> str`**
- Strip leading ./, convert backslashes, lowercase (for case-insensitive FS)
- Ensures coverage file paths match graph node paths reliably
- Example: `./my/module.py` → `my/module.py`; `my\module.py` → `my/module.py`

**`_node_spans_line(node, line: int) -> bool`**
- Check if node's source_range covers the given line number
- Handles both {start_line, end_line} and {start: {line}, end: {line}} formats
- Returns False if node has no source_range

**`_stable_edge_id(source_id, target_id, kind) -> str`**
- Generate deterministic edge ID from source + target + kind
- Uses SHA256 hash to ensure consistency across runs
- Prevents duplicate edges if same call appears multiple times in trace

**`_decode_numbits(numbits_blob: bytes) -> list[int]`**
- Decompress coverage.py's line number bitmap
- Each byte encodes 8 line numbers (little-endian bit order)
- Returns sorted list of 1-based line numbers

## Data Representations

All outputs are **immutable after construction**. Paths are `Path` objects; all indices are 1-based line numbers from AST.

### Coverage Data

```python
@dataclass
class CoverageSpan:
    file: str
    lines_covered: set[int]
    lines_missing: set[int]
    branch_coverage: float | None
    covered_branches: int = 0
    total_branches: int = 0

@dataclass
class CoverageData:
    type: str = "coverage"  # e.g. "coverage", "cobertura"
    format: str = "cobertura"
    files: list[dict]
    summary: dict[str, float]  # line_rate, branch_rate, lines_valid, lines_covered, ...
```

### Trace Data

```python
@dataclass
class TraceEvent:
    name: str
    cat: str
    ph: str
    ts: float
    dur: float
    pid: int
    tid: int
    args: dict[str, Any]

@dataclass
class TraceData:
    type: str = "trace"
    format: str = "chrome"  # e.g. "chrome", "custom"
    events: list[dict]
    duration_ms: float
```

### Enrichment Result

```python
@dataclass
class EnrichmentResult:
    nodes_enriched: int
    edges_added: int
    coverage_spans_matched: int
    trace_calls_matched: int
    errors: list[str]
    confidence_tier_distribution: dict[str, int]
```

## Common Usage Patterns

### Enrich with Coverage Only

```python
from cogant.dynamic.enrichment import enrich_graph
from cogant.graph import ProgramGraph

graph = ProgramGraph(...)  # From static + graph pipeline

result = enrich_graph(
    graph,
    coverage_path="/path/to/coverage.xml",
    trace_path=None
)

print(f"Enriched {result.nodes_enriched} nodes")
print(f"Coverage spans matched: {result.coverage_spans_matched}")

# Nodes now have coverage_hits and branch_coverage metadata
for node in graph.nodes.values():
    if hasattr(node, 'coverage_hits') and node.coverage_hits > 0:
        print(f"  {node.name}: {node.coverage_hits} lines covered")
```

### Enrich with Traces Only

```python
from cogant.dynamic.enrichment import enrich_graph

result = enrich_graph(
    graph,
    coverage_path=None,
    trace_path="/path/to/trace.json"
)

print(f"Added {result.edges_added} dynamic CALLS edges")
print(f"Trace calls matched: {result.trace_calls_matched}")

# Graph now has dynamic CALLS edges derived from execution
for edge in graph.edges.values():
    if edge.kind == EdgeKind.CALLS_DYNAMIC:
        print(f"  {edge.source_id} → {edge.target_id} (dynamic)")
```

### Full Enrichment with Both

```python
from cogant.dynamic.enrichment import enrich_graph

result = enrich_graph(
    graph,
    coverage_path="/path/to/.coverage",
    trace_path="/path/to/chrome_trace.json"
)

print(f"Enrichment result:")
print(f"  Nodes enriched: {result.nodes_enriched}")
print(f"  Edges added: {result.edges_added}")
print(f"  Errors: {len(result.errors)}")

if result.errors:
    for err in result.errors:
        logger.warning(f"  {err}")

# Inspect confidence distribution
print(f"Confidence tiers:")
for tier, count in result.confidence_tier_distribution.items():
    print(f"  {tier}: {count} nodes")
```

### Parse Chrome DevTools Trace

```python
from cogant.dynamic.traces import TraceIngester

ingester = TraceIngester()
events = ingester.ingest_chrome_trace("devtools_trace.json")

print(f"Parsed {len(events[0]['events'])} events")
print(f"Duration: {events[0]['duration_ms']:.1f} ms")

# Inspect call graph
call_graph = ingester.extract_call_graph()
for func, targets in call_graph.items():
    print(f"{func} calls: {targets}")
```

### Parse Cobertura Coverage XML

```python
from cogant.dynamic.coverage import CoverageIngester

ingester = CoverageIngester()
coverage_data = ingester.ingest_coverage_xml("coverage.xml")

print(f"Line coverage: {coverage_data['summary']['line_rate']:.1%}")
print(f"Branch coverage: {coverage_data['summary']['branch_rate']:.1%}")

spans = ingester.map_coverage_to_spans()
for span in spans:
    print(f"{span['file']}: {len(span['lines_covered'])} lines covered")
```

## Key Concepts & Design Decisions

### Path Normalization

Coverage tools report paths inconsistently (with or without `./`, backslashes, case variations). The dynamic module normalizes all paths before matching:
- Strip leading `./`
- Convert backslashes to forward slashes
- Lowercase on case-insensitive filesystems (optional)
- Match normalized coverage paths against normalized graph node paths

### Source Range Matching

A coverage line is attributed to a graph node if:
1. Node's file path matches coverage file path (after normalization)
2. Line number falls within node's source_range (start_line ≤ line ≤ end_line)

Multiple nodes may span a single line (e.g., nested functions); all matching nodes are enriched.

### Dynamic Edge Deduplication

The trace ingester may record the same call multiple times (in a loop or across trace segments). The dynamic edge ID function:
- Takes source_id, target_id, kind
- Computes SHA256 hash
- Ensures one edge per (source, target, kind) triple

### Confidence Tiers

Enriched nodes are marked with two-tier confidence:
- **STATIC_ONLY**: Node extracted from AST; no runtime data
- **RUNTIME_DYNAMIC**: Node appeared in coverage or trace during test run

This tier is consumed by `statespace/` to weight evidence when learning matrices (RUNTIME_DYNAMIC gets higher confidence weight).

### Optional Layer Philosophy

Dynamic enrichment is **completely optional**:
- Pipeline produces valid GNN bundles without it
- When files are missing, enrichment gracefully returns early with empty results
- Error messages logged but don't halt pipeline
- Enables "coverage-driven analysis" workflows vs. pure static

## How to Extend

### Add Support for a New Trace Format

1. Implement new `ingest_<format>()` method in `TraceIngester`
2. Parse JSON/binary and extract events with fields: {name, caller, callee, ts, dur, ...}
3. Normalize to canonical TraceEvent format
4. Increment self.call_graph in-place
5. Example:
   ```python
   def ingest_opentelemetry(self, json_path: str) -> list[dict]:
       """Parse OpenTelemetry JSON trace."""
       with open(json_path) as f:
           otel = json.load(f)
       
       normalized = []
       for span in otel.get("resourceSpans", []):
           for event in span.get("instrumentationLibrarySpans", []):
               for sp in event.get("spans", []):
                   normalized.append({
                       "name": sp.get("name"),
                       "ts": sp.get("startTimeUnixNano", 0),
                       "dur": sp.get("endTimeUnixNano", 0) - sp.get("startTimeUnixNano", 0),
                       ...
                   })
       return [{"type": "trace", "format": "opentelemetry", "events": normalized}]
   ```

### Add Support for a New Coverage Format

1. Implement new `ingest_<format>()` method in `CoverageIngester`
2. Parse coverage file (XML, JSON, binary) and extract file-level coverage
3. Return dict with {files: [...], summary: {...}}
4. Implement `map_coverage_to_spans()` if needed (e.g., for branch-level granularity)
5. Example:
   ```python
   def ingest_istanbul(self, json_path: str) -> dict[str, Any]:
       """Parse Istanbul (JS/TS) coverage JSON."""
       with open(json_path) as f:
           data = json.load(f)
       
       files = []
       for file_key, file_data in data.items():
           lines_covered = set()
           for line_num, line_data in file_data["lines"].items():
               if line_data["count"] > 0:
                   lines_covered.add(int(line_num))
           files.append({
               "file": file_key,
               "lines_covered": list(lines_covered),
               ...
           })
       
       return {"type": "coverage", "format": "istanbul", "files": files}
   ```

### Add New Node Annotation

1. Modify `_enrich_with_coverage()` or `_enrich_with_traces()` to compute new metadata
2. Store in node's metadata dict or as direct attribute (if immutability allows)
3. Example: add "execution_count" per node from trace event count
   ```python
   for node in graph.nodes.values():
       if node.qualified_name in trace_exec_counts:
           node.metadata["execution_count"] = trace_exec_counts[node.qualified_name]
   ```

### Filter Enrichment by Criteria

1. Extend enrich_graph to accept filtering parameters (e.g., min_coverage_threshold)
2. Skip enrichment for nodes that don't meet criteria
3. Example:
   ```python
   def enrich_graph(..., min_coverage_threshold: float = 0.0) -> EnrichmentResult:
       ...
       for node in graph.nodes.values():
           if node.coverage_hits >= len(node.source_range) * min_coverage_threshold:
               node.confidence_tier = "RUNTIME_DYNAMIC"
   ```

## Error Handling & Diagnostics

All ingesters follow a consistent pattern:

```python
try:
    data = ingester.ingest_coverage_xml("coverage.xml")
except FileNotFoundError:
    logger.error(f"Coverage file not found")
    return None  # or default empty structure
except Exception as exc:
    logger.warning(f"Failed to parse coverage: {exc}")
    return None  # Fail gracefully
```

**Expected error cases**:
- File not found → log error, return empty structure
- Malformed XML/JSON → log warning, skip record, continue
- Path mismatch → no harm, node simply not enriched
- Missing source_range → node skipped from coverage attribution

## File Map

| File | Purpose |
|------|---------|
| `traces.py` | TraceIngester, Chrome DevTools + custom trace parsing, call graph extraction |
| `coverage.py` | CoverageIngester, coverage.py + Cobertura parsing, numbits decompression |
| `enrichment.py` | enrich_graph orchestrator, path normalization, node/edge matching, enrichment result |
| `__init__.py` | Public API exports (enrich_graph, TraceIngester, CoverageIngester) |
| `traces.pyi` | Type stubs for traces module |
| `coverage.pyi` | Type stubs for coverage module |
| `enrichment.pyi` | Type stubs for enrichment module |

## Integration with Graph & Statespace

After enrichment, the graph is ready for downstream stages:
1. **translate/** — Uses confidence tiers to weigh static edges during translation rule application
2. **statespace/** — Binds evidence from RUNTIME_DYNAMIC edges when compiling A/B/C/D matrices
3. **scoring/** — Factors coverage and execution diversity into bundle quality scores

See `cogant/statespace/` for how confidence tiers influence matrix compilation.

## Known Limitations & Future Work

### Currently Implemented (v0.5.0)
- Coverage.py SQLite and Cobertura XML ingestion
- Chrome DevTools trace parsing
- File + source_range matching
- coverage_hits and branch_coverage annotations

### Planned for v0.7.x (Phase 2)
- Method-level trace data (distinguish static CALLS edges from dynamic ones observed in trace)
- Execution count per node (frequency of invocation)
- Call chain context (caller → target with intermediate calls)
- Dynamic vs. static confidence threshold learning

### Not Planned
- Real-time instrumentation (dynamic rewriting)
- Fuzzing-driven coverage expansion
- Multi-threaded trace correlation

## See Also

- `py/cogant/dynamic/README.md` — module-level overview
- `py/cogant/graph/` — ProgramGraph definition and node/edge types
- `py/cogant/statespace/` — Consumes enriched graph, learns matrix bindings
- `py/cogant/examples/` — Fixtures with coverage and trace data
- COGANT evaluation docs — Coverage metrics and dynamic analysis impact on GNN quality
