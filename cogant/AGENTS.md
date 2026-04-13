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
│   ├── graph/                  ← stage 3: ProgramGraph construction + analysis
│   ├── translate/              ← stage 4: fixpoint engine + 22 declarative rules
│   ├── statespace/             ← stage 5: A/B/C/D matrix compilation
│   ├── markov/                 ← stage 6: Markov blanket partition (5 seed strategies)
│   ├── gnn/                    ← stage 7: AII-spec GNN bundle emission
│   ├── validate/               ← stage 8: AII validator (0–100 score)
│   ├── export/                 ← stage 9: 9 output formats (JSON, GraphML, Parquet, …)
│   ├── viz/                    ← stage 10: PNG/PDF/SVG/Mermaid/HTML visualization
│   ├── reverse/                ← reverse path: GNN → Python package synthesis
│   ├── runtime/                ← AgentRuntime: multi-episode Bayesian learning
│   ├── api/                    ← PipelineConfig, orchestration, session management
│   ├── server/                 ← FastAPI app (REST + WebSocket)
│   ├── cli/                    ← 22 Typer subcommands
│   ├── protocols.py            ← 9 @runtime_checkable Protocols
│   └── types.py                ← 15+ TypedDicts, type aliases
├── rust/                       ← PyO3 Rust workspace (optional acceleration)
│   ├── cogant-core/            ← StableId, NodeKind, SemanticRole types
│   ├── cogant-graph/           ← connected_components (FFI)
│   └── cogant-ffi/             ← Python bindings (COGANT_USE_RUST=1)
├── parsers/                    ← tree-sitter grammar files (JS, TS, Go, Python, Rust)
├── specs/                      ← RFCs and IR schema contracts
├── examples/                   ← 14+ runnable sample repos (ground-truth fixtures)
│   └── zoo/                    ← 23 roundtrip evaluation fixtures
├── evaluation/                 ← benchmark corpora, METRICS.yaml, dashboards
├── docs/                       ← MkDocs documentation site (100+ pages, 16 sections)
├── tests/                      ← 2,129 passing tests (83.42% coverage)
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
| Test suite | 2,129 passing, 83.42% coverage (gate: 75%) |
| Export formats | 9 (JSON, GraphML, Parquet, SVG, PNG, PDF, Mermaid, DOT, JSONLINES) |
| CLI subcommands | 22 |
| Protocols / TypedDicts | 9 Protocols, 15+ TypedDicts, 49 .pyi stubs |

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
