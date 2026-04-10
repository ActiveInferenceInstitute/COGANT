# Recipe 12: Batch-Scanning Multiple Repos

**Goal:** Translate many repositories in a single shell loop and collect results.
**Time:** ~10 minutes.

## Prerequisites

- COGANT installed
- Multiple repository directories (or a directory of cloned repos)

## Steps

### 1. Organize your repos

```
repos/
  repo-alpha/
  repo-beta/
  repo-gamma/
```

### 2. Batch translate

```bash
#!/usr/bin/env bash
set -e

REPOS_DIR="./repos"
OUTPUT_DIR="./batch-output"
ERRORS=()

for repo in "$REPOS_DIR"/*/; do
  name=$(basename "$repo")
  echo "=== Translating $name ==="

  if cogant translate "$repo" --output "$OUTPUT_DIR/$name" --no-dynamic 2>&1; then
    echo "  OK: $name"
  else
    echo "  FAIL: $name"
    ERRORS+=("$name")
  fi
done

echo ""
echo "=== Summary ==="
echo "Total: $(ls -d "$REPOS_DIR"/*/ | wc -l | tr -d ' ')"
echo "Failed: ${#ERRORS[@]}"
for e in "${ERRORS[@]}"; do
  echo "  - $e"
done
```

### 3. Validate all outputs

```bash
for dir in ./batch-output/*/; do
  name=$(basename "$dir")
  echo "--- $name ---"
  cogant validate "$dir" || echo "  INVALID: $name"
done
```

### 4. Export a combined summary

```bash
for dir in ./batch-output/*/; do
  name=$(basename "$dir")
  echo "$name: $(jq '.errors | length' "$dir/bundle.json" 2>/dev/null || echo 'N/A') errors"
done
```

### 5. Run in parallel (GNU parallel)

```bash
ls -d ./repos/*/ | parallel -j4 \
  'name=$(basename {}); cogant translate {} --output ./batch-output/$name --no-dynamic'
```

## Expected output

Each repo produces its own output directory with `bundle.json` and
(if validation passes) a `gnn_package/` subdirectory.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Some repos fail | Check the error output; common causes are missing source files or permission issues |
| Disk space | Each output is typically 1-10 MB; clean up with `rm -rf ./batch-output/*/` |
| Slow on many repos | Use GNU parallel (`-j4`) or `xargs -P4` for concurrent runs |
