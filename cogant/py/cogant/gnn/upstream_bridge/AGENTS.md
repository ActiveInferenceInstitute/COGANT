# `cogant.gnn.upstream_bridge`

## Purpose

Lazy facade over the Active Inference Institute upstream package
**`generalized-notation-notation`** (PyPI distribution name; GNN >= 4.0
installs the top-level import package `gnn`). Lets COGANT validate / parse /
round-trip GNN markdown using the canonical reference implementation while
keeping heavy dependencies (JAX, PyTorch) out of the eager import path.

* **Optional** dependency: installed only through the `upstream` extra
  (`uv sync --extra upstream`; not part of `all`). The extra pins a full
  commit of the published GNN v5.0.1 tag in `cogant/pyproject.toml`
  (mirrored in `uv.lock`); `tools/gnn_upstream_audit_surface.py` and
  `tools/audit_release_integrity.py` check that pin against the lock.
* Version gate: `_require_upstream_gnn()` raises `ImportError` (surfaced as
  "unavailable") when the distribution is missing, older than
  `MIN_UPSTREAM_MAJOR` (4), or when the importable `gnn` package belongs to
  a different distribution.
* Upstream license: **CC-BY-NC-SA-4.0** — see `cogant/LICENSES.md`.
* Upstream calls are **opt-in**. `GNNValidator.validate_package` runs
  upstream validation only for `upstream_gnn=True`, or for
  `upstream_gnn=None` when `COGANT_ENABLE_UPSTREAM_GNN` is truthy
  (`1` / `true` / `yes`). The pipeline passes
  `PipelineConfig.upstream_gnn_validation` (default `False`) explicitly,
  and the 25-step pass needs `PipelineConfig.upstream_gnn_pipeline = True`.
  `COGANT_DISABLE_UPSTREAM_GNN` (truthy) beats `COGANT_ENABLE_UPSTREAM_GNN`
  for `upstream_gnn=None`; an explicit `True`/`False` always wins.
* The `GNN v2.0.0` value under `## GNNVersionAndFlags` is COGANT's own schema
  identifier (`cogant.schema.versions.CURRENT_GNN_VERSION`), not the upstream
  release.

## Public API

All callers should use the `upstream_*` facade — never `import gnn`
directly anywhere else in the package.

| Symbol | Returns | Use |
| --- | --- | --- |
| `is_upstream_gnn_available()` | `bool` | Probe (runs the version/ownership gate); never raises. |
| `upstream_version()` | `str \| None` | Upstream `gnn.__version__` (`"5.0.1"` for the current pin), when available. |
| `UPSTREAM_DISTRIBUTION`, `UPSTREAM_IMPORT_NAME`, `MIN_UPSTREAM_MAJOR`, `DEFAULT_VALIDATION_LEVEL` | constants | `"generalized-notation-notation"`, `"gnn"`, `4`, `"standard"`. |
| `UpstreamGNNValidation` | dataclass | Outcome of a validation call (`available`, `ok`, `errors`, `version`, `skipped_reason`). |
| `run_upstream_validate_gnn(markdown, *, validation_level="standard")` | `UpstreamGNNValidation` | Stage the markdown to a temporary `.gnn.md` file and run upstream `validate_gnn_syntax` at the given `ValidationLevel` (`basic` / `standard` / `strict` / `research` / `round_trip`). |
| `upstream_validate_markdown(markdown)` | `UpstreamGNNValidation` | Alias with the default level. |
| `upstream_validate_file_content(content, *, is_content=True)` | `dict` | Upstream `validate_gnn_source` on raw content or a path (GNN 2.x `validate_gnn_file`). |
| `upstream_parse_file(path)` | `Any` | Upstream `parse_gnn_file`. |
| `upstream_discover_files(root)` | `Any` | Upstream `discover_gnn_files`. |
| `upstream_process_directory(input_dir, output_dir, **kw)` | `Any` | Upstream `process_gnn_directory`. |
| `upstream_process_directory_lightweight(input_dir, output_dir, **kw)` | `Any` | Upstream `process_gnn_directory_lightweight`. |
| `upstream_process_multi_format(input_dir, output_dir, log=None, **kw)` | `Any` | Upstream `process_gnn_multi_format`. |
| `upstream_parse_formal(*a, **kw)` | `Any` | Upstream `parse_gnn_formal`. |
| `upstream_validate_syntax_formal(*a, **kw)` | `Any` | Upstream `validate_gnn_syntax` (GNN 2.x `validate_gnn_syntax_formal`). |
| `upstream_validate_structure(*a, **kw)` | `Any` | Upstream `check_gnn_file_structure` (GNN 2.x `validate_gnn_structure`). |
| `upstream_generate_report(*a, **kw)` | `Any` | Upstream `generate_gnn_report`. |
| `upstream_module_info(*a, **kw)` | `Any` | Upstream `get_module_info`. |
| `get_upstream_parsing_system()` | `Any` | Upstream `GNNParsingSystem` instance. |
| `get_upstream_gnn_format_enum()` | `Any` | Upstream `GNNFormat` enum. |
| `parse_upstream_model_gnn_md(package_dir)` | `dict` | One-shot parse of a synthesized package's `model.gnn.md`; returns an `error` entry instead of raising. |
| `json_safe(obj)` | `Any` | Best-effort JSON-coerce upstream return values for bundle storage. |

