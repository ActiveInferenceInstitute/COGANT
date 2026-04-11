# Experimental setup: environment, API, and configuration

# Experimental setup

## Environment

**Requirements**: Python 3.11 or newer (enforced in `pyproject.toml`), plus an optional Rust toolchain (`cargo`, stable 1.70+) when building native acceleration crates under `../cogant/rust/`.

From the COGANT package root [`../cogant/`](../cogant/) (where `pyproject.toml` and `py/cogant/` live), install with `uv sync --all-extras`, or `pip install -e ".[dev,viz]"` / `pip install -e ".[all]"` as in [GETTING_STARTED.md](../cogant/GETTING_STARTED.md). Run those commands from that directory when working inside this monorepo layout. Python sources live under [`../cogant/py/cogant/`](../cogant/py/cogant/); see the package [README.md](../cogant/README.md).

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

Use the `cogant` CLI for scripted batch runs—see `../cogant/docs/cli/README.md` for the command list that matches the installed version.
