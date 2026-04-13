# Agents — py/cogant/runtime

## Owner
Semantic Lead / Runtime Execution

## What Is the Runtime Module

The `runtime/` module is the **executable Active Inference agent** that brings synthesized A/B/C/D matrices to life. It provides a pure-Python perception-action loop that:

1. **Observes** — infers hidden state from observations via likelihood matrix A
2. **Updates belief** — performs Bayesian-like state updates using observed evidence
3. **Plans** — selects actions by evaluating preference_score under each action's predicted outcome
4. **Transitions** — advances state belief via transition matrix B
5. **Learns** — accumulates multi-episode observations and updates A and D matrices from experience

The runtime is **zero-dependency** (no numpy, scipy, torch, etc.) to maximize portability. All computation uses native Python lists and arithmetic. Results are deterministic and reproducible.

## Pipeline Integration

```
stage 9: reverse/synthesizer.py  → synthesized matrices module (A, B, C, D)
    ↓
stage 10: runtime/              → Agent episodes, learning trajectories, free energy
    ↓
output: Episode transcripts, learned matrices, metrics (CSV, JSON)
```

The runtime is the **final stage** — everything upstream converges to matrix emission. The runtime then:
- Executes synthesized packages in test harnesses and benchmarks
- Validates that matrices exhibit expected behavioral properties (convergence, entropy reduction)
- Records multi-episode learning dynamics for evaluation in METRICS.yaml

## Core Components

### Main Classes & Functions

**AgentRuntime** — The perception-action loop engine
- **`__init__(matrices: Any)`** — Accept a module/namespace with A, B, C, D attributes
- **`from_matrices_dict(d: dict) -> AgentRuntime`** — Factory from raw nested lists
- **`step() -> AgentStep`** — Execute one perception-action cycle
- **`run_n_steps(n: int) -> list[AgentStep]`** — Run N steps, return step records
- **`run_until_convergence(max_steps=100) -> list[AgentStep]`** — Run until KL divergence stabilizes
- **`run_episode() -> EpisodeResult`** — Run one learning episode with observation accumulation
- **`run_multi_episode(n_episodes: int) -> MultiEpisodeResult`** — Run and learn across episodes
- **`reset()`** — Clear episode state and rewind to initial D prior
- **`get_free_energy() -> float`** — Query current step's variational free energy
- **`serialize() -> dict`** — Export state (belief, trajectory) to JSON-compatible dict
- **`deserialize(d: dict)`** — Load state from serialized dict
- **`update_A_from_counts(learning_rate=1e-2)`** — Bayesian A matrix update from observation counts
- **`update_D_from_posterior(learning_rate=1e-2)`** — Dirichlet-like D update from final beliefs

**AgentConfig** — Configuration dataclass
- **`max_steps: int = 100`** — Maximum inference steps per episode
- **`convergence_threshold: float = 1e-4`** — KL(state | prior) cutoff for early stopping
- **`action_selection: str = "preference"`** — Strategy: "preference" (argmax) or future: "entropy"
- **`seed: int = 42`** — Random seed (reserved for stochastic action selection)
- **`from_yaml(path) -> AgentConfig`** — Load from YAML file
- **`to_yaml(path)`** — Save to YAML file
- **`with_defaults() -> AgentConfig`** — Create instance with defaults

**AgentStep** — Record of one inference cycle
- **`t: int`** — Timestep index (0-based)
- **`state_dist: list[float]`** — Belief state: P(hidden_state | obs_history)
- **`obs: int`** — Index of observed modality (argmax from likelihood)
- **`action: int`** — Index of selected action
- **`free_energy: float`** — Variational free energy at this step