## Upstream GNN 25-step pipeline (`pipeline.py`)

`pipeline.py` drives the upstream numbered pipeline over a COGANT-built
`gnn_package/`. GNN 4.x binds step selection, source identity, output
ownership, and deadlines to one invocation, so the driver issues exactly
**one** `python -m gnn.main --target-dir … --output-dir … --only-steps …`
subprocess on COGANT's active interpreter and reads per-step outcomes from
`<output_dir>/00_pipeline_summary/pipeline_execution_summary.json`.

| Symbol | Purpose |
| --- | --- |
| `UPSTREAM_STEP_SCRIPTS: tuple[str, ...]` | Canonical 25 numbered scripts indexed by step number; single source of truth. |
| `DEFAULT_SKIP_STEPS: frozenset[int]` | `{1, 2, 11, 12}` — setup, tests, render, execute; off by default. |
| `SUCCESS_STATUSES` | `{"SUCCESS", "SUCCESS_WITH_WARNINGS", "SKIPPED"}` — statuses counted as a passing step. |
| `DEFAULT_TIMEOUT_S` | Bridge-level wall-clock ceiling (3600 s) for the single invocation; upstream applies its own per-step deadlines inside it. |
| `resolve_steps(only, skip)` | Pure helper returning the ordered step indices to request. |
| `UpstreamPipelineConfig` | Inputs: `target_dir`, `output_dir`, `only_steps`, `skip_steps` (default `sorted(DEFAULT_SKIP_STEPS)`), `frameworks`, `llm_model` (child-env `OLLAMA_MODEL`; the caller's env is never mutated), `timesteps`, `verbose`, `skip_llm`, `timeout_s`. |
| `UpstreamStepResult` | Per-step outcome: `step_index`, `script`, `status` (upstream status, or `NOT_RUN` / `TIMEOUT` / `BRIDGE_ERROR`), `success`, `duration_s`, `exit_code`, `memory_delta_mb`, `output_dir`, `error`. |
| `UpstreamPipelineResult` | Aggregate: `available`, `steps`, `executed`, `skipped`, `total_duration_s`, `output_dir`, `target_dir`, `error`, `upstream_status`, `run_id`, `auto_included`, plus `success_count` / `failure_count` / `success_rate` and `to_dict()`. |
| `run_upstream_pipeline(cfg)` | Driver: stages `*.gnn.md` into `<output_dir>/_cogant_input/`, runs the single invocation (console log to `<output_dir>/upstream_pipeline.log`), maps the upstream summary onto one `UpstreamStepResult` per requested step, and writes `<output_dir>/upstream_pipeline_summary.json`. |

### Step catalogue

| # | Script | Default | Notes |
| --- | --- | --- | --- |
| 0 | `0_template.py` | on | Project scaffolding sanity check. |
| **1** | `1_setup.py` | **off** | Provisions a uv environment relative to an upstream source checkout; from an installed wheel it creates a stray `.venv` in the caller's environment and its `uv sync` repair can uninstall packages. Do not enable it against a shared environment. |
| **2** | `2_tests.py` | **off** | Upstream's own repository test suite, which the wheel does not ship. |
| 3 | `3_gnn.py` | on | Core GNN parsing / discovery. |
| 4 | `4_model_registry.py` | on | Register parsed models. |
| 5 | `5_type_checker.py` | on | Type-check of GNN sections. |
| 6 | `6_validation.py` | on | Schema + cross-section validation. |
| 7 | `7_export.py` | on | Multi-format export. |
| 8 | `8_visualization.py` | on | Static visualisations. |
| 9 | `9_advanced_viz.py` | on | Interactive visualisations; some features need the D2 CLI. Filename retained verbatim for upstream parity. |
| 10 | `10_ontology.py` | on | Active Inference Ontology (AIO) lookup. |
| **11** | `11_render.py` | **off** | Framework code generation (PyMDP, JAX, DisCoPy, bnlearn, …). |
| **12** | `12_execute.py` | **off** | Runs the rendered scripts (upstream default `GNN_SANDBOX=off`). |
| 13 | `13_llm.py` | on | LLM analysis (Ollama; honours `--upstream-gnn-llm-model`). With `skip_llm=True` the bridge adds 13 to the skip set, so it is never requested. |
| 14 | `14_ml_integration.py` | on | ML integration (training skipped without scikit-learn). |
| 15 | `15_audio.py` | on | Audio rendering of model dynamics. |
| 16 | `16_analysis.py` | on | Statistical analysis. |
| 17 | `17_integration.py` | on | Cross-format integration checks. |
| 18 | `18_security.py` | on | Security scan of the package. |
| 19 | `19_research.py` | on | Research-mode exploration. |
| 20 | `20_website.py` | on | Static HTML report for the package. |
| 21 | `21_mcp.py` | on | Model Context Protocol exports. |
| 22 | `22_gui.py` | on | GUI export (static headless artifacts without Gradio). |
| 23 | `23_report.py` | on | Pipeline report. |
| 24 | `24_intelligent_analysis.py` | on | Final synthesis pass. |

Upstream GNN 5.0.1 resolves hard step prerequisites inside the invocation:
`12_execute` requires `3, 11`, `16_analysis` requires `3, 7, 12`, and
`18_security` requires `11`. Upstream applies `--skip-steps` *after* that
resolution, so the bridge always passes its skip set (`skip_steps`, plus `13`
under `skip_llm`) explicitly: a skipped step never runs, and a requested step
whose prerequisite is skipped still runs with an upstream prerequisite warning
(the default selection runs `16`/`18` without `11`/`12`). Prerequisites that
are *not* skipped are auto-included by upstream; the bridge reports them in
`UpstreamPipelineResult.auto_included`, includes their step records, and
counts them in `executed`.

### Wiring

* `PipelineConfig.upstream_gnn_pipeline` (default `False`) is the master
  opt-in. When `True`, `PipelineRunner._stage_validate` invokes
  `run_upstream_pipeline` against `bundle.artifacts['_gnn_package_dir']`
  after COGANT's own GNN validator runs (output root
  `<run output>/upstream_pipeline/` unless
  `PipelineConfig.upstream_gnn_output_dir` is set).
