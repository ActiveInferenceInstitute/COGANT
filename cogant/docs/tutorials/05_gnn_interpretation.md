# Tutorial 5: Reading the A / B / C / D matrices

> **What this page is:** A guided reading of an exported GNN bundle's A/B/C/D matrices, explaining each entry in terms of the source code that produced it.
>
> **Prerequisites:** [What is a GNN?](../concepts/gnn.md), [Active Inference for programmers](../concepts/active_inference.md), and any earlier tutorial that produced a bundle.
>
> **Reading time:** ~20 minutes
>
> **Next steps:** [Tutorial 6: Reverse mode](06_reverse_mode.md) · [The forward-reverse cycle](../concepts/roundtrip.md) · [`cogant.gnn` API reference](../api/gnn.md)

> **Goal.** Take an exported GNN bundle, open the matrices, and explain each entry in terms of the source code that produced it.

> **Theory background:** The A / B / C / D matrices are the canonical building blocks of an
> [Active Inference](../concepts/active_inference.md) generative model. The bundle they live in
> is COGANT's [GNN package](../concepts/gnn.md). Read the Active Inference primer first if the
> `p(o, s, a)` factorization shown in the next section is new — it makes the index
> walkthroughs much easier to follow.

COGANT's `gnn_package/` directory contains four probabilistic structures at the heart of an
Active Inference generative model: **A** (likelihood), **B** (transition), **C** (log-preference),
**D** (prior). This tutorial walks through a worked example on the `calculator` fixture and
then on `flask_app`.

## Background

Active Inference models the world as a generative process:

```text
   p(o, s, a) = p(o | s) · p(s' | s, a) · p(s_0) · softmax(-C)
                  A            B             D
```

where:

- `o` = observation (what the agent senses)
- `s` = hidden state (the true latent world)
- `a` = action (what the agent does)

The four matrices encode the agent's beliefs about that process. COGANT derives them **from
the program graph** rather than learning them.

| Matrix | Shape | Source edges | Semantics |
| --- | --- | --- | --- |
| **A** | `[n_obs × n_states]` | `READS`, `OBSERVES`, `DEPENDS_ON` | `P(observation | hidden_state)` |
| **B** | `[n_states × n_states × n_actions]` | `WRITES`, `MUTATES`, `CALLS` | `P(next_state | current_state, action)` |
| **C** | `[n_obs]` (log-preference) | `CONSTRAINT` / `PREFERENCE` confidence | Preferred observations |
| **D** | `[n_states]` | `CONFIGURATION` nodes, type domains | `P(initial hidden_state)` |

