# Executing explicit GNN matrices through composable inference

Updated 2026-10-15. This page describes the current finite categorical execution
contract. It distinguishes the handwritten model integration fixture from
inference on a repository's actual exported GNN.

## Handwritten model fixture

The fixture in `tests/integration/test_generated_inference.py` declares a single
global hidden-state axis with two states, an observation axis with two
outcomes, and a control axis with two actions. Its complete matrices are:

```text
A = [[0.8, 0.2],
     [0.2, 0.8]]
B[:, :, action] = identity for each action
C = [1.0, -1.0]
D = [0.6, 0.4]
```

These are authored model coefficients, not measured repository transition
frequencies. State, observation and action cardinalities are explicit;
the prior is already normalized and is used without factor projection.

The integration path parses the GNN, plans and synthesizes a package, loads
its generated matrices, and supplies them to `AgentRuntime`. The callable
path uses `MatrixFunctions` directly from the parsed model. Both supply
complete A/B/C/D matrices to the same categorical calculation. The fixture
checks normalized beliefs, finite VFE, valid action indices and ordered
timesteps. Those checks establish execution of the declared model; they do
not establish correctness of an arbitrary source-code abstraction.

## Filtering and action selection

Each step records the incoming prior, conditions on the observation, scores
actions, selects the minimum score, and predicts the next prior using B.
VFE is KL(posterior || incoming prior) minus expected log likelihood for the
observed outcome. Its value at the exact represented posterior is negative
log observation evidence. The initial D is not reused as the reference prior
at every later step.

The action objective is KL(predicted observations || softmax(C)) plus expected
likelihood entropy under predicted states. It contains both outcome preference
and state-information terms. The public trace uses a one-step horizon and
lowest-index ties. It does not maximize preference alone or enumerate all
observation-contingent policies.

Zero observation evidence fails conditioning. Missing or malformed matrices,
incompatible dimensions, and invalid probability vectors fail admission.
A structural model with no supported execution matrices remains an analysis
artifact, not a successfully executed agent.

## Direct repository export to inference

From the inner package root, translate a source fixture to a new output
directory, then execute that run's actual GNN:

```bash
uv run cogant translate examples/control_positive/calculator \
  -o output/calculator --no-dynamic
uv run cogant infer output/calculator/gnn_package/model.gnn.md \
  --steps 8 -o output/calculator/data/inference_trace.json
```

Use a new trace path, or supply `--overwrite` when deliberately replacing a
generated trace. With `--observations observations.json`, the command reads
an array of observation indices. Otherwise it generates modal observations
from the predicted observation distribution and records mode `model_rollout`.
A generated observation is not an external measurement.

The trace contains the exact GNN-text SHA-256, a separate parsed-matrix digest,
matrix snapshot, ordered axis labels, and step records. Figure admission
checks source and matrix identity and replays canonical execution. The
calculator export is an execution smoke case: its single state leaves no
hidden-state uncertainty to recover, and its uniform likelihood produces
flat scores. The informative handwritten fixture and other controlled matrix
cases address different numerical behaviors.

## Generated standalone execution

Reverse synthesis embeds the shared dependency-free categorical kernel in
the generated matrix module. The generated package can therefore execute its
declared matrices without importing COGANT. The direct parsed-model route
avoids code generation; standalone execution is a distinct delivery surface.

The regression test
`test_categorical_shared_execution.py::test_generated_kernel_runs_without_cogant_and_matches_independent_score`
runs the generated module with Python's `-I -S` isolation flags, compares
candidate EFE scores with an independent analytic expression, and checks
lowest-index action selection. This qualifies the tested generated scoring
surface without relying on an installed COGANT package. Full-trace parity
additionally requires comparison of posterior, selected action, predicted
belief and VFE for identical inputs. Merely inspecting generated source or
checking a successful process exit is insufficient. Both contracts remain
separate from source-program equivalence and role preservation in a
forward-reverse-forward analysis.

## Interpretation and limits

Repository-derived matrices encode the extraction rules, adjacency
normalization and documented defaults. Execution verifies a calculation on
those matrices; empirical dynamics require independently justified
observations and predictive evaluation. Authored finite specifications have
a separate coefficient-preservation contract on their declared state domain.

A successful trace does not prove a Galois connection, strict graph
isomorphism, empirical adequacy, convergence or globally optimal control.
The manuscript's mathematical comparison remains scoped separately from
numerical execution. See [finite-model API](../api/finite_models.md),
[implementation status](../reference/implementation_status.md), and
[discrete active inference synthesis](https://arxiv.org/html/2001.07203v2)
for the relevant interface, status and theoretical context.