* Per-step results are recorded as
  `bundle.artifacts['upstream_pipeline_steps']` (list of step dicts) and
  `bundle.artifacts['upstream_pipeline_summary']` (aggregate). A failing
  step adds a single line to `validation.warnings` but never fails the
  validate stage.
* CLI: `cogant analyze | translate | validate --upstream-gnn-pipeline`
  toggles the pass; `--upstream-gnn-only-steps "3,5,7"` and
  `--upstream-gnn-skip-steps "1,2,11,12,13"` refine it (`""` skips
  nothing). `cogant upstream-gnn <package_dir>` runs the pass against an
  existing package directory and exits 1 when any requested step fails.

### Side-effects to know

* Importing `gnn.main` has no working-directory or import-path side effects
  in GNN 4.x, so the bridge needs no cwd guard.
* The child process inherits COGANT's environment with `PYTHONUNBUFFERED=1`,
  `GNN_RUN_ID` / `GNN_RUN_CONTEXT_FILE` removed (upstream mints a fresh run
  identity), and `OLLAMA_MODEL` set only when `llm_model` is given.
* Only GNN markdown is staged as the upstream corpus: GNN 4.x discovery
  treats every `*.json` file as a model source, and the COGANT sidecars are
  package evidence, not standalone models.
* A summary older than the invocation start is ignored (it belongs to a
  previous run in the same output root); requested steps upstream never
  reached are reported as `NOT_RUN`.
* For the calculator example the default selection takes a few minutes
  (about 140 s on 2026-10-14).

## Conventions

* Every facade function is **side-effect-free at import time**: heavy
  upstream imports happen inside the function body via
  `_require_upstream_gnn()` so `import cogant` does not pull in JAX.
* `run_upstream_validate_gnn` never raises on a missing upstream — it
  returns `UpstreamGNNValidation(available=False, ok=True, skipped_reason=…)`
  so callers can fall back to COGANT-only checks. The thin `upstream_*`
  passthroughs raise `ImportError` when upstream is unavailable;
  `parse_upstream_model_gnn_md` returns a dict with an `"error"` key instead.
* Parsing helpers return JSON-coercible payloads via `json_safe()` so the
  bundle's `to_json()` succeeds even when upstream returns Pydantic models or
  dataclasses.
* `pipeline.py` follows the same rules: it returns an
  `UpstreamPipelineResult(available=False, error=…)` instead of raising
  when `gnn.main` cannot be imported.

## Tests

* `tests/unit/test_gnn_upstream_bridge.py` — the absent `src.gnn` surface,
  the version/ownership gate, renamed-API routing to the GNN 4.x names, and
  validator wiring.
* `tests/unit/test_gnn_upstream_bridge_contract.py` — `json_safe` coercion
  and smoke calls for every `upstream_*` facade.
* `tests/unit/test_gnn_validator_upstream_flags.py` — `_resolve_upstream_flag`
  and the validator's upstream branches.
* `tests/unit/test_upstream_pipeline_resolution.py` — step catalogue
  invariants, `resolve_steps`, the single-invocation command, summary
  mapping (`NOT_RUN`, ignored previous summaries, timeouts), and the
  unavailable-bridge result.
* `tests/integration/test_upstream_gnn_pipeline.py` — real package, real
  `python -m gnn.main` invocations: `only_steps=[3,5]`, upstream acceptance
  steps 3/5/6 on a freshly emitted package, default-skip semantics, JSON
  round-trip, and render+execute opt-in (gated on `jax`). Tests skip when
  `gnn.main` is not importable.
