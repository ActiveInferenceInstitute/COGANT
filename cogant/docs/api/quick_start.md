## Quick Start

> **What this page is:** Copy-pasteable Python snippets for the two most common COGANT API entry points: a manual `Session` and an orchestrated `PipelineRunner`.
>
> **Prerequisites:** [Installation](installation.md) and the [API overview](overview.md).
>
> **Reading time:** ~5 minutes
>
> **Next steps:** [Session API](session_api.md) · [PipelineRunner API](pipelinerunner_api.md) · [Bundle API](bundle_api.md)

```python
from cogant import Session, PipelineRunner, Bundle
from cogant.api.pipeline import PipelineConfig

# Method 1: Simple Session
session = Session.from_target("./my_repo")
session.extract_static()
session.build_graph()
session.translate_to_gnn()
session.export_all("output/")

# Method 2: Orchestrated Pipeline
runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_repo", config)

# Access results
print(bundle.repo_summary())
bundle.save_json("output/bundle.json")  # same artifact as `cogant translate --output output/`
bundle.render_site("html_site/")
```

## Examples

The two snippets above are run end-to-end against real targets in:

- **Zoo:** [`examples/zoo/01_simple_state/`](../../examples/zoo/01_simple_state/) — point `Session.from_target("./examples/zoo/01_simple_state")` here for the smallest reproducible run.
- **Zoo:** [`examples/zoo/12_full_pomdp/`](../../examples/zoo/12_full_pomdp/) — exercises every stage in `PipelineConfig.stages` on a non-trivial repo.
- **Cookbook:** [Recipe 1: Scan your first Python project](../cookbook/01_scan_basic.md) — Method 1 (Session) recipe.
- **Cookbook:** [Recipe 2: JSON output](../cookbook/02_json_output.md) — Method 2 (PipelineRunner + `bundle.save_json`).
- **Tutorial:** [Tutorial 1: Quickstart](../tutorials/01_quickstart.md) — five-minute walkthrough that maps directly onto Method 1.
- **Tutorial:** [Tutorial 3: Flask walkthrough](../tutorials/03_flask_walkthrough.md) — same API on a real-world six-module Flask app.

