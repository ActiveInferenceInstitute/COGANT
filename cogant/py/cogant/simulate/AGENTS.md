# Agents — py/cogant/simulate

## Owner
Simulation and Active Inference Lead

## Responsibilities
Validate state space models for well-formedness. Simulate execution trajectories using Active Inference with free energy minimization. Compute belief dynamics and action selection. Generate trajectory data for analysis and visualization.

## Key Responsibilities
- Run ModelRunner.validate_model() to check state space consistency
- Run ModelRunner.run() to simulate trajectories with stochastic transitions
- Use FreeEnergyCalculator for VFE and EFE computations
- Apply Active Inference action selection policy
- Track state history, free energy evolution, and action sequences

## How to Extend
Add new distribution types to CategoricalDistribution or TransitionMatrix. Extend FreeEnergyCalculator with new cost functions or information metrics. Create new policy classes for action selection beyond current EFE. Add statistical analysis methods to SimulationVisualizer.

## Coordination
- Consumes: StateSpaceModel from statespace/
- Produces: Trajectory data consumed by export/, viz/
- Feeds: Results to validation and analysis pipelines
