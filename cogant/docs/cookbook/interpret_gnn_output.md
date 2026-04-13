# Recipe: Interpret GNN Output

**Goal:** Take an exported GNN bundle, open the four matrices, and explain
what each row and column means in terms of the source code that produced it.

> This is the short recipe. For the full mathematical narrative — the
> `p(o, s, a)` factorization, the per-edge derivation, and a worked example
> on both the `calculator` and `flask_app` fixtures — see
> [Tutorial 5: Reading the A / B / C / D matrices](../tutorials/05_gnn_interpretation.md).

## What's in a GNN bundle

After running `cogant translate <target> --output <out>`, you get
`<out>/gnn_package/`:

| File | Shape / Format | Source |
| --- | --- | --- |
| `A.json` | `[n_obs × n_states]` | Likelihood `P(observation \| hidden_state)` |
| `B.json` | `[n_states × n_states × n_actions]` | Transition `P(s' \| s, a)` |
| `C.json` | `[n_obs]` | Log-preference over observations |
| `D.json` | `[n_states]` | Initial-state prior `P(s_0)` |
| `model.gnn.md` | Markdown | Human-readable role table |
| `model.gnn.json` | JSON | Same content, machine-readable |
| `manifest.json` | JSON | Validator score, edge / node counts |

The matrix builder lives in
[`cogant.gnn.matrices`](../api/gnn.md#matrix-builder); the validator lives in
[`cogant.gnn.validator`](../api/gnn.md#validator).

## Step 1 — generate a small bundle

```bash
uv run cogant translate examples/zoo/04_pomdp_minimal \
    --output output/pomdp_minimal --layout-output
ls output/pomdp_minimal/gnn_package/
```

## Step 2 — read the A matrix (likelihood)

```python
import json

A = json.load(open("output/pomdp_minimal/gnn_package/A.json"))
for row in A["matrix"]:
    print(["{:.2f}".format(x) for x in row])
```

Each **row** is an observation modality; each **column** is a hidden-state
factor. A `1.0` means "this observation is fully informative about that
state"; rows are softmax-normalized.

## Step 3 — read the B matrix (transition)

```python
B = json.load(open("output/pomdp_minimal/gnn_package/B.json"))
print("shape:", B["shape"])  # [n_states, n_states, n_actions]
```

`B[s', s, a]` is the probability of transitioning from `s` to `s'` under
action `a`. Each `B[:, :, a]` slice is a column-stochastic matrix.

## Step 4 — read C and D

```python
C = json.load(open("output/pomdp_minimal/gnn_package/C.json"))  # log-preferences over observations
D = json.load(open("output/pomdp_minimal/gnn_package/D.json"))  # prior over initial hidden states
print("C:", C["vector"])
print("D:", D["vector"])
```

`C` is in log-space — apply `softmax(-C)` to get the preferred-observation
distribution. `D` is already a probability vector.

## Step 5 — validate the bundle

```bash
uv run cogant validate output/pomdp_minimal/gnn_package
```

A clean fixture should score 100 / 100. If not, see
[Recipe 14: Validating a hand-written GNN against AII spec](14_gnn_validation.md).

## Common questions

- **Why are some rows in `A` all zeros?** — that observation modality has
  no `READS` / `OBSERVES` / `DEPENDS_ON` edges in the program graph.
  Either the source genuinely doesn't observe that state, or you're missing
  a static analysis pass — re-run with `--verbose` and check the
  `static` stage output.
- **Why does `B` have only one action slice?** — the `cogant.translate`
  engine produced exactly one ACTION mapping. Add an actor class or
  re-run with a relaxed `ActionRule` keyword set.
- **What does the validator score actually measure?** — see
  [`cogant.gnn.validator`](../api/gnn.md#validator).

## See also

- [Tutorial 5: Reading the A / B / C / D matrices](../tutorials/05_gnn_interpretation.md) — full narrative on `calculator` and `flask_app`.
- [`docs/api/gnn.md`](../api/gnn.md) — the matrix builder, runner, validator, and JSON exporter.
- [Recipe 14: Validating a GNN](14_gnn_validation.md) — what the score 0–100 means.
