# Experimental setup: environment, API, and configuration {#sec:06-01-environment-api-and-config}

## Environment

**Requirements**: Python 3.11 or newer (enforced in `pyproject.toml`), plus an optional Rust toolchain (`cargo`, stable 1.70+) when building native acceleration crates under `../cogant/rust/`.

From the COGANT package root [`../cogant/`](../cogant/) (where `pyproject.toml` and `py/cogant/` live), install with `uv sync --all-extras`, or `pip install -e ".[dev,viz]"` / `pip install -e ".[all]"` as in the MkDocs guides [`../cogant/docs/getting-started/installation.md`](../cogant/docs/getting-started/installation.md) and [`../cogant/docs/getting-started/quickstart.md`](../cogant/docs/getting-started/quickstart.md). Run those commands from that directory when working inside this monorepo layout. Python sources live under [`../cogant/py/cogant/`](../cogant/py/cogant/); see the package [README.md](../cogant/README.md).

## Terminology: runner stages and conceptual IRs

The **`PipelineRunner`** executes an ordered list of **runner stages** (for example ingest → static → normalize → graph → dynamic → translate → statespace → process → export → validate), recorded in `cogant/evaluation/METRICS.yaml` as `pipeline.runner_stages`. Separately, Chapter 2 and [`06_02_exports_parser_and_ir_stages.md`](06_02_exports_parser_and_ir_stages.md) describe a **six-layer conceptual IR progression** (repo snapshot through validation reports). Those layers are *artifacts* and documentation structure; they are not a 1:1 rename of the runner-stage list. Use “runner stage” when referring to `PipelineConfig.stages`, and “IR layer” when referring to the methodological table.

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

YAML configuration can drive pipeline behavior (paths, stages, plugin options). [`../cogant/docs/architecture/README.md`](../cogant/docs/architecture/README.md) and [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md) describe the configuration surface; keep project-specific secrets out of version control.

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

Use the `cogant` CLI for scripted batch runs—see `../cogant/docs/cli/README.md` and [`../cogant/docs/cli_reference.md`](../cogant/docs/cli_reference.md) for the command list that matches the installed version.

## See also (MkDocs)

Installation and environment: [`../cogant/docs/getting-started/installation.md`](../cogant/docs/getting-started/installation.md). Pipeline stage order (runner): [`../cogant/docs/reference/pipeline_stages.md`](../cogant/docs/reference/pipeline_stages.md).
