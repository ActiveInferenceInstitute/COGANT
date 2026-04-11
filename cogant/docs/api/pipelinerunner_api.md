## PipelineRunner API

The `PipelineRunner` orchestrates all stages in sequence with configuration.

### Basic Usage

```python
from cogant.api.pipeline import PipelineRunner, PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_repo", config)
```

### Configuration

```python
from cogant.api.pipeline import PipelineConfig

config = PipelineConfig(
    # Stages to execute in order
    stages=[
        "ingest",
        "static",
        "normalize",
        "graph",
        "translate",
        "statespace",
        "process",
        "export",
        "validate",
    ],
    # Skip specific stages
    skip_stages=["dynamic", "process"],
    # Plugin configurations
    plugins={
        "python": {"version": "3.9"},
        "java": {"jdk_home": "/usr/lib/jvm/java-11"},
    },
    # Output directory
    output_dir="output/",
    # Enable verbose logging
    verbose=True,
    # Dry run (no side effects)
    dry_run=False,
)

bundle = runner.run("./my_repo", config)
```

### Accessing Results

```python
# Check for errors
if bundle.errors:
    print(f"Errors: {bundle.errors}")

# Get stage results
for stage, result in bundle.stage_results.items():
    print(f"{stage}: {result['type']}")

# Access specific stages
graph = bundle.stage_results.get("graph", {})
gnn = bundle.stage_results.get("translate", {})
state_space = bundle.stage_results.get("statespace", {})
```

## Examples

`PipelineRunner` and `PipelineConfig` (including the `stages` / `skip_stages` / `plugins` knobs above) are exercised by:

- **Zoo:** [`examples/zoo/04_pomdp_minimal/`](../../examples/zoo/04_pomdp_minimal/) — smallest target that meaningfully exercises every stage in the default `stages=[...]` list.
- **Zoo:** [`examples/zoo/12_full_pomdp/`](../../examples/zoo/12_full_pomdp/) — full pipeline integration target including `process` and `validate` stages.
- **Cookbook:** [Recipe 1: Scan your first Python project](../cookbook/01_scan_basic.md) — `PipelineRunner.run()` from a one-liner.
- **Cookbook:** [Recipe 5: Multi-project scans](../cookbook/05_multi_project.md) — reusing one `PipelineConfig` across many targets.
- **Cookbook:** [Recipe: Analyze a Flask app](../cookbook/analyze_a_flask_app.md) — `PipelineRunner` against the canonical 98-node fixture.
- **Tutorial:** [Tutorial 1: Quickstart](../tutorials/01_quickstart.md) — Method 2 (orchestrated pipeline) walkthrough.
- **Tutorial:** [Tutorial 3: Flask walkthrough](../tutorials/03_flask_walkthrough.md) — full `stages` list against a real-world repo.

