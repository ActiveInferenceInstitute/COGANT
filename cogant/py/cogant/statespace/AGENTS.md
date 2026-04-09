# Agents — py/cogant/statespace

## Owner
Semantic Analysis Lead

## Responsibilities
Extract and compile complete state space models from program graphs using semantic mappings. Identify hidden state variables, observation modalities, actions, and transitions. Support Active Inference modeling with preferences and likelihood distributions. Analyze temporal execution patterns and determine time regimes.

## Key Responsibilities
- Run StateVariableExtractor to identify hidden state from semantic mappings
- Run StateSpaceCompiler to extract observations, actions, transitions, likelihoods, preferences
- Use TemporalAnalyzer to determine time regime and extract temporal orderings
- Compute confidence levels and track provenance for all extracted elements

## How to Extend
Add new StateVariableType enums for different variable classes. Extend TemporalAnalyzer._detect_async_nodes to recognize new asynchronous patterns. Add new distribution types in compiler._extract_likelihoods. Create PolicyExtractor subclasses for domain-specific preference patterns.

## Coordination
- Consumes: ProgramGraph from graph/, semantic mappings from ingest/
- Produces: StateSpaceModel consumed by simulate/, export/, validate/
- Works with: process/ for cross-model consistency, provenance/ for evidence tracking
