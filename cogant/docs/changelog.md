<!-- Canonical source: `CHANGELOG.md` at repository root. Edit that file first, then copy here so MkDocs stays aligned: `cp CHANGELOG.md docs/changelog.md` -->

# CHANGELOG

All notable changes to COGANT are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.5.0] - 2026-04-10

### Major Achievement
**Roundtrip Isomorphism:** 19/23 ISOMORPHIC (v0.4.0) → **23/23 ISOMORPHIC (v0.5.0)** with mean ε = 1.0.0. All 23 targets in the canonical roundtrip evaluation set (12 zoo fixtures, 3 curated real-world examples, 8 uncurated libraries) now achieve ε ≥ 0.8 after POLICY/CONTEXT stub fixes in the reverse synthesizer.

### Added
- **Incremental analysis mode** — `cogant translate --incremental <git-ref>` / `PipelineConfig.incremental_since`. Reuses cached program graph for unchanged files; 19.6× no-change speedup, 5.6× single-file speedup on Flask benchmark.
- **Multi-episode Bayesian learning** — `AgentRuntime.run_multi_episode`, `run_episode`, `update_D_from_posterior`, `update_A_from_counts`. Enables streaming belief updates and learned parameter adaptation.
- **Production FastAPI server** — `cogant.server.app` with `/health` and `/translate` endpoints. Includes integration test suite, Dockerfile (python:3.12-slim + uv, `EXPOSE 8080`), and docker-compose.yml.
- **Enhanced diagnostics** — `cogant doctor` extended with tree-sitter grammar checks, uv lockfile parity audit, optional-dependency verification.
- **Project scaffolding** — `cogant init <path>` guides setup: `cogant.yaml`, source structure, `pyproject.toml` template.
- **POLICY stub emission** — Reverse synthesizer generates `decide_*` methods proportional to origin GNN POLICY role count (not fixed scaffolding).
- **CONTEXT stub emission** — Reverse synthesizer generates `get_context_*` methods for CONTEXT/CONFIG roles.
- **CONSTRAINT stub fix** — Reverse synthesizer scales `check_*` stub generation to match origin constraint counts.
- **Tutorial notebooks 07–12** — Flask walkthrough, constraints, plugins, YAML DSL, multi-episode learning, cross-language roundtrip examples.
- **Cross-language roundtrip** — JavaScript Observer (`examples/zoo/13_js_observer`) round-trips to GNN with role_match_score=1.0.
- **Scaling regression tests** — Guards for B-tensor sparsity, BFS traversal, AST cache eviction, INHERITS edge deduplication at high edge density (dulwich benchmark).
- **Benchmark dashboard** — `evaluation/dashboards/benchmarks.html` (Chart.js, self-contained) tracks performance over runs.
- **Documentation overhaul** — Comprehensive docstring pass, mkdocs navigation restructure, getting-started guide, API reference updates.
- **Manuscript appendices A–E** — Galois connection proofs, GNN spec compliance audit, ε derivation, scaling analysis, cross-language extension claims; 40+ new citations.
- **Theory documentation** — New `docs/theory/roundtrip.md` explaining round-trip validation, epsilon classifications (ISOMORPHIC/APPROXIMATE/DIVERGENT), and the v0.5.0 23/23 achievement.

### Fixed
- **Tree-sitter JS grammar fallback** — `.ts` files on mixed JS/TS repositories no longer fail hard; grammar fallback to JavaScript parser prevents parse errors.
- **TypeScript parse test** — Loosened assertion to accommodate JS grammar fallback path.
- **Roundtrip improvements** — POLICY stub + CONTEXT stub + CONSTRAINT fix resolves all pre-v0.5.0 failure modes (zoo/07, zoo/09, zoo/10, zoo/12, tqdm, fastapi, click, httpx, urllib3, requests, flask_app).

### Changed
- **Dependency updates** — `pyproject.toml` refreshed, `uv.lock` synchronized.
- **Pipeline runner** — Default stages now explicitly list all 10 (ingest, static, normalize, graph, dynamic, translate, statespace, process, export, validate).

### Test and Type Safety
- **2129 tests passing** with 86 skipped (optional toolchains), 12 failing (known xfails), 1 xpassed. Line coverage: **83.42%** on `py/cogant/`.
- **mypy strict: 0 errors** across 179 source files.
- **ruff check: 0 violations** on v0.5.0 codebase.

### Measurement
- **Incremental mode speedups:** 19.6× no-change (cached graph), 5.6× single-file (partial re-run) on Flask.
- **Roundtrip metric:** 23/23 ISOMORPHIC, mean ε = 1.0000, min ε = 1.0000, max ε = 1.0000 (perfect match on all targets).
- **Semantic roles discovered:** 22 translation rules assigned HIDDEN_STATE, OBSERVATION, ACTION, POLICY, CONSTRAINT, CONTEXT roles; 7 total role kinds.
- **Markov blanket strategies:** 5 seed strategies (auto, module, class, subgraph, manual) for blanket extraction; auto strategy deterministic with O(V+E) complexity.

## [0.4.0] - 2026-04-10

