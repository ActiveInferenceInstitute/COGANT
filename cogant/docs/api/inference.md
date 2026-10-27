# Execute an exported GNN model

COGANT runs complete A/B/C/D matrices directly from GNN Markdown. This route
uses the same categorical kernel as the package runner, simulation, and generated
matrix modules. It does not execute generated Python.

From the inner package root:

```bash
uv run cogant translate examples/control_positive/calculator -o output/calculator --no-dynamic --layout-output
uv run cogant infer output/calculator/gnn_package/model.gnn.md --steps 8 -o output/calculator/data/inference_trace.json
```

The default observation mode is `model_rollout`: at each step the engine uses
the lowest-index most probable observation under the incoming belief. To condition
on external observations, provide a JSON array of zero-based observation indices:

```bash
uv run cogant infer model.gnn.md --observations observations.json -o trace.json
```

An omitted step count follows the supplied array length. A supplied count must
match it. The output file is created exclusively; `--overwrite` explicitly replaces
an existing generated artifact. Standard output receives JSON when `-o` is omitted.
Invalid, incomplete, degraded, or impossible inputs return a nonzero exit status.

## Python interface

```python
from pathlib import Path
from cogant.runtime import InferenceOptions, run_gnn_inference

text = Path("model.gnn.md").read_bytes().decode("utf-8")
trace = run_gnn_inference(text, InferenceOptions(steps=2, observations=(0, 1)))
first = trace.trace[0]
print(first.prior, first.posterior, first.action, first.predicted_belief)
```

The immutable schema records the exact UTF-8 source digest, parsed matrix snapshot
and digest, axis labels, observation mode, and every step's incoming prior,
filtered posterior, next state prediction, prior predictive observation,
selected action, per-action expected free energy, and filtering free energy.
The complete fenced matrix axes are authoritative; descriptive factor cardinalities
do not resize or replace exported matrix values.

Filtering conditions on the current observation before action selection. The
runtime minimizes one-step risk plus likelihood ambiguity, with preferences
normalized from log weights and lowest-index action ties. Filtering free energy
uses the incoming prior. This is greedy one-step control; finite-sequence scoring
in the kernel does not make this interface an optimal long-horizon planner.

The default limits are 10,000 steps and 100,000,000 estimated work units, where
work is steps times actions times (states squared plus states times observations).
`InferenceOptions.max_work_units` and CLI `--max-work-units` admit a bounded run.
Parser allocation limits apply before execution.

## Fixed-policy preference sensitivity

To inspect how the existing policy objective changes with C, load the same
GNN matrices through the parsed-model interface:

```python
from cogant.reverse.callable import MatrixFunctions

functions = MatrixFunctions.from_gnn_text(text)
gradient = functions.score_preference_gradient(functions.prior(), [0])
```

The returned vector follows the C observation axis. For normalized outcomes
and a fixed H-action sequence, it is `H * softmax(C) - sum_t predicted_outcomes_t`.
The implementation retains the actual outcome mass admitted within stochastic
column tolerance. It holds A, B, beliefs, and every supplied action fixed,
changes no parameters, and rejects empty policies or invalid axes.

`CategoricalModel` and generated standalone `matrices.py` modules expose the
same `score_preference_gradient` method/helper. It differentiates the model
objective with respect to log preferences; it does not differentiate selected
actions, the extraction pipeline, or original program execution. See the
[DiffProg review](../rnd/differentiable_programming.md) for the derivation,
primary sources, verification design, and research proposals.

## Stored traces and figures

`write_inference_trace_artifact(run_dir, steps=8)` reads the run's
`gnn_package/model.gnn.md` and writes `data/inference_trace.json` when the data
directory exists. `load_inference_trace(run_dir)` verifies both digests and
replays the records before admitting the artifact. A stale source, changed
posterior, malformed trace, or missing export is an error.

`cogant.viz.inference_view.render_inference_trace_png(run_dir)` plots admitted
posterior and next-prediction heatmaps, action scores and selections, and filtering
free energy. Its sidecar binds the image to the exact trace and GNN. Publication
promotion requires this evidence even when an older PNG is present.

Repository extraction supplies structural candidate matrices. An executable trace
establishes behavior of that model under its declared observations and actions.
Source-program adequacy requires an independently defined observation interface
and source executions. See [explicit finite models](finite_models.md) for authored
transition and observation kernels and coefficient preservation.
