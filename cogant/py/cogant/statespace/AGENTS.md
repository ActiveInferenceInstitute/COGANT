# Agents — py/cogant/statespace

## Owner
Semantic Analysis & State Space Modeling

## What Is the StateSpace Module

The `statespace/` module compiles **Active Inference state spaces** from semantic mappings and program graphs. It is stage 5 of the 10-stage COGANT pipeline. Given a `ProgramGraph` (with control flow and data dependencies) and `SemanticMappings` (which assign roles like HIDDEN_STATE, OBSERVATION, ACTION, POLICY, CONTEXT), this module extracts:

1. **Hidden State Variables** — latent program state (values of variables, execution flags, loop counters)
2. **Observation Modalities** — outputs and side effects visible to agents
3. **Actions** — controllable transitions (function calls, assignments, method invocations)
4. **Transitions** — deterministic or stochastic state evolution rules
5. **Likelihoods (A matrix)** — probability of observations given hidden states
6. **Preferences (C matrix)** — reward structure and goal preferences
7. **Time Regime** — synchronous, asynchronous, event-driven, or hybrid execution

The module produces a `StateSpaceModel` — a complete, self-contained IR ready for Active Inference simulation, free energy computation, policy learning, and GNN export.

## Pipeline Integration

```
stage 4: translate/         → ProgramGraph + SemanticMappings
    ↓
stage 5: statespace/        → StateSpaceModel (A/B/C/D matrices, variables, actions)
    ↓
stage 6: process/           → ProcessModel (causal structure + factor graph)
    ↓
stage 7: gnn/               → GNN bundle (markdown + JSON)
    ↓
stage 8-10: export, validate, scoring, ...
```

The statespace module is the **bridge between semantic analysis and executable Active Inference models**. All downstream simulations depend on the quality of variable extraction and factorization.

## Core Components

### StateVariable & VariableRegistry (variables.py)

**StateVariableType** — enum of six variable kinds:
- `BOOLEAN` — binary state (true/false, present/absent)
- `DISCRETE` — finite enumerated set (function call count, loop iteration index)
- `CONTINUOUS` — real-valued state (elapsed time, probability)
- `CATEGORICAL` — ordered discrete (error level: NONE, WARN, ERROR, FATAL)
- `VECTOR` — multi-dimensional state (embedding, tensor)
- `COMPOSITE` — product of sub-variables (compound objects, dataclass instances)

**ConfidenceLevel** — five-tier confidence for all extracted elements:
- `DEFINITE` — extracted directly from type hints or unambiguous code
- `HIGH` — inferred from assignments, control flow, or strong heuristics
- `MEDIUM` — heuristic-based, requires validation
- `LOW` — speculative, high uncertainty
- `UNCERTAIN` — no supporting evidence

**StateVariable** — dataclass representing a single hidden state variable:
- `id` — unique identifier within the state space
- `name` — symbol name (e.g., "user_id", "request_count")
- `var_type` — StateVariableType
- `node_id` — source node in the ProgramGraph
- `cardinality` — size of domain (for discrete/categorical)
- `domain` — explicit value set (e.g., ["IDLE", "RUNNING", "STOPPED"])
- `factors` — list of child variable IDs (for composite variables)
- `is_discrete` — boolean (auto-derived from var_type)
- `confidence` — extraction confidence level
- `description` — human-readable documentation
- `mutations` — IDs of code nodes that write to this variable
- `reads` — IDs of code nodes that read from this variable
- `observable` — whether this variable can be directly observed (read from output/side effect)

**VariableRegistry** — dual-index registry for variables:
- `add_hidden(var)` — register a hidden state variable
- `add_observation(obs)` — register an observation variable
- `get_hidden(var_id)` — lookup by ID
- `get_observation(obs_id)` — lookup by ID
- `find_by_role(role)` — filter by semantic role (e.g., "CONTROLLER", "ENVIRONMENT")
- `to_list()` — export as JSON-serializable list

**FactorizationInfo** — captures variable independence:
- `factors` — list of child variable IDs
- `independence_score` — [0.0, 1.0] measuring conditional independence
- `dependencies` — {var_id: [list of dependent var_ids]}

### StateVariableExtractor (variables.py)

Ingests a `ProgramGraph` and `SemanticMappings` to extract all hidden state variables.

**Key Methods:**
- `extract(semantic_mappings)` — main entry; returns `dict[str, StateVariable]`
- `get_state_variables()` — returns extracted variables
- `get_factorization(var_id)` — retrieves factorization info
- `compute_dimensionality()` — total state space size (product of cardinalities)

