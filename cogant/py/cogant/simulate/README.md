# Simulate

Validates state space models and simulates execution trajectories using Active Inference. Implements free energy minimization for belief updates, stochastic state transitions, and trajectory analysis.

## API

ModelRunner validates and simulates state space models. Call validate_model(state_space) to check well-formedness, or run(state_space, steps, seed) to simulate a trajectory. Returns validation dict or trajectory dict with state history, actions taken, free energy evolution, and metadata.

CategoricalDistribution models discrete probability distributions with sample() for drawing from the distribution and log_prob(category) for probability queries. Supports uniform or custom initialization with automatic normalization.

TransitionMatrix represents state-to-state transition probabilities, including matrix operations and analysis. Useful for Markov chain analysis of state space.

FreeEnergyCalculator computes variational free energy (VFE) for belief updating and expected free energy (EFE) for action selection. Implements Active Inference mechanics including expected cost, information gain, and ambiguity reduction.

SimulationVisualizer generates trajectory plots showing state evolution, free energy dynamics, action sequences, and belief trajectories. Produces charts for analysis of simulation outcomes.

## Usage

```python
from cogant.simulate import ModelRunner, FreeEnergyCalculator
from cogant.statespace import StateSpaceCompiler

# Compile state space first
compiler = StateSpaceCompiler(graph, "my_schema")
state_space = compiler.compile(mappings)

# Validate and simulate
runner = ModelRunner(seed=42)
validation = runner.validate_model(state_space)

if validation["valid"]:
    result = runner.run(state_space, steps=100)
    print(f"Final state: {result['final_state']}")
    print(f"Free energy: {result['free_energy']}")
```
