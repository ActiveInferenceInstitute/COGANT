# What is a GNN?

GNN stands for **Generalized Notation Notation** -- a structured markdown format created by the Active Inference Institute for describing Active Inference state-space models. It is not "graph neural networks." This distinction matters because the entire COGANT pipeline produces GNN files as its primary output, and reading them correctly is the key to understanding what COGANT has learned about your codebase.

## The purpose of GNN

A GNN file is a self-contained description of a generative model. It tells you: what hidden states exist, what observations the system can make, what actions it can take, how states transition given actions, how observations relate to hidden states, and what the system prefers. In COGANT's case, the "system" is your codebase and the generative model is derived from static analysis of your source code.

The format is a markdown file with specific `##` section headers that parsers and type-checkers recognize. COGANT produces files that satisfy the upstream GNN v1.1 specification while also appending extended sections for provenance, Markov blankets, and confidence metrics.

## Anatomy of a GNN file

A GNN file emitted by COGANT contains these sections in canonical order:

### GNNSection and GNNVersionAndFlags

The header block that identifies the file as a GNN model and declares the version. COGANT emits `v1.1` with flags indicating the file was machine-generated.

### ModelName and ModelAnnotation

Human-readable name and description. COGANT fills these from the repository name and commit hash.

### StateSpaceBlock

The core of the model. Declares every hidden state variable, its type, and its cardinality. For example, a calculator codebase might produce:

```
## StateSpaceBlock
- s_f0: display (int, cardinality=10)
- s_f1: accumulator (float, cardinality=1)
- s_f2: history_len (int, cardinality=100)
```

Each `s_fN` entry corresponds to a class attribute or mutable variable that COGANT's `MutatingSubsystemRule` identified as internal state.

### Connections

Describes how state variables relate to observations and actions. This section encodes the A matrix (likelihood) and B matrix (transition) structure as named edges between variables.

### InitialParameterization

The D matrix -- prior beliefs about the initial hidden state. When COGANT finds `CONFIGURATION` nodes (config files, `Settings` classes), their values seed this section. When no configuration evidence exists, the prior defaults to uniform.

### ActInfOntologyAnnotation

Maps every variable in the model to its Active Inference ontology concept. This is where COGANT's [role assignments](role_assignment.md) become visible in the output. Each annotation uses one of the canonical ontology terms: `HiddenState`, `Observation`, `Action`, `Policy`, `LikelihoodMatrix`, `TransitionMatrix`, `PreferenceVector`, `PriorBelief`, `ExpectedFreeEnergy`, or `Time`.

## The 7 semantic roles

COGANT assigns every code node one of seven primary semantic roles. These roles map directly to GNN sections:

| Role | GNN section | What it means in code |
| --- | --- | --- |
| HIDDEN_STATE | StateSpaceBlock | Mutable attributes, caches, buffers |
| OBSERVATION | Observation Modalities | Getters, read APIs, loggers |
| ACTION | Actions/Policies | Setters, mutators, event publishers |
| POLICY | Actions/Policies | Controllers, routers, schedulers |
| CONSTRAINT | Preferences/Constraints | Validators, test assertions |
| CONTEXT | InitialParameterization | Config files, feature flags, env vars |
| DATA_FLOW | Connections | Reader-writer pipelines |

See [How COGANT assigns roles](role_assignment.md) for the full rule engine.

## How COGANT reads GNN files

COGANT's `load_gnn_package()` function parses a GNN package directory (produced by a forward run) back into in-memory data structures. This is the entry point for [reverse mode](roundtrip.md):

```python
from pathlib import Path
from cogant.gnn.runner import load_gnn_package

package_dir = Path("output/my_project/gnn_package")
gnn = load_gnn_package(package_dir)

# Enumerate the model's variables
for var in gnn.state_space.variables.values():
    print(f"Hidden state: {var.name} ({var.var_type})")

for obs in gnn.state_space.observations.values():
    print(f"Observation: {obs.name}")

for act in gnn.state_space.actions.values():
    print(f"Action: {act.name}")
```

The package directory contains `model.gnn.md` (the human-readable GNN), `model.gnn.json` (the machine-readable version), and satellite files for matrices, provenance, and the [Markov blanket](markov_blanket.md) partition.

## A concrete example

Given a Python module with a `Calculator` class, COGANT's forward pipeline produces a GNN whose `StateSpaceBlock` contains entries like `s_f0: display`, `s_f1: accumulator` -- because these are the mutable attributes identified by `MutatingSubsystemRule`. The `ObservationRule` maps `get_display()` and `get_history()` to observation modalities. The `ActionRule` maps `_execute_operation()` to an action. The resulting GNN file is a complete Active Inference model that a PyMDP agent could run immediately.

## Further reading

- [Active Inference from a programmer's perspective](active_inference.md) -- the theory behind A/B/C/D matrices
- [How COGANT assigns roles](role_assignment.md) -- the rule engine that populates GNN sections
- [The forward-reverse cycle](roundtrip.md) -- how GNN files participate in the roundtrip
- [Program graphs in COGANT](program_graph.md) -- the intermediate representation before GNN
