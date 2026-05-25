# Tutorial 1: Quickstart — end-to-end in five minutes

> **What this page is:** The fastest path from "nothing installed" to "first GNN bundle in hand" using the `calculator` fixture.
>
> **Prerequisites:** Python 3.11+ and a terminal. No prior COGANT or Active Inference background required.
>
> **Reading time:** ~5 minutes
>
> **Next steps:** [Tutorial 2: Small repo walkthrough](02_small_repo_walkthrough.md) · [Tutorial 5: Reading the A/B/C/D matrices](05_gnn_interpretation.md) · [API quick start](../api/quick_start.md)

> **Goal.** Install COGANT, translate the `calculator` fixture, and read the generated GNN bundle. Five minutes, one terminal, no optional stages.

> **Theory background:** This tutorial produces a [GNN (Generalized Notation Notation)](../concepts/gnn.md)
> bundle from source code. The pipeline assigns Active Inference roles to graph nodes via the
> [role assignment system](../concepts/role_assignment.md). If you have never seen these terms
> before, skim those two pages first — five minutes is enough to follow this tutorial after.

## Prerequisites

- Python 3.11 or 3.12
- [`uv`](https://github.com/astral-sh/uv) (recommended) or plain `pip`
- `git`

Everything else (tree-sitter, reportlab, the rust backend) is optional for this tutorial.

## 1. Clone and install

```bash
git clone https://github.com/docxology/cogant.git
cd cogant
uv sync --extra all
uv run cogant doctor
```

`cogant doctor` prints a diagnostic table. You should see `ok` next to `python`, `uv`,
`cogant package`, and `examples/control_positive`. A warning on `rust backend` is fine —
it is optional.

## 2. Translate the calculator fixture

```bash
uv run cogant translate examples/control_positive/calculator \
    --output output/calculator \
    --layout-output
```

This runs the default pipeline:

```text
ingest → static → normalize → graph → translate → statespace → process → export → validate
```

The `--layout-output` flag reorganizes the result into five subdirectories:

| Subdirectory | Contents |
| --- | --- |
| `data/` | `bundle.json`, stage outputs, program graph JSON |
| `diagrams/` | Mermaid sources + Graphviz `.dot` renders of the graph and blanket |
| `site/` | A minimal HTML site (navigable in a browser) |
| `reports/` | `model.gnn.md` (copied from `gnn_package/`) and `run_summary.md` |
| `figures/` | Raster (`*.png`) and vector (`*.svg`) renders, including `summary_cover.png`, `connections_matrix.png`, `model_gnn*.png`, `process_gantt.png`, `program_graph.png`, `state_space_factor.png`, `markov_blanket.png` |

The batch runner (`run_all.py`) populates four extra directories under the same target root: `analysis/` (graph metrics), `exports/` (multi-format graph exports), `gnn_package/` (full upstream-GNN spec package), and `roundtrip/` (forward + reverse GNN round-trip). The top-level `data/bundle.json` remains the canonical machine-readable artifact; everything else is a view over it.

## 3. Validate the GNN bundle

```bash
uv run cogant validate output/calculator/gnn_package
```

Expected output:

```text
GNN validation: output/calculator/gnn_package
  Score:    100.0 / 100
  Errors:   0
  Warnings: 0
  Sections: 18 / 18
  Matrices: A (3x3), B (3x3x1), C (3,), D (3,)
  Status:   PASS
```

Score 100.0 means the GNN bundle conforms exactly to the AII upstream spec for state-space
block, connections, initial parameterization, time, and ontology annotation sections.

## 4. Inspect what the pipeline found

Open the generated GNN markdown:

```bash
less output/calculator/gnn_package/model.gnn.md
```

You should see bracket-notation sections like:

```text
## StateSpaceBlock
s_f0[1,1,type=int]        # Calculator.display (sensory observation)
u_f0[1,1,type=int]        # _execute_operation action id
x_f0[3,1,type=float]      # Calculator internal state (display, accumulator, history_len)

## Connections
x_f0 > s_f0
u_f0 > x_f0
```

The full format reference is [Tutorial 5: Reading A/B/C/D matrices](05_gnn_interpretation.md).

## 5. What the rules decided

`bundle.json` contains every translation decision with evidence. A quick view:

```bash
uv run python -c "
import json
data = json.load(open('output/calculator/bundle.json'))
for m in data['stages']['translate']['mappings']:
    print(f\"{m['kind']:12s} {m['qualified_name']:40s} conf={m['confidence']:.2f}\")
"
```

Expected roles on the calculator fixture (six total semantic mappings):

| Role | Count | Example |
| --- | ---: | --- |
| HIDDEN_STATE | 1 | `Calculator` (class with mutated `display`, `accumulator`, `history` attrs) |
| OBSERVATION | 3 | `get_display`, `get_history`, `assert_display` |
| ACTION | 1 | `_execute_operation` |
| CONSTRAINT | 1 | `assert_history_length` |

These six assignments are asserted end-to-end by
`tests/unit/test_ai_role_validation.py::test_calculator_qualitative`.

## Next

- [Tutorial 2: small repo walkthrough](02_small_repo_walkthrough.md) — same pipeline, more detail.
- [Tutorial 3: Flask app walkthrough](03_flask_walkthrough.md) — 98 nodes, 597 edges, real code.
- [Tutorial 5: interpreting GNN matrices](05_gnn_interpretation.md) — what the A / B / C / D
  values actually mean.
