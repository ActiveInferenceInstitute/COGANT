# Active Inference from a programmer's perspective

> **What this page is:** A programmer-friendly translation of Active Inference (POMDPs, hidden states, observations, actions, policies) into vocabulary from everyday software engineering.
>
> **Prerequisites:** Comfort reading Python; no neuroscience background required.
>
> **Reading time:** ~12 minutes
>
> **Next steps:** [Markov blankets in codebases](markov_blanket.md) · [What is a GNN?](gnn.md) · [Tutorial: Reading the A/B/C/D matrices](../tutorials/05_gnn_interpretation.md)

Active Inference is a framework from computational neuroscience that describes how agents interact with their environment. COGANT uses it as a formal model for codebases. This page translates the key Active Inference concepts into programming terms you already know.

## The POMDP framing

Active Inference operates on a Partially Observable Markov Decision Process (POMDP). If you have written any state machine, you already understand the core structure:

- **Hidden states** -- the true state of the world that you cannot directly see. In code: private fields, database rows, in-memory caches.
- **Observations** -- noisy or partial views of the hidden state. In code: getter methods, API responses, log entries.
- **Actions** -- things the agent does that change the hidden state. In code: setter methods, database writes, HTTP requests.
- **Policies** -- rules for choosing which action to take next. In code: controllers, routers, schedulers, retry strategies.

The "partially observable" part is the key insight for software: a caller of your module cannot see your private fields directly. It can only observe them through your public API. This is not a metaphor -- it is a structural isomorphism.

## Free energy minimization

In Active Inference, an agent minimizes **variational free energy** -- a measure of the difference between what the agent expects and what it observes. High free energy means surprise. Low free energy means the agent's model of the world is accurate.

Translated to software:

```python
# High free energy: the system is "surprised"
# (what we expected != what we observed)
def handle_request(self, request):
    result = self.backend.query(request)
    if result != self.cached_prediction:
        # This is variational free energy in action:
        # update internal state to reduce surprise
        self.cache.invalidate()
        self.model.retrain(result)
        raise RetryableError("prediction mismatch")
```

Error handling, retry logic, and validation are all mechanisms for reducing free energy. A circuit breaker that trips after too many failures is literally an agent that has decided the environment is too surprising to continue interacting with.

## The A/B/C/D matrices

Active Inference models are specified by four matrices. COGANT derives all four from your [program graph](program_graph.md):

### A matrix -- likelihood (observation model)

**Shape:** `[n_observations x n_states]`

**What it answers:** "Given the hidden state, what will I observe?"

**In code terms:** This is the `observe()` or `get_*()` layer. Every `READS` or `OBSERVES` edge in the program graph contributes evidence to the A matrix. If `get_display()` reads from `self.display`, that creates a non-zero entry in A linking the `display` hidden state to the `get_display` observation.

```python
# This method IS an entry in the A matrix:
# P(observation="get_display" | hidden_state="display") is high
def get_display(self) -> str:
    return str(self.display)
```

COGANT uses a heuristic `0.9 / 0.1` diagonal-vs-off-diagonal fill: the state that a getter directly reads gets 0.9, and all other states get a small `0.1 / (n-1)` share. This produces a valid probability distribution without learned parameters.

### B matrix -- transition (dynamics model)

**Shape:** `[n_states x n_states x n_actions]`

**What it answers:** "Given the current state and an action, what is the next state?"

**In code terms:** This is the `update_state()` or `set_*()` layer. Every `WRITES` or `MUTATES` edge contributes. If `_execute_operation()` writes to `self.accumulator`, that creates a non-zero B entry linking the action to the state transition.

```python
# This method IS a slice of the B matrix:
# P(next_state="accumulator_updated" | current_state, action="_execute_operation")
def _execute_operation(self, op: str, value: float):
    if op == "+":
        self.accumulator += value  # WRITES edge -> B matrix entry
    self.history.append(op)        # WRITES edge -> B matrix entry
```

When an action has no `WRITES` edges, COGANT fills the B slice with an identity matrix (the state does not change under that action).

### C matrix -- preference (what the system wants)

**Shape:** `[n_observations]`

**What it answers:** "Which observations does the system prefer?"

**In code terms:** This is the `validate()` and `assert_*()` layer. Every [`CONSTRAINT`](../reference/translation_rules.md) mapping contributes to C — these are detected by `PreferenceRule` (semantic) and `TestAssertionRule` (behavioral) in `cogant.translate.rules`. A test assertion like `assert result > 0` encodes a preference for observations where the result is positive.

```python
# This function contributes to the C vector:
# preferred observation = "display shows correct result"
def test_addition_works(calculator):
    calculator.input_digit(3)
    calculator.input_operation("+")
    calculator.input_digit(2)
    calculator.equals()
    assert calculator.get_display() == "5"  # preference encoded here
```

