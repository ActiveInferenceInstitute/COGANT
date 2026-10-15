# Source-bound code-to-GNN execution evidence

Updated 2026-10-15. **Status: executable-model verification; empirical
adequacy of the source-to-model interpretation is not established.**

COGANT can analyze a Python source fixture, export a GNN matrix model, and
execute that exported model through the canonical categorical runtime.
The observation sequence, matrix identity and numerical trace make this an
inspectable execution result. It does not establish that the model captures
the source program's full state space or behavior.

## Evidence layers

| Layer | Inspectable artifact | What it establishes |
| --- | --- | --- |
| Source analysis | `program_graph.json`, rule evidence and source-content digest | The graph extracted from the analyzed source under the recorded parser and rules |
| Candidate state abstraction | `state_space.json` and semantic mapping provenance | Which structural entities were assigned state, observation or action roles |
| Emitted model | `gnn_package/model.gnn.md` and its complete A/B/C/D matrices | The finite categorical model actually supplied to inference |
| Numerical execution | `inference_trace.json` | Conditioning, candidate action scores, chosen action and next-state prediction for that model |
| Behavioral adequacy | Independent executions and a justified measurement/model mapping | A separate evaluation requirement; not established by the preceding artifacts |

An extracted variable node is not automatically an enumerated program-state
valuation. A source attribute's declared cardinality does not prove that a
matrix axis covers all of its values or the joint values of other attributes.
Normalized adjacency and explicit defaults provide model coefficients; they
are not learned transition frequencies.

## Current calculator execution

A fresh run on `examples/control_positive/calculator` completed the ordered
pipeline stages:

```text
ingest -> static -> normalize -> graph -> dynamic -> translate
       -> statespace -> process -> export -> validate
```

The bundle records success for all ten stages, no skipped stages and no errors.
Raster rendering was disabled for this execution check. No coverage or
external execution trace was supplied; the dynamic stage's successful return
therefore does not imply that runtime observations were collected.

The emitted calculator model has one state-axis entry, three observation
outcomes, and six action slices. Its likelihood is uniform over observations,
its prior is a point mass on the sole state, and its transitions preserve that
state. Canonical inference starts from the emitted D and uses the emitted
matrices without replacement.

For this model rollout, beliefs remain fixed and all action scores tie.
The controller chooses the lowest action index. VFE is log(3) at each step,
because the chosen observation has probability one third. A flat trace here
is a consequence of the admitted model, not evidence of recovered uncertainty,
successful program control, or convergence from an uncertain state.

The run's trace records:

- exact GNN source SHA-256 and parsed-matrix SHA-256;
- matrix snapshot and ordered axis labels;
- mode `model_rollout`, one-step horizon and `risk_plus_ambiguity` objective;
- incoming prior, posterior and predicted next belief for every observation;
- observation and action indices, candidate scores and VFE.

Source and matrix digests must agree with the actual exported files. Replaying
the recorded inputs must reproduce the numerical trace. Structural validation
alone is insufficient to establish that agreement.

## Reproduce the source-to-execution route

Run from the inner package root with new output paths:

```bash
COGANT_PIPELINE__RENDER_VISUALIZATIONS=false \
  uv run cogant translate examples/control_positive/calculator \
  -o output/calculator_execution

uv run cogant infer output/calculator_execution/gnn_package/model.gnn.md \
  --steps 8 -o output/calculator_execution/inference_trace.json
```

Inspect `bundle.json` for stage outcomes and errors before interpreting the
trace. `cogant infer` rejects malformed or incomplete matrices and preserves
an existing trace unless `--overwrite` is explicitly supplied.

Without an observations file, inference chooses the lowest-index modal
predicted observation. With `--observations observations.json`, it conditions
on the supplied JSON array of observation indices; an explicit step count must
match its length. Supplying indices does not by itself establish that they are
valid measurements of the source system.

The actions in this calculation select transition slices. They do not invoke
the analyzed source program's functions or establish a closed feedback loop
with an external environment.

## Mathematical and scientific interpretation

For a single persisted example that also records the current repository
roundtrip verdict, run from the inner package root:

```bash
uv run python scripts/repository_inference.py \
  examples/control_positive/calculator --output output/repository_execution
```

The output directory must be new. It retains translation logs, the forward
package and typed inference trace, roundtrip intermediates and JSON, and a
report identifying the `model_rollout` scope. A failed translation or roundtrip
exits nonzero; role preservation is not promoted to strict isomorphism.

Filtering uses the incoming predicted prior and the observed likelihood.
VFE at the exact represented posterior equals negative log observation
evidence. It need not decrease monotonically across changing observations
and priors. A zero-evidence observation is rejected; empty models are not
assigned a finite uncertainty score.

Action scoring combines outcome risk relative to softmax(C) and expected
likelihood entropy. The current CLI performs one-step greedy selection,
with deterministic lowest-index ties. More discriminative authored fixtures
can test posterior updates and action sensitivity, as described in
[explicit GNN execution](FIRST_INFERENCE.md) and the
[finite-model API](../api/finite_models.md).

Roundtrip role preservation and matrix execution are separate checks.
Neither a role score nor a successful numerical trace proves strict graph
isomorphism, a Galois connection, or semantic equivalence to the analyzed
program. Those comparisons require their own stated relations and evidence.

The distinction between verifying a calculation and validating a model
against independent observations is central. The
[discrete active-inference synthesis](https://arxiv.org/html/2001.07203v2)
provides the theoretical context; the
[verification/validation methodology of Oberkampf and Trucano](https://www.sciencedirect.com/science/article/pii/S0376042102000052)
provides a CFD methodological analogy. Neither reference supplies empirical
validation of COGANT's extraction rules.
