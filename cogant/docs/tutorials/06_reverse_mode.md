# Tutorial 6: Reverse mode — GNN to code

> **What this page is:** A walkthrough of `cogant reverse` and `cogant roundtrip` — synthesizing source code back from a GNN bundle and verifying the round-trip diff.
>
> **Prerequisites:** [Tutorial 5: Reading the A/B/C/D matrices](05_gnn_interpretation.md) and [The forward-reverse cycle](../concepts/roundtrip.md).
>
> **Reading time:** ~18 minutes
>
> **Next steps:** [Reverse API reference](../api/reverse.md) · [Tutorial 7: Plugin authoring](07_plugin_authoring.md) · [What is a GNN?](../concepts/gnn.md)

> **Status.** Reverse synthesis is available in v0.6.0. `cogant reverse` and `cogant roundtrip` are CLI subcommands. Roundtrip output now reports `roundtrip_status`, `role_preservation_score`, and explicit invariant booleans.

> **Theory background:** "Forward → reverse → forward" is the COGANT
> [roundtrip](../concepts/roundtrip.md) construction, and the role-preservation / invariant ledger reported by
> `cogant roundtrip` is defined there. The synthesis API surface used in the programmatic
> sections lives in [api/reverse.md](../api/reverse.md). Read the roundtrip page first if you
> want the categorical / Galois framing behind the score.

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

This is the roundtrip-validation version of COGANT: the regenerated package is
checked through the current `roundtrip_status`, `role_preservation_score`, and
invariant ledger rather than assumed to be a lossless inverse. The historical
categorical sketch is preserved in
[`../evaluation/ISOMORPHISM_THEOREM.md`](https://github.com/docxology/cogant/blob/main/docs/evaluation/ISOMORPHISM_THEOREM.md),
but the current operational contract is [the roundtrip concept page](../concepts/roundtrip.md).

## Current state (v0.6.0)

What **does** work:

- `cogant reverse <gnn_package_dir> --output <out_dir>` synthesizes a Python package.
- `cogant roundtrip <repo_dir> --output <out_dir>` runs forward → reverse → forward and
  reports the roundtrip status, role-preservation score, and invariant ledger.
- `py/cogant/reverse/__init__.py` exposes `PackagePlan` for programmatic use.
- `gnn/matrices.py`: given a `StateSpaceModel` and `GNNMatrices`, enumerate hidden states,
  observations, and actions in a stable order.
- `simulate/runner.py` runs a PyMDP-style agent simulation over the derived matrices.

Known limitations:

- Only Python synthesis is supported (TypeScript/Rust output is post-1.0).
- The synthesized `code'` is **role-preserving when the ledger says so**, not generally
  semantically or textually equivalent to the original. Whitespace, docstrings, comments,
  statement ordering, and many implementation details are not recovered.

## Programmatic walkthrough

Start from a `gnn_package/` directory produced by a forward run.

```python
# doctest: +SKIP  # example requires runtime context or external resources
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
written. Current API:

```python
# doctest: +SKIP  # example requires runtime context or external resources
from cogant.reverse import plan_package, PackagePlan

plan: PackagePlan = plan_package(model)  # model is a ReverseGNNModel

print(plan)
# PackagePlan(package_name="calculator_synth", nodes=[...])
#   calculator_synth/
#     __init__.py
#     hidden_state.py    # class Display, Accumulator, HistoryLen
#     observations.py    # def get_display, get_history, assert_display
#     actions.py         # def execute_operation
#     model.py           # A, B, C, D as module-level constants
```

> **API note.** `plan_package` is the public entry point exported from
> `cogant.reverse` (see `py/cogant/reverse/__init__.py`). It takes a
> `ReverseGNNModel` and returns a `PackagePlan` describing the directory
> layout. Earlier drafts of this tutorial referenced `build_package_plan`
> — that name was renamed before the current reverse API and no longer exists.

## Roadmap to full reverse mode

Tracked in [`../evaluation/SCOPING_REPORT.md § reverse`](https://github.com/docxology/cogant/blob/main/docs/evaluation/SCOPING_REPORT.md#reverse) and
[`../evaluation/R&D_LOG.md`](https://github.com/docxology/cogant/blob/main/docs/evaluation/R&D_LOG.md):

| Milestone | Status |
| --- | --- |
| `PackagePlan` dataclass + directory layout | Complete |
| GNN → `StateSpaceModel` round-trip load | Complete |
| Python code emitter (Jinja2 templates) | Complete |
| `cogant reverse` CLI command | Complete |
| `cogant roundtrip` CLI command (forward + reverse verify) | Complete |
| Roundtrip invariant tests (forward ∘ reverse ∘ forward) | Complete — role-preservation and strict-invariant status reported separately |
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
- [The forward-reverse cycle](../concepts/roundtrip.md) — the current roundtrip taxonomy and
  invariant ledger.
- [`../evaluation/ISOMORPHISM_THEOREM.md`](https://github.com/docxology/cogant/blob/main/docs/evaluation/ISOMORPHISM_THEOREM.md) —
  the historical theory sketch that originally motivated reverse mode.
