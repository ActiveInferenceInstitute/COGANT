# COGANT Roadmap Overview

**Current release:** v0.5.0 + wave-21 (2026-04-13). The project is in active development;
breaking changes remain possible until v1.0.0 stabilizes the public API.

> **Ground truth:** What is implemented in the Python package is tracked in
> `CHANGELOG.md` and `evaluation/METRICS.yaml`. Sections below are forward-looking.
> Calendar quarters are directional, not commitments.

---

## Where We Are (v0.5.0 + wave-21)

COGANT translates software repositories into AII-spec GNN bundles for Active Inference.
The core pipeline is exercised end-to-end against 8+ real-world Python repos and
a 23-fixture cross-language roundtrip suite (ε = 1.0, 100% ISOMORPHIC).

**Shipped capability at a glance:**

| Area | Status |
|------|--------|
| Python parser (full AST) | ✅ Production |
| JS/TS parser (tree-sitter) | ✅ Production |
| 22 translation rules (5+5+3+4+5 families) | ✅ Production |
| Markov blanket partition (5 seed strategies, O(V+E)) | ✅ Production |
| State space compiler (A/B/C/D matrices) | ✅ Production |
| GNN bundle emission (AII-spec compliant) | ✅ Production |
| Round-trip (code → GNN → code → GNN): ε=1.0 | ✅ Production |
| Active Inference agent runtime (multi-episode Bayesian) | ✅ Production |
| Incremental analysis (19.6× no-change speedup) | ✅ Production |
| Static analysis (complexity, coupling, dead code, Halstead) | ✅ Production |
| Network/graph analysis (centrality, community, SCC) | ✅ Production |
| Visualization suite (PDF, PNG, Mermaid, SVG) | ✅ Production |
| Export: 9 formats (JSON, GraphML, Parquet, SVG, PNG, PDF, Mermaid, DOT, JSONLINES) | ✅ Production |
| FastAPI server + WebSocket streaming | ✅ Production |
| CLI: 26 subcommands | ✅ Production |
| Type system: 14 Protocols, 15 TypedDicts, 231 .pyi stubs | ✅ Production |
| Test suite: see `evaluation/METRICS.yaml` for current counts (wave-20: 8,980 passing / 9,011 total / 95.11% coverage — run `uv run pytest tests/ -q --cov=cogant` for live numbers) | ✅ Production |
| Rust PyO3 acceleration (optional) | ✅ Beta |
| Java parser | ⬜ Planned (v0.6.x) |
| Rust parser | ⬜ Planned (v0.6.x) |
| Dynamic analysis / trace integration | ⬜ Planned (v0.7.x) |
| Cross-repository analysis | ⬜ Planned (v0.7.x) |
| Public API freeze / v1.0 | ⬜ Planned (v1.0) |

---

## Near-Term Plan: v0.6.x

**Theme: Language breadth and streaming scale**

The core pipeline is solid. v0.6.x extends the language surface and addresses
production-scale constraints discovered during real-world use.

Priority items:
1. Java parser (tree-sitter + Spring/JPA rules)
2. Rust parser (tree-sitter + ownership → CONSTRAINT heuristics)
3. Streaming export for graphs >100k nodes (Parquet, GraphML, JSONLINES)
4. Intra-procedural type inference engine
5. Alias analysis to prune redundant READS/WRITES edges

See: [version_060_planned.md](version_060_planned.md)

---

## Medium-Term Plan: v0.7.x–v0.8.x

**Theme: Dynamic analysis and cross-system modeling**

1. Dynamic analysis integration: coverage traces → rule refinement → `STATIC_PLUS_RUNTIME` tier
2. Cross-repository analysis: multi-root `ProgramGraph` + `INTER_REPO` edge kind
3. Interprocedural dataflow (taint/reach across callgraph)
4. VSCode extension (inline role annotations)
5. Interactive web dashboard (Cytoscape.js / D3-force)
6. Plugin / rule registry for third-party rule families

---

## Long-Term Plan: v1.0.0

**Theme: Public API freeze and production hardening**

1. Stable public API freeze (semver-guaranteed stability)
2. Promote staging tree: `projects_in_progress/cogant/` → `projects/cogant/`
3. Stubgen-based .pyi auto-generation with CI drift check
4. Full schema versioning + migration harness (v0.1→v0.5→v1.0 bundle migration)
5. Distributed / parallel file processing (Ray or ProcessPoolExecutor)
6. Pre-trained GNN node encoder (PyG HeteroData from Parquet bundles)

See: [version_100_planned.md](version_100_planned.md)

---

## Known Limitations (v0.5.0)

| Limitation | Workaround | Target Fix |
|-----------|-----------|-----------|
| Java, Rust, C/C++ parsers missing | Manual annotation or JS/TS fallback | v0.6.x |
| Static analysis only (no runtime traces) | Use incremental mode with coverage data as proxy | v0.7.x |
| Single-repo analysis only | Run separately per repo, merge Parquet exports | v0.7.x |
| Dulwich scaling cliff at ~1.8 e/n ratio (>380s / 8.5 GB) | Use incremental mode; split analysis by module | v0.6.x |
| `.git/index.lock` immutable in some sandbox environments | Use `GIT_INDEX_FILE` env var plumbing workaround | Infrastructure |
| `mypy --strict` possible drift on new modules | Run `make type-check` before every commit | Ongoing |

---

## Quality Bar

| Metric | Current | v0.6.x Target | v1.0 Target |
|--------|---------|---------------|-------------|
| Tests passing | see `evaluation/METRICS.yaml` (wave-20: 8,980 passing / 9,011 total) | >9,000 | >10,000 |
| Coverage | see `evaluation/METRICS.yaml` (wave-20: 95.11%; live: run `uv run pytest tests/ -q --cov=cogant`) | 95% | 97% |
| mypy errors | see `evaluation/METRICS.yaml` (`mypy_strict_errors`) | 0 | 0 |
| Ruff violations | see `evaluation/METRICS.yaml` (`ruff_violations`) | 0 | 0 |
| Roundtrip ε | 1.0 (23/23) | 1.0 (extend to Java) | 1.0 (all languages) |
| AII validator score | 100/100 (all fixtures) | 100/100 | 100/100 |
| Real-world repos passing | 8/8 | 15/15 | 30/30 |
