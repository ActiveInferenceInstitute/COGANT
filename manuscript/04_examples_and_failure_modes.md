# Examples and Failure Modes {#sec:04-examples-and-failure-modes}

This section walks through a concrete example run of the pipeline on a small Flask application, shows representative fragments of the artifacts it produces (semantic mappings and state-space transitions), and then documents the degradation behavior that users should expect when inputs are missing or partial. Together these illustrate what a successful run produces, how downstream consumers interpret partial bundles, and the confidence tiers that mark degradation.

## Example outputs

**Intent.** Use the Flask walkthrough to see end-to-end graph and mapping **counts** on a real multi-module app; use `json_stdlib` to see **partial evidence** and validator behaviour; use the YAML/JSON fragments to match **field names** in exported artifacts. The failure-mode subsections document **degradation signatures** in bundles.

The package tree includes runnable examples under [`../cogant/examples/`](../cogant/examples/) (for example `control_positive/`, `python-service/`, `workflow-engine/`, and `thin_orchestrated/`) and generated sample outputs under [`../cogant/output/`](../cogant/output/) (for example `roundtrip_calculator/` with `model.gnn.md`, diagrams, and rendered charts). Use `cogant translate --layout-output` or `PipelineConfig(layout_output=True)` to place pipeline JSON under `data/` automatically; run `python -m cogant.tools.render_output_figures` on the output root for PNGs. Regenerate these trees by running the packaged pipeline against the example sources when validating releases.

### Concrete walkthrough: Flask REST API

**Read this for:** representative node/edge/mapping and GNN validation numbers aligned with the benchmark tables in Section 6.

To make the pipeline's behavior tangible, consider the `flask_app` fixture distributed under `../cogant/examples/real_world/flask_app/`: a small six-module Flask application (`__init__.py`, `app.py`, `config.py`, `models.py`, `services.py`, `utils.py`) totalling 866 lines of Python analyzed end-to-end by the **public** pipeline (`cogant.api.orchestration`, the same code path as `cogant translate` and the benchmark harness). Canonical `flask_app` numbers in `../cogant/evaluation/figures/metrics.json` are produced by `evaluation/figures/generate_figures.py` and match graph size rows in @tbl:benchmark-suite-results. (The `examples/orchestrate_roundtrip.py` demo can emit a larger serialized graph, including a call graph, for dashboard-heavy exports; the manuscript and `metrics.json` stay on the API pipeline so one definition of \(|V|\) and \(|E|\) applies throughout.)

| Metric | Value |
|--------|-------|
| Source files discovered | 6 |
| Lines analyzed | 866 |
| **Nodes** | **98** |
| **Edges** | **154** |
| Total semantic mappings | 72 (`mappings_total` for `flask_app` in `../cogant/evaluation/figures/metrics.json`; same post-`statespace` count as the `mappings` column in @tbl:benchmark-suite-results) |
| GNN package files | 27 |
| GNN validation | PASS (score 100.0, 0 errors, 0 warnings) |

The default graph stage in this path emits structural kinds (MODULE, CLASS, METHOD, FUNCTION) and, at v{{VERSION}}, `CONTAINS`, `INHERITS`, and `self`-dataflow `READS` / `WRITES` edges. The richer taxonomy in `cogant.schemas.core.NodeKind` and `EdgeKind` (18 kinds each; see `../cogant/docs/reference/schemas_reference.md`) also includes `CALLS`, `IMPORTS`, and others: those appear when the call-graph pass is part of the built graph; the **API orchestration** graph used for this table omits `CALLS` and `IMPORTS` so the counts align with the bundle statistics behind @tbl:benchmark-suite-results. Dynamic enrichment (`dynamic/`) can add additional edges when traces are available.

| Node kind | Count | Percentage |
|-----------|-------|-----------|
| MODULE | 6 | 6.1% |
| CLASS | 25 | 25.5% |
| METHOD | 57 | 58.2% |
| FUNCTION | 10 | 10.2% |

