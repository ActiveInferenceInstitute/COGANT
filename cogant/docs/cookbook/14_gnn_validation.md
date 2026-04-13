# Recipe 14: Validating a Hand-Written GNN Against AII Spec

**Goal:** Run COGANT's GNN validator on a manually authored or edited GNN package.
**Time:** ~3 minutes.

## Prerequisites

- COGANT installed
- A GNN package directory containing at minimum `manifest.json` and `model.gnn.md`

## Steps

### 1. Understand the expected structure

A valid GNN package directory looks like:

```
gnn_package/
  manifest.json
  model.gnn.md
  model.gnn.json     (optional)
  program_graph.json  (optional)
  semantic_mappings.json (optional)
```

### 2. Validate the package

```bash
cogant validate ./gnn_package
```

COGANT detects the `manifest.json` + `model.gnn.md` pair and runs
the full `GNNValidator`, which checks:

- Manifest schema conformance
- GNN markdown section structure
- State-space completeness (S, O, A, pi)
- Matrix dimension consistency
- Cross-reference integrity

### 3. Validate a bundle directory instead

If you have a run output directory (from `cogant translate`):

```bash
cogant validate ./output
```

COGANT looks for `gnn_package/` inside and validates it, or falls
back to lightweight `bundle.json` structure checks.

### 4. Interpret the score

```
VALID  score=87.5/100
errors=0  warnings=3
```

The score is 0-100. Warnings are informational; errors indicate
spec violations that must be fixed.

## Expected output

```
Validating ./gnn_package
 VALID  score=92.0/100
 errors=0  warnings=1
 package: ./gnn_package
Warnings:
  - Missing optional field: model.gnn.json
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `INVALID` with errors | Read each error message; common issues are missing manifest fields or malformed markdown |
| `Not a file or directory` | Check the path exists |
| `No gnn_package/ and no bundle.json` | Ensure the directory contains either `manifest.json` + `model.gnn.md` or a `bundle.json` |
| Score lower than expected | Warnings reduce the score; fix them for a higher result |
