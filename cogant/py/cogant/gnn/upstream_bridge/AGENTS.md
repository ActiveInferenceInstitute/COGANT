# `cogant.gnn.upstream_bridge`

## Purpose

Lazy facade over the Active Inference Institute upstream package
**`generalized-notation-notation`** (PyPI distribution name;
import path `src.gnn`). Lets COGANT validate / parse / round-trip GNN
markdown using the canonical reference implementation while keeping
heavy dependencies (JAX, PyTorch) out of the eager import path.

* Upstream license: **CC-BY-NC-SA-4.0** — see `cogant/LICENSES.md`.
* Disable upstream calls with the env flag
  `COGANT_DISABLE_UPSTREAM_GNN=1`, or via the
  `PipelineConfig.upstream_gnn_validation = False` knob.

## Public API

All callers should use the `upstream_*` facade — never `import src.gnn`
directly anywhere else in the package.

| Symbol | Returns | Use |
| --- | --- | --- |
| `is_upstream_gnn_available()` | `bool` | Probe; never raises. |
| `upstream_version()` | `str \| None` | Upstream package version, when available. |
| `UpstreamGNNValidation` | dataclass | Outcome of a validation call (`available`, `ok`, `errors`, `version`, `skipped_reason`). |
| `run_upstream_validate_gnn(markdown)` | `UpstreamGNNValidation` | Run upstream validators against an in-memory GNN markdown string. |
| `upstream_validate_markdown(markdown)` | `UpstreamGNNValidation` | Convenience alias. |
| `upstream_validate_file_content(text, name)` | `UpstreamGNNValidation` | Validate a string with a synthetic file name (used by reverse path). |
| `upstream_parse_file(path)` | `Any` | Parse a single `.md` file. |
| `upstream_discover_files(root)` | `Any` | List GNN files under a root. |
| `upstream_process_directory(root, **kw)` | `Any` | Run upstream's batch processing pipeline. |
| `upstream_process_directory_lightweight(root, **kw)` | `Any` | Skip simulator-heavy steps; used in tests. |
| `upstream_process_multi_format(root, **kw)` | `Any` | Multi-format export driver. |
| `upstream_parse_formal(*a, **kw)` | `Any` | Bridge to upstream formal-grammar parser. |
| `upstream_validate_syntax_formal(*a, **kw)` | `Any` | Strict syntactic validation. |
| `upstream_validate_structure(*a, **kw)` | `Any` | Structural (section-level) validation. |
| `upstream_generate_report(*a, **kw)` | `Any` | Render upstream's report HTML/JSON. |
| `upstream_module_info(*a, **kw)` | `Any` | Introspection helper. |
| `get_upstream_parsing_system()` | `Any` | Upstream `ParsingSystem` instance. |
| `get_upstream_gnn_format_enum()` | `Any` | Upstream `GNNFormat` enum. |
| `parse_upstream_model_gnn_md(package_dir)` | `dict` | One-shot parse of a synthesized package's `model.gnn.md`. |
| `json_safe(obj)` | `Any` | Best-effort JSON-coerce upstream return values for bundle storage. |

## Upstream GNN 25-step pipeline (`pipeline.py`)

`pipeline.py` drives the upstream **`src.main.execute_pipeline_step`**
orchestrator over a COGANT-built `gnn_package/`, exposing the full 25-step
Active Inference processing chain as a configurable post-validate pass.

| Symbol | Purpose |
| --- | --- |
| `UPSTREAM_STEP_SCRIPTS: tuple[str, ...]` | Canonical 25 numbered scripts indexed by step number; single source of truth. |
| `DEFAULT_SKIP_STEPS: frozenset[int]` | `{11, 12}` — render and execute, off by default. |
| `resolve_steps(only, skip)` | Pure helper returning the ordered step indices to execute. |
| `UpstreamPipelineConfig` | Inputs: `target_dir`, `output_dir`, `only_steps`, `skip_steps` (default `[11, 12]`), `frameworks`, `llm_model`, `timesteps`, `verbose`, `skip_llm`. |
| `UpstreamPipelineResult.success_rate` | Convenience ratio in `[0.0, 1.0]`; `0.0` for empty / unavailable runs. |
| `UpstreamStepResult` | Per-step outcome: `step_index`, `script`, `status`, `success`, `duration_s`, `exit_code`, `memory_delta_mb`, `output_dir`, `error`. |
| `UpstreamPipelineResult` | Aggregate outcome with `available`, `executed`, `skipped`, `success_count`, `failure_count`, `to_dict()` for JSON storage. |
| `run_upstream_pipeline(cfg)` | Driver — adapts a `PipelineArguments`, iterates the resolved step set, and calls `src.main.execute_pipeline_step` per step. Captures exceptions per step (one bad step does not abort the run). |

### Step catalogue