**Algorithm:**
1. Traverse ProgramGraph nodes with role HIDDEN_STATE
2. For each, infer type from annotations, assignment analysis, or type inference
3. Determine cardinality from control flow (loop bounds, enum sets, bitwidth hints)
4. Extract read/write edges to identify mutations and observations
5. Build factorization graph by analyzing Markov blanket structure
6. Assign confidence scores based on evidence strength

### TemporalAnalyzer (temporal.py)

Determines execution timing, ordering constraints, and event patterns.

**TimeRegime** — enum of four temporal modes:
- `SYNCHRONOUS` — all actions and state transitions happen in lockstep
- `ASYNCHRONOUS` — events and callbacks fire independently; time is local
- `EVENT_DRIVEN` — state changes only on explicit trigger events
- `HYBRID` — mix of synchronous and event-driven (e.g., scheduled tasks + interrupts)

**TemporalOrdering** — partial-order constraint:
- `predecessor_id` — node that must complete first
- `successor_id` — node that must follow
- `constraint_type` — "sequential", "before", "during", "after", "concurrent"
- `confidence` — [0.0, 1.0] confidence in the ordering

**EventPattern** — identifies event-trigger-handler chains:
- `event_node_id` — the event source (e.g., exception, interrupt, signal)
- `trigger_nodes` — conditions that activate the handler
- `handler_nodes` — nodes executed in response
- `is_async` — whether handler runs asynchronously

**TemporalMetrics** — summary statistics:
- `async_fraction` — ratio of async edges to total edges
- `event_driven_fraction` — ratio of event-driven to all transitions
- `parallel_edges_count` — concurrent edges
- `sequential_edges_count` — sequential edges
- `event_patterns_count` — number of event-handler pairs
- `has_async_handlers`, `has_event_triggers`, `has_loops` — boolean flags
- `is_discrete` — whether state transitions are discrete or continuous

**Key Methods:**
- `analyze()` — determine TimeRegime
- `get_ordering_constraints()` — return TemporalOrdering list
- `get_event_patterns()` — return EventPattern list
- `get_critical_path()` — longest path in execution DAG
- `get_markov_order()` — maximum dependency order in state evolution
- `find_feedback_loops()` — returns cycles in execution graph
- `to_mermaid()` — render as Mermaid sequence diagram

### StateSpaceModel (compiler.py)

Complete, immutable representation of an Active Inference state space.

**Fields:**
- `id` — unique model identifier
- `schema_name` — target schema (e.g., "pymcts", "pomdp")
- `variables` — `dict[str, StateVariable]` of all hidden states
- `observations` — `dict[str, ObservationModality]` of output channels
- `actions` — `dict[str, Action]` of controllable transitions
- `transitions` — `dict[str, Transition]` of state evolution rules
- `likelihoods` — `dict[str, Likelihood]` (A matrix, observation model)
- `preferences` — `dict[str, Preference]` (C matrix, goal structure)
- `time_regime` — TimeRegime classification
- `metadata` — arbitrary extra data (e.g., timestamp, source file, pipeline version)
- `degraded_output` — DegradedOutput if extraction failed partially

**Key Methods:**
- `validate()` — checks structural consistency; returns `list[str]` of errors
- `to_summary()` — export as flat `dict[str, Any]` for logging/display
- `get_hidden_state_dimension()` — total state space cardinality

### ObservationModality, Action, Transition, Likelihood, Preference (compiler.py)

**ObservationModality** — represents one output channel:
- `id`, `name`, `source_node_id` — identity and source
- `modality_type` — "numeric", "categorical", "symbolic", "signal"
- `cardinality` — size of observation set (None for continuous)
- `description`, `confidence` — documentation and confidence

**Action** — controllable program transition:
- `id`, `name`, `controller_id` — identity and actor
- `parameters` — `dict[str, Any]` of input arguments
- `effects` — list of variable IDs modified by this action
- `preconditions` — conditions that must hold to invoke the action
- `description`, `confidence` — documentation and confidence

**Transition** — single state evolution:
- `id`, `source_state`, `target_state` — source and target state tuples
- `action_id` — action triggering the transition (None if spontaneous)
- `triggered_by` — event or condition name
- `probability` — [0.0, 1.0] for stochastic transitions (None for deterministic)
- `confidence` — extraction confidence

**Likelihood** — observation probability model (A matrix):
- `id`, `variable_id` — identity and associated state variable
- `distribution_type` — "categorical", "gaussian", "poisson", "tabular"
- `parameters` — distribution parameters (e.g., {"mean": 0.5, "std": 0.2})
- `confidence` — how well the distribution fits empirical data

**Preference** — goal and reward structure (C matrix):
- `id`, `name`, `description` — identity
- `scope` — list of variable IDs that this preference applies to
- `expression` — symbolic expression (e.g., "user_count >= 100", "latency < 100ms")
- `weight` — [0.0, ∞) multiplicative priority
- `source` — "explicit" (from code annotations), "inferred", "heuristic"
- `confidence` — confidence in the preference modeling

