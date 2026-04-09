# Examples and Failure Modes

This section walks through a concrete example run of the pipeline on a small Flask application, shows representative fragments of the artifacts it produces (semantic mappings and state-space transitions), and then documents the degradation behavior that users should expect when inputs are missing or partial. Together these illustrate both what a successful run looks like and how the system communicates partial success.

## Example outputs

The package tree includes runnable examples under [`../cogant/examples/`](../cogant/examples/) (for example `control_positive/`, `python-service/`, `workflow-engine/`, and `thin_orchestrated/`) and generated sample outputs under [`../cogant/output/`](../cogant/output/) (for example `roundtrip_calculator/` with `model.gnn.md`, diagrams, and rendered charts). Use `cogant translate --layout-output` or `PipelineConfig(layout_output=True)` to place pipeline JSON under `data/` automatically; run `python -m cogant.tools.render_output_figures` on the output root for PNGs. Regenerate these trees by running the packaged pipeline against the example sources when validating releases.

### Concrete walkthrough: Flask REST API

To make the pipeline's behavior tangible, consider a small Flask application with three HTTP endpoints, two utility modules, and one data-access layer -- 800 lines of Python across 6 files, of which 782 lines are non-blank, non-comment code analyzed by the pipeline. Running `cogant scan ./flask_app && cogant extract-static ./flask_app -o output/ && cogant graph ./flask_app && cogant translate ./flask_app -o output/` on this repository produces a program graph with the following characteristics:

| Metric | Value |
|--------|-------|
| Source files discovered | 6 |
| Lines analyzed | 782 / 800 (97.8%) |
| **Nodes** | **147** |
| **Edges** | **389** |
| Mean node confidence | 0.91 |
| Validation status | PASS (0 errors, 3 warnings) |

The node and edge populations distribute across kinds as follows:

**Table 1. Node kind distribution (Flask API example).**

| Node kind | Count | Percentage |
|-----------|-------|-----------|
| FUNCTION | 38 | 25.9% |
| VARIABLE | 52 | 35.4% |
| TYPE | 11 | 7.5% |
| MODULE | 6 | 4.1% |
| CONTROLFLOW_NODE | 18 | 12.2% |
| DATA_STRUCTURE | 7 | 4.8% |
| ERRORHANDLER | 5 | 3.4% |
| CONSTANT | 6 | 4.1% |
| EXTERNAL | 4 | 2.7% |

**Table 2. Edge kind distribution (Flask API example).**

| Edge kind | Count | Percentage |
|-----------|-------|-----------|
| CALLS | 87 | 22.4% |
| USES | 104 | 26.7% |
| DEFINES | 62 | 15.9% |
| HAS_TYPE | 48 | 12.3% |
| DATA_FLOW | 34 | 8.7% |
| MEMBER_OF | 29 | 7.5% |
| INHERITS | 3 | 0.8% |
| Other | 22 | 5.7% |

### Example semantic mapping output

During the translation stage, each program-graph node is matched against the active rule set and assigned a semantic role with an associated confidence score. The following excerpt shows three representative mappings from the Flask example:

```
Node: get_users  (kind=FUNCTION, file=routes/users.py:14)
  Matched rule: rule_fn_def_001
  Target role:  FUNCTION_DEF
  Confidence:   0.98  (base=1.0, -0.02 missing docstring penalty)
  Provenance:   SourceCode

Node: db.session.query  (kind=FUNCTION, file=routes/users.py:22)
  Matched rule: rule_method_call_001
  Target role:  METHOD_CALL
  Confidence:   0.82  (base=0.90, -0.08 receiver type inferred heuristically)
  Provenance:   Heuristic

Node: User  (kind=TYPE, file=models/user.py:5)
  Matched rule: rule_type_def_001
  Target role:  TYPE_DEF
  Confidence:   1.00
  Provenance:   SourceCode
```

The `db.session.query` call illustrates how the confidence model (Equation \ref{eq:confidence-core} in Section 2) penalizes heuristic provenance: the receiver type of `session` is resolved by import tracing rather than explicit annotation, reducing $\kappa$ below 1.0 and yielding a final confidence of 0.82 in the MEDIUM tier.

### Example state-space excerpt

When dynamic traces are available, the state-space compiler produces a behavioral model alongside the static graph. The following excerpt shows a fragment of the state-space IR for the `/users` endpoint:

```json
{
  "variables": [
    {"name": "request.method", "type": "str", "domain": ["GET", "POST"]},
    {"name": "db_connected",   "type": "bool", "domain": [true, false]},
    {"name": "response_code",  "type": "int",  "domain": [200, 400, 500]}
  ],
  "actions": [
    {"name": "validate_input", "source": "routes/users.py:18"},
    {"name": "query_database",  "source": "routes/users.py:22"},
    {"name": "format_response", "source": "routes/users.py:30"}
  ],
  "transitions": [
    {
      "from_state": {"request.method": "GET", "db_connected": true},
      "action": "query_database",
      "to_state": {"response_code": 200},
      "confidence": 0.94,
      "tier": "STATIC_PLUS_RUNTIME"
    },
    {
      "from_state": {"request.method": "POST", "db_connected": true},
      "action": "validate_input",
      "to_state": {"response_code": 400},
      "confidence": 0.71,
      "tier": "STATIC_ONLY"
    },
    {
      "from_state": {"db_connected": false},
      "action": "query_database",
      "to_state": {"response_code": 500},
      "confidence": 0.58,
      "tier": "RUNTIME_ONLY"
    }
  ]
}
```

