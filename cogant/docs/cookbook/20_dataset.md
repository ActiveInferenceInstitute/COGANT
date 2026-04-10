# Recipe 20: Exporting a Training Dataset for ML

**Goal:** Export COGANT analysis results as a structured dataset for machine learning.
**Time:** ~10 minutes.

## Prerequisites

- COGANT installed
- `jq` installed
- One or more translated repositories

## Steps

### 1. Translate a project

```bash
cogant translate ./my-project --output ./output --no-dynamic
```

### 2. Export the bundle as JSON

```bash
cogant export-gnn ./output/bundle.json --output ./export --format json
```

### 3. Extract node features

Create a node-level dataset with features and labels:

```bash
jq '[
  .stage_results.translate.nodes[]
  | {
      name: .name,
      kind: .kind,
      role: .role,
      confidence: .confidence,
      in_degree: (.edges_in // [] | length),
      out_degree: (.edges_out // [] | length),
      method_count: (.methods // [] | length),
      has_state: (.has_state // false)
    }
]' ./output/bundle.json > nodes_dataset.json
```

### 4. Convert to CSV

```bash
jq -r '
  ["name","kind","role","confidence","in_degree","out_degree","method_count","has_state"],
  (.[] | [.name, .kind, .role, .confidence, .in_degree, .out_degree, .method_count, .has_state])
  | @csv
' nodes_dataset.json > nodes_dataset.csv
```

### 5. Extract edge features

```bash
jq '[
  .stage_results.graph.edges[]
  | {
      source: .source,
      target: .target,
      kind: .kind,
      weight: (.weight // 1.0)
    }
]' ./output/bundle.json > edges_dataset.json
```

### 6. Batch-export from multiple repos

```bash
for repo in ./repos/*/; do
  name=$(basename "$repo")
  cogant translate "$repo" --output "./batch/$name" --no-dynamic 2>/dev/null

  jq --arg repo "$name" '[
    .stage_results.translate.nodes[]
    | . + {repo: $repo}
  ]' "./batch/$name/bundle.json"
done | jq -s 'add' > combined_nodes.json
```

### 7. Generate adjacency matrices

```bash
jq '{
  nodes: [.stage_results.graph.nodes | keys[]],
  edges: [
    .stage_results.graph.edges[]
    | [.source, .target, (.weight // 1.0)]
  ]
}' ./output/bundle.json > adjacency.json
```

## Expected output

`nodes_dataset.csv`:

```csv
"name","kind","role","confidence","in_degree","out_degree","method_count","has_state"
"UserService","class","mu",0.87,3,5,4,true
"auth_handler","function","a",0.72,1,2,0,false
"db_connection","module","eta",0.91,0,3,0,false
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `null` values in jq output | Use `// default` to provide fallback values |
| Empty dataset | Ensure `cogant translate` completed without errors |
| Missing fields | COGANT's JSON schema may vary by version; inspect with `jq 'keys'` first |
| Large files | Filter by role or confidence threshold before export |
