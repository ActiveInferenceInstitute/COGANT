# Agents — evaluation/

## Owner

Test / evaluation maintainers (`CODEOWNERS`: `tests/`)

## Responsibilities

Benchmark drivers, dataset JSONL, static dashboards, figure generators, and pinned third-party trees under `eval_repos/` for roundtrip tests. Not part of the installable `py/cogant/` package.

## Coordination

- Narrative reports live in [`docs/evaluation/`](../docs/evaluation/README.md).
- Do not strip `LICENSE` files from `eval_repos/` upstreams.
- `run_eval.py` is the main real-world evaluation entry point (see [README.md](README.md)).

## Files

- `run_eval.py` — evaluation driver.
- `dataset/` — JSONL, card, regeneration scripts.
- `dashboards/` — static HTML summaries.
- `figures/` — figure generation and notes.
- `eval_repos/` — vendored upstreams (no per-folder AGENTS; upstream docs only).
