## Changelog

All notable changes to COGANT are documented in this file. COGANT translates software repositories into **Generalized Notation Notation** (GNN) — the Active Inference Institute's structured state-space and process-model notation, not graph neural networks.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and COGANT adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### [Unreleased]

#### Added
- Full `gnn_pipeline/` subfolder emitted by the round-trip orchestrator. Contains the complete GNN package (17 canonical JSON artifacts + `model.gnn.md` / `model.gnn.json`), a `manifest.json`, `validation_report.json`, `execution_trace.json`, `execution_report.md`, `pipeline_manifest.json`, plus `diagrams/` and `visualizations/` subdirectories.
- PNG output generation via `cogant.viz.png_export`: `program_graph.png` (matplotlib + networkx) and automatic `.dot → .png` conversion when Graphviz is available.
- GraphML export (`program_graph.graphml`) and Parquet export (`parquet/nodes.parquet`, `parquet/edges.parquet`) wired into the orchestrator via `cogant.export.graphml.GraphMLExporter` and `cogant.export.parquet.ParquetExporter`.
- HTML site renderer (`site/`) wired via `cogant.viz.html_renderer.HTMLSiteRenderer` with index, graph, models, assets, and provenance pages.
- Boundary maps: `module_boundaries.mermaid`, `type_boundaries.mermaid`, `boundary_report.json` via `cogant.viz.boundary.BoundaryMapper`.
- Self-diff artifacts: `diff_view.html`, `diff_view.json` via `cogant.viz.diff_view.DiffVisualizer`.
- Thin orchestrated examples in `examples/thin_orchestrated/` demonstrating each stage independently (ingest, graph, translate, statespace, process, GNN export, simulation, validation).
- Canonical technical docs consolidated under `docs/` (see [README.md](./README.md)); changelog and benchmarks live in this file ([Benchmarks and performance](cogant_benchmarks.md#cogant-benchmarks)).

#### Changed
- Terminology across all docs and source: "Graph Neural Network" replaced with "Generalized Notation Notation" everywhere, with explicit disambiguation from graph neural networks.
- `api/orchestration.py`: every public `run_*` function now has full Args/Returns/Raises documentation.
- `viz/html_renderer.py`: fixed an f-string bug (`{{}}` inside an f-string evaluated to a dict literal, breaking `.get()` defaults). Precomputed values now used for all `_render_*` helpers.
- Dashboard (`dashboard.html`) expanded from 6 tabs to 9: Overview, Graph, State Space, Process, Semantic, Details, Active Inference, GNN Package, Factor Graph. ~93 KB output per repo.
- Mermaid generator now emits 10 diagram types including a dedicated Active Inference loop diagram (`active_inference_diagram.mermaid`).

#### Fixed
- `statespace/compiler.py`: action effect extraction now uses CONTAINS edges (parent class → method) in addition to direct WRITES, so every action has non-empty effects.
- `gnn/package.py`: iterated `.items()` on the node dict rather than keys; added helper `_count_edges_by_kind()`; added three previously missing canonical JSON files (`actions_policies.json`, `connections.json`, `preferences_constraints.json`).
- `gnn/formatter.py`: fixed file-count (now counts both FILE and MODULE nodes), section header canonicalization, transition probability derivation, and observation dependency extraction.
- `simulate/distributions.py`: relaxed probability normalization — any positive sum is now auto-normalized rather than rejected.
- `process/extractor.py`: fixed a Node comparison bug and improved stage naming via `_find_primary_node()`.

#### Performance / Testing
- Test suite: 463 passed, 1 skipped, 0 failures.
- Line coverage: 65% overall (up from 20%).
- All three control-positive example repos (`calculator`, `flask_mini`, `event_pipeline`) achieve **100% GNN validation score** and produce 111 total files each.

### [0.1.0] — 2026 initial release

#### Added
- Nine-stage compiler pipeline: ingest → static → normalize → graph → translate → statespace → process → export → validate → simulate.
- Python AST parser with function, class, method, import, decorator, and docstring extraction.
- Polyglot regex-based parsers for TypeScript, Rust, and Go.
- Typed program graph with stable IDs and provenance, emitted as `program_graph.json`, `typed_graph.json`, `cytoscape.json`, `graph_d3.json`, and `adjacency_matrix.json`.
- Translation engine with 12+ rules: `ReadOnlyInputRule`, `MutatingSubsystemRule`, `OrchestratorRule`, `TestAssertionRule`, `EventBusRule`, `RetryPatternRule`, plus observation / action / policy / preference / context / inheritance / containment mappers.
- Confidence model with static/runtime/review tiers and rationale strings.
- State-space compiler producing hidden states, observation modalities, actions, transitions, likelihoods, and preferences, with cardinalities inferred from class attributes and method names.
- Process extractor producing workflow stages, connections, and policies with trigger inference.
- GNN package emission: `GNNPackageBuilder` writes 14+ files matching the Active Inference Institute's canonical layout.
- GNN validator scoring packages 0–100% against the 18 canonical sections.
- GNN runner (`GNNModelRunner`) executing the compiled model under Active Inference (VFE and EFE computed per step, Bayesian belief updating, policy selection).
- Simulation runner (`simulate.runner`) with variational free energy (`VFE = KL(Q||P) - E_Q[log P(o|s)]`) and expected free energy (`EFE = epistemic - pragmatic`) using a 3-step planning horizon.
- Visualizations: dependency / class / state / sequence / flowchart / boundary / timeline / active-inference Mermaid diagrams; factor graph, ontology sunburst, confidence radar, and state-space matrix SVGs; free-energy trajectory HTML; Gantt CSS timeline.

[Unreleased]: https://github.com/example/cogant/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/example/cogant/releases/tag/v0.1.0

