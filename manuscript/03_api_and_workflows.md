# API and Workflows

This section describes the programmatic surface that the shipped Python package exposes in practice, aligned with `../cogant/docs/api/README.md` and the inventory-style notes under `../cogant/docs/reference/`. It is **not** an empirical benchmark section; COGANT does not ship comparative timing claims in the manuscript layer. Instead, it records the **surface area** users can rely on: two complementary entry points (a Session for stepwise work and a Pipeline for batch runs), the Bundle accessors that expose their artifacts, a command-line interface, and a Review API for human-in-the-loop curation.

## Session-oriented workflow

Use `Session` for interactive exploration, notebook-driven debugging, and incremental re-runs where you want to materialize each stage's output as a Python attribute. It is the right choice when a user wants to inspect intermediate artifacts between stages, iterate on a single repository in a notebook, or debug a specific extraction step without committing to a full scripted run. Each call returns control to the caller so that the graph, mappings, or state-space model can be examined before the next stage is invoked.

`Session.from_target` accepts a local path or URL, then supports a stepwise workflow:

- `extract_static` — AST-oriented extraction for supported languages.
- `extract_dynamic` — traces and coverage when inputs exist.
- `build_graph` — program graph construction.
- `translate_to_gnn` — Generalized Notation Notation (GNN) representation.
- `compile_state_space` — behavioral model when the pipeline has sufficient data.
- `export_all` — writes JSON artifacts under a chosen output directory.

This path suits interactive notebooks and incremental debugging.

## Pipeline-oriented workflow

Use `PipelineRunner` for scripted, reproducible batch runs where all stages are configured up front and the end-state is a single `Bundle`. It is the right choice when a user wants to process many repositories with a fixed configuration, wire COGANT into CI, or guarantee that every run executes the same ordered stages with the same plugin settings. Because the whole run is described by a single `PipelineConfig`, it can be checked into version control and replayed without manual intervention.

`PipelineRunner` with `PipelineConfig` runs an ordered list of stages (ingest, static, normalize, graph, translate, state space, process, export, validate). Configuration can skip stages (for example dynamic analysis), attach **plugin** settings per language, set `output_dir`, verbosity, and dry-run mode. Results aggregate into a **Bundle** with `stage_results`, error lists, and accessors described below.

## Bundle accessors

The bundle API exposes stage summaries and convenience render/export helpers, including:

- `repo_summary`, `program_graph`, `state_space_model`, `process_model`
- `gnn_markdown` — compact markdown summary built from `stage_results["translate"]`
- `validation_report`
- `render_site` — static HTML site with graph and model views
- `to_json` / `save_json`

For canonical 18-section Generalized Notation Notation artifacts (`model.gnn.md` plus companion JSON), use the export outputs documented in `../cogant/docs/export/README.md`; `Bundle.gnn_markdown()` is intentionally a lightweight report surface.

## Command-line interface

The CLI entry point (`cogant.cli.main`) registers 22 subcommands. The high-traffic paths are `cogant translate` (full pipeline, equivalent to `cogant analyze`; accepts `--incremental <git-ref>` for per-commit CI re-runs over a Git diff), `cogant validate`, `cogant reverse`, `cogant roundtrip`, and `cogant doctor` (environment diagnostics). Additional commands cover scanning (`scan`, `extract-static`, `extract-dynamic`, `graph`), visualization (`render`, `viz`, `diff`), review (`explain`), and lifecycle management (`init`, `plugin`, `migrate`, `benchmark`, `changed`). Exact flags live in `../cogant/docs/cli/README.md`; the manuscript does not duplicate them to avoid drift.

## Review API

`ReviewAPI` supports interactive curation: load a bundle, present mappings, accept, reject, or edit, then save a curated bundle. This closes the loop when human review is part of the ML dataset construction.
