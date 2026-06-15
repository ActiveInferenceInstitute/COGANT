# Examples and Failure Modes {#sec:04-examples-and-failure-modes}

This section walks through concrete example runs of the pipeline, first through the rendered calculator artifact chain and then through a small Flask application summary. It shows representative fragments of the artifacts COGANT produces (semantic mappings, state-space transitions, provenance traces, and runtime smoke outputs) and then documents the degradation behavior that users should expect when inputs are missing or partial. Together these illustrate what a successful run produces, how downstream consumers interpret partial bundles, and which confidence tiers mark degradation.

## Example outputs

**Intent.** Use the Flask walkthrough to see end-to-end graph and mapping **counts** on a real multi-module app; use `json_stdlib` to see **partial evidence** and validator behaviour; use the YAML/JSON fragments to match **field names** in exported artifacts. The failure-mode subsections document **degradation signatures** in bundles.

The package tree includes runnable examples under `../cogant/examples/` (for example `control_positive/`, `python-service/`, `workflow-engine`, and `thin_orchestrated/`) and generated sample outputs under `../cogant/output/` (for example `calculator/` with `model.gnn.md`, diagrams, PNG figures, `roundtrip/forward/`, and `roundtrip/reverse/`). Use `cogant translate --layout-output` or `PipelineConfig(layout_output=True)` to place pipeline JSON under `data/` automatically; run `python -m cogant.tools.render_output_figures` on the output root for PNGs. Regenerate these trees by running the packaged pipeline against the example sources when validating releases.

### Rendered end-to-end figures: code, GNN, and roundtrip {#sec:04-rendered-end-to-end-figures}

The manuscript generation script copies a curated subset of real package-output PNGs from `../cogant/output/` into `../output/figures/` so the PDF/HTML build uses the same artifacts a user receives from `run_all.py`. The graphical abstract in @fig:cogant-graphical-abstract is the quick route, while @fig:cogant-interpretability-overview is the reading map for the detailed panels below. The evidence chain is deliberately staged: code is converted into a program graph in @fig:cogant-forward-program-graph, semantic mappings become a state-space factor graph in @fig:cogant-state-space-factor, the factor graph is compiled into A/B/C/D matrices in @fig:cogant-abcd-matrices, the structural boundary is recorded in @fig:cogant-markov-blanket, the emitted Generalized Notation Notation bundle is accepted by the upstream GNN visualization path in @fig:cogant-upstream-generative, the batch runner records the explicit forward-reverse-forward roundtrip stage in @fig:cogant-roundtrip-gantt, the aggregate batch evidence is summarized in @fig:cogant-batch-evidence-summary, and the later diagnostic panels expose rule evidence, review-readiness, roundtrip drift, and runtime smoke traces behind those claims.

@tbl:figure-reading-order states the intended scholarly use of each promoted figure group. This keeps the figure set from reading as a gallery: each visual has a reviewer question, source artifact family, and claim boundary.

| Figure group | Primary figures | Reviewer question | Claim boundary |
|---|---|---|---|
| Orientation | @fig:cogant-graphical-abstract, @fig:cogant-interpretability-overview | What are the conversion boundaries? | Layout and evidence-chain map only; inspect detailed panels for counts. |
| Static extraction | @fig:cogant-forward-program-graph | Which source facts entered the program graph? | Static artifact audit, not complete runtime semantics. |
| Model construction | @fig:cogant-state-space-factor, @fig:cogant-abcd-matrices, @fig:cogant-markov-blanket | How do roles become state variables, matrices, and structural blankets? | Shape, matrix-value, and partition evidence, not a causal-independence proof. |
| Interoperability | @fig:cogant-gnn-markdown-render, @fig:cogant-upstream-generative | Can the emitted GNN artifact be read and passed to compatible tooling? | Format and pipeline compatibility, not semantic adequacy. |
| Roundtrip and batch provenance | @fig:cogant-roundtrip-gantt, @fig:cogant-batch-evidence-summary, @fig:cogant-roundtrip-visual-diff | Did the roundtrip and batch evidence actually run? | Run-manifest and invariant-ledger evidence, not benchmark generalization. |
| Rule and review diagnostics | @fig:cogant-rule-evidence-trace, @fig:cogant-confidence-calibration | Why did mappings fire and which evidence remains unreviewed? | Provenance and review-readiness, not labelled false-negative coverage or calibration. |
| Runtime smoke | @fig:cogant-inference-trace | Can exported matrices drive a deterministic trace? | Executability smoke signal, not behavioural-performance validation. |

