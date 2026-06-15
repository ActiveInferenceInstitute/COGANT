# Your First Project (End-to-End)

> **What this page is:** A full COGANT workflow guide using the `examples/zoo/01_simple_state` fixture, from CLI invocation to bundle inspection. This is the narrative companion to the terse [Quick Start](../getting-started/quickstart.md) in `getting-started/`: read it after installing COGANT to see a complete translate → roundtrip → interpret cycle on a real example.
>
> **Prerequisites:** [Installation](../getting-started/installation.md) and [Quick Start](../getting-started/quickstart.md) complete.
>
> **Reading time:** ~12 minutes
>
> **Next steps:** [Tutorial 2: Small repo walkthrough](../tutorials/02_small_repo_walkthrough.md) · [Tutorial 5: Reading the A/B/C/D matrices](../tutorials/05_gnn_interpretation.md) · [API quick start](../api/quick_start.md)

This guide walks through a full COGANT workflow using the smallest
example in the test zoo: `examples/zoo/01_simple_state`. You will:

1. Install COGANT
2. Translate a single-file "belief state" class into a GNN model
3. Read and interpret the emitted GNN markdown
4. Run the forward-reverse roundtrip and inspect the epsilon (ε) metric
5. Interpret what ε tells you about the translation quality

Every command here is runnable as shown, assuming a POSIX shell and a
checked-out copy of the repository.

---

## 1. Install

