# Small repo walkthrough: `calculator`

The `calculator` fixture under `tests/fixtures/control_positive/calculator/` is the smallest control-positive example that still exercises every layer of the pipeline: ingest, static parse, graph build, semantic translation, Markov blanket partitioning, and GNN export.

> **Theory background:** The four sections below correspond directly to four COGANT concept
> pages. Read them in this order if you are new:
>
> - [Program graph](../concepts/program_graph.md) — what `ingest`, `static`, and `graph` build.
> - [Role assignment](../concepts/role_assignment.md) — how HIDDEN_STATE / OBSERVATION /
>   ACTION / CONSTRAINT mappings are produced.
> - [Markov blankets](../concepts/markov_blanket.md) — the agent / non-agent partition.
> - [GNN](../concepts/gnn.md) — what the exported `gnn_package/` actually contains.

## Run it

```bash
cogant translate tests/fixtures/control_positive/calculator \
  --output output/calculator \
  --layout-output
```

This writes `data/`, `diagrams/`, `site/`, `reports/`, and `figures/` subdirectories plus a top-level `bundle.json`.

## What the pipeline finds

### Semantic mapping counts

| Role | Count | Example nodes |
| --- | ---: | --- |
| HIDDEN_STATE | 1 | `Calculator` (class with `display`, `accumulator`, `history` attrs) |
| OBSERVATION | 3 | `get_display`, `get_history`, `assert_display` |
| ACTION | 1 | `_execute_operation` |
| CONSTRAINT | 1 | `assert_history_length` |
| **Total** | **6** | |

The role split is exactly what the qualitative validation tests in `tests/unit/test_ai_role_validation.py` assert on the calculator fixture. The `Calculator` class becomes hidden state because `MutatingSubsystemRule` sees incoming `WRITES` edges from its methods. `get_*` methods match `ObservationRule`'s keyword set. `_execute_operation` is the only method whose name hits `ActionRule`'s keyword list (via `execute`). `assert_history_length` fires `PreferenceRule` because it starts with `assert_`.

### Markov blanket partition (auto strategy)

The `auto` strategy scores modules by cohesion / coupling and seeds on the one with the highest internal-edge ratio. For `calculator` it picks the `calculator` module:

| Role | Count | Nodes |
| --- | ---: | --- |
| Internal (mu) | 10 | methods held inside the class cluster |
| Sensory (s) | 1 | `Calculator` class itself (incoming edges only) |
| Active (a) | 0 | — |
| External (eta) | 1 | the enclosing `calculator` module |

Internal ratio: 0.833. Boundary ratio: 0.083. A clean minimal blanket for a single-class fixture.

### Why the module is external

The auto-seed scorer picks the class cluster (higher cohesion) as the system of interest, so the module that `contains` the class becomes environment. It is a correct application of the scoring function but counter-intuitive — worth keeping in mind when reading blanket reports.

## GNN output excerpt

The exported `model.gnn.md` contains bracketed state-space sections. A representative fragment:

```
## StateSpaceBlock
s_f0[1,1,type=int]        # Calculator.display (sensory observation)
u_f0[1,1,type=int]        # _execute_operation action id
x_f0[3,1,type=float]      # Calculator internal state (display, accumulator, history_len)

## Connections
x_f0 > s_f0               # hidden state emits observation
u_f0 > x_f0               # action updates hidden state

## InitialParameterization
A_m0 = identity-biased likelihood (0.9 diagonal)
B_f0 = identity fallback (no WRITES evidence per action)
C_m0 = 0.0                # uniform preferences (no CONSTRAINT confidence available)
D_f0 = uniform            # no CONFIGURATION nodes
```

The identity-biased `A` matrix and identity `B` fallback are documented limitations of the v0.1.x matrix builder — see [Active Inference mapping § Known Limitations](../theory/active_inference.md#known-limitations).

## Explain a single node

```bash
cogant explain tests/fixtures/control_positive/calculator Calculator
```

Expected output shape:

```
Node: Calculator (CLASS)
Qualified name: calculator.Calculator
Assigned role: HIDDEN_STATE (confidence: 0.85)

Rules that fired (in priority order):
  1. MutatingSubsystemRule [priority=80]
     Reason: class has 3 incoming WRITES edges from its own methods
     Evidence:
       - WRITES Calculator.__init__ -> Calculator.display
       - WRITES Calculator.input_digit -> Calculator.display
       - WRITES Calculator._execute_operation -> Calculator.accumulator

Markov blanket role: s (sensory boundary)
  Reason: incoming contains-edge from calculator module; no outbound boundary edges
```

## Next

- [Flask app walkthrough](flask.md) — same pipeline on a 98-node real-world application.
- [Active Inference mapping](../theory/active_inference.md) — how the roles and matrices are derived.
