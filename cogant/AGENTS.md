# Agents — COGANT (repository root)

**COGANT** translates software repositories into **Generalized Notation Notation** (GNN) bundles
for Active Inference — the AII's structured state-space notation (not graph neural networks).

---

## Quick Navigation

| Destination | Link |
|-------------|------|
| Documentation home (MkDocs) | [`docs/index.md`](docs/index.md) |
| Module map | [`docs/reference/documentation_modules.md`](docs/reference/documentation_modules.md) |
| Agent coordination conventions | [`docs/AGENTS.md`](docs/AGENTS.md) |
| Architecture overview | [`docs/architecture/README.md`](docs/architecture/README.md) |
| Roadmap and version plans | [`docs/roadmap/README.md`](docs/roadmap/README.md) |
| CLI reference | [`docs/cli/README.md`](docs/cli/README.md) |
| Python package | [`py/cogant/AGENTS.md`](py/cogant/AGENTS.md) |
| CHANGELOG | [`CHANGELOG.md`](CHANGELOG.md) |

---

## Repository Layout

```
cogant/                         ← package root (this directory)
├── py/cogant/                  ← installable Python package (import cogant)
│   ├── ingest/                 ← stage 1: file discovery, language detection
│   ├── static/                 ← stage 2: AST facts (symbols, imports, calls, complexity)
│   ├── normalize/              ← stage 3: language-agnostic canonical normalization
│   ├── graph/                  ← stage 4: ProgramGraph construction + analysis
│   ├── dynamic/                ← stage 5: coverage / trace enrichment (skippable)
│   ├── translate/              ← stage 6: fixpoint engine + 22 declarative rules
│   ├── statespace/             ← stage 7: A/B/C/D matrix compilation
│   ├── process/                ← stage 8: process / execution model extraction
│   ├── export/                 ← stage 9: 9 output formats (JSON, GraphML, Parquet, …)
│   ├── validate/               ← stage 10: schema + AII validator (0–100 score)
│   ├── markov/                 ← (post-pipeline) Markov blanket (`explicit`/`module`/`kind`/`auto`/`mapping_kind`)
│   ├── gnn/                    ← (post-pipeline) AII-spec GNN bundle emission, used by export + validate
│   ├── viz/                    ← (post-pipeline) PNG/PDF/SVG/Mermaid/HTML visualization
│   ├── scoring/                ← (post-pipeline) confidence + roundtrip scorers
│   ├── reverse/                ← reverse path: GNN → Python package synthesis
│   ├── runtime/                ← AgentRuntime: multi-episode Bayesian learning
│   ├── api/                    ← PipelineConfig, orchestration, session management
│   ├── server/                 ← FastAPI app (REST + WebSocket)
│   ├── cli/                    ← 26 `@app.command` on `app` + `plugin`/`migrate` groups → 28 names on `cogant --help`; 29 leaf commands incl. `plugin list|info`, `migrate migrate`
│   ├── protocols.py            ← 14 @runtime_checkable Protocols
│   └── types.py                ← 15 TypedDicts, type aliases
├── rust/                       ← PyO3 Rust workspace (8 crates; optional acceleration)
│   ├── cogant-core/            ← StableId, NodeKind, SemanticRole types
│   ├── cogant-graph/           ← connected_components (FFI)
│   ├── cogant-translate/       ← Rule engine and graph transformations
│   ├── cogant-statespace/       ← State space compilation
│   ├── cogant-store/           ← Persistent storage and indexing
│   ├── cogant-trace/           ← Trace collection and processing
│   ├── cogant-gnn/             ← GNN tensor generation
│   └── cogant-ffi/             ← Python bindings (COGANT_USE_RUST=1)
├── parsers/                    ← tree-sitter grammar files (JS, TS, Go, Python, Rust)
├── specs/                      ← RFCs and IR schema contracts
├── examples/                   ← 20+ runnable sample repos / fixtures (3 control_positive + 13 zoo + standalone)
│   └── zoo/                    ← 13 Active Inference fixtures (01–13); 23 total roundtrip evaluation targets across all fixture sources
├── evaluation/                 ← benchmark corpora, METRICS.yaml, dashboards
├── docs/                       ← MkDocs documentation site (~380 Markdown pages under docs/; run `find docs -name '*.md' | wc -l` from the package root for the live count)
├── tests/                      ← full pytest suite (run from package root; coverage policy in pyproject.toml)
├── benchmarks/                 ← performance benchmark scripts
├── scripts/                    ← manuscript pipeline scripts
└── pyproject.toml              ← uv/pip install config
```

---

## Current State (v0.5.0 + wave-21)

| Metric | Value |
|--------|-------|
| Translation rules | 22 (5 structural + 5 semantic + 3 control + 4 behavioral + 5 resilience) |
| Languages supported | Python (full AST), JS/TS (tree-sitter) |
| Roundtrip ε | 1.0 — 23/23 ISOMORPHIC fixtures |
| Test suite | Large and growing; `uv run pytest tests/ -q`. Coverage: line gate, `--cov-fail-under=89`, omits in `pyproject.toml` |
| Export formats | 9 (JSON, GraphML, Parquet, SVG, PNG, PDF, Mermaid, DOT, JSONLINES) |
| CLI subcommands | 26 `@app.command` + `plugin`/`migrate` groups (**28** top-level names); **29** leaves incl. `plugin list|info`, `migrate migrate` |
| Protocols / TypedDicts | 14 Protocols, 15 TypedDicts, 233 .pyi stubs |

---

## Key Commands (run from `cogant/` package root)

```bash
uv sync --extra all                          # install all deps
uv run cogant doctor                         # environment check
uv run cogant translate <repo>               # full forward pipeline
uv run cogant roundtrip <repo>               # forward + reverse + forward
uv run cogant analyze-static <repo>          # static analysis report
uv run cogant analyze-graph <repo>           # network/graph analysis
uv run cogant visualize <repo>               # generate PDF/PNG/Mermaid outputs
uv run cogant export <repo> --format all     # export in all 9 formats
uv run cogant analyze <repo> --upstream-gnn-pipeline   # forward pipeline + AII 25-step pass (Render/Execute off)
uv run cogant upstream-gnn <package_dir>     # re-run the AII 25-step pass on an existing gnn_package/
uv run pytest tests/ -q                      # full test suite
uv run mypy py/cogant/                       # strict type check (0 errors target)
uv run ruff check py/cogant/                 # linting (0 violations target)
```

---

## Common Agent Tasks

- **Understand a module**: read its `AGENTS.md` first, then `py/cogant/<module>/__init__.py`.
- **Add a translation rule**: see [`py/cogant/translate/AGENTS.md`](py/cogant/translate/AGENTS.md) — follow the 22-rule pattern.
- **Add a test**: place in `tests/unit/` (fast) or `tests/integration/` (full pipeline); see pytest markers.
- **Modify the pipeline**: start from `py/cogant/api/pipeline.py`; `PipelineConfig` is the entry point.
- **Update manuscript numbers**: run `regenerate_metrics.py` from the package root, then `z_generate_manuscript_variables.py` from the repo root.
