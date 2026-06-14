## Validation Report

### Format

```json
{
  "version": "1.0.0",
  "validation_run": {
    "id": "val_001",
    "timestamp": "2024-10-01T14:00:00Z",
    "analyzed_graph": "graph_pyproject",
    "status": "PASS"  // PASS, WARN, FAIL
  },
  "metrics": {
    "coverage": {...},
    "confidence": {...},
    "consistency": {...}
  },
  "issues": [
    {
      "level": "WARNING",
      "code": "W001",
      "message": "Node fn_helper has no callers",
      "node_id": "node_xyz",
      "file": "src/helpers.py",
      "line": 50,
      "suggested_action": "Consider removing or documenting"
    }
  ],
  "statistics": {
    "total_issues": 5,
    "info_count": 2,
    "warning_count": 3,
    "error_count": 0
  },
  "reproducibility": {
    "cogant_version": "0.6.0",
    "input_hash": "sha256:abc123...",
    "config_hash": "sha256:def456..."
  }
}
```

### Generate Report

```python
# doctest: +SKIP  # example requires runtime context or external resources
from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_project", config)

# Get validation report
report = bundle.validation_report()

# Print summary
print(f"Passed: {report.get('passed')}")
print(f"Checks: {report.get('checks', {})}")
for warning in report.get("warnings", []):
    print(f"  WARNING: {warning}")

# Save bundle (includes validation) as JSON
bundle.save_json("output/bundle.json")
```
