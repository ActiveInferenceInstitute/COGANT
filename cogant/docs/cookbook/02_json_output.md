# Recipe 2: Exporting Program Graph as JSON

**Goal:** Translate a repository and export the program graph as a JSON file.
**Time:** ~5 minutes.

## Prerequisites

- COGANT installed
- A Python or JS/TS project directory

## Steps

### 1. Run the full translation pipeline

```bash
cogant translate ./my-project --output ./cogant-output
```

This runs all pipeline stages (ingest, static, normalize, graph,
translate, statespace, process, export, validate) and writes
`bundle.json` to the output directory.

### 2. Inspect the bundle

```bash
cat ./cogant-output/bundle.json | python3 -m json.tool | head -40
```

The bundle contains `target`, `artifacts`, `stage_results`, `errors`,
and `metadata` keys.

### 3. Re-export in JSON-only format

If you already have a bundle and want a clean re-export:

```bash
cogant export-gnn ./cogant-output/bundle.json --output ./export --format json
```

### 4. Extract the program graph with jq

```bash
jq '.stage_results.graph' ./cogant-output/bundle.json > program_graph.json
```

## Expected output

```
Exporting ./cogant-output/bundle.json
 JSON  ./export/bundle.json

 Export complete
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `bundle.json` is empty | Check `cogant translate` completed without errors |
| `stage_results.graph` is null | The graph stage may have been skipped; run without `--skip` |
| Large JSON file | Use `jq` to extract only the keys you need |
