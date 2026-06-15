# Experimental setup: environment, API, and configuration {#sec:06-01-environment-api-and-config}

## Environment

**Requirements**: Python 3.11 or newer (enforced in `pyproject.toml`), plus an optional Rust toolchain (`cargo`, stable 1.70+) when building native acceleration crates under `../cogant/rust/`.

From the COGANT package root `../cogant/` (where `pyproject.toml` and `py/cogant/` live), install with `uv sync --all-extras`, or `pip install -e ".[dev,viz]"` / `pip install -e ".[all]"` as in the MkDocs installation and quickstart guides under `../cogant/docs/getting-started/`. Run those commands from that directory when working inside this monorepo layout. Python sources live under `../cogant/py/cogant/`; package orientation is in `../cogant/README.md`.

The environment claim is checked operationally rather than by prose alone, consistent with software-citation and reproducible-record guidance [@smith2016softwareCitationPrinciples; @vanDeSandt2019zenodoSoftwareCitations]. From `../cogant/`, `uv run cogant doctor` exercises the installed interpreter, optional runtime dependencies, parser availability, Rust-extension visibility, and Git context. Configuration-shape regressions are covered by `uv run pytest tests/unit/test_api_pipeline_config_validation.py tests/unit/test_typed_config_loaders_e2e.py -q`, while CLI/runtime environment reporting is covered by `uv run pytest tests/unit/test_cli_doctor.py -q`. These checks do not prove that every user machine will match the development environment; they bound the environment claim to the package's documented install and configuration contracts.

## Terminology: runner stages and conceptual IRs

The **`PipelineRunner`** executes an ordered list of **runner stages** (for example ingest → static → normalize → graph → dynamic → translate → statespace → process → export → validate), recorded in `cogant/evaluation/METRICS.yaml` as `pipeline.runner_stages`. Separately, @sec:02-01-program-graph-and-formal-foundations and @sec:06-02-exports-parser-and-ir-stages describe a **six-layer conceptual IR progression** (repo snapshot through validation reports). Those layers are *artifacts* and documentation structure; they are not a 1:1 rename of the runner-stage list. Use “runner stage” when referring to `PipelineConfig.stages`, and “IR layer” when referring to the methodological table.

## Running the API

Minimal **Session** run:

```python
from cogant import Session

session = Session.from_target("./path/to/repo")
session.extract_static()
session.build_graph()
session.translate_to_gnn()
session.export_all("output/")
```

Minimal **Pipeline** run:

```python
from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./path/to/repo", config)
```

Adjust `PipelineConfig.stages`, `skip_stages`, and `plugins` to match the languages and tooling available on the machine.

## Configuration files

YAML configuration can drive pipeline behavior (paths, stages, plugin options). The architecture and implementation-status package docs under `../cogant/docs/` describe the configuration surface; keep project-specific secrets out of version control.

A minimal pipeline configuration looks like this:

```yaml
# cogant.config.yaml
pipeline:
  stages:
    - ingest
    - static
    - normalize
    - graph
    - dynamic       # optional; skipped if no coverage/trace inputs
    - translate
    - statespace
    - process
    - export
    - validate

  skip_stages: []   # e.g. ["dynamic"] to force static-only runs

  plugins:
    dynamic:
      coverage_path: "./coverage.xml"
      trace_path: "./chrome_trace.json"

  output_dir: "./cogant_output/"
  verbose: true
  dry_run: false
```

Each stage key corresponds to a handler in `cogant.api.pipeline.PipelineRunner.stage_handlers`; plugin sub-dictionaries are passed through to the stage at invocation time. `cogant translate --config` accepts either a top-level `pipeline` object or a flat mapping and normalizes both forms into `PipelineConfig`.

## CLI

Use the `cogant` CLI for scripted batch runs; `../cogant/docs/cli/README.md` and `../cogant/docs/cli_reference.md` contain the command list that matches the installed version.