| # | Script | Default | Notes |
| --- | --- | --- | --- |
| 0 | `0_template.py` | on | Project scaffolding sanity check. |
| 1 | `1_setup.py` | on | Environment / deps; harmless when already met. |
| 2 | `2_tests.py` | on | Upstream's own GNN test sweep. |
| 3 | `3_gnn.py` | on | Core GNN parsing / discovery. |
| 4 | `4_model_registry.py` | on | Register parsed models. |
| 5 | `5_type_checker.py` | on | Strict type-check of GNN sections. |
| 6 | `6_validation.py` | on | Schema + cross-section validation. |
| 7 | `7_export.py` | on | Multi-format export (JSON, GraphML, Mermaid). |
| 8 | `8_visualization.py` | on | Static visualisations. |
| 9 | `9_advanced_viz.py` | on | Interactive / advanced visualisations. |
| 10 | `10_ontology.py` | on | Active Inference Ontology (AIO) lookup. |
| **11** | `11_render.py` | **off** | Framework code generation (PyMDP, RxInfer, JAX). Heavy; opt-in via `skip_steps=[]` or `only_steps=[..., 11, ...]`. |
| **12** | `12_execute.py` | **off** | Runs the rendered model. Requires JAX/PyMDP and a runnable bundle. |
| 13 | `13_llm.py` | on | LLM analysis (Ollama; honours `--upstream-gnn-llm-model`). |
| 14 | `14_ml_integration.py` | on | ML pipeline integration. |
| 15 | `15_audio.py` | on | Audio rendering of model dynamics. |
| 16 | `16_analysis.py` | on | Statistical analysis. |
| 17 | `17_integration.py` | on | Integration tests / cross-format checks. |
| 18 | `18_security.py` | on | Security scan of the package. |
| 19 | `19_research.py` | on | Research-mode exploration. |
| 20 | `20_website.py` | on | Static HTML report for the package. |
| 21 | `21_mcp.py` | on | Model Context Protocol exports. |
| 22 | `22_gui.py` | on | GUI export. |
| 23 | `23_report.py` | on | Pipeline report. |
| 24 | `24_intelligent_analysis.py` | on | Final synthesis pass. |

### Wiring

* `PipelineConfig.upstream_gnn_pipeline` (default `False`) is the master
  opt-in. When `True`, `PipelineRunner._stage_validate` invokes
  `run_upstream_pipeline` against `bundle.artifacts['_gnn_package_dir']`
  after COGANT's own GNN validator runs.
* Per-step results are recorded as
  `bundle.artifacts['upstream_pipeline_steps']` (list of step dicts) and
  `bundle.artifacts['upstream_pipeline_summary']` (aggregate). A failing
  step adds a single line to `validation.warnings` but never fails the
  validate stage.
* CLI: `cogant analyze | translate | validate --upstream-gnn-pipeline`
  toggles the pass; `--upstream-gnn-only-steps "3,5,7"` and
  `--upstream-gnn-skip-steps "11,12,13"` refine it. `cogant upstream-gnn
  <package_dir>` runs the pass against an existing package directory.

### Side-effects to know

* Importing `src.main` ``chdir``s to its own project root. The bridge
  saves and restores `os.getcwd()` around every upstream call via the
  internal `_preserve_cwd()` context manager so callers never observe
  the change.
* Each enabled step runs as a subprocess (upstream invokes
  `<venv>/bin/python <step>.py`). For the calculator example the full
  default-skip pass takes a few minutes, hence the
  `COGANT_RUN_UPSTREAM_PIPELINE=1` gate on the integration sweep.

## Conventions

* Every facade function is **side-effect-free at import time**: heavy
  upstream imports happen inside the function body via
  `_require_src_gnn()` so `import cogant` does not pull in JAX.
* Functions never raise on missing upstream — they return an
  `UpstreamGNNValidation` with `available=False` (or an empty `dict`
  with an `"error"` key) so callers can fall back to COGANT-only
  checks.
* Parsing helpers always return JSON-coercible payloads via
  `json_safe()` so the bundle's `to_json()` succeeds even when
  upstream returns Pydantic models or dataclasses.
* `pipeline.py` follows the same rules: it returns an
  `UpstreamPipelineResult(available=False, error=…)` instead of raising
  when `src.main` cannot be imported.

## Tests

* `tests/unit/test_upstream_bridge.py` — facade availability + JSON-safe
  coercion.
* `tests/unit/test_upstream_pipeline_resolution.py` — step catalogue
  invariants, `resolve_steps`, dataclass round-trips, unavailable-bridge
  fallback.
* `tests/integration/test_validate_stage.py` exercises
  `run_upstream_validate_gnn` end-to-end via `run_validate`.
* `tests/integration/test_upstream_gnn_pipeline.py` — real package, real
  subprocesses: default skip semantics, `only_steps=[3,5]`, JSON
  round-trip, render+execute opt-in (gated on `jax`), full-sweep test
  gated on `COGANT_RUN_UPSTREAM_PIPELINE=1`.
