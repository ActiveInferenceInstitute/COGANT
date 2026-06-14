# Version 1.0.0 — Planned

**Theme: Public API freeze, production hardening, and ecosystem readiness**
**Status:** Planning | **Prerequisite:** v0.6.x–v0.9.x shipped and stable | **Target:** Q1 2027

This document scopes the v1.0.0 milestone. v1.0.0 is not a feature release — it is a stability
and hardening release that makes COGANT safe to depend on. The public API contract is frozen at
1.0.0; breaking changes require a new major version (2.0.0).

---

## Goals

1. **API freeze**: Define and freeze the stable public API surface. Everything in `__all__` at 1.0 is semver-guaranteed.
2. **Template render path**: Keep the working sidecar linked under `projects/working/cogant/` with current render commands.
3. **Zero known regressions**: No failed fixtures, all validators at 100/100, and language-specific roundtrip targets met.
4. **Production readiness**: Distributed processing, cloud deployment, current-schema validation, IDE extension.
5. **Ecosystem**: Plugin marketplace, DuckDB query interface, pre-trained GNN encoder (beta).

---

## Scheduled Work

### H1 — Public API Freeze

**Effort:** M | **Blocks:** everything downstream

Define the stable surface. Everything outside `__all__` in public modules is internal and may change.

- [ ] Audit all `__all__` declarations across `py/cogant/` (currently ~50 modules)
- [ ] Move implementation details under `_internal/` or add underscore prefixes
- [ ] Write `API_STABILITY.md`: tier classification (stable / experimental / internal)
- [ ] Changelog entries for any pre-1.0 interfaces being dropped
- [ ] `cogant.__version__` follows semver; `cogant.version_info: tuple[int, int, int]`
- [ ] All public classes/functions have Google-style docstrings with full Args/Returns/Raises/Examples

### H2 — Template Render Path (PROMOTION.md)

**Effort:** S | **Blocks:** PDF rendering, `run.sh`, pipeline discovery

The sidecar-root / package-root split creates orientation cost for every new contributor.
The current render path is `projects/working/cogant/`.

- [ ] Verify sidecar/template linking exposes `projects/working/cogant/`
- [ ] Fix hard-coded render-path literals in docs, scripts, CI workflows
- [ ] Verify `./run.sh` and `infrastructure/project/discovery.py` discover the project
- [ ] End-to-end PDF rendering via `scripts/03_render_pdf.py --project working/cogant`
- [ ] Manuscript variable injection end-to-end: `regenerate_metrics.py` → `z_generate_manuscript_variables.py` → PDF

### H3 — Current Schema Contract Harness

**Effort:** M | **Owner:** export team

Bundles created by the current package must declare the active schema contract
and fail fast when a reader sees an unsupported header. The v1.0.0 gate should
make that behavior explicit across bundle manifests, validators, and fixtures.

- [ ] `BundleManifest.schema_version: str` bump policy documented in `deprecation_policy.md`
- [ ] `cogant migrate <bundle_dir>`: current-contract verifier that reports unsupported headers
- [ ] Automated current-contract tests across all packaged fixtures
- [ ] `cogant validate-bundle manifest.json`: includes schema version check + checksum verification

### H4 — Stubgen CI Check

**Effort:** S | **Owner:** typing team

- [ ] `make gen-stubs` target: `mypy --stubgen --package cogant -o stubs/`
- [ ] CI job: diff committed stubs vs generated; fail if unexpected delta (tolerates additions, rejects removals)
- [ ] Decision recorded: curated stubs are the source of truth; generated stubs are the verification artifact

### H5 — Dynamic Analysis Integration (via v0.7.x)

**Prerequisite:** v0.7.x ships this first

- [ ] `PipelineConfig.trace_paths: list[Path]` fully integrated
- [ ] `ConfidenceTier.STATIC_PLUS_RUNTIME` path fully exercised in test suite
- [ ] `cogant translate --with-traces coverage.json` documented in CLI guide

### H6 — Distributed / Parallel File Processing {#h6}

**Effort:** XL | **Owner:** pipeline team

Large monorepos (>1,000 files) need parallel ingestion.

- [ ] `cogant/pipeline/parallel.py`: `ParallelPipelineRunner`
  - Worker pool via `ProcessPoolExecutor` (default) or Ray (optional dep)
  - File-level sharding for `ingest` + `parsers` stages
  - Shared `ProgramGraph` builder with thread-safe merge step
- [ ] `PipelineConfig.workers: int = 1` (1 = current single-process behavior)
- [ ] Benchmark: worker count vs. throughput on 100-file, 1000-file, 10000-file synthetic repos
- [ ] Scaling regression test: assert linear throughput up to 8 workers

### H7 — Cloud / Serverless Deployment

**Effort:** M | **Owner:** server team

