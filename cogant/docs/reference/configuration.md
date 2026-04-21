## Configuration

### Project Configuration

```yaml
# cogant.yaml in project root

version: 1

discovery:
  languages: [python, javascript, rust]
  include_tests: false
  exclude_patterns:
    - "**/test_*.py"
    - "**/mock_*.js"

parsing:
  python_version: "3.11"
  javascript_version: "es2021"

translation:
  rule_set: "default"
  min_confidence: 0.6
  include_low_confidence: true
  custom_rules:
    - path: "my_rules.py"

statespace:
  trace_file: "trace.json"

validation:
  min_coverage: 0.95

export:
  formats: [json, pytorch_geometric, dgl]
  compression: gzip
  output_dir: "./gnn_bundles"
```

### Precedence

1. Defaults (built-in)
2. Global config (`~/.cogant/config.yaml`)
3. Project config (`cogant.yaml`)
4. Stage-specific config (`cogant.{stage}.yaml`)
5. CLI arguments