### Added
- CONSTRAINT synthesizer: proportional `check_*` stubs — variable-count assertion scaffolding matching origin GNN role counts (was fixed 3-4 stubs)
- Empirical claim extended: full 10-step Active Inference cycles on zoo/02_observer, zoo/04_pomdp_minimal, zoo/06_hierarchical
- mypy strict: 0 errors across 177 source files (was 163 at v0.3.0 start)
- Coverage: 81% total (was 76% at v0.3.0)
- tree-sitter multi-language parser: JS/TS + Python fallback
- Tutorial notebooks: 6 Jupyter notebooks (01-06)
- Interactive playground: single-file HTML with cytoscape.js + CodeMirror
- mkdocs-material docs site + GitHub Pages workflow
- ROUNDTRIP_EVAL.md: 23-target roundtrip ε evaluation — now 19/23 ISOMORPHIC (83%) after CONSTRAINT fix

### Fixed
- CONSTRAINT role collapse: `cnst_` prefix not detected by forward pipeline's PreferenceRule → now emits `check_` prefix proportional to origin count
- model_name default lowercased: `CogantModel` → `cogant_model` (law7 property enforcement)
- MatrixFunctions public/private split: AgentRuntime now reads A/B/C/D correctly
- Parser ontology fallback: non-standard variable names (s_hidden, o_sensor) now classified via ActInfOntologyAnnotation

### Improved
- Roundtrip ε: 14/23 ISOMORPHIC (61%) → 19/23 ISOMORPHIC (83%) after CONSTRAINT fix
- Real-world eval: 8/8 repos pass forward pipeline
- Type annotations: 50+ modules updated to modern Python typing (Counter[str], list[T])

### Performance
- Dulwich scaling cliff documented: 1.80 e/n ratio → 380s / 8.5 GB (known issue, wave 15 target)

## [0.2.0] - 2026-04-09

### Added

**Reverse Pipeline (GNN to Code)**
- `cogant.reverse` subpackage: GNN markdown parser, package planner, Python synthesizer, idempotency checker
- Runtime-callable matrix functions (likelihood, transition, EFE, best_action) without exec
- ISOMORPHISM_THEOREM.md: Galois connection proof + ε-bounded roundtrip error formalization

**Active Inference Runtime**
- Active Inference agent loop with step/convergence/VFE metrics
- 12-repo Active Inference example zoo with hand-written GNN models for repos 04, 06, 12

**Pipeline and Infrastructure**
- DAG execution engine with topological sort and cycle detection
- Content-addressed result cache keyed on repo sha256
- Entry-point plugin registry + `cogant plugin list/info` CLI
- Schema versioning + `cogant migrate` CLI subcommand
- YAML rule DSL compiled to Python matchers for custom role rules without code
- Structured logging + in-process metrics (Counter, Histogram, span) observability layer

**CLI and Ergonomics**
- `cogant doctor` environment check subcommand
- `cogant init` project scaffolding subcommand
- `cogant explain` rule-level attribution for AI role assignments
- Progress bars, better error messages, rich `--help`
- Composable pydantic config system

**Documentation**
- 16 mkdocs-material documentation sections with tutorials and API reference
- 6 deep concept explainers (GNN, Active Inference, Markov blankets, roles, roundtrip, program graphs)
- 20 cookbook recipes (scan, reverse, CI, custom rules, dataset export)
- 35 honest Q&A FAQ covering accuracy, limitations, and roadmap
- 83+ annotated bibliography entries across 14 themes
- 6 Jupyter tutorial notebooks
- FastAPI demo server
- BENCHMARK_VS_PRIOR.md comparing COGANT vs tree-sitter, pyan, LLM-only, and manual approaches
- CALIBRATION.md with per-rule confidence scores and inline justifications

**Testing and Quality**
- Hypothesis property tests for 7 COGANT correctness laws
- Mutation testing report + targeted hardening tests
- End-to-end pipeline, CLI, and roundtrip integration tests
- ML dataset v0.1: 6 fixtures with node-level role labels (HuggingFace-style card)
- Reproducible 6-fixture benchmark harness with stage timing + memory + GNN stats

**Multi-Language**
- Tree-sitter multi-language substrate with JS/TS parsers
- Git-diff incremental analysis mode

**Theory and Rigor**
- Qualitative AI role validation tests + ACTIVE_INFERENCE_MAPPING.md
- GNN spec compliance: 3 AII non-conformances found and fixed
- Real-world evaluation on 8 open-source Python repositories

### Changed
- Complete README rewrite for v0.2.0 feature set
- Docstring audit and type annotation hygiene across all modules
- Test suite: 1300+ tests, 0 failures (skips for optional deps only)
- py.typed marker added (PEP 561 compliance)
- RuleExplanation model + per-rule `.explain()` with calibration docstrings
- GitHub Actions matrix CI + perf smoke + CODEOWNERS + PR template

### Fixed
- Resolved 6 reverse-module test failures
- ActionRule: extended with encode/decode/dump/load keywords + >=2 WRITES edge fallback
- SemanticMapping export: `mapping.kind.value` (was incorrect attribute access)
- PNG tests: matplotlib-dependent tests properly skipped when `cogant[viz]` not installed
- GNN upstream formatter: DiscreteTime token split, bare variable names in connections
- CI workflows: moved `.github/` to git root so GitHub Actions discovers workflows
- Event pipeline roundtrip xfail documented (47.6% role match -- known synthesizer limitation)

## [0.1.0] - 2026-04-08

Initial R&D release: forward pipeline (ingest -> static -> normalize -> graph -> translate -> export), 22 translation rules, 7 semantic roles, Markov blanket partition.