Confidence tiers follow the thresholds defined in `determine_confidence_tier`: **STATIC_PLUS_RUNTIME** ($c \geq 0.65$, with both static and dynamic evidence) indicates corroboration from AST analysis and execution traces; **STATIC_ONLY** ($c \geq 0.5$, static evidence only) reflects assertions grounded in source structure alone; **RUNTIME_ONLY** ($c \geq 0.4$, dynamic evidence only) flags inferences from runtime data without static corroboration. A fourth tier, **HUMAN_REVIEWED** ($c \geq 0.9$, with human review evidence), is available for manually curated mappings.

### Failure modes and graceful degradation

COGANT is designed so that missing or partial inputs degrade the output bundle rather than halt it, and the manuscript records these degradation paths explicitly so that downstream consumers can interpret a partial run without guessing what was skipped [@peng2011reproducible]. Five failure modes are worth naming because each has a visible signature in the emitted artifacts.

**No dynamic traces available.** When neither coverage data nor execution traces are supplied, `enrich_graph()` is a no-op: no `coverage_hits`, `branch_coverage`, `call_count`, `avg_duration_ms`, or `is_hot_path` metadata is attached, and the graph's `evidence_sources` list never acquires `dynamic_coverage` or `dynamic_trace` markers. The state-space compiler still runs end-to-end using the semantic mappings and static graph alone, but every resulting transition is confined to the `STATIC_ONLY` tier (or lower), and no transition can be promoted to `STATIC_PLUS_RUNTIME`. Downstream code that consumes the bundle can identify a purely-static run at a glance by checking the evidence source markers on the graph metadata rather than scanning individual transitions.

**Incomplete coverage data.** When coverage is supplied but covers only a subset of the project, `_enrich_with_coverage` annotates the matched files only. The enrichment loop walks each coverage span, normalizes the reported file path, looks up candidate nodes whose path matches, and annotates those whose `source_range` overlaps the covered line; unmatched files are silently skipped with an informational log line, and nodes in unmatched files retain no coverage metadata at all. The result is a partially enriched graph in which some regions are eligible for tier promotion and others are not. Because the enrichment summary returns the number of annotated nodes, users can check whether the observed annotation rate matches their expectations for the provided coverage input.

**Translation rules that do not match.** When the active rule set fails to produce any mapping for a node -- whether because no rule fires, or because all firing rules are pruned during conflict resolution -- that node remains outside `self.mappings` and simply does not appear in any `graph_fragment_node_ids`. The translation engine's `get_coverage_report()` reports this directly: the returned dictionary contains the total node count, the covered count, a two-decimal `coverage_percent`, and the sorted list of `uncovered_node_ids`. Rather than treat uncovered nodes as an error, the engine surfaces them as an explicit gap list so that authors can either extend the rule set, hand the gap list to the `ReviewAPI` for curation, or accept the partial mapping for downstream Generalized Notation Notation (GNN) export.

**Fixpoint non-convergence.** The translation engine bounds its fixpoint loop at `max_iterations = 10` by default. If a rule set is pathological enough to keep emitting new mappings past that bound -- for example because two rules can produce mutually triggering mappings -- the engine emits a `"Max iterations reached without convergence"` warning, stops the loop, and proceeds to conflict resolution with whatever mappings it has accumulated. The iteration cap therefore guarantees termination even for misconfigured rule sets, and the warning in the log gives rule authors a clear signal that the cap was hit. Because each iteration also writes an `iteration_complete` entry into the engine's internal match log, the exact per-pass mapping counts are available for diagnosis without rerunning the pipeline.

**Pipeline error tolerance.** The default pipeline configuration (`cogant/py/cogant/config/defaults.py`) marks the `dynamic`, `translate`, `state_space`, and `process` stages with `skip_on_error=True`, while structural stages such as `ingest`, `static`, `graph`, `export`, and `validate` keep the stricter default `skip_on_error=False`. When an optional stage raises, the runner records the error in the bundle, emits a warning, and continues to the next stage rather than aborting the run. Downstream bundle accessors (`state_space_model`, `process_model`) simply return `None` for stages that did not produce output, so a downstream consumer can detect a skipped stage by checking its accessor rather than by parsing log text. The net effect is that a partial bundle -- for example, a program graph and semantic mappings without a state-space model -- remains a first-class artifact with a clear provenance trail, rather than an opaque failure.

## Rust layer

Native crates (`cogant-core`, `cogant-graph`, `cogant-translate`, `cogant-statespace`, `cogant-gnn`, `cogant-ffi`, and related packages) implement typed graph operations and export formatting. When PyO3 bindings are active, Python delegates heavy graph work through `cogant-ffi`. Where bindings are not yet wired for a code path, Python fallbacks apply; see SPEC **Implementation status** for the current boundary.
