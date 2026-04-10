# Recipe 4: Tuning Confidence Thresholds

**Goal:** Adjust the translation confidence thresholds via a pipeline config file.
**Time:** ~5 minutes.

## Prerequisites

- COGANT installed
- A Python project directory

## Steps

### 1. Create a pipeline config file

```bash
cat > cogant-config.yaml << 'EOF'
pipeline:
  stages:
    - ingest
    - static
    - normalize
    - graph
    - translate
    - statespace
    - process
    - export
    - validate
  plugins:
    translate:
      confidence_threshold: 0.65
      min_evidence_edges: 2
EOF
```

The `confidence_threshold` controls how confident a translation rule
must be before assigning a role. Lower values produce more assignments
but with more noise; higher values are stricter.

### 2. Run translate with the config

```bash
cogant translate ./my-project --config cogant-config.yaml --output ./output-tuned
```

### 3. Compare against the default threshold

Run a second translation with defaults:

```bash
cogant translate ./my-project --output ./output-default
```

Then diff the two runs:

```bash
cogant diff ./output-default ./output-tuned
```

### 4. Iterate

Adjust `confidence_threshold` in the YAML and re-run. Common ranges:

| Threshold | Behavior |
|-----------|----------|
| 0.3 - 0.5 | Aggressive: more nodes assigned, more false positives |
| 0.5 - 0.7 | Balanced (default range) |
| 0.7 - 0.9 | Conservative: fewer assignments, higher precision |

## Expected output

The `cogant diff` output shows which nodes gained or lost role
assignments between the two runs, along with an architectural drift
score.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Warning: failed to load config` | Check YAML syntax; ensure `pipeline:` is the top-level key |
| All nodes unassigned | Threshold is too high; lower it to 0.5 |
| Too many noisy assignments | Raise the threshold or increase `min_evidence_edges` |
