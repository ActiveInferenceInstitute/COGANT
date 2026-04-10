# Recipe 8: Using COGANT in CI/CD (GitHub Actions)

**Goal:** Add COGANT translation and validation to a GitHub Actions workflow.
**Time:** ~10 minutes.

## Prerequisites

- A GitHub repository
- COGANT available on PyPI or installable from source

## Steps

### 1. Create the workflow file

```bash
mkdir -p .github/workflows
```

### 2. Write the workflow

Create `.github/workflows/cogant.yml`:

```yaml
name: COGANT Analysis

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  cogant:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install COGANT
        run: pip install cogant

      - name: Check environment
        run: cogant doctor

      - name: Translate repository
        run: cogant translate . --output ./cogant-output --no-dynamic

      - name: Validate GNN output
        run: cogant validate ./cogant-output

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: cogant-output
          path: ./cogant-output/
          retention-days: 30
```

### 3. Add baseline diffing for PRs (optional)

Extend the workflow to compare the PR branch against main:

```yaml
      - name: Translate baseline (main)
        if: github.event_name == 'pull_request'
        run: |
          git stash
          git checkout ${{ github.event.pull_request.base.sha }}
          cogant translate . --output ./cogant-baseline --no-dynamic
          git checkout -
          git stash pop || true

      - name: Diff against baseline
        if: github.event_name == 'pull_request'
        run: cogant diff ./cogant-baseline ./cogant-output -o drift-report.md

      - name: Comment drift report
        if: github.event_name == 'pull_request'
        uses: marocchino/sticky-pull-request-comment@v2
        with:
          path: drift-report.md
```

## Expected output

The workflow produces a `cogant-output` artifact containing the full
bundle, GNN package, and validation results. On PRs, the drift report
is posted as a comment.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `cogant doctor` fails | Install missing system dependencies in the workflow |
| Translate times out | Add `--no-dynamic` to skip coverage/trace analysis; use `--skip validate` for speed |
| Diff step fails | Ensure both baseline and current outputs exist; check git checkout succeeded |
