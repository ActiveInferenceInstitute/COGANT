# Recipe 15: Visualizing Markov Blanket Partitions

**Goal:** Generate a visual diagram of the Markov blanket partitions in a program graph.
**Time:** ~5 minutes.

## Prerequisites

- COGANT installed with viz extras: `pip install "cogant[viz]"`
- Graphviz installed (`brew install graphviz` or `apt install graphviz`)

## Steps

### 1. Translate the project

```bash
cogant translate ./my-project --output ./output --no-dynamic --layout-output
```

The `--layout-output` flag organizes artifacts into `data/`,
`diagrams/`, `figures/` subdirectories.

### 2. Generate PNG visualizations

```bash
cogant viz ./output
```

This walks the output directory and rasterizes every `.mermaid`,
`.mmd`, `.svg`, and `.dot` file to PNG. It also generates
`program_graph.png` from `program_graph.json` when present.

### 3. Inspect the blanket partitions

The program graph visualization color-codes nodes by their Markov
blanket role:

| Role | Symbol | Meaning |
|------|--------|---------|
| mu | Internal states | Hidden state variables |
| s | Sensory states | Observation/input nodes |
| a | Active states | Action/output nodes |
| eta | External states | Environment boundary |

### 4. Find the generated PNGs

```bash
find ./output -name "*.png" -type f
```

### 5. Export the state space for further analysis

```bash
cogant statespace ./my-project
```

This prints the count of states, observations, actions, and policies
without writing files.

## Expected output

```
Rasterizing visualizations in /path/to/output
┌───────────┬───────┐
│ Category  │ Count │
├───────────┼───────┤
│ mermaid   │ 3     │
│ svg       │ 1     │
│ dot       │ 2     │
│ network   │ 1     │
└───────────┴───────┘
 Wrote 7 visualization files
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `cogant viz` not found | Ensure you installed `cogant[viz]`; run `pip install "cogant[viz]"` |
| No PNGs generated | Check the output directory contains `.mermaid`, `.svg`, or `.dot` files |
| Graphviz errors | Install graphviz: `brew install graphviz` (macOS) or `apt install graphviz` (Linux) |
| Blank PNG | The diagram may be empty if the repo has very few modules; check `cogant scan` output |