### StateSpaceCompiler (compiler.py)

Main orchestrator: consumes ProgramGraph + SemanticMappings, produces StateSpaceModel.

**Key Methods:**
- `__init__(program_graph, schema_name)` — initialize with target schema
- `compile(semantic_mappings)` — main entry; returns StateSpaceModel
- `compile_incremental(semantic_mappings, prev_result)` — reuse variables from previous run if graph is unchanged
- `explain()` — returns narrative explanation of extracted state space (useful for debugging)

**DegradedOutput** — NamedTuple indicating partial extraction:
- `reason` — why extraction failed (e.g., "insufficient type information", "circular dependencies")
- `affected_matrices` — which matrices are incomplete (["A", "B", "C"] → [A, B, C])

## Data Representations

### Example: State Space for a Simple Request Handler

```python
from cogant.statespace import (
    StateSpaceCompiler, StateVariable, StateVariableType, ConfidenceLevel,
    ObservationModality, Action, Transition, Likelihood, Preference,
    TemporalAnalyzer, TimeRegime
)

# Given: program_graph from graph/, semantic_mappings from translate/
compiler = StateSpaceCompiler(program_graph, schema_name="pymcts")
state_space = compiler.compile(semantic_mappings)

# Inspect extracted variables
for var_id, var in state_space.variables.items():
    print(f"{var.name}: {var.var_type} (confidence={var.confidence})")
    # Example output:
    # request_id: DISCRETE (confidence=definite)
    # status: CATEGORICAL (confidence=high)
    # retry_count: DISCRETE (confidence=high)

# Inspect observations
for obs_id, obs in state_space.observations.items():
    print(f"[OBS] {obs.name}: {obs.modality_type} (cardinality={obs.cardinality})")
    # Example output:
    # [OBS] response_code: categorical (cardinality=6)
    # [OBS] latency_ms: numeric (cardinality=None)

# Inspect actions
for act_id, act in state_space.actions.items():
    print(f"[ACT] {act.name}: {len(act.effects)} effects")
    # Example output:
    # [ACT] send_request: 2 effects (status, timestamp)

# Temporal regime
print(f"Time regime: {state_space.time_regime}")
# Output: asynchronous (callbacks + retry logic)

# Validate consistency
errors = state_space.validate()
if errors:
    for err in errors:
        print(f"Error: {err}")
```

## Common Usage Patterns

### Extract State Variables from Semantic Mappings

```python
from cogant.statespace import StateVariableExtractor
from cogant.graph import ProgramGraph

graph: ProgramGraph = ...  # from graph builder
extractor = StateVariableExtractor(graph)

# Provide semantic mappings
mappings = {
    "var_request_id": SemanticMapping(role="HIDDEN_STATE", ...),
    "var_status": SemanticMapping(role="HIDDEN_STATE", ...),
    "func_send": SemanticMapping(role="ACTION", ...),
}

variables = extractor.extract(mappings)

# Query extracted variables
for var_id, var in variables.items():
    print(f"{var.name}: {var.var_type} @ {var.node_id}")
    if var.is_discrete:
        print(f"  Domain size: {var.cardinality}")
    print(f"  Mutated by: {var.mutations}")
    print(f"  Read by: {var.reads}")
```

### Analyze Temporal Structure

```python
from cogant.statespace import TemporalAnalyzer

analyzer = TemporalAnalyzer(graph)
regime = analyzer.analyze()
print(f"Execution regime: {regime}")

# Get ordering constraints
for constraint in analyzer.get_ordering_constraints():
    print(f"{constraint.predecessor_id} -> {constraint.successor_id} "
          f"({constraint.constraint_type}, confidence={constraint.confidence})")

# Identify event patterns
for pattern in analyzer.get_event_patterns():
    print(f"Event {pattern.event_node_id}:")
    print(f"  Triggers: {pattern.trigger_nodes}")
    print(f"  Handlers: {pattern.handler_nodes}")
    print(f"  Async: {pattern.is_async}")

# Get critical path
critical = analyzer.get_critical_path()
print(f"Critical path length: {len(critical)}")
```

### Compile Complete State Space