Full derivation details live in
[`py/cogant/gnn/matrices.py`](https://github.com/docxology/cogant/blob/main/cogant/py/cogant/gnn/matrices.py).

## Step 1 — open the package

```bash
uv run cogant translate examples/control_positive/calculator \
    --output output/calculator --layout-output
ls output/calculator/gnn_package/
# A.json  B.json  C.json  D.json  manifest.json  model.gnn.md  model.gnn.json  ...
```

## Step 2 — read the A matrix (likelihood)

```bash
uv run python -c "
import json
A = json.load(open('output/calculator/gnn_package/A.json'))
for row in A['matrix']:
    print(['{:.2f}'.format(x) for x in row])
"
```

Expected for calculator (3 observations × 3 hidden states):

```text
['0.90', '0.05', '0.05']     # P(get_display  | display, accumulator, history_len)
['0.05', '0.90', '0.05']     # P(get_history  | display, accumulator, history_len)
['0.05', '0.05', '0.90']     # P(assert_display | display, accumulator, history_len)
```

Interpretation. Column 0 says: "when the hidden state `Calculator.display` is the true value,
there is a 90% chance the `get_display()` observation reflects it accurately, and a 5% chance
it is contaminated by one of the other two hidden-state channels." The `0.90 / 0.05` split is
the `_DEFAULT_DIRECT_MASS / _DEFAULT_INDIRECT_MASS` placeholder defined at the top of
`matrices.py`. It is **not learned** — it is a documented fallback.

**Where did column 0 come from?** The READS-edge query in `compute_A()` found one incoming READS
edge from `Calculator.display` to `get_display`. That's the "direct" hit. The other two hidden
observations share the residual `0.10` mass uniformly. A is column-stochastic: each hidden-state
column sums to one over observation outcomes.

## Step 3 — read the B matrix (transition)

```bash
uv run python -c "
import json
B = json.load(open('output/calculator/gnn_package/B.json'))
n_states = B['n_states']; n_actions = B['n_actions']
print(f'shape: [{n_states} x {n_states} x {n_actions}]')
for a_idx in range(n_actions):
    print(f'\\naction {a_idx} ({B[\"action_names\"][a_idx]}):')
    for row in B['matrix'][a_idx]:
        print(['{:.2f}'.format(x) for x in row])
"
```

Expected for calculator:

```text
shape: [3 x 3 x 1]

action 0 (_execute_operation):
['1.00', '0.00', '0.00']
['0.00', '1.00', '0.00']
['0.00', '0.00', '1.00']
```

Interpretation. With only one `ACTION` node (`_execute_operation`) and **no** outgoing
`WRITES` edges that target an individual hidden-state channel, the B builder falls back to
**identity per action**: each hidden state stays put when the action fires. This is the
documented identity fallback in `compute_B()`.

If the fixture instead had a `WRITES` edge from `_execute_operation` to `Calculator.accumulator`,
that action slice would bias the diagonal toward `accumulator` (~0.9) and leave ~0.1 residual
on the other diagonal entries. See the `event_pipeline` B matrix for a non-identity example.

## Step 4 — read the C vector (preferences)

```bash
uv run python -c "
import json
C = json.load(open('output/calculator/gnn_package/C.json'))
for name, c_val in zip(C['observation_names'], C['vector']):
    print(f'{name:30s} C = {c_val:+.2f}')
"
```

Expected:

```text
get_display                    C = +0.00
get_history                    C = +0.00
assert_display                 C = +0.00
```

All three entries are uniform zeros, which means "no preference expressed." The calculator
fixture has only one `CONSTRAINT` node (`assert_history_length`) and zero `PREFERENCE` nodes.
For the C vector to be non-uniform, COGANT needs at least one `assert_*` or `expect_*` call
targeting a specific observation channel. See the `flask_mini` fixture's C vector for a
sparse-but-populated example.

**Sign convention.** Positive C means "I prefer to see this observation." Negative means
aversive. The softmax is taken over `-C` so higher C lowers the expected free energy of the
corresponding observation.

## Step 5 — read the D vector (prior)

```bash
uv run python -c "
import json
D = json.load(open('output/calculator/gnn_package/D.json'))
for name, d_val in zip(D['state_names'], D['vector']):
    print(f'{name:30s} D = {d_val:.3f}')
"
```

Expected:

```text
Calculator.display             D = 0.333
Calculator.accumulator         D = 0.333
Calculator.history_len         D = 0.333
```

Uniform 1/3 prior. The D builder produces a uniform distribution whenever no `CONFIGURATION`
node with an explicit initial value is found. To get a non-uniform D, add a `CONFIG` node like
`DEFAULT_DISPLAY = 0` with a `WRITES` edge into `Calculator.display`.

## Step 6 — cross-check with the markdown file

`model.gnn.md` contains a human-readable version of the same four matrices under
`## InitialParameterization`. It is the canonical file for human review; the JSON files are
for programmatic consumption.

## When matrices look wrong

If your output matrices look unexpected, the debugging steps are, in order:

1. `cat output/<project>/gnn_package/reports/gnn_score.json` — any validator warnings will
   appear here with an explanation.
2. `uv run python -c "import json; print(json.load(open('output/<project>/bundle.json'))['stages']['translate']['mappings'])"` — check which nodes got which roles.
3. `uv run cogant viz output/<project>` — rasterize Mermaid/SVG/dot artifacts and `program_graph.png` for visual inspection of READS/WRITES edges.
4. Open the rule definitions in `py/cogant/translate/rules/` — every rule documents its
   matching conditions in its docstring.

## Next

- [Tutorial 6: reverse mode](06_reverse_mode.md) — take the matrices back to code.
- [Theory: Active Inference mapping](../theory/active_inference.md) — the full derivation
  including known limitations.
- [Theory: GNN format reference](../theory/gnn_format_reference.md) — bracket notation syntax.