When no `CONSTRAINT` mappings exist, C defaults to uniform (no preference).

### D matrix -- prior (initial beliefs)

**Shape:** `[n_states]`

**What it answers:** "What is the initial state before any observations?"

**In code terms:** This is the `__init__()` and configuration layer. [`CONFIGURATION`](../reference/translation_rules.md) nodes (YAML files, Settings classes, environment variables) seed the D vector — these are detected by `ConfigRule` and `FeatureFlagRule` in `cogant.translate.rules.control`. A `config.yaml` with `max_retries: 3` contributes a prior belief about the initial system state.

```python
# Configuration nodes become D matrix entries:
# P(initial_state) is informed by these defaults
class AppConfig:
    max_retries: int = 3          # CONFIGURATION node -> D vector
    timeout_seconds: float = 30.0  # CONFIGURATION node -> D vector
    debug_mode: bool = False       # CONFIGURATION node -> D vector
```

When no configuration evidence exists, D defaults to uniform.

## Putting it together

The complete Active Inference cycle maps to a standard request-response loop:

1. **Observe** (A matrix): read the current state through getters and sensors
2. **Infer** (A + D): update beliefs about hidden state given observations
3. **Evaluate** (C matrix): compare beliefs to preferences
4. **Plan** (B matrix): select an action that minimizes expected free energy
5. **Act** (B matrix): execute the action and transition to a new state
6. **Repeat**

COGANT's job is to extract this loop from your source code and make it explicit. The [GNN output](gnn.md) is the fully specified model. The [A/B/C/D matrices](gnn.md#the-7-semantic-roles) are the numerical representation. The [Markov blanket](markov_blanket.md) is the boundary that separates your system from its environment.

## What this means for your code

If COGANT reports that your A matrix is nearly singular (most observations have weak evidence linking them to hidden states), it means your getters do not clearly expose your internal state -- a measurable form of "hidden coupling." If the B matrix is mostly identity, your actions do not clearly change state -- possibly dead code. If C is uniform, you have no tests or validators. These are not analogies: they are numerical signatures of real architectural properties.

## Implementation

The four matrices, the agent loop, and the rule wiring are implemented across three packages:

| Concept on this page | Module (`py/cogant/...`) | API reference | Key class / function |
| --- | --- | --- | --- |
| A / B / C / D matrix construction | `gnn/matrices.py` | [`cogant.gnn` → Matrix builder](../api/gnn.md#matrix-builder) | `build_matrices`, `MatrixBuilder` |
| `READS`/`OBSERVES` → A matrix entries | `translate/rules/structural.py`, `translate/rules/semantic.py` | [`cogant.translate` → Rules](../api/translate.md#rules) | `ReadOnlyInputRule`, `ObservationRule` — see [translation rules reference](../reference/translation_rules.md) |
| `WRITES`/`MUTATES` → B matrix entries | `translate/rules/structural.py`, `translate/rules/semantic.py` | [`cogant.translate` → Rules](../api/translate.md#rules) | `MutatingSubsystemRule`, `ActionRule` — see [translation rules reference](../reference/translation_rules.md) |
| `CONSTRAINT` mappings → C vector | `translate/rules/semantic.py`, `translate/rules/behavioral.py` | [`cogant.translate` → Rules](../api/translate.md#rules) | `PreferenceRule`, `TestAssertionRule` — see [translation rules reference](../reference/translation_rules.md) |
| `CONFIGURATION` nodes → D vector | `translate/rules/control.py` | [`cogant.translate` → Rules](../api/translate.md#rules) | `ConfigRule`, `FeatureFlagRule` — see [translation rules reference](../reference/translation_rules.md) |
| Free-energy minimization loop (Observe → Infer → Plan → Act) | `runtime/loop.py` | [`cogant.runtime` → Loop](../api/runtime.md#loop) | `AgentRuntime`, `run_n_steps`, `run_until_convergence` |
| Free-energy / KL divergence numerics | `runtime/metrics.py` | [`cogant.runtime` → Metrics](../api/runtime.md#metrics) | numerically-stable helpers |
| Agent hyperparameters | `runtime/config.py` | [`cogant.runtime` → Config](../api/runtime.md#config) | `AgentConfig` |

## Further reading

- [What is a GNN?](gnn.md) -- the output format that encodes A/B/C/D
- [Markov blankets in codebases](markov_blanket.md) -- the boundary between system and environment
- [How COGANT assigns roles](role_assignment.md) -- how code nodes become states, observations, and actions
- [`cogant.runtime` API reference](../api/runtime.md) -- the agent loop that consumes the synthesized matrices
- [`cogant.gnn` API reference](../api/gnn.md) -- where the matrices themselves are built
