## Configuration System

### Config Hierarchy

```
Defaults → Global → Project → Stage → CLI
   │          │         │        │      └─ Highest precedence
   │          │         │        └─────────
   │          │         └──────────────────
   │          └─────────────────────────────
   └──────────────────────────────────────── Lowest precedence
```

### Example Config

```yaml
version: 1

discovery:
  languages: [python]
  include_tests: false

parsing:
  python_version: "3.11"

translation:
  rule_set: "default"
  min_confidence: 0.6

export:
  formats: [json, pytorch_geometric]
  output_dir: "./output"
```

