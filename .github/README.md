# COGANT — Codebase-to-GNN Translation

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20705351.svg)](https://doi.org/10.5281/zenodo.20705351)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%E2%80%933.13-blue.svg)](../cogant/pyproject.toml)

> **Translate software repositories into Active Inference generative models.**

**COGANT** (Codebase-to-GNN Translation) deterministically converts Python, JavaScript, and
TypeScript codebases into [Active Inference Institute](https://activeinference.org/)
**Generalized Notation Notation (GNN)** state-space models — complete with A/B/C/D probabilistic
matrices, Markov-blanket partitions, and principled free-energy derivations.

It is best understood as an **evidence compiler**: it propagates reviewable program facts through
a finite fixpoint rule pipeline and emits graph, matrix, provenance, visualization, and round-trip
artifacts — each node and edge carrying **confidence** and **provenance** — rather than a single
opaque embedding. A reverse synthesizer reconstructs a runnable Python package from an emitted GNN
bundle, closing a forward → reverse → forward evaluation loop.

> GNN here means the Active Inference Institute's **Generalized Notation Notation**, *not* graph
> neural networks. COGANT's tensor exports can feed graph-neural-network pipelines, but those are a
> *consumer* of COGANT's output, not its format.

## What it does

```text
repo/ ──[ingest]──► ProgramGraph ──[translate]──► SemanticMappings ──[statespace]──► GNN
  V = nodes          declarative rules              HIDDEN_STATE,                A/B/C/D
  E = typed edges    fixpoint to convergence        OBSERVATION, ACTION, ...     matrices
```

- **Forward path** — source → program-dependence graph → fixpoint translation → semantic mappings
  → compiled state space → AII-spec GNN markdown bundle.
- **Reverse path** — `cogant reverse` / `cogant roundtrip` synthesize a runnable Python package
  from any GNN bundle and report `STRUCTURALLY_ISOMORPHIC`, `ROLE_PRESERVED`, `DRIFT`, or `FAILED`.
- **Incremental mode** — `cogant analyze --incremental <git-ref>` re-uses the prior run's program
  graph for unchanged paths (measured no-change / single-file speedups on the Flask benchmark).
- **Packaged demo server** — `cogant.server.app` exposes `/health` and `/translate`; a packaged
  `Dockerfile` (python:3.12-slim + uv) and `docker-compose.yml` run it as a container. It ships
  **no auth** — run it locally or behind your own reverse proxy, TLS, and authentication.

## Quick start

```bash
git clone --recurse-submodules https://github.com/ActiveInferenceInstitute/COGANT.git
cd COGANT/cogant            # the installable package lives in the nested cogant/ directory

uv sync --extra all
uv run cogant translate examples/control_positive/calculator \
    --output output/calculator --layout-output
uv run cogant validate output/calculator/gnn_package
```

Expected: a populated `output/calculator/` tree with `bundle.json`, `gnn_package/model.gnn.md`,
and a validator report scoring **100.0 / 100** on the calculator fixture.

**Batch / all formats:** from the project root, [`run_all.sh`](../run_all.sh) runs `translate`,
`scan`, `graph`, `export-gnn`, `render`, `viz`, and `validate` for each target in
[`run_all.json`](../run_all.json), writing a per-target tree plus a cross-target dashboard.

## Manuscript

The accompanying manuscript — *COGANT: Deterministic Codebase-to-GNN Translation* — documents the
IR theory, translation engine, confidence/provenance model, round-trip evaluation, and
reproducibility contract. The rendered PDF ships as an asset on the
[v0.6.0 release](https://github.com/ActiveInferenceInstitute/COGANT/releases/tag/v0.6.0); the
markdown sources live under [`manuscript/`](../manuscript/).

## Citation

If you use COGANT, please cite the archived release (metadata in [`CITATION.cff`](../CITATION.cff)):

- **Version DOI (v0.6.0):** [10.5281/zenodo.20705351](https://doi.org/10.5281/zenodo.20705351)
- **Concept DOI (all versions):** [10.5281/zenodo.20705350](https://doi.org/10.5281/zenodo.20705350)

> Friedman, Daniel Ari (2026). *COGANT: Deterministic Codebase-to-GNN Translation* (v0.6.0).
> Active Inference Institute. https://doi.org/10.5281/zenodo.20705351

## License

COGANT is released under the [MIT License](../LICENSE).

It depends on the Active Inference Institute **generalized-notation-notation** package (Python
import `src.gnn`) for parsing and validating against the upstream GNN toolchain; that dependency is
licensed **CC-BY-NC-SA-4.0** (see [`cogant/LICENSES.md`](../cogant/LICENSES.md)). COGANT's own code
remains MIT.

## More

- [`cogant/README.md`](../cogant/README.md) — full package overview, features, and CLI reference
- [`README.md`](../README.md) — repository layout and maintainer / rendering workflow
- [`cogant/CONTRIBUTING.md`](../cogant/CONTRIBUTING.md) — contribution guidelines and dev setup
- [`AGENTS.md`](AGENTS.md) — notes on this `.github/` configuration directory
