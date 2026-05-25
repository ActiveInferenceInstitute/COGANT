# First Active Inference Inference Step on a Round-Tripped Codebase

**Date:** 2026-04-09

## The Model

- **Name:** HandwrittenMiniPOMDP
- **Hidden-state factors:** 2 (s_f0 with cardinality 3, s_f1 with cardinality 2)
- **Observation modalities:** 1 (o_m0 with cardinality 2)
- **Action factors:** 1 (u_c0 with cardinality 2)
- **Prior D:** [0.4, 0.5] (aggregated from D_f0={0.3, 0.4, 0.3} and D_f1={0.5, 0.5})
- **Likelihood A:** [[0.8, 0.5], [0.2, 0.5]] (aggregated 2x2 from A_m0)
- **Preference C:** [1.0, -1.0] (prefers observation 0 over observation 1)
- **Transition B:** identity per factor (default)

## Pipeline Steps

1. **Parse GNN** -- `cogant.reverse.parser.parse_gnn(HAND_WRITTEN_GNN)` reads the GNN v1 markdown specification and extracts a `ReverseGNNModel` with all state-space slots, cardinalities, ontology annotations, connections, and A/B/C/D matrices.

2. **Plan package** -- `cogant.reverse.planner.plan_package(model)` maps each GNN role to a Python construct: hidden states become `state.py` dataclass fields, observations become `observe.py` functions, actions become `act.py` functions.

3. **Synthesize package** -- `cogant.reverse.synthesizer.synthesize_package(plan, model, tmp_path)` emits a complete Python package with `__init__.py`, `state.py`, `observe.py`, `act.py`, `policy.py`, `constraints.py`, `matrices.py`, `main.py`, and smoke tests.

4. **exec() matrices.py** -- The generated `matrices.py` is compiled and executed to produce a namespace with `A`, `B`, `C`, `D` as nested Python lists, plus `likelihood()`, `transition()`, and `preference_score()` as callable helpers.

5. **Create AgentRuntime** -- `cogant.runtime.loop.AgentRuntime(namespace)` wraps the matrices module and binds the helper functions (or falls back to built-in implementations).

6. **Run 3 inference steps** -- `runtime.run_n_steps(3, initial_state=None)` executes the perception-action cycle starting from the prior D:
   - **Step 0 (t=0):** Predict observations from D, Bayesian belief update, select action by evaluating preference over each action's predicted next-observation, transition state.
   - **Step 1 (t=1):** Same cycle on the posterior from step 0.
   - **Step 2 (t=2):** Same cycle on the posterior from step 1.

## Outputs

At each step the agent produces:

- **state_dist:** A normalized probability distribution over hidden states (sums to 1.0 within 1e-6)
- **obs:** The argmax-selected observation index
- **action:** The discrete action that maximizes preference score over predicted next observations
- **free_energy:** Variational free energy = -log P(o|s) + KL(posterior || prior), finite at every step

## What This Demonstrates

A Python codebase's generative model structure was specified as a GNN markdown document. That GNN was parsed, planned, and synthesized into a standalone Python package. The package's matrices module was then executed as an Active Inference agent that performed perception, inference, action selection, and state transition -- producing normalized belief distributions and finite free energy at every timestep.

This is the first time a COGANT-generated package has been run as a working agent.

## The Galois Connection

The COGANT pipeline establishes a Galois connection between code and generative models:

```
forward(code)  ~=  gnn          # analysis: code -> GNN specification
reverse(gnn)   ~=  code'        # synthesis: GNN -> executable package
forward(code') ~=  gnn          # round-trip: re-analysis recovers the GNN
run(code')     =   working agent # execution: the package runs Active Inference
```

The roundtrip is not byte-identical and should not be described as strict structural isomorphism under the current taxonomy. The historical milestone is weaker and still useful: the same hidden-state, observation, and action roles survive the cycle, and the synthesized code runs, infers, and acts.

## The No-Exec Path

A second test (`test_inference_demo_no_exec`) demonstrates the same pipeline using `cogant.reverse.callable.MatrixFunctions` instead of `exec()`. MatrixFunctions builds runtime-callable Python closures directly from the parsed GNN model, producing numerically identical results without code generation or dynamic execution. This is the safer, production-ready path.

## Limitations and Next Steps

The current milestone uses a hand-written GNN rather than one produced by COGANT's forward pipeline on a real codebase. The matrices are small (2x2 aggregated), the transition model is identity (no real dynamics), and the agent's "observations" are argmax projections rather than actual sensor readings. The free-energy computation uses a simplified VFE formula without epistemic value.

Next steps: (1) run the full forward-reverse-run pipeline on a real repository analyzed by COGANT's forward pass, (2) implement non-trivial transition dynamics in the B tensor so the agent's state evolves meaningfully, (3) add epistemic value to the action selection (expected free energy with information gain), and (4) connect the agent loop to an actual environment where observations come from external state rather than self-prediction.
