## Dynamic Enrichment API

The dynamic enrichment API merges coverage and trace data directly onto a `ProgramGraph`, annotating nodes with runtime metadata and inserting observed call edges. It builds on the `CoverageIngester` and `TraceIngester` primitives documented above.

### Standalone Enrichment

```python
# doctest: +SKIP  # example requires runtime context or external resources
from cogant.dynamic import enrich_graph, CoverageIngester, TraceIngester
from cogant.schemas.graph import ProgramGraph

# Load or build a program graph
graph: ProgramGraph = session.build_graph()

# Enrich with coverage and/or trace data
summary = enrich_graph(
    graph,
    coverage_path="coverage.xml",
    trace_path="trace.json",
)
# Summary keys (see ``cogant.dynamic.enrichment.enrich_graph``):
#   - coverage_nodes_enriched: int  -- nodes annotated from the coverage DB
#   - trace_nodes_enriched:    int  -- nodes annotated from the trace JSON
#   - evidence_sources:        list[str]  -- markers added to graph metadata
#                                            (e.g. ``"dynamic_coverage"``,
#                                            ``"dynamic_traces"``)
#   - graph:                   ProgramGraph  -- the same instance, mutated
print(
    f"Enriched coverage={summary['coverage_nodes_enriched']} "
    f"trace={summary['trace_nodes_enriched']} "
    f"sources={summary['evidence_sources']}"
)
```

Either `coverage_path` or `trace_path` may be omitted to apply only one source of runtime data. Nodes and edges that have no matching coverage or trace data are left unchanged.

### Pipeline Integration

When coverage or trace paths are provided via plugin configuration, the pipeline applies enrichment automatically during the `dynamic` stage:

```python
# doctest: +SKIP  # example requires runtime context or external resources
from cogant.api.pipeline import PipelineRunner, PipelineConfig

config = PipelineConfig(
    plugins={
        "dynamic": {
            "coverage_path": "coverage.xml",
            "trace_path": "trace.json",
        }
    },
    output_dir="output/",
)
runner = PipelineRunner()
bundle = runner.run("./my-repo", config)
```

### What Enrichment Adds

**Node metadata** (added to each matched node's `metadata` dict):

| Field | Type | Description |
| --- | --- | --- |
| `coverage_hits` | `int` | Number of times the node's source lines were executed |
| `branch_coverage` | `float` | Fraction of branches covered (0.0 -- 1.0) |
| `call_count` | `int` | Total invocation count observed in traces |
| `avg_duration_ms` | `float` | Mean wall-clock duration per invocation |
| `is_hot_path` | `bool` | `True` if the node appears in a top-N hot path |

**Dynamic edges** (new `Edge` records inserted into `graph.edges`; see `cogant.dynamic.enrichment._enrich_with_traces`):

| Field | Type | Description |
| --- | --- | --- |
| `kind` | `EdgeKind` | Always `EdgeKind.CALLS` for dynamic call edges |
| `source_id` / `target_id` | `str` | Node identifiers for caller and callee |
| `weight` | `float` | Normalized frequency relative to the hottest observed edge |
| `metadata["source"]` | `str` | Always `"dynamic_trace"` |
| `evidence_sources` | `list[str]` | Includes `"dynamic_trace"` (extended on edges that already existed from the static pass) |
