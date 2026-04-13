# Recipe 9: Pre-commit Hook for GNN Drift Detection

**Goal:** Detect GNN drift before commits land using a pre-commit hook.
**Time:** ~5 minutes.

## Prerequisites

- COGANT installed
- A git repository with an existing COGANT baseline

## Steps

### 1. Generate the baseline

Run a full translate on the current commit and save it:

```bash
cogant translate . --output .cogant/baseline --no-dynamic
```

Commit the baseline so it is available for comparison:

```bash
git add .cogant/baseline/
git commit -m "chore: add COGANT baseline"
```

### 2. Create the pre-commit hook

```bash
cat > .git/hooks/pre-commit << 'HOOK'
#!/usr/bin/env bash
set -e

# Only run if Python/JS/TS files changed
changed=$(cogant changed . --source-only 2>/dev/null)
if [ -z "$changed" ]; then
  exit 0
fi

echo "[cogant] Source files changed -- checking for GNN drift..."

# Translate the working tree
cogant translate . --output .cogant/current --no-dynamic 2>/dev/null

# Compare against baseline
drift_output=$(cogant diff .cogant/baseline .cogant/current 2>&1)
echo "$drift_output"

# Clean up
rm -rf .cogant/current

# Fail if drift report contains errors
if echo "$drift_output" | grep -q "INVALID"; then
  echo "[cogant] GNN drift detected -- review the diff above"
  exit 1
fi

echo "[cogant] No significant drift detected"
HOOK

chmod +x .git/hooks/pre-commit
```

### 3. Alternatively, use a `.pre-commit-config.yaml` entry

If you use the [pre-commit](https://pre-commit.com/) framework:

```yaml
repos:
  - repo: local
    hooks:
      - id: cogant-drift
        name: COGANT drift check
        entry: bash -c 'cogant translate . --output /tmp/cogant-check --no-dynamic && cogant validate /tmp/cogant-check && rm -rf /tmp/cogant-check'
        language: system
        types: [python]
        pass_filenames: false
```

### 4. Test the hook

```bash
echo "# test change" >> some_module.py
git add some_module.py
git commit -m "test: trigger drift check"
```

## Expected output

```
[cogant] Source files changed -- checking for GNN drift...
Diff complete
[cogant] No significant drift detected
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Hook is slow | Add `--skip validate` or use `--no-dynamic` to reduce pipeline stages |
| False positives | Regenerate the baseline after intentional architectural changes |
| Hook not running | Check `chmod +x .git/hooks/pre-commit` |