COGANT is developed and tested with [`uv`](https://docs.astral.sh/uv/)
on Python 3.11+:

```bash
git clone https://github.com/ActiveInferenceInstitute/COGANT.git
cd cogant/cogant
uv sync
uv run cogant doctor
```

`cogant doctor` prints a table of required and optional dependencies and
reports `READY` when the environment is ready for a translate run:

```text
✅ Python 3.11 or newer
✅ cogant (core)
✅ networkx (core)
✅ pyarrow (core)
✅ duckdb (core)
```

If any core check fails, re-run `uv sync` and consult the warning detail
printed beside the failed row.

---

## 2. First Translate

The test zoo ships a minimal single-factor Active Inference pattern at
`examples/zoo/01_simple_state/state.py`:

```python
class BeliefState:
    """A single hidden state factor representing beliefs about position."""

    def __init__(self, num_states: int = 4) -> None:
        self.state: list[float] = [1.0 / num_states] * num_states
        self.num_states = num_states

    def update_state(self, observation_index: int) -> None:
        """Bayesian-style belief update given an observation."""
        ...
```

Translate it into a GNN bundle:

```bash
uv run cogant translate examples/zoo/01_simple_state \
    --output output/simple_state \
    --no-dynamic
```

`--no-dynamic` skips coverage/trace enrichment — it is optional and
requires running the target under `coverage.py` first. The output
directory will contain:

```text
output/simple_state/
├── bundle.json            # The canonical bundle (schema-versioned)
├── model.gnn.md           # The GNN markdown rendering
├── program_graph.json     # Raw program graph (nodes + edges)
├── mappings.json          # Rule → mapping provenance
├── markov_blanket.json    # Four-role partition
└── reports/
    └── validation.json    # Contract + isomorphism checks
```

---

## 3. Read the Generated GNN

Open `model.gnn.md`. The interesting sections are:

```markdown
## ModelName
simple_state

## StateSpaceBlock
s_f0[4,1,type=int]         # hidden state factor from BeliefState.state
o_m0[4,1,type=int]         # observation modality from update_state(obs)
u_c0[1,1,type=int]         # action factor for update_state itself

## Connections
(D_f0) > (s_f0)
(s_f0) > (A_m0) > (o_m0)
(s_f0, u_c0) > (B_f0) > (s_f0)

## InitialParameterization
D_f0 = { (0.25, 0.25, 0.25, 0.25) }
```

The rule that assigned `BeliefState` to `HIDDEN_STATE` and `update_state`
to `ACTION` can be inspected with:

```bash
uv run cogant explain examples/zoo/01_simple_state BeliefState
```

`explain` prints the rule name, priority, the pattern it matched, and
the confidence score — the full rationale for the assignment.

---

## 4. Run the Roundtrip

The empirical bar COGANT holds itself against is the forward-reverse-forward
round-trip. Run it:

```bash
uv run cogant roundtrip output/simple_state/model.gnn.md \
    --output output/simple_state/roundtrip \
    --json
```

The JSON summary looks like (shape emitted by `cogant.reverse.cli.roundtrip_command`):

```json
{
  "roundtrip_status": "ROLE_PRESERVED",
  "role_preservation_score": 1.0,
  "role_preserved": true,
  "structurally_isomorphic": false,
  "matrix_preserved": true,
  "gnn_sections_preserved": true,
  "generated_code_ok": true,
  "original_roles": {"HIDDEN_STATE": 1, "OBSERVATION": 1, "ACTION": 1},
  "synthesized_roles": {"HIDDEN_STATE": 1, "OBSERVATION": 1, "ACTION": 1},
  "invariants": {"role_preserved": true, "generated_code_ok": true},
  "errors": []
}
```

What each field means:

- **`roundtrip_status`** — one of `STRUCTURALLY_ISOMORPHIC`,
  `ROLE_PRESERVED`, `DRIFT`, or `FAILED`, computed from the invariant ledger.
- **`role_preservation_score`** — Symmetric Active Inference role-multiset
  overlap across the cycle: per role, `min(original, synthesized) /
  max(original, synthesized)`, averaged over the union of roles. Range
  `[0.0, 1.0]`; `1.0` is a perfect role-multiset match. (NOTE: this is
  the project-wide convention — see
  [`docs/concepts/roundtrip.md`](../concepts/roundtrip.md#the-roundtrip-measure).
  Earlier drafts used a complementary "epsilon = drift" formulation
  where `0.0` was best — current reports use `role_preservation_score`.)
- **`original_roles` / `synthesized_roles`** — Per-role multisets recovered
  from the source GNN versus the forward pipeline run on the synthesized
  package, respectively.
- **`shape_match`** — Per-dimension booleans (`n_states`, `n_obs`,
  `n_actions`) reporting whether each cardinality survives the round-trip.

You can also run the roundtrip directly from Python using the
`cogant.reverse.callable.MatrixFunctions` closures — no code generation,
no `exec()`:

```python
# doctest: +SKIP  # example requires runtime context or external resources
from cogant.reverse.parser import parse_gnn
from cogant.reverse.callable import MatrixFunctions
from cogant.runtime.loop import AgentRuntime

gnn = open("output/simple_state/model.gnn.md").read()
mf = MatrixFunctions.from_gnn_text(gnn)

runtime = AgentRuntime(mf)
steps = runtime.run_n_steps(10)
print("final belief:", steps[-1].state_dist)
print("final VFE:", steps[-1].free_energy)
```

---

## 5. Interpret `s_role`

The `s_role` metric quantifies **how much of the original semantic
structure survives a forward → reverse → forward cycle**. The current
project-wide convention is the role-preservation ratio in
[`docs/concepts/roundtrip.md`](../concepts/roundtrip.md#the-roundtrip-measure):
`s_role = 1.0` means every role was preserved (idempotent cycle), and the
public ROLE_PRESERVED threshold is `s_role >= 0.5` (see
`evaluation/METRICS.yaml`). Values you might observe in practice:

| `role_preservation_score` (`s_role`) | Meaning                                              |
|------------------------|------------------------------------------------------|
| `1.00`                 | Idempotent; every role preserved.                    |
| `0.80 – 0.99`          | High-confidence role preservation with non-strict structural drift. |
| `0.50 – 0.79`          | Public ROLE_PRESERVED tier; inspect the invariant ledger. |
| `< 0.50`               | Below the public role-preservation threshold.        |

A `role_preservation_score < 1.0` is **not** automatically a failure: it simply
means the forward and reverse pipelines disagree about some aspect of
the mapping. The `validate` subcommand reports the same metric alongside
contract checks:

```bash
uv run cogant validate output/simple_state
```

---

## Next Steps

- Run `cogant scan` on a larger real repository (try any small Python
  library) and compare the resulting `markov_blanket.json` to the
  four-role canonical schematic.
- Read [the roundtrip tutorial](../tutorials/06_reverse_mode.md) for a
  deeper dive into the `reverse` and `roundtrip` subcommands.
- Browse the [cookbook](../cookbook/README.md) for copy-paste recipes
  (custom rules, CI integration, dataset export, and more).
- Explore the API reference for
  [`cogant.runtime.loop`](../api/runtime.md),
  [`cogant.reverse.callable`](../api/reverse.md),
  [`cogant.translate.rules`](../api/translate.md), and
  [`cogant.markov`](../api/markov.md).
