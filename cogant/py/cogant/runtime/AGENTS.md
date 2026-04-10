# Agents — py/cogant/runtime

## Owner

Semantic Lead

## Responsibilities

Executable Active Inference loop on synthesized A/B/C/D matrices: `AgentRuntime`, `AgentConfig`, `AgentStep`, `EpisodeResult`, `MultiEpisodeResult`, plus helpers `run_n_steps` and `run_until_convergence`. Pure Python; pairs with packages emitted by `reverse/synthesizer.py`.

## Coordination

No external ML stack required; used in tests, benchmarks, and demos that exercise synthesized code.

## Files

- `config.py` — `AgentConfig`.
- `loop.py` — `AgentRuntime`, step records, run helpers.
- `__init__.py` — public exports.