: Manuscript figure reading order and claim boundaries. {#tbl:figure-reading-order}

COGANT treats these views as **method outputs** rather than decorative drawings. The program-graph renderer uses a deterministic containment-first layout for code hierarchies, with Graphviz/dot layered layout when available and alternate force-directed layouts for less hierarchical fragments, following standard graph-drawing practice for layered and relational structures [@sugiyama1981methods; @fruchterman1991graph; @gansner1993technique]. The dashboard sequence applies overview, filter, detail-on-demand, and task-typology principles to a research pipeline [@shneiderman1996eyes; @heer2012interactive; @brehmer2013typology; @bostock2011d3], and it respects visualization-design warnings that a wrong upstream abstraction invalidates even a polished downstream visual encoding [@munzner2009nested; @sedlmair2012design]. COGANT's dashboard panels are therefore part of the validation surface: a reviewer should be able to trace a manuscript figure back to its JSON source, renderer, digest, displayed counts, and known limitations. The design also follows graphical-perception and scientific-figure guidance: use common baselines and direct labels for quantitative comparisons, avoid decorative encodings, avoid relying on hue alone, and keep the caption explicit about what the figure does and does not establish [@cleveland1984graphical; @rougier2014figures; @crameri2020misuseColour]. For source-code views specifically, the figures follow software-visualization and program-comprehension cautions that source-code visuals must choose meaningful mappings and navigable encodings rather than relying on visual metaphor alone [@gracanin2005software; @herman2000graph; @ghoniem2004comparison; @storey2005program; @wettel2007cities].

![COGANT interpretability overview for the calculator fixture. The figure is generated from the same run directory as the detailed panels: `data/program_graph.json`, semantic-mapping evidence, `data/state_space.json`, and `gnn_package/markov_blanket.json`. Read it left to right as a map of the inspection workbench: graph structure, role assignments, compiled GNN state space, and structural blanket partition. The compact panels are orientation aids; the detailed figures below remain the source for counts, deltas, and limitations.](../figures/cogant_interpretability_overview.png){#fig:cogant-interpretability-overview width=98%}

![Forward codebase-to-program-graph evidence view for the calculator fixture. The renderer reads the same `data/program_graph.json` consumed by semantic mapping: node fill encodes program entity kind, edge color and line style encode relation kind, role outlines appear when rule-evidence traces identify Active Inference mappings, and the footer/sidecar record artifact digests, displayed counts, and sampling status. The figure verifies inspectable static extraction structure; it does not prove that all dynamic behavior or external effects were recovered.](../figures/cogant_forward_program_graph.png){#fig:cogant-forward-program-graph width=98%}

The first conversion follows the same broad representational move as code property graphs: source-level structure is fused into a graph that later passes can traverse and transform [@yamaguchi2014modeling]. COGANT's graph is narrower than a vulnerability-mining CPG because its destination is an Active-Inference-ready model rather than a graph-query database, but the design premise is shared: make program structure explicit before learning, inference, or validation. @fig:cogant-forward-program-graph should therefore be read as an **artifact audit**. The important claim is not that the layout is aesthetically optimal; it is that the nodes, edges, relation kinds, optional semantic-role outlines, and counts are generated from the same artifact chain used by the translator.

![Forward program-graph-to-state-space conversion on the calculator fixture. The factor graph is generated from `data/state_space.json`: blue denotes hidden-state factors, teal denotes observations, orange denotes actions, and text labels plus edge direction redundantly identify the role relationships. Edges mark the likelihood (state→observation) and control (action→state) relationships that populate the corresponding entries of the A and B arrays (the C preference and D prior vectors are node attributes, not edges). This is a compiled representation of extracted evidence, not a learned behavioral model.](../figures/cogant_forward_state_space_factor.png){#fig:cogant-state-space-factor width=98%}

![A/B/C/D matrix panel for the richer Flask application fixture. The heatmaps are rendered from exported `model.gnn.json` arrays: A shows likelihood values with non-uniform state columns, C shows the real zero preference vector, D shows the exported prior vector, and B shows the recorded max-over-actions summary of the exported transition tensor. Hidden-state indices 0-11 are concrete program/service state variables, while indices 12-13 are inheritance-role hidden states; that grouping explains the sparse lower-right transition/prior region rather than indicating a renderer fault. Panel annotations report source/display shapes, distinct values, nonzero cells, and B identity-slice diagnostics so real structure and weak-evidence regions are visible before downstream inference.](../figures/cogant_forward_abcd_matrices.png){#fig:cogant-abcd-matrices width=98%}

![Structural Markov-blanket partition for the calculator fixture. The renderer reads `gnn_package/markov_blanket.json` and lays out internal, sensory, active, and external node groups with displayed counts from the sidecar. This is a structural boundary extracted from emitted program nodes and seed rules; it is not a probabilistic conditional-independence proof over source-code behavior.](../figures/cogant_markov_blanket.png){#fig:cogant-markov-blanket width=98%}

The state-space, matrix, and blanket figures are the concrete bridge from program analysis to discrete active inference: observations, actions, priors, transitions, and structural boundaries are represented in the same broad A/B/C/D and Markov-blanket vocabulary used in discrete-state active-inference tutorials and runtimes [@dacosta2020active; @smith2022stepbystep; @heins2022pymdp]. The important reproducibility detail is that these are not manuscript-only redraws; they are copied by `tools/manuscript_figures.py` from the package's generated run directory and therefore remain coupled to the code that emits the JSON bundle. The blanket panel should be read with the scoped definition in @def:markov-blanket-partition: COGANT exports a total structural role partition, not an empirical proof that the induced program graph satisfies a causal or probabilistic blanket property.

![Upstream Generalized Notation Notation visualization of the emitted POMDP generative-model structure. This figure is copied from `cogant/output/upstream_pipeline/8_visualization_output/` and demonstrates that the generated package can pass through the external GNN visualization stage. Inspect it as interoperability evidence for the exported model structure, not as an independent validation of COGANT's semantic mapping rules.](../figures/cogant_upstream_generative_model.png){#fig:cogant-upstream-generative width=92%}

The upstream visualization in @fig:cogant-upstream-generative is the second one-way conversion: COGANT's emitted `model.gnn.md` is handed to the Active Inference Institute Generalized Notation Notation tooling, whose repository describes GNN as a text-based language for Active Inference generative models and an analysis/visualization pipeline around those files [@friedman2024gnn]. The visual is useful because it verifies interoperability at the representation boundary, not just internal rendering.

![Calculator-target publication timeline rendered from `cogant/output/run_manifest.json`. The wide horizontal bars show the recorded calculator command sequence and local wall-clock durations, while validation and roundtrip gate markers distinguish evidence checks from ordinary execution stages. The sidecar preserves the full batch target and command context; the figure itself is provenance for the selected target, not a benchmark.](../figures/cogant_roundtrip_batch_gantt.png){#fig:cogant-roundtrip-gantt width=98%}

Finally, @fig:cogant-roundtrip-gantt shows the calculator roundtrip as an executed stage rather than a prose assertion. The renderer selects the calculator target from the batch manifest so the publication image remains legible, and records the full batch target count, command count, selected target, selected command count, gate count, and failed-step count in the sidecar. In this run, `run_all.py` invokes `cogant roundtrip <target> --output <run_dir>/roundtrip --keep-tmp`, preserving the forward GNN and reverse-synthesized Python package beside the rest of the per-target output. The accompanying `roundtrip/metrics.json` records role preservation, graph node/edge deltas, edge-kind deltas, GNN section diffs, matrix shape/value deltas, and generated-code compile/test status, so the dashboard can separate representational drift from executable reverse-synthesis failures. The roundtrip metric reported elsewhere in the manuscript asks whether the semantic role distribution and the supporting structural artifacts survive the `forward -> reverse -> forward` cycle, aligning the implementation with the bidirectional lens framing in @sec:08-03-lenses-and-synthesis [@foster2007lenses].

![Aggregate batch evidence summary rendered from `cogant/output/dashboard/metrics_per_target.json`. The four small multiples show semantic-role totals, validation-score buckets, roundtrip status, and visual-workbench completeness for the regenerated `run_all.py` batch. Inspect the role bars as emitted mapping evidence and the other panels as coverage checks over the same target set. The chart reports artifact counts for this run; it does not establish semantic correctness, role-ground-truth coverage, or benchmark performance.](../figures/cogant_batch_evidence_summary.png){#fig:cogant-batch-evidence-summary width=98%}

@fig:cogant-batch-evidence-summary is promoted only because the regenerated batch output contains nonzero graph, mapping, role, validation, roundtrip, and visual-artifact evidence. The one degenerate JavaScript fixture remains visible in the dashboard JSON, but it no longer controls whether the whole aggregate figure is meaningful: the figure sidecar records the target count, total nodes, total edges, total mappings, validation-score count, role totals, visual-artifact total, and the number of targets with complete evidence support.

![Roundtrip visual diff for the calculator fixture. The panel is generated from `roundtrip/metrics.json` and shows, as bars, the original-versus-regenerated node and edge count deltas, the normalized graph-edit distance, the missing and extra GNN sections, and the maximum absolute matrix delta; below the bars it lists per-invariant pass/check status and a status line that separates the strict-structure, role, matrix, GNN, and generated-code checks. Read role preservation as a weaker success tier than strict structural isomorphism.](../figures/cogant_roundtrip_visual_diff.png){#fig:cogant-roundtrip-visual-diff width=98%}

The roundtrip diff in @fig:cogant-roundtrip-visual-diff is the manuscript-facing form of the new invariant ledger: node preservation, edge preservation, role preservation, state-space shape preservation, matrix preservation, regenerated-code compile status, and optional generated-code smoke tests are all recorded as named checks. A failing check is therefore inspectable as a specific representational discrepancy rather than collapsed into a single score.

![Rule evidence trace for the calculator fixture. The native publication PNG is generated from `data/rule_evidence_trace.json`: bars count rule contributions, the annotation line reports mapping and conflict totals, and the sidecar records the same source digest used by the evidence-coverage panel. Read it as mapping-level provenance for proposed role assertions; it supports precision review of emitted mappings but does not quantify missed mappings without a labelled false-negative corpus.](../figures/cogant_rule_evidence_trace.png){#fig:cogant-rule-evidence-trace width=98%}

@fig:cogant-rule-evidence-trace makes the rule engine auditable at the level where human review actually happens. The source artifact is `rule_evidence_trace.json`, emitted during export and copied into the organized run tree. Reviewer annotations can mark individual mappings as accepted or rejected, after which the same trace reports per-rule reviewed counts and precision proxies without claiming missed-role coverage unless a labelled false-negative corpus is supplied. This mirrors visual-analytics practice for learned systems: the goal is to help people understand when a model or pipeline works, when it fails, and how to improve it, rather than to replace the underlying evidence with a plot [@hohman2019visual].

![Evidence-coverage and review-priority view for the calculator fixture. The native publication PNG is generated from the same rule-evidence JSON as the companion rule-evidence trace and displays proposed mapping counts, rule contribution totals, confidence-tier distribution, conflict outcomes, and reviewer-annotation coverage. The current calculator artifact has 0 reviewed mapping rows, so this is a review-priority and provenance panel rather than a calibration curve or a claim about semantic correctness.](../figures/cogant_confidence_calibration.png){#fig:cogant-confidence-calibration width=98%}

The evidence-coverage panel deliberately avoids presenting a reliability curve when no reviewer labels exist. Uncertainty-visualization studies show that confidence displays require careful evaluation because readers may treat displayed uncertainty or confidence as stronger decision evidence than the study design supports [@hullman2019uncertainty]. COGANT therefore reports the available evidence -- mapping counts, confidence tiers, conflicts, and reviewed-row counts -- while leaving calibration, false-negative coverage, and semantic truth as separate claims that require labelled review data.

The batch dashboard still writes audit sidecars such as `output/dashboard/metrics_per_target.json`, `output/dashboard/role_distribution.mmd`, `output/dashboard/roundtrip_status.mmd`, and `output/dashboard/visual_completeness.mmd`. The manuscript inserts only the registered publication summary in @fig:cogant-batch-evidence-summary because its source JSON has nonzero graph, mapping, role, validation, roundtrip, and visual-artifact data. Reviewers should inspect the dashboard JSON and Mermaid sidecars when evaluating a release run; the figure is an overview of emitted evidence, not a substitute for target-level artifacts.

![Deterministic inference trace generated from the package's built-in demonstration A/B/C/D matrices (`default_demo_matrices`), which share the shape of an exported model but are not the calculator fixture's own exported values. The runtime demo emits `data/inference_trace.json` and the corresponding native publication PNG with belief trajectories, selected actions, preference satisfaction, and the package's reported free-energy diagnostic. Read the curve as an executable-matrix smoke signal, not as a calibrated psychological, biological, or benchmarked control-performance measurement.](../figures/cogant_inference_trace.png){#fig:cogant-inference-trace width=98%}

The inference trace in @fig:cogant-inference-trace is intentionally a deterministic demonstration rather than a benchmark of agent quality. It shows that A/B/C/D matrices of the form COGANT exports can drive a reproducible belief/action/preference/free-energy trace through the bundled deterministic demo runtime, which is the smallest executable bridge between an exported model bundle and downstream discrete active-inference runtimes [@dacosta2020active; @heins2022pymdp].

### Concrete walkthrough: Flask REST API

**Read this for:** representative node/edge/mapping and GNN validation numbers aligned with the benchmark tables in @sec:06-03-performance-and-fixture-metrics.

To make the pipeline's behavior tangible, consider the `flask_app` fixture distributed under `../cogant/examples/real_world/flask_app/`: a small six-module Flask application (`__init__.py`, `app.py`, `config.py`, `models.py`, `services.py`, `utils.py`) totalling {{FIXTURE_FLASK_APP_LOC}} lines of Python analyzed end-to-end by the **public** pipeline (`cogant.api.orchestration`, the same code path as `cogant translate` and the benchmark harness). Canonical `flask_app` numbers in `../cogant/evaluation/figures/metrics.json` are produced by `evaluation/figures/generate_figures.py` and match graph size rows in @tbl:benchmark-suite-results. (The `examples/orchestrate_roundtrip.py` demo can emit a larger serialized graph, including a call graph, for dashboard-heavy exports; the manuscript and `metrics.json` stay on the API pipeline so one definition of \(|V|\) and \(|E|\) applies throughout.)

| Metric | Value |
|--------|-------|
| Source files discovered | 6 |
| Lines analyzed | 866 |
| **Nodes** | **98** |
| **Edges** | **163** |
| Total semantic mappings | {{FIXTURE_FLASK_APP_MAPPINGS_TOTAL}} (`mappings_total` for `flask_app` in `../cogant/evaluation/figures/metrics.json`; same post-`statespace` count as the `mappings` column in @tbl:benchmark-suite-results) |
| GNN package files | 28 |
| GNN validation | PASS (score 100.0, 0 errors, 0 warnings) |

The default graph stage in this path emits structural kinds (MODULE, CLASS, METHOD, FUNCTION) and, at v{{VERSION}}, `CONTAINS`, `INHERITS`, `IMPORTS`, and `self`-dataflow `READS` / `WRITES` edges when the public API path has that evidence. The richer taxonomy in `cogant.schemas.core.NodeKind` and `EdgeKind` (18 kinds each; see `../cogant/docs/reference/schemas_reference.md`) also includes `CALLS` and others: those appear when the call-graph pass is part of the built graph. Dynamic enrichment (`dynamic/`) can add additional edges when traces are available.

| Node kind | Count | Percentage |
|-----------|-------|-----------|
| MODULE | 6 | 6.1% |
| CLASS | 25 | 25.5% |
| METHOD | 57 | 58.2% |
| FUNCTION | 10 | 10.2% |

: Node kind distribution (Flask API example). {#tbl:flask-api-node-kinds}

| Edge kind | Count | Percentage |
|-----------|-------|-----------|
| CONTAINS | 92 | 56.4% |
| IMPORTS | 9 | 5.5% |
| INHERITS | 9 | 5.5% |
| READS | 38 | 23.3% |
| WRITES | 15 | 9.2% |

: Edge kind distribution (Flask API example, `metrics.json`). {#tbl:flask-api-edge-kinds}

`CONTAINS` edges dominate the API-built graph, followed by dataflow `READS` / `WRITES` and the import/inheritance edges visible in `metrics.json`. When optional `CALLS` edges are present (for example in a full `orchestrate_roundtrip.py` run with call-graph construction), their counts appear in that output's `program_graph.json` instead; they are not double-counted here. Broadening coverage for optional node and edge kinds is tracked as P1-2 and P1-3 in the R&D backlog (`../cogant/docs/evaluation/SCOPING_REPORT.md`).

### Walkthrough: `json_stdlib` (degraded-output defaults and validator score)

**Read this for:** how the pipeline remains valid with sparse static evidence and identity/default matrix entries (validator notes in the bundle).

The `examples/real_world/json_stdlib/` fixture exercises **partial-evidence** paths without failing validation. In the current rule set, the expanded `ActionRule` keyword set matches `dump`, `dumps`, `load`, `loads`, and serialisation synonyms; the auto-generated `METRICS.yaml` records `state_variables: {{FIXTURE_JSON_STDLIB_STATE_VARIABLES}}`, `observations: {{FIXTURE_JSON_STDLIB_OBSERVATIONS}}`, `actions: {{FIXTURE_JSON_STDLIB_ACTIONS}}`, and `mappings_total: {{FIXTURE_JSON_STDLIB_MAPPINGS_TOTAL}}`. Of the {{ABLATION_JSON_STDLIB_B_ACTIONS_TOTAL}} action slices of $B$, {{ABLATION_JSON_STDLIB_B_ACTIONS_IDENTITY}} default to the identity tensor (no WRITES edges link those actions to hidden states at the AST extraction granularity), and {{ABLATION_JSON_STDLIB_A_COLS_UNIFORM}} of the {{ABLATION_JSON_STDLIB_A_COLS_TOTAL}} state columns of $A$ is uniform. The pipeline still emits a structurally valid `gnn_package/` (the 16 required files plus generated diagram/visualization assets): Validation Notes (section 19 of the bundle) list every maximum-entropy entry so downstream consumers can distinguish evidence-backed matrix entries from structural defaults; @sec:02-04-gnn-export-and-error-handling defines the structural validity boundary.

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

The second row illustrates a key property of the confidence model (@eq:confidence-core in @sec:02-03-confidence-scoring): when the parser resolves a receiver type via import traces rather than a direct definition, `parser_certainty` is lower, and @eq:confidence-core yields a sub-1.0 `confidence_score` even before dynamic evidence arrives.

### Example state-space excerpt

**Read this for:** how variables, actions, and transitions are represented in the state-space IR layer and how tiers attach to transitions.

When dynamic traces are available, the state-space compiler produces a behavioral model alongside the static graph. The following excerpt shows a fragment of the state-space IR layer for the `/users` endpoint:

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

The previous excerpt shows a purely-static run. When `.coverage` / Cobertura XML and Chrome DevTools trace inputs are supplied to the `dynamic` stage, `enrich_graph()` annotates the affected nodes with `coverage_hits`, `branch_coverage`, `call_count`, `avg_duration_ms`, and `is_hot_path` metadata, and appends `dynamic_coverage` / `dynamic_trace` markers to the program graph's `evidence_sources` list. The downstream state-space compiler then becomes eligible to promote individual transitions from `STATIC_ONLY` to `STATIC_PLUS_RUNTIME` whenever the diversity bonus in @eq:confidence-core clears the 0.65 boundary. The following excerpt shows the same Flask `/users` endpoint after re-running the pipeline with the application's `.coverage` file and a captured Chrome DevTools trace attached:

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

Two consequences of the enrichment are visible above. First, the `request.method` state variable's `is_hot_path: true` annotation, combined with the `dynamic_coverage` and `dynamic_trace` markers in its `evidence_sources`, carried enough diversity mass through the confidence formula to lift the previously-static `GET` transition from the `STATIC_ONLY` tier into `STATIC_PLUS_RUNTIME`, and the transition's `evidence` field now records both the `rule_id` that fired statically and the `avg_duration_ms` measured dynamically. Second, the previously-`RUNTIME_ONLY` `db_connected=false` transition remains in its lower tier because it has only dynamic evidence (the error branch fired twice in the captured trace but has no corroborating static rule match) — a concrete illustration of the degradation behaviour documented in the "Incomplete coverage data" and "No dynamic traces available" subsections below.

### Failure modes and graceful degradation

COGANT is designed so that missing or partial inputs degrade the output bundle rather than halt it, and the manuscript records these degradation paths explicitly so that downstream consumers can interpret a partial run without guessing what was skipped [@peng2011reproducible]. Five failure modes are worth naming because each has a visible signature in the emitted artifacts.

**No dynamic traces available.** When neither coverage data nor execution traces are supplied, `enrich_graph()` is a no-op: no `coverage_hits`, `branch_coverage`, `call_count`, `avg_duration_ms`, or `is_hot_path` metadata is attached, and the graph's `evidence_sources` list never acquires `dynamic_coverage` or `dynamic_trace` markers. The state-space compiler still runs end-to-end using the semantic mappings and static graph alone, but every resulting transition is confined to the `STATIC_ONLY` tier (or lower), and no transition can be promoted to `STATIC_PLUS_RUNTIME`. Downstream code that consumes the bundle can identify a purely-static run at a glance by checking the evidence source markers on the graph metadata rather than scanning individual transitions.

**Incomplete coverage data.** When coverage is supplied but covers only a subset of the project, `_enrich_with_coverage` annotates the matched files only. The enrichment loop walks each coverage span, normalizes the reported file path, looks up candidate nodes whose path matches, and annotates those whose `source_range` overlaps the covered line; unmatched files are skipped (logged as informational), and nodes in unmatched files retain no coverage metadata at all. The result is a partially enriched graph in which some regions are eligible for tier promotion and others are not. Because the enrichment summary returns the number of annotated nodes, users can check whether the observed annotation rate matches their expectations for the provided coverage input.

**Translation rules that do not match.** When the active rule set fails to produce any mapping for a node -- whether because no rule fires, or because all firing rules are pruned during conflict resolution -- that node remains outside `self.mappings` and simply does not appear in any `graph_fragment_node_ids`. The translation engine's `get_coverage_report()` reports this directly: the returned dictionary contains the total node count, the covered count, a two-decimal `coverage_percent`, and the sorted list of `uncovered_node_ids`. Rather than fail, the engine treats uncovered nodes as an explicit **gap** and surfaces the list. Authors can extend the rule set, curate gaps via the `ReviewAPI` (documented in @sec:03-api-and-workflows), or accept the partial mapping for downstream GNN export.

**Fixpoint non-convergence.** The translation engine bounds its fixpoint loop at `max_iterations = 10` by default. If a rule set is pathological enough to keep emitting new mappings beyond that bound -- for example because two rules can produce mutually triggering mappings -- the engine emits a `"Max iterations reached without convergence"` warning, stops the loop, and proceeds to conflict resolution with whatever mappings it has accumulated. The iteration cap therefore forces termination of that loop even for misconfigured rule sets, and the warning in the log gives rule authors a clear signal that the cap was hit. Because each iteration logs an `iteration_complete` entry, diagnosis is possible post-hoc: authors can inspect per-pass mapping counts and resolution events in the match log without re-running the pipeline.

**Pipeline error tolerance.** The default pipeline configuration (`cogant/py/cogant/config/defaults.py`) marks the `dynamic`, `translate`, `statespace`, and `process` stages with `skip_on_error=True`, while structural stages such as `ingest`, `static`, `graph`, `export`, and `validate` keep the stricter default `skip_on_error=False`. When an optional stage raises, the runner records the error in the bundle, emits a warning, and continues to the next stage rather than aborting the run. Downstream bundle accessors (`state_space_model`, `process_model`) simply return `None` for stages that did not produce output, so a downstream consumer can detect a skipped stage by checking its accessor rather than by parsing log text. The net effect is that a partial bundle -- for example, a program graph and semantic mappings without a state-space model -- remains a first-class artifact with a clear provenance trail, rather than an opaque failure.

### Failure-mode matrix

| Condition | Symptom | Where it appears | Recovery |
|-----------|---------|------------------|----------|
| No coverage or traces | All transitions stay `STATIC_ONLY`; no `dynamic_*` evidence | `program_graph` metadata, transition `tier` | Supply `.coverage` / trace inputs; re-run `cogant translate` (see `../cogant/docs/reference/implementation_status.md`) |
| Partial coverage | Mixed enriched and bare nodes | `coverage_hits` sparse by file | Expand coverage to full tree or accept partial tier promotion |
| Optional `cogant[multilang]` / grammars missing | JS/TS parse skips or warnings | ingest logs, `parse_errors` in bundle | `uv sync --extra tree-sitter` + install grammars; re-run |
| Rule gaps on stdlib APIs | Zero `ACTION` mappings, low `mappings_total` | `semantic_mappings.json`, `metrics.json` | Extend rules or explicitly accept degraded-output defaults with validator notes |
| `--incremental <ref>` cached graph drift | Unexpected diff vs full run | `PipelineConfig.incremental_since` | Full run without incremental, or refresh ref |
| Fixpoint cap hit | `"Max iterations reached"` in log | `TranslationEngine` match log | Reduce conflicting rules; raise `max_iterations` only after debugging |

## Rust layer

Native crates (`cogant-core`, `cogant-graph`, `cogant-translate`, `cogant-statespace`, `cogant-gnn`, `cogant-ffi`, and related packages) implement typed graph operations and export formatting. When PyO3 bindings are active, Python delegates heavy graph work through `cogant-ffi`. The Rust-wired paths and their Python-only counterparts are enumerated in the implementation-status table under `../cogant/docs/reference/`; all paths produce identical results regardless of backend.
