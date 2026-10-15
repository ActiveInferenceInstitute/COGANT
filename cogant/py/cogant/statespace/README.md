# State Space

Extracts and compiles state space models from program graphs and semantic mappings. Identifies hidden state variables, observation modalities, actions, transitions, likelihoods, and preferences for Active Inference modeling.

## API

StateSpaceCompiler builds the complete state space model. Initialize with program_graph and schema_name, then call compile(semantic_mappings) to get a StateSpaceModel containing variables, observations, actions, transitions, likelihoods, preferences, and temporal analysis.

StateVariable represents a single state variable with type, cardinality, domain, and factorization info. StateVariableType classifies variables as boolean, discrete, continuous, categorical, vector, or composite. ConfidenceLevel tracks extraction confidence across all extracted elements.

ObservationModality represents observation channels (sensor, log, metric, event) linked to read-only nodes. Action represents system actions tied to controller nodes, with parameters, effects, and preconditions. Transition captures state transitions with source/target states, triggering actions/events, and probability.

Likelihood models probability distributions over state variables using bernoulli, categorical, gaussian, or other types. Preference captures constraints and goals over state space with logical expressions and weights.

TemporalAnalyzer determines time regime (synchronous, asynchronous, event-driven, hybrid) and extracts temporal orderings and event patterns. TemporalMetrics quantifies async fraction, event-driven fraction, and parallel/sequential edge counts.

StateVariableExtractor identifies hidden state from hidden_state mappings, computing cardinality, domain, and factorization. FactorizationInfo tracks factor independence and dependencies for variable decomposition.

## Explicit finite models

`FiniteModelSpec`, `compile_finite_model`, and `verify_finite_model` provide an
authored-model route with ordered complete states and total probability kernels.
`FiniteModel` stores immutable A/B/C/D coefficients and can create a runtime with
independent mutable copies. See the [finite-model guide](../../../docs/api/finite_models.md)
for the schema, resource contract, CLI, and examples. This interface is separate
from graph-based state-variable extraction.

## Graph-derived usage

```python
from cogant.statespace import StateSpaceCompiler
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import SemanticMapping

# Create program graph and semantic mappings
graph = ProgramGraph(...)
mappings = {...}  # Dict[str, SemanticMapping]

# Compile state space model
compiler = StateSpaceCompiler(graph, schema_name="my_schema")
model = compiler.compile(mappings)

# Access components
print(f"Variables: {len(model.variables)}")
print(f"Actions: {len(model.actions)}")
print(f"Time regime: {model.time_regime}")
```
