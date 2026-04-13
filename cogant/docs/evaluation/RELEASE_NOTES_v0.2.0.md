# COGANT v0.2.0 -- Release Notes

**Release date:** 2026-04-09
**Status:** Alpha
**Wheel:** `cogant-0.2.0-py3-none-any.whl` (512 KB)

## Overview

COGANT v0.2.0 is the first feature-complete release of the Codebase-to-GNN Translation Engine. Where v0.1.0 delivered the forward pipeline (source code to GNN state-space models), v0.2.0 closes the loop with a full reverse pipeline, an Active Inference runtime, and the infrastructure needed to make COGANT usable beyond a research prototype. The test suite has grown from 869 to 1300+ tests with zero failures, every public API has docstrings and type annotations, and the documentation site covers concepts, cookbooks, FAQs, and API reference.

The headline feature is `cogant.reverse` -- a symmetric pipeline that parses GNN markdown back into a Python package plan and synthesizes an idempotent package whose re-ingestion recovers the original semantic roles. This is backed by a formal Galois connection proof (ISOMORPHISM_THEOREM.md) with measured ε-bounded roundtrip error on the evaluation set. Alongside the reverse pipeline, a new Active Inference runtime lets users instantiate agent loops from GNN models, stepping through belief updates with VFE convergence metrics, making the generated models not just descriptive but executable.

On the infrastructure side, v0.2.0 adds a DAG-based pipeline executor with topological sort, a content-addressed result cache, an entry-point plugin registry, schema versioning with `cogant migrate`, and a YAML rule DSL that lets users define custom role-assignment rules without writing Python. Observability gains structured logging and in-process metrics (counters, histograms, spans). The CLI now includes `cogant doctor` for environment diagnostics, `cogant init` for project scaffolding, and `cogant explain` for per-rule attribution of every AI role assignment.

Documentation has been substantially expanded: 83+ annotated bibliography entries, 20 cookbook recipes, 35 FAQ items, 6 deep concept explainers, and a complete mkdocs-material site. A FastAPI demo server and Jupyter notebooks provide interactive on-ramps. The ML dataset ships 6 fixtures with node-level role labels in a HuggingFace-compatible format, and a reproducible benchmark harness measures stage timing, memory, and GNN statistics across the full fixture set.

## Installation

```bash
pip install cogant==0.2.0
```

With optional extras:

```bash
pip install 'cogant[viz]==0.2.0'        # plotly + matplotlib visualization
pip install 'cogant[multilang]==0.2.0'  # tree-sitter JS/TS parsers
pip install 'cogant[all]==0.2.0'        # everything
```

Verify:

```bash
python -c "import cogant; print(cogant.__version__)"   # -> 0.2.0
cogant doctor                                          # environment check
cogant --help                                          # subcommand list
```

Requires Python >=3.11.

## What's New vs v0.1.0

- **Reverse pipeline**: GNN markdown parser + package planner + Python synthesizer + idempotency checker
- **Active Inference runtime**: agent loop with step/convergence/VFE metrics + 12-repo example zoo
- **Pipeline DAG executor**: topological sort, cycle detection, content-addressed caching
- **Plugin system**: entry-point plugin registry with `cogant plugin list/info`
- **Schema versioning**: `cogant migrate` CLI subcommand
- **YAML rule DSL**: custom role rules compiled to Python matchers without code
- **Observability**: structured logging + in-process metrics (Counter, Histogram, span)
- **CLI ergonomics**: `cogant doctor`, `cogant init`, `cogant explain`, progress bars, rich `--help`
- **Documentation**: 83+ bibliography entries, 20 cookbooks, 35 FAQs, 6 concept explainers, mkdocs site
- **Testing**: 1300+ tests (up from 869), Hypothesis property tests, mutation testing, roundtrip integration
- **ML dataset v0.1**: 6 fixtures with node-level role labels, HuggingFace-style card
- **Multi-language**: tree-sitter JS/TS parsers + git-diff incremental mode
- **Theory**: ISOMORPHISM_THEOREM.md Galois connection proof, CALIBRATION.md, AII spec compliance audit

## Known Limitations

- Event pipeline roundtrip achieves 47.6% role match (fan-out synthesis limitation, tracked as xfail)
- Rust hot path is scaffolding only -- all benchmarks reflect pure-Python execution
- ML dataset is 6 fixtures -- sufficient for calibration, too small for supervised training
- JS/TS translation rule coverage is partial compared to Python
- mkdocs site built but not yet deployed to a stable URL