: Table 1 — Node kind distribution (Flask API example). {#tbl:flask-api-node-kinds}

| Edge kind | Count | Percentage |
|-----------|-------|-----------|
| CONTAINS | 92 | 59.7% |
| INHERITS | 9 | 5.8% |
| READS | 38 | 24.7% |
| WRITES | 15 | 9.7% |

: Table 2 — Edge kind distribution (Flask API example, `metrics.json`). {#tbl:flask-api-edge-kinds}

`CONTAINS` and inheritance edges dominate the API-built graph. When `CALLS` and `IMPORTS` are present (for example in a full `orchestrate_roundtrip.py` run with call-graph construction), their counts appear in that output’s `program_graph.json` instead; they are not double-counted here. Broadening coverage for optional node and edge kinds is tracked as P1-2 and P1-3 in the R&D backlog (`../cogant/docs/evaluation/SCOPING_REPORT.md`).

### Walkthrough: `json_stdlib` (fallbacks and validator score)

**Read this for:** how the pipeline remains valid with sparse static evidence and identity/default matrix rows (validator notes in the bundle).

The `examples/real_world/json_stdlib/` fixture exercises **partial-evidence** paths without failing validation. In v0.5.0 the expanded `ActionRule` keyword set matches `dump`, `dumps`, `load`, `loads`, and serialisation synonyms; the canonical `metrics.json` entry records `state_variables: 3`, `observations: 1`, `actions: 15`, and `mappings_total: 19`. Of the 15 action slices of $B$, 12 default to the identity tensor (no WRITES edges link those actions to hidden states at the AST extraction granularity), and the single observation row of $A$ is uniform. The pipeline still emits a valid 27-file `gnn_package/` with **validator 100.0/100**: Validation Notes (section 18 of the bundle) list every maximum-entropy entry so downstream consumers can distinguish evidence-backed matrix rows from structural defaults (see [`02_04_gnn_export_and_error_handling.md`](02_04_gnn_export_and_error_handling.md)).

### Example semantic mapping output

**Read this for:** the shape of `SemanticMapping` records (`kind`, `confidence_tier`, `provenance`).

During the translation stage, each program-graph node is matched against the active rule set and assigned a `SemanticMapping` with a `MappingKind` and confidence fields defined in [`../cogant/py/cogant/schemas/semantic.py`](../cogant/py/cogant/schemas/semantic.py). The following excerpt uses real COGANT field names and structure drawn from the `flask_app` fixture. Node IDs and file paths are illustrative; for verbatim output see `../cogant/output/flask_app/semantic_mappings.json` (generated by re-running the orchestrator):

```yaml
# Illustrative SemanticMapping-shaped records (see semantic.SemanticMapping)
- id: sm_get_users_obs
  kind: OBSERVATION
  graph_fragment_node_ids: [fn_get_users]
  semantic_label: "GET /users handler"
  confidence_score: 0.98
  confidence_tier: STATIC_ONLY
  parser_certainty: 1.0
  provenance:
    - {source: static_analysis, confidence: 1.0}

- id: sm_query_action
  kind: ACTION
  graph_fragment_node_ids: [call_db_session_query]
  semantic_label: "database query"
  confidence_score: 0.82
  confidence_tier: STATIC_ONLY
  parser_certainty: 0.90
  provenance:
    - {source: static_analysis, confidence: 0.90, metadata: {note: "receiver type partly heuristic"}}

- id: sm_user_model_hidden
  kind: HIDDEN_STATE
  graph_fragment_node_ids: [class_user]
  semantic_label: "User model state"
  confidence_score: 1.0
  confidence_tier: STATIC_ONLY
  provenance:
    - {source: static_analysis, confidence: 1.0}
```

The second row illustrates a key property of the confidence model (Equation \ref{eq:confidence-core} in @sec:02-03-confidence-scoring): when the parser resolves a receiver type via import traces rather than a direct definition, `parser_certainty` is lower, and Equation \ref{eq:confidence-core} yields a sub-1.0 `confidence_score` even before dynamic evidence arrives.

### Example state-space excerpt

**Read this for:** how variables, actions, and transitions are represented in the state-space IR and how tiers attach to transitions.

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

### Dynamically enriched excerpt

**Read this for:** how coverage and trace inputs change evidence on variables and transition tiers.

The previous excerpt shows a purely-static run. When `.coverage` / Cobertura XML and Chrome DevTools trace inputs are supplied to the `dynamic` stage, `enrich_graph()` annotates the affected nodes with `coverage_hits`, `branch_coverage`, `call_count`, `avg_duration_ms`, and `is_hot_path` metadata, and appends `dynamic_coverage` / `dynamic_trace` markers to the program graph's `evidence_sources` list. The downstream state-space compiler then becomes eligible to promote individual transitions from `STATIC_ONLY` to `STATIC_PLUS_RUNTIME` whenever the diversity bonus in Equation \ref{eq:confidence-core} clears the 0.65 boundary. The following excerpt shows the same Flask `/users` endpoint after re-running the pipeline with the application's `.coverage` file and a captured Chrome DevTools trace attached:

```json
{
  "variables": [
    {
      "name": "request.method", "type": "str", "domain": ["GET", "POST"],
      "evidence_sources": ["static_ast", "dynamic_coverage", "dynamic_trace"],
      "coverage_hits": 47, "call_count": 47, "is_hot_path": true
    },
    {
      "name": "db_connected", "type": "bool", "domain": [true, false],
      "evidence_sources": ["static_ast", "dynamic_coverage"],
      "coverage_hits": 47, "branch_coverage": 0.92, "is_hot_path": false
    }
  ],
  "transitions": [
    {
      "from_state": {"request.method": "GET", "db_connected": true},
      "action": "query_database",
      "to_state": {"response_code": 200},
      "confidence": 0.94, "tier": "STATIC_PLUS_RUNTIME",
      "evidence": {
        "static": {"rule_id": "rule_method_call_001", "parser_certainty": 0.95},
        "dynamic": {"coverage_hits": 47, "call_count": 47,
                    "avg_duration_ms": 12.4, "is_hot_path": true}
      }
    },
    {
      "from_state": {"db_connected": false},
      "action": "query_database",
      "to_state": {"response_code": 500},
      "confidence": 0.58, "tier": "RUNTIME_ONLY",
      "evidence": {
        "dynamic": {"coverage_hits": 2, "call_count": 2,
                    "avg_duration_ms": 3.1, "is_hot_path": false}
      }
    }
  ]
}
```

Two consequences of the enrichment are visible above. First, the `request.method` state variable's `is_hot_path: true` annotation, combined with the `dynamic_coverage` and `dynamic_trace` markers in its `evidence_sources`, carried enough diversity mass through the confidence formula to lift the previously-static `GET` transition from the MEDIUM tier into `STATIC_PLUS_RUNTIME`, and the transition's `evidence` field now records both the `rule_id` that fired statically and the `avg_duration_ms` measured dynamically. Second, the previously-`RUNTIME_ONLY` `db_connected=false` transition remains in its lower tier because it has only dynamic evidence (the error branch fired twice in the captured trace but has no corroborating static rule match) — a concrete illustration of the degradation behaviour documented in the "Incomplete coverage data" and "No dynamic traces available" subsections below.

### Failure modes and graceful degradation

COGANT is designed so that missing or partial inputs degrade the output bundle rather than halt it, and the manuscript records these degradation paths explicitly so that downstream consumers can interpret a partial run without guessing what was skipped [@peng2011reproducible]. Five failure modes are worth naming because each has a visible signature in the emitted artifacts.

**No dynamic traces available.** When neither coverage data nor execution traces are supplied, `enrich_graph()` is a no-op: no `coverage_hits`, `branch_coverage`, `call_count`, `avg_duration_ms`, or `is_hot_path` metadata is attached, and the graph's `evidence_sources` list never acquires `dynamic_coverage` or `dynamic_trace` markers. The state-space compiler still runs end-to-end using the semantic mappings and static graph alone, but every resulting transition is confined to the `STATIC_ONLY` tier (or lower), and no transition can be promoted to `STATIC_PLUS_RUNTIME`. Downstream code that consumes the bundle can identify a purely-static run at a glance by checking the evidence source markers on the graph metadata rather than scanning individual transitions.

**Incomplete coverage data.** When coverage is supplied but covers only a subset of the project, `_enrich_with_coverage` annotates the matched files only. The enrichment loop walks each coverage span, normalizes the reported file path, looks up candidate nodes whose path matches, and annotates those whose `source_range` overlaps the covered line; unmatched files are skipped (logged as informational), and nodes in unmatched files retain no coverage metadata at all. The result is a partially enriched graph in which some regions are eligible for tier promotion and others are not. Because the enrichment summary returns the number of annotated nodes, users can check whether the observed annotation rate matches their expectations for the provided coverage input.

**Translation rules that do not match.** When the active rule set fails to produce any mapping for a node -- whether because no rule fires, or because all firing rules are pruned during conflict resolution -- that node remains outside `self.mappings` and simply does not appear in any `graph_fragment_node_ids`. The translation engine's `get_coverage_report()` reports this directly: the returned dictionary contains the total node count, the covered count, a two-decimal `coverage_percent`, and the sorted list of `uncovered_node_ids`. Rather than fail, the engine treats uncovered nodes as an explicit **gap** and surfaces the list. Authors can extend the rule set, curate gaps via the `ReviewAPI` (documented in @sec:03-api-and-workflows), or accept the partial mapping for downstream GNN export.

**Fixpoint non-convergence.** The translation engine bounds its fixpoint loop at `max_iterations = 10` by default. If a rule set is pathological enough to keep emitting new mappings past that bound -- for example because two rules can produce mutually triggering mappings -- the engine emits a `"Max iterations reached without convergence"` warning, stops the loop, and proceeds to conflict resolution with whatever mappings it has accumulated. The iteration cap therefore guarantees termination even for misconfigured rule sets, and the warning in the log gives rule authors a clear signal that the cap was hit. Because each iteration logs an `iteration_complete` entry, diagnosis is possible post-hoc: authors can inspect per-pass mapping counts and resolution events in the match log without re-running the pipeline.

**Pipeline error tolerance.** The default pipeline configuration (`cogant/py/cogant/config/defaults.py`) marks the `dynamic`, `translate`, `state_space`, and `process` stages with `skip_on_error=True`, while structural stages such as `ingest`, `static`, `graph`, `export`, and `validate` keep the stricter default `skip_on_error=False`. When an optional stage raises, the runner records the error in the bundle, emits a warning, and continues to the next stage rather than aborting the run. Downstream bundle accessors (`state_space_model`, `process_model`) simply return `None` for stages that did not produce output, so a downstream consumer can detect a skipped stage by checking its accessor rather than by parsing log text. The net effect is that a partial bundle -- for example, a program graph and semantic mappings without a state-space model -- remains a first-class artifact with a clear provenance trail, rather than an opaque failure.

### Failure-mode matrix

| Condition | Symptom | Where it appears | Recovery |
|-----------|---------|------------------|----------|
| No coverage or traces | All transitions stay `STATIC_ONLY`; no `dynamic_*` evidence | `program_graph` metadata, transition `tier` | Supply `.coverage` / trace inputs; re-run `cogant translate` (see `../cogant/docs/reference/implementation_status.md`) |
| Partial coverage | Mixed enriched and bare nodes | `coverage_hits` sparse by file | Expand coverage to full tree or accept partial tier promotion |
| Optional `cogant[multilang]` / grammars missing | JS/TS parse skips or warnings | ingest logs, `parse_errors` in bundle | `uv sync --extra tree-sitter` + install grammars; re-run |
| Rule gaps on stdlib APIs | Zero `ACTION` mappings, low `mappings_total` | `semantic_mappings.json`, `metrics.json` | Extend rules or accept fallbacks (validator may still score 100) |
| `--incremental <ref>` stale graph | Unexpected diff vs full run | `PipelineConfig.incremental_since` | Full run without incremental, or refresh ref |
| Fixpoint cap hit | `"Max iterations reached"` in log | `TranslationEngine` match log | Reduce conflicting rules; raise `max_iterations` only after debugging |

## Rust layer

Native crates (`cogant-core`, `cogant-graph`, `cogant-translate`, `cogant-statespace`, `cogant-gnn`, `cogant-ffi`, and related packages) implement typed graph operations and export formatting. When PyO3 bindings are active, Python delegates heavy graph work through `cogant-ffi`. The Rust-wired paths and their Python-only counterparts are enumerated in [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md); all paths produce identical results regardless of backend.

## See also (MkDocs)

Step-by-step tutorials on shipped fixtures: [`../cogant/docs/tutorials/calculator.md`](../cogant/docs/tutorials/calculator.md), [`../cogant/docs/tutorials/flask.md`](../cogant/docs/tutorials/flask.md). Cookbook-style recipes: [`../cogant/docs/cookbook/README.md`](../cogant/docs/cookbook/README.md).