**EpisodeResult** — Complete episode trajectory
- **`steps: list[AgentStep]`** — Ordered step records
- **`final_posterior: list[float]`** — Final state belief (last step's state_dist)
- **`obs_counts: list[float]`** — Histogram of observations seen
- **`obs_state_counts: list[list[float]]`** — Joint soft counts [n_obs x n_states] for A learning
- **`mean_free_energy: float`** — Average VFE across episode
- **`final_free_energy: float`** — VFE at last step

**MultiEpisodeResult** — Multi-episode learning summary
- **`episodes: list[EpisodeResult]`** — Per-episode records
- **`vfe_trajectory: list[float]`** — Mean VFE per episode
- **`final_vfe_trajectory: list[float]`** — Final-step VFE per episode
- **`D_trajectory: list[list[float]]`** — Snapshots of D prior after each episode
- **`learning_rate: float`** — Learning rate used for matrix updates

**EpisodeMetrics** — Single-episode summary statistics
- **`episode_id: int`** — Unique episode identifier
- **`n_steps: int`** — Number of steps executed
- **`mean_free_energy: float`** — Mean VFE
- **`final_free_energy: float`** — Final-step VFE
- **`n_unique_obs: int`** — Count of distinct observations
- **`action_entropy: float`** — Shannon entropy of action distribution
- **`to_csv_row() -> dict`** — Export for CSV logging

**RunMetrics** — Multi-episode aggregate
- **`episodes: list[EpisodeMetrics]`** — Per-episode metrics
- **`total_steps: int`** — Sum of steps across all episodes
- **`summary_statistics() -> dict[str, float]`** — Compute mean/std/min/max over episodes
- **`plot_free_energy() -> matplotlib.Figure`** — Plot VFE trajectory (requires matplotlib)

### Module-Level Functions

**`run_n_steps(runtime, n) -> list[AgentStep]`**
- Convenience wrapper: execute N perception cycles on a runtime instance

**`run_until_convergence(runtime, max_steps=100) -> list[AgentStep]`**
- Run until KL(state_dist || D) < convergence_threshold, or max_steps reached

**`kl_divergence(p, q) -> float`**
- Compute KL(p || q) = Σ p[i] * log(p[i] / q[i]) with epsilon safety

**`free_energy(state_dist, obs_idx, A, C, D) -> float`**
- Compute variational free energy = -log P(o | state) + KL(state || D)

### Internal Helpers

**`_normalize(dist) -> list[float]`**
- Normalize a distribution to unit sum (with epsilon to avoid divide-by-zero)

**`_argmax(values) -> int`**
- Return index of maximum value (pure Python, no numpy)

**`_mat_vec(mat, vec) -> list[float]`**
- Matrix-vector multiply A @ x using nested loops

**`_default_likelihood(A, state_dist) -> list[float]`**
- Fallback A @ q when synthesized module has no likelihood() method

**`_default_transition(B, state_dist, action) -> list[float]`**
- Fallback B[:, :, action] @ q when synthesized module has no transition() method

**`_default_preference_score(C, obs_dist) -> float`**
- Fallback C · o when synthesized module has no preference_score() method

## Data Representations

All outputs are **dataclasses** (immutable after construction). All distributions are **plain lists of floats** (no numpy, torch, or scipy). Numerical stability is ensured by epsilon constants (1e-10) in logarithms and normalization.

```python
@dataclass
class AgentStep:
    t: int
    state_dist: list[float]
    obs: int
    action: int
    free_energy: float

@dataclass
class EpisodeResult:
    steps: list[AgentStep]
    final_posterior: list[float]
    obs_counts: list[float]
    obs_state_counts: list[list[float]]
    mean_free_energy: float
    final_free_energy: float

@dataclass
class MultiEpisodeResult:
    episodes: list[EpisodeResult]
    vfe_trajectory: list[float]
    final_vfe_trajectory: list[float]
    D_trajectory: list[list[float]]
    learning_rate: float

@dataclass
class AgentConfig:
    max_steps: int = 100
    convergence_threshold: float = 1e-4
    action_selection: str = "preference"
    seed: int = 42

@dataclass
class EpisodeMetrics:
    episode_id: int
    n_steps: int
    mean_free_energy: float
    final_free_energy: float
    n_unique_obs: int = 0
    action_entropy: float = 0.0

@dataclass
class RunMetrics:
    episodes: list[EpisodeMetrics]
    total_steps: int = 0
```

## Common Usage Patterns

### Run a Single Episode

```python
from cogant.runtime.loop import AgentRuntime

# Create runtime from raw matrices
rt = AgentRuntime.from_matrices_dict({
    "A": [[0.9, 0.1], [0.1, 0.9]],    # Likelihood: 2 obs, 2 states
    "B": [[[1.0], [0.0]], [[0.0], [1.0]]],  # Transition: 2 states, 1 action
    "C": [1.0, 0.0],                   # Preference: obs 0 preferred
    "D": [0.5, 0.5],                   # Prior: uniform
})

# Run a single episode and inspect results
episode = rt.run_episode()
print(f"Steps: {len(episode.steps)}")
print(f"Mean VFE: {episode.mean_free_energy:.4f}")
print(f"Final belief: {episode.final_posterior}")
```

### Multi-Episode Learning

```python
from cogant.runtime.loop import AgentRuntime

rt = AgentRuntime.from_matrices_dict({...})

# Learn across 10 episodes with A and D updates
result = rt.run_multi_episode(
    n_episodes=10,
    update_A=True,
    update_D=True,
    learning_rate=1e-2
)

# Plot VFE trajectory
import matplotlib.pyplot as plt
fig = result.episodes_metrics().plot_free_energy()
plt.show()

# Inspect learned matrices
print(f"Final A matrix: {rt.A}")
print(f"Final D prior: {rt.D}")
```

### Convergence Testing

```python
from cogant.runtime.loop import run_until_convergence
from cogant.runtime.config import AgentConfig

cfg = AgentConfig(max_steps=500, convergence_threshold=1e-5)
rt = AgentRuntime.from_matrices_dict({...})

steps = run_until_convergence(rt, max_steps=cfg.max_steps)
print(f"Converged in {len(steps)} steps")
print(f"Final free energy: {steps[-1].free_energy:.6f}")
```

### Serialize and Resume

```python
from cogant.runtime.loop import AgentRuntime

rt = AgentRuntime.from_matrices_dict({...})
state = rt.serialize()

# Save to JSON
import json
with open("agent_state.json", "w") as f:
    json.dump(state, f)

# Load and resume
with open("agent_state.json") as f:
    restored = json.load(f)
rt.deserialize(restored)
rt.reset()
steps = rt.run_n_steps(5)
```

### Configuration from YAML

```python
from cogant.runtime.config import AgentConfig

# Load from file
cfg = AgentConfig.from_yaml("agent_config.yaml")
print(f"Max steps: {cfg.max_steps}")

# Save modified config
cfg.max_steps = 200
cfg.to_yaml("agent_config_new.yaml")
```

## Key Concepts & Design Decisions

### Perception-Action Cycle

Each **step** executes the canonical Active Inference loop:

1. **Likelihood update**: P(o | q) via A matrix (argmax observation)
2. **State update**: q_new = softmax(log A[o, :] + log D) (Bayesian-ish)
3. **Action selection**: argmax_a { expected_preference(a) } via C matrix
4. **Transition**: q_final = B[state, action] @ q (deterministic dynamics)

### Numerical Stability

- All distributions are normalized to sum ≈ 1.0 using epsilon safety (1e-10)
- Logarithms use epsilon guards: log(max(x, eps)) to avoid domain errors
- Free energy is guaranteed finite even on near-degenerate distributions

### No-Dependency Philosophy

- Pure Python lists and arithmetic only
- No numpy arrays, no scipy, no torch
- Synthesized packages can be deployed to constrained environments (embedded, serverless)
- Benchmarks compare against numpy baselines (via optional `benchmarks/` suite)

### Multi-Episode Learning

- **A matrix learning**: frequency-based update using obs_state_counts soft histogram
- **D matrix learning**: posterior averaging (Dirichlet-like update)
- Both use exponential moving average with configurable learning_rate
- No gradient descent; all updates are closed-form Bayesian

### Action Selection Strategy

Currently only **"preference"** (argmax of C · predicted_obs) is implemented.
Reserved for future: **"entropy"** (minimize expected information entropy of posterior).

## How to Extend

### Add a New Action Selection Strategy

1. Modify `AgentConfig.action_selection` validation in `config.py`
2. Implement selection logic in `AgentRuntime.step()`:
   ```python
   if self.config.action_selection == "my_strategy":
       action = self._select_action_my_strategy(...)
   ```
3. Add docstring explaining strategy and cite decision theory reference
4. Test on all fixture matrices to ensure convergence properties

### Add a Custom Likelihood Function

If synthesized module exposes a custom `likelihood(state_dist) -> list[float]`:
1. AgentRuntime binds it automatically in `__init__`
2. Custom function receives belief state, returns predicted observation distribution
3. Must be numerically stable and sum to ≈ 1.0

### Extend Learning Rules

1. Subclass AgentRuntime and override `update_A_from_counts()` or `update_D_from_posterior()`
2. Implement new Bayesian update rule (e.g., Gamma-Poisson conjugate prior)
3. Document prior assumptions and convergence rate
4. Benchmark against existing learning on fixtures

### Add Serialization Formats

1. Extend `serialize()` to emit new formats (e.g., MessagePack, Protocol Buffers)
2. Add `deserialize_<format>()` class method
3. Ensure round-trip fidelity: serialize → deserialize → same agent behavior
4. Test with all fixture matrices

## File Map

| File | Purpose |
|------|---------|
| `loop.py` | AgentRuntime, AgentStep, EpisodeResult, MultiEpisodeResult, run_n_steps, run_until_convergence, helper functions |
| `config.py` | AgentConfig dataclass with validation and YAML serialization |
| `metrics.py` | EpisodeMetrics, RunMetrics, free_energy, kl_divergence, statistical aggregation |
| `__init__.py` | Public API exports and module docstring |
| `loop.pyi` | Type stubs for runtime module (mypy) |
| `config.pyi` | Type stubs for config module |
| `metrics.pyi` | Type stubs for metrics module |

## Common Failure Modes & Debugging

### Diverging Free Energy

**Symptom**: VFE increases or oscillates wildly across steps.
**Cause**: Misaligned A/B/C/D matrix shapes or invalid likelihood computation.
**Fix**: Check that A and B row/column dimensions match the number of states. Validate that likelihood always returns a list of length n_obs.

### Non-Converging Belief State

**Symptom**: KL(state | prior) remains high even after max_steps.
**Cause**: Weak evidence (A matrix nearly uniform) or high prior entropy (uniform D).
**Fix**: Increase max_steps or lower convergence_threshold. Inspect A matrix: very low peak values prevent sharp state updates.

### Multi-Episode Learning Plateaus

**Symptom**: A and D don't improve after first few episodes; VFE flat-lines.
**Cause**: Learning rate too low or observation counts insufficient.
**Fix**: Increase learning_rate (e.g., 1e-1 instead of 1e-2). Run more episodes per learning cycle. Check that all cells of A are being updated (some rows may have zero coverage).

### Serialization/Deserialization Mismatch

**Symptom**: After deserialize(), agent behavior differs from original.
**Cause**: Floating-point precision loss or state not fully captured.
**Fix**: Use serialize() → JSON → deserialize() round-trip in tests. Verify that all matrices and belief state are present in serialized dict.

## Integration with Reverse & Synthesis

The runtime is designed to pair with outputs of `cogant/reverse/synthesizer.py`:
- Synthesized module exposes A, B, C, D as nested lists
- Optional helper methods: `likelihood()`, `transition()`, `preference_score()`
- Runtime binds helpers via `__init__` inspection; falls back to defaults if missing
- All downstream tests and benchmarks use runtime to validate synthesized code

See `cogant/examples/` fixtures for reference synthesized packages and their runtime usage.

## See Also

- `py/cogant/runtime/README.md` — module-level overview
- `py/cogant/reverse/` — synthesizer that produces matrices modules
- `py/cogant/examples/` — fixture packages and runtime test harnesses
- `py/cogant/statespace/` — compiles semantic mappings to A/B/C/D matrices
- `cogant/evaluation/METRICS.yaml` — ground truth for multi-episode learning benchmarks (regenerated via `tools/regenerate_metrics.py`)
