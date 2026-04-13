# Recipe 7: Customizing Synthesized Package Layout

**Goal:** Control the output directory and structure of reverse-synthesized code.
**Time:** ~5 minutes.

## Prerequisites

- COGANT installed
- A GNN markdown file

## Steps

### 1. Choose your output directory

```bash
cogant reverse ./model.gnn.md --output ./my-custom-output
```

The `--output` flag sets the root directory. COGANT creates a named
subdirectory inside it based on the GNN model name.

### 2. Examine the default structure

```bash
tree ./my-custom-output/
```

Typical layout:

```
my-custom-output/
  my_project_gnn/
    __init__.py
    factors.py
    observations.py
    actions.py
    policies.py
    constraints.py
    matrices.py
```

### 3. Verify the package is importable

```bash
cd ./my-custom-output
python3 -c "import my_project_gnn; print(dir(my_project_gnn))"
```

### 4. Feed the synthesized package back into COGANT

```bash
cogant translate ./my-custom-output/my_project_gnn --output ./re-translated
```

This closes the loop: GNN to code to GNN.

### 5. Compare the original and re-translated GNN

```bash
cogant diff ./original-output ./re-translated
```

## Expected output

The re-translated bundle should produce a GNN structurally similar to
the original, with high role-match score from `cogant roundtrip`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Output directory already exists | COGANT overwrites files; use a fresh directory if you need to preserve old output |
| Package not importable | Check `__init__.py` exists; ensure no syntax errors in generated code |
| Drift between original and re-translated | Expected for large models; inspect per-node diffs with `cogant explain` |
