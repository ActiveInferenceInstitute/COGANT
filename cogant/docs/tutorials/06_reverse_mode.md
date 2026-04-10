# Tutorial 6: Reverse mode — GNN to code

> **Status.** Reverse synthesis is a **prototype**. v0.1.0 ships the scaffolding under `py/cogant/reverse/` and a handful of planning primitives. There is no public CLI surface yet. This tutorial walks through the current API and the roadmap to a full `cogant reverse` command.

## Why reverse

A cogant forward run answers: *"given this code, what is its Active Inference generative
model?"* The reverse direction answers: *"given this generative model, what is the minimum
Python package that implements it?"*

The two together close the loop:

```text
code ──forward──► GNN ──reverse──► code'
```

where `code'` is a new Python package with:

- a class per hidden-state node,
- a method per action,
- a getter per observation,
- preference and prior metadata baked into module-level constants.

This is the "isomorphism theorem" version of COGANT — the informal statement lives in
[`_rnd/ISOMORPHISM_THEOREM.md`](https://github.com/cogant-contributors/cogant/blob/main/_rnd/ISOMORPHISM_THEOREM.md).

## Current state (v0.1.0)

What **does** work today:

- `py/cogant/reverse/__init__.py` exposes scaffolding for a `PackagePlan` data model
  (directory layout, per-module content, import graph).
- `gnn/matrices.py` is the inverse-friendly entry point: given a `StateSpaceModel` and a
  `GNNMatrices` instance, you can enumerate hidden states, observations, and actions in a
  stable order.
- `simulate/runner.py` uses the matrices to run a PyMDP-style agent simulation over an
  arbitrary number of steps, which is the same numerical path a synthesized package would
  take at runtime.

What does **not** work yet:

- A `cogant reverse` CLI subcommand. You must drive the reverse pipeline from Python.
- Arbitrary-language output. Only Python is on the v0.1 roadmap.
- Round-trip `code → gnn → code'` with byte-identical output. The forward pipeline throws
  away whitespace and docstrings, so the reverse pipeline produces **semantically equivalent**
  not **textually equivalent** code.

## Programmatic walkthrough

Start from a `gnn_package/` directory produced by a forward run.

```python
from pathlib import Path

from cogant.gnn.runner import load_gnn_package  # load bundle + matrices
from cogant.simulate.runner import SimulationRunner

package_dir = Path("output/calculator/gnn_package")
gnn = load_gnn_package(package_dir)

print("Hidden states:", [s.name for s in gnn.state_space.variables.values()])
print("Observations:", [o.name for o in gnn.state_space.observations.values()])
print("Actions:", [a.name for a in gnn.state_space.actions.values()])
```

Expected output on the calculator bundle:

```text
Hidden states: ['display', 'accumulator', 'history_len']
Observations: ['get_display', 'get_history', 'assert_display']
Actions: ['_execute_operation']
```

Run a simulation to confirm the matrices describe a valid Active Inference model:

```python
runner = SimulationRunner(gnn.matrices)
trace = runner.run(n_steps=10, seed=42)

for t, step in enumerate(trace):
    print(f"t={t}: s={step.hidden_state}, o={step.observation}, a={step.action}")
```

Expected: ten steps with hidden states sampled from `D`, observations sampled from `A`, and
actions selected by the identity-B fallback.

## Building a `PackagePlan` (prototype)

The reverse module's `PackagePlan` captures the Python package structure before any files are
written. Current API (subject to change in 0.2):

```python
from cogant.reverse import build_package_plan, PackagePlan

plan: PackagePlan = build_package_plan(
    gnn=gnn,
    package_name="calculator_synth",
    output_root=Path("output/reverse/"),
)

print(plan.directory_layout())
# calculator_synth/
#   __init__.py
#   hidden_state.py    # class Display, Accumulator, HistoryLen
#   observations.py    # def get_display, get_history, assert_display
#   actions.py         # def execute_operation
#   model.py           # A, B, C, D as module-level constants
```

## Roadmap to full reverse mode

Tracked in [`_rnd/SCOPING_REPORT.md § reverse`](https://github.com/cogant-contributors/cogant/blob/main/_rnd/SCOPING_REPORT.md#reverse) and
[`_rnd/R&D_LOG.md`](https://github.com/cogant-contributors/cogant/blob/main/_rnd/R&D_LOG.md):

| Milestone | Status |
| --- | --- |
| `PackagePlan` dataclass + directory layout | Prototype |
| GNN → `StateSpaceModel` round-trip load | Complete |
| Python code emitter (jinja2 templates) | Not started |
| `cogant reverse` CLI command | Not started |
| `cogant roundtrip` CLI command (forward + reverse verify) | Not started |
| Idempotence tests (forward ∘ reverse ∘ forward = forward) | Not started |
| Language-agnostic output (TypeScript, Rust) | Post-1.0 |

## What you can experiment with today

- **Edit a GNN markdown file by hand**, re-validate it with `cogant validate`, and watch the
  validator catch structural drift. This is the best way to build intuition about the 18-section
  format before writing an emitter.
- **Swap A/B/C/D numerically** in a cloned `gnn_package/`, then run the simulation loop and
  see how the sampled trajectories change. This is the numerical equivalent of "editing the
  synthesized code and running its tests."
- **Write a small jinja2 template** that consumes `PackagePlan` and produces Python source. The
  reverse module explicitly does not ship a template engine — writing one is a great first
  contribution.

## Next

- [Tutorial 7: authoring a language plugin](07_plugin_authoring.md) — the forward direction of
  the language-agnostic roadmap.
- [`_rnd/ISOMORPHISM_THEOREM.md`](https://github.com/cogant-contributors/cogant/blob/main/_rnd/ISOMORPHISM_THEOREM.md) — the informal theorem
  that motivates reverse mode.
