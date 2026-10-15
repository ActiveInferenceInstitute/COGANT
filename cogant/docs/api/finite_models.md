# Explicit finite state-space models

`FiniteModelSpec` describes an authored finite generative model. COGANT compiles
its transition and observation tables into immutable A/B/C/D matrices, checks
them against the declarations, and can hand them to the existing agent runtime.
This interface takes explicit model definitions; it does not infer program
behavior from source repositories.

## Compile and verify

Run from the inner package root, the directory containing `pyproject.toml` and
`py/cogant/`:

```bash
uv run cogant finite compile examples/finite_models/toggle.json -o output/finite/toggle.json
uv run cogant finite verify examples/finite_models/toggle.json output/finite/toggle.json
```

The [toggle specification](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/cogant/examples/finite_models/toggle.json) has
`off`/`on` states, `hold`/`toggle` actions, and `dark`/`lit` observations. The
[counter specification](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/cogant/examples/finite_models/counter.json) demonstrates
saturation and partial observability: distinct `zero` and `one` states both
produce the `low` observation.

Compilation prints the artifact as JSON when `--output` is omitted. An output
file must be a new path; existing files are preserved. Verification emits a JSON
report containing `passed`, `checked_entries`, `mismatch_count`, and a bounded
list of `counterexamples`.

| Exit code | Meaning |
| --- | --- |
| `0` | Compilation succeeded, or verification agrees with the specification |
| `1` | A well-formed compiled artifact differs from the specification |
| `2` | Invalid input, unsupported schema, exhausted budget, or file operation failure |

## Modeling contract

- `schema_version` is `"1.0"`; it can be omitted to select the current schema.
- `states`, `actions`, and `observations` are ordered, nonempty, unique label
  sequences. Labels retain their order. A state denotes a complete configuration
  chosen by the model author, rather than an automatically enumerated variable.
- `transitions` rows contain `state`, `action`, `next_state`, and optional
  `probability` (default unit mass). Every declared state/action pair needs a
  distribution; multiple outcomes encode stochastic transitions.
- `likelihoods` rows contain `state`, `observation`, and optional `probability`.
  Every state needs an observation distribution. Different states can emit the
  same observation.
- `prior` rows contain `state` and `probability`. Missing states have zero prior
  mass; the complete prior must sum to one.
- `preferences` rows contain `observation` and finite `log_preference`. Missing
  observations have neutral, zero log preference. C is not a probability vector.
- Omitted transition or likelihood outcomes have zero mass. Duplicate rows,
  unknown labels, missing input cases, nonfinite values, negative probabilities,
  and nonunit probability columns are rejected. Text and boolean values are not
  probability inputs. Kernel sums use the admission tolerance declared in
  `cogant.statespace.finite_spec.MASS_TOLERANCE`; coefficients are preserved.

For example, a stochastic row can split one state/action case across outcomes:

```json
[
  {"state": "off", "action": "toggle", "next_state": "off", "probability": 0.2},
  {"state": "off", "action": "toggle", "next_state": "on", "probability": 0.8}
]
```

These rows replace the deterministic row for that case. The other declared
state/action cases and likelihood columns still need complete distributions.

## Matrix and resource contract

| Field | Meaning and axis order |
| --- | --- |
| `A[o][s]` | Observation likelihood, P(observation given state) |
| `B[next][current][action]` | Controlled next-state distribution |
| `C[o]` | Log preference over observations |
| `D[s]` | Initial state distribution |

The dense entry count is `states² × actions + observations × states +
observations + states`. Compilation checks it before allocating the matrices.
`--max-entries` selects the CLI budget; Python callers can pass `max_entries` to
`compile_finite_model`. Exceeding it raises an error. The declared state axis is
preserved in full; this compiler does not prune states, smooth distributions,
or renormalize declared coefficients. Input parsing and sparse table validation
are separate from this dense-allocation budget.

The artifact records ordered axes, its `declared_finite_model` semantics, and
`source_sha256`: a digest of the normalized specification JSON, including default
fields. It identifies the authored input; it is not a proof that a repository
implements that input.

## Python and runtime use

```python
from pathlib import Path
from cogant.statespace import FiniteModelSpec, compile_finite_model, verify_finite_model

spec = FiniteModelSpec.model_validate_json(
    Path("examples/finite_models/toggle.json").read_text(encoding="utf-8")
)
model = compile_finite_model(spec)
report = verify_finite_model(spec, model)
assert report.passed

runtime = model.to_runtime()
step = runtime.step([1.0, 0.0], obs_idx=0)
assert model.actions[step.action] == "toggle"
assert step.state_dist == [0.0, 1.0]
```

`to_runtime()` creates mutable copies for `AgentRuntime`; runtime updates do not
change the frozen compiled artifact. The existing runtime performs belief
updates and preference-based action selection. A successful kernel check does
not establish policy optimality, learned dynamics, calibration, or physical
adequacy of a modeled system.

## What the checker establishes

`verify_finite_model` first checks axes, name, and source digest. When these
agree, it visits every A/B/C/D entry, including implied zeros, and requires exact
agreement with the parsed declaration. It counts all mismatches while retaining
only a bounded diagnostic sample. Shape and normalization checks alone would
accept a wrong successor with unit probability; this checker rejects it.

Tests additionally compare toggle and counter traces against independently
written Python logic. This application-level check is separate from checking a
matrix representation of the authored tables. Neither result establishes
behavioral equivalence for arbitrary source-code translation.

The design draws on Handwired's explicit numeric builders, domain contracts,
and independent reference tests. Its [operational documentation](https://github.com/chenglou/handwired/blob/4ea7fcb27ebe93acf49b9f29a93e162b975bad46/docs/README.md)
describes manual program construction; COGANT implements the finite-state path
independently, using probability kernels rather than neural arithmetic. No
Handwired source is vendored and no neural-network dependency is added.

See [State-space extraction](statespace.md), [Runtime](runtime.md), and
[API overview](README.md) for the surrounding interfaces.
