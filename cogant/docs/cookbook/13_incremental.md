# Recipe 13: Incremental Rescanning (Skip Unchanged Files)

**Goal:** Re-analyze only the files that changed since a previous run.
**Time:** ~5 minutes.

## Prerequisites

- COGANT installed
- A git repository with a previous COGANT output

## Steps

### 1. List changed files

```bash
cogant changed . --source-only
```

This compares against `HEAD~1` by default. To compare against a
specific ref:

```bash
cogant changed . --since main --source-only
```

### 2. Write the changed file list to disk

```bash
cogant changed . --source-only --output changed-files.txt
```

### 3. List only Python changes

```bash
cogant changed . --python-only
```

### 4. Full incremental workflow

Combine `changed` with `translate` for a focused re-run:

```bash
# Check if any source files changed
count=$(cogant changed . --source-only 2>&1 | head -1 | grep -oE '[0-9]+')

if [ "$count" = "0" ]; then
  echo "No source files changed -- skipping re-translate"
else
  echo "$count files changed -- re-translating"
  cogant translate . --output ./output-incremental --no-dynamic
fi
```

### 5. Compare against previous output

```bash
cogant diff ./output-previous ./output-incremental
```

## Expected output

```
3 source files changed since HEAD~1
  src/auth.py
  src/billing.py
  tests/test_auth.py
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Not a git repository` (exit code 1) | The directory must be inside a git working tree |
| 0 files but changes exist | Check the `--since` ref is correct; verify with `git diff --name-only` |
| `--python-only` misses `.pyi` files | `.pyi` files are included in `--source-only` but not `--python-only` |
