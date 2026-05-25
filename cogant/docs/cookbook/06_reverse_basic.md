# Recipe 6: Generating Code from a GNN

**Goal:** Synthesize a runnable Python package from a GNN markdown file.
**Time:** ~3 minutes.

## Prerequisites

- COGANT installed
- A GNN markdown file (produced by `cogant translate` or written by hand)

## Steps

### 1. Locate your GNN file

After running `cogant translate`, find the GNN markdown in the output:

```bash
find ./output -name "model.gnn.md" -type f
```

### 2. Run reverse synthesis

```bash
cogant reverse ./output/gnn_package/model.gnn.md --output ./synthesized
```

COGANT parses the GNN, plans the package layout, and emits:

- One `Factor<N>` class per hidden-state slot
- `observe_<name>` functions for each observation modality
- `act_<name>` functions for each action
- A `select_policy` helper
- `check_<name>` predicates for each constraint
- Runtime `A`/`B`/`C`/`D` matrices in `matrices.py`

### 3. Inspect the synthesized package

```bash
ls ./synthesized/
```

### 4. Get a JSON summary instead of the Rich table

```bash
cogant reverse ./output/gnn_package/model.gnn.md --output ./synthesized --json
```

## Expected output

```
Synthesized package: ./synthesized/my_project_gnn/
  Hidden states:  4
  Observations:   3
  Actions:        2
  Policies:       1
  Constraints:    2
  Matrices:       A, B, C, D
```

### 5. Verify roundtrip preservation

```bash
cogant roundtrip ./output/gnn_package/model.gnn.md --keep-tmp
```

This forward-translates the synthesized package and checks the current
roundtrip taxonomy: strict structural isomorphism when all invariant-ledger
checks pass, `ROLE_PRESERVED` when semantic roles survive but structure drifts,
and `DRIFT` / `FAILED` for weaker outcomes. For day-to-day reverse work, inspect
`role_preservation_score` and the invariant table rather than treating a
role-only match as structural isomorphism.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Error during synthesis` | Check the GNN file is valid markdown with the expected section headers |
| Missing matrix files | The GNN may not define all four matrices; this is expected for simple models |
| Round-trip score below threshold | Complex repos may have information loss; inspect `--keep-tmp` output to debug |
