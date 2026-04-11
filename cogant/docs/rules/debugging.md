## Debugging

### Enable Rule Logging

```yaml
# cogant.yaml
translation:
  rule_set: default
  debug: true
  log_level: debug
```

Output:
```
[INFO] Applying rule_fn_def_001 to fn_process
[DEBUG] - Matches: true (type_name="Callable[[list], dict]")
[DEBUG] - Confidence: 1.0
[DEBUG] - Applied mapping: FUNCTION_DEF
```

### Inspect Rule Application

```python
# doctest: +SKIP  # example requires runtime context or external resources
from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./my_project", config)

# Inspect translation stage results
translate_result = bundle.stage_results.get("translate", {})
print(f"Mappings: {len(translate_result.get('mappings', []))}")
```