```python
from cogant.statespace import StateSpaceCompiler

compiler = StateSpaceCompiler(graph, schema_name="pymcts")
state_space = compiler.compile(semantic_mappings)

# Summary
summary = state_space.to_summary()
print(f"State dimension: {summary['state_dimensionality']}")
print(f"Observation dim: {summary['observation_dimensionality']}")
print(f"Action dim: {summary['action_dimensionality']}")
print(f"Time regime: {summary['time_regime']}")

# Validate
errors = state_space.validate()
if not errors:
    print("✓ State space is consistent")
else:
    print(f"✗ {len(errors)} validation errors:")
    for e in errors:
        print(f"  - {e}")

# Export for downstream use
import json
data = {
    "id": state_space.id,
    "variables": {vid: {...} for vid, var in state_space.variables.items()},
    "observations": {...},
    "actions": {...},
    "time_regime": state_space.time_regime.value,
}
with open("state_space.json", "w") as f:
    json.dump(data, f, indent=2)
```

### Incremental Compilation (for CI/Rebuild)

```python
from cogant.statespace import StateSpaceCompiler

compiler = StateSpaceCompiler(graph, schema_name="pymcts")

# Previous state space (from cached file or previous run)
prev_state_space = load_previous_result()

# Recompile; reuses variables if graph structure unchanged
state_space = compiler.compile_incremental(
    semantic_mappings,
    prev_result=prev_state_space
)

print(f"Compilation took: {state_space.metadata.get('duration_ms')} ms")
```

## Integration with Downstream Stages

1. **ProcessModel** (stage 6) — consumes variables and actions from StateSpaceModel to build causal factor graphs
2. **GNN Export** (stage 7) — converts A/B/C/D matrices to markdown and JSON
3. **Simulation** (via gnn/runner) — executes Active Inference update loops using state space
4. **Validation** (stage 8) — checks state space consistency and confidence metrics
5. **Scoring** (stage 10) — compares state spaces across pipeline runs to detect drift

## Responsibilities & Coordination

### Core Responsibilities
- Extract hidden state variables from semantic mappings
- Infer variable types, cardinality, and domain from code analysis
- Build observation modalities and action sets
- Determine transitions and likelihood distributions
- Analyze temporal structure and execution regime
- Track confidence and provenance for all elements
- Generate degraded outputs when information is incomplete
- Support incremental recompilation for faster iterative analysis

### Coordination
- **Input**: ProgramGraph (from graph/), SemanticMappings (from translate/)
- **Output**: StateSpaceModel (variables, observations, actions, transitions, likelihoods, preferences, time regime)
- **Consumed by**: ProcessModel (stage 6), GNNPackageBuilder (stage 7), GNNModelRunner, ValidationReport (stage 8)
- **Configuration**: schema_name (target Active Inference schema, e.g., "pymcts", "pomdp")
- **No mutable state**: Results are immutable dataclasses; thread-safe

## How to Extend

### Add a New Variable Type
1. Extend `StateVariableType` enum in `variables.py`
2. Add inference logic to `StateVariableExtractor._infer_type()`
3. Update factorization analysis in `StateVariableExtractor._compute_factorization()`
4. Test on fixtures with the new type
5. Update `.pyi` stub

### Support New Distribution Families
1. Add distribution_type string to `Likelihood` in `compiler.py`
2. Implement parameter extraction in `StateSpaceCompiler._extract_likelihoods()`
3. Add validation rules to `StateSpaceModel.validate()`
4. Document in distribution catalogs

### Track New Temporal Patterns
1. Extend `TemporalAnalyzer._detect_*` methods for new event/loop patterns
2. Add EventPattern detection logic
3. Update TimeRegime classification logic
4. Test on async/callback-heavy fixtures

### Add Confidence Tiers
1. Define new ConfidenceLevel enum value
2. Update confidence assignment logic in extractors
3. Add aggregation rules in `StateSpaceModel.to_summary()`

## Error Handling & Diagnostics

All extractors follow a consistent error handling pattern:

```python
try:
    result = extractor.extract(input)
except Exception as e:
    logger.warning(f"Extraction error: {e}")
    # Return partial result with degraded_output set
    return StateSpaceModel(..., degraded_output=DegradedOutput(
        reason=str(e),
        affected_matrices=["A", "B"]  # which matrices are incomplete
    ))
```

- Type inference errors are logged; default types used
- Missing cardinality information → assumed unbounded CONTINUOUS
- Circular dependencies → topological sort with fallback ordering
- Ambiguous temporal ordering → constraint relaxation with confidence penalty

## Validation Points

`StateSpaceModel.validate()` checks:
- All action effects reference existing variables
- All observation modalities reference valid nodes
- All transitions connect valid state tuples
- Likelihoods and Preferences are well-formed
- Markov blanket independence constraints hold
- No dangling references to undefined variables
- Time regime is consistent with temporal structure

## See Also

- `py/cogant/statespace/README.md` — module-level overview
- `py/cogant/translate/` — produces SemanticMappings
- `py/cogant/process/` — consumes StateSpaceModel
- `py/cogant/gnn/` — exports state space to GNN format
- `py/cogant/simulate/` — executes models using state space