- [ ] AWS Lambda handler: `cogant/server/lambda_handler.py` wrapping `translate` endpoint
- [ ] GCP Cloud Run: `Dockerfile.cloudrun` (stateless, ephemeral, scales to zero)
- [ ] Terraform module: `cogant/infra/terraform/` for auto-scaling inference cluster
- [ ] Deployment guide in `docs/guides/cloud_deployment.md`

### H8 — VSCode Extension (Beta)

**Effort:** L | **Owner:** dx team | **Dependency:** H1 (API freeze required for stable LSP integration)

- [ ] `cogant-vscode/`: TypeScript extension package
  - Hover: show SemanticRole for symbol under cursor
  - Gutter icons: translation rule match confidence
  - "Export to GNN" command palette entry
  - "Show Markov Blanket" webview panel
- [ ] Language server: wrap `cogant translate` in LSP `textDocument/hover` handler
- [ ] Published to VSCode Marketplace under `cogant.cogant-vscode`

### H9 — Interactive Web Dashboard

**Effort:** M | **Owner:** viz team

Upgrade static `cogant render` HTML to a fully interactive experience.

- [ ] Cytoscape.js or D3-force graph with zoom/pan
- [ ] Role-color overlay toggle (HIDDEN_STATE=blue, OBSERVATION=green, ACTION=red, POLICY=purple)
- [ ] Markov blanket boundary highlighting (configurable seed strategy)
- [ ] Drill-down: click node → source file + line number
- [ ] Community detection overlay with Louvain coloring
- [ ] Export current view as SVG/PNG

### H10 — Plugin / Rule Marketplace

**Effort:** M | **Owner:** ecosystem team

- [ ] `cogant.plugins.RulePlugin` ABC with `cogant_rules` entry-point group
- [ ] `cogant plugin install <package>`: pip install + rule registration
- [ ] Plugin validation: verify rule implements `TranslationRule` Protocol
- [ ] Marketplace docs: how to publish a rule package to PyPI
- [ ] 3 reference rule packages: `cogant-rules-django`, `cogant-rules-flask`, `cogant-rules-fastapi`

### H11 — DuckDB Query Interface

**Effort:** S | **Owner:** export team

- [ ] `cogant query "SELECT * FROM nodes WHERE role='HIDDEN_STATE'"` subcommand
  - Auto-load from latest bundle's Parquet files via DuckDB in-process
  - Support `--bundle <path>` to target a specific bundle
- [ ] Pre-defined query library: `cogant/queries/` with common analysis patterns
- [ ] Export query results: `--format csv|json|table`
- [ ] `docs/guides/sql_analysis.md`: DuckDB query guide for graph analysis

### H12 — Pre-Trained GNN Node Encoder (Beta) {#h12}

**Effort:** XL | **Owner:** ml team

- [ ] PyG `HeteroData` loader from Parquet bundles (`cogant/ml/dataset.py`)
- [ ] `CogantGNNEncoder`: R-GCN or HGT over heterogeneous node/edge kinds
- [ ] Training corpus: 100+ open-source Python repos exported to Parquet
- [ ] `cogant train-encoder --corpus-dir repos/ --output encoder.pt`
- [ ] `ConfidenceModel.with_encoder()`: fusion of rule heuristics + embedding similarity
- [ ] `cogant export --with-embeddings`: add embedding vectors to Parquet output

---

## Out of Scope for v1.0

- Real-time / LSP live analysis (post-1.0)
- Full distributed cluster (Ray) — ProcessPoolExecutor covers 95% of use cases
- C/C++ parser (post-1.0)
- WASM browser-native parsing

---

## Quality Bar for v1.0 Release

| Metric | Target |
|--------|--------|
| Tests passing | >3,000 |
| Coverage | ≥90% |
| mypy --strict errors | 0 |
| Ruff violations | 0 |
| Native roundtrip role preservation (Python + JS/TS) | `role_preservation_score >= 0.95` on a native ledger with zero non-native rows |
| Roundtrip role preservation (Java) | `s_role >= 0.85` |
| AII validator score (all fixtures) | 100/100 |
| Real-world repos passing forward pipeline | ≥30 |
| Public API modules with complete docstrings | 100% |
| Current bundle schema contract validation | Pass |
| CI pipeline duration | <10 min |

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| API freeze removes experimental features users depend on | Medium | Maintain `cogant.experimental` namespace for incubating APIs |
| Distributed processing introduces non-determinism | Medium | Hash-seed everything; property test determinism law |
| VSCode extension version lag behind CLI | High | Pin extension to compatible CLI minor version; semver compatibility matrix |
| Pre-trained encoder requires large training corpus | High | Scope as "beta" opt-in; heuristic rules remain default |
| Schema contract checks grow inconsistent across CLI/API paths | Medium | Integration test every validator entry point automatically |
