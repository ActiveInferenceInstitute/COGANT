## Dynamic Enrichment API

The dynamic enrichment API merges coverage and trace data directly onto a `ProgramGraph`, annotating nodes with runtime metadata and inserting observed call edges. It builds on the `CoverageIngester` and `TraceIngester` primitives documented above.

### Standalone Enrichment

```python
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
# summary contains counts of enriched nodes and inserted edges
print(f"Enriched {summary['nodes_enriched']} nodes, added {summary['edges_added']} dynamic edges")
```

Either `coverage_path` or `trace_path` may be omitted to apply only one source of runtime data. Nodes and edges that have no matching coverage or trace data are left unchanged.

### Pipeline Integration

When coverage or trace paths are provided via plugin configuration, the pipeline applies enrichment automatically during the `dynamic` stage:

```python
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

**Dynamic edges** (new edges inserted into the graph):

| Field | Type | Description |
| --- | --- | --- |
| `type` | `str` | Always `"CALLS"` for dynamic call edges |
| `source` / `target` | `str` | Node identifiers for caller and callee |
| `frequency` | `int` | Number of times this call was observed |
| `weight` | `float` | Normalized frequency relative to the hottest edge |

