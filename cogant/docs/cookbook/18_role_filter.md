# Recipe 18: Filtering Results by Semantic Role

**Goal:** Extract only nodes with a specific Active Inference role from COGANT output.
**Time:** ~5 minutes.

## Prerequisites

- COGANT installed
- `jq` installed for JSON processing

## Steps

### 1. Translate the project

```bash
cogant translate ./my-project --output ./output --no-dynamic
```

### 2. Inspect the program graph

```bash
jq 'keys' ./output/bundle.json
```

The translation results include nodes with semantic roles assigned.

### 3. Filter nodes by role using jq

Extract all nodes assigned the "internal state" (mu) role:

```bash
jq '[
  .stage_results.translate.nodes[]
  | select(.role == "mu")
  | {name: .name, role: .role, confidence: .confidence}
]' ./output/bundle.json
```

### 4. Filter for sensory nodes

```bash
jq '[
  .stage_results.translate.nodes[]
  | select(.role == "eta")
  | {name: .name, role: .role}
]' ./output/bundle.json
```

### 5. Get a role distribution summary

```bash
jq '
  .stage_results.translate.nodes
  | group_by(.role)
  | map({role: .[0].role, count: length})
  | sort_by(-.count)
' ./output/bundle.json
```

### 6. Export filtered nodes to a CSV

```bash
jq -r '
  .stage_results.translate.nodes[]
  | select(.role == "mu" or .role == "a")
  | [.name, .role, .confidence]
  | @csv
' ./output/bundle.json > active_nodes.csv
```

### 7. Use explain for deep inspection

For any node in the filtered list:

```bash
cogant explain ./my-project "NodeName" --format json
```

## Expected output

```json
[
  {"name": "UserService", "role": "mu", "confidence": 0.87},
  {"name": "DatabasePool", "role": "mu", "confidence": 0.92},
  {"name": "CacheManager", "role": "mu", "confidence": 0.78}
]
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `null` or empty result | Check the correct JSON path; run `jq 'keys' bundle.json` to explore |
| No nodes with a role | The translation may have produced empty results; check `cogant scan` output |
| jq syntax error | Ensure jq is version 1.6+; test filters incrementally |
