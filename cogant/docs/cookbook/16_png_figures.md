# Recipe 16: Exporting Program Graph as PNG

**Goal:** Rasterize all diagram artifacts in a COGANT output directory to PNG.
**Time:** ~3 minutes.

## Prerequisites

- COGANT installed with viz extras: `pip install "cogant[viz]"`
- Graphviz installed for `.dot` rendering

## Steps

### 1. Run the pipeline first

```bash
cogant translate ./my-project --output ./output --no-dynamic
```

### 2. Generate PNGs

```bash
cogant viz ./output
```

COGANT recursively walks the output directory and converts:

| Source format | Output |
|---------------|--------|
| `.mermaid` / `.mmd` | `<name>.png` |
| `.svg` | `<name>.png` |
| `.dot` | `<name>.png` |
| `program_graph.json` | `program_graph.png` |

### 3. Check the results

```bash
ls ./output/**/*.png
```

### 4. Re-run after edits

`cogant viz` is idempotent. Existing PNGs are overwritten:

```bash
# Edit a .mermaid file, then regenerate
cogant viz ./output
```

### 5. Use with --layout-output for organized output

```bash
cogant translate ./my-project --output ./output --no-dynamic --layout-output
cogant viz ./output
ls ./output/figures/
```

The `--layout-output` flag moves diagram artifacts into a `figures/`
subdirectory before rasterization.

## Expected output

```
Rasterizing visualizations in /path/to/output
┌───────────┬───────┐
│ Category  │ Count │
├───────────┼───────┤
│ mermaid   │ 2     │
│ dot       │ 1     │
│ network   │ 1     │
└───────────┴───────┘
 Wrote 4 visualization files
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Path does not exist` (exit code 2) | Check the output directory path is correct |
| `Not a directory` (exit code 2) | `cogant viz` requires a directory, not a file |
| 0 PNGs written | The output directory has no renderable artifacts; ensure translate completed |
| Missing graphviz | `.dot` files need graphviz; install it or skip dot diagrams |
