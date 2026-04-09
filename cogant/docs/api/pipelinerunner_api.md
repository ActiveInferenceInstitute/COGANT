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

