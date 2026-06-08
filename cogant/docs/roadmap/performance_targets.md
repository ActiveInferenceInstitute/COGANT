# Performance Targets

Last updated: 2026-06-06 (v0.6 current status). Measured values from `evaluation/METRICS.yaml`
and the Flask benchmark (`cogant translate --incremental`).

---

## Measured Baselines

| Benchmark | Result | Notes |
|-----------|--------|-------|
| Flask app — no-change incremental | **19.6× speedup** | Re-uses previous ProgramGraph |
| Flask app — single-file change | **5.6× speedup** | Only changed paths re-analyzed |
| Roundtrip ledger classification (24 fixtures/reductions) | **24 ROLE_PRESERVED / 0 DRIFT / 0 non-native rows** | Native v0.6 ledger; strict structural isomorphism remains 0/24 |
| AII validator score (all fixtures) | **100/100** | |
| `cogant translate` on 8 real-world repos | all pass | flask, requests, dulwich, etc. |
| Dulwich edge-density stress case | Checked-in fixture: 380.02s / 8510.9 MB; post-fix target: <120s | 1.80 e/n ratio; needs refreshed external fixture before new public timing claim |

Export timing (from `export/AGENTS.md`):

| Format | Typical Time | Notes |
|--------|-------------|-------|
| JSON | 1–10s | |
| GraphML | 2–30s | XML generation |
| Parquet | 1–20s | Columnar compression |
| SVG | 5–60s | Graphviz layout + rendering (optional) |
| Bundle manifest | ~100ms | |
| SHA256 checksum | 100–500ms | |

---

## Targets by Project Size

### Single-Process (default; `PipelineConfig.workers=1`)

| Stage | 10K nodes | 100K nodes | 1M nodes |
|-------|-----------|-----------|---------|
| Ingest + parse | <5s | <30s | <5min |
| Graph construction | <2s | <10s | <60s |
| Translation (fixpoint) | <1s | <5s | <30s |
| Static analysis | <5s | <30s | <5min |
| Export (JSON + Parquet) | <2s | <10s | <60s |
| **Total** | **<15s** | **<90s** | **<15min** |
| Peak memory | <300MB | <2GB | <8GB |

### With Incremental Mode (`--incremental <git-ref>`)

| Scenario | Target |
|---------|--------|
| No-change re-run | <2s (any size) |
| Single-file change | <5s (any size) |
| 10% changed files | proportional reduction |

### With Streaming Export (planned v0.6.x)

| Graph size | Parquet streaming | GraphML streaming |
|-----------|------------------|-----------------|
| 100k nodes | <30s, <500MB peak | <60s, <1GB peak |
| 500k nodes | <120s, <2GB peak | <300s, <3GB peak |
| 1M nodes | <5min, <4GB peak | <10min, <6GB peak |

### With Parallel Processing (planned v1.0)

| Workers | Expected speedup |
|---------|-----------------|
| 2 | ~1.8× |
| 4 | ~3.2× |
| 8 | ~5.5× |

---

## Dulwich Edge-Density Stress Case

At ~1.80 edges-per-node (Dulwich repo), the checked-in external fixture records
380.02 seconds elapsed and 8510.9 MB peak memory. Profiling attributed the blow-up to:

1. Markov blanket BFS traversal at high edge density (superlinear traversal cost)
2. In-memory INHERITS edge deduplication (quadratic on large class hierarchies)
3. No streaming in the graph construction phase

**Current evidence boundary:** implementation fixes target <120s and bounded
package size, but the external fixture must be rerun before replacing the
checked-in Dulwich timing table. Keep Dulwich-class edge density in the benchmark
suite as a regression watch item.

**Target fix:** Streaming graph construction + alias analysis reduces e/n ratio (v0.6.x); parallel
processing reduces wall clock (v1.0).

---

## Test Coverage Targets

| Component | v0.5.0 Actual | v0.6.x Target | v1.0 Target |
|-----------|--------------|--------------|------------|
| Core pipeline (`graph/`, `translate/`, `statespace/`) | ~85% | 88% | 92% |
| Parsers (`parsers/`, `ingest/`, `static/`, `dynamic/`) | ~78% | 83% | 90% |
| Translation rules (22 rules) | ~80% | 85% | 95% |
| Export (`export/`) | ~75% | 85% | 92% |
| Visualization (`viz/`) | ~70% | 78% | 88% |
| Runtime (`runtime/`, `markov/`) | ~82% | 87% | 93% |
| API/server (`server/`, `api/`) | ~72% | 80% | 88% |
| **Overall** | **96.22%** | **96%** | **97%** |

**May 2026 package-hardening snapshot:** **9,222 tests passing** (9,253 total, 31 skipped), **96.22%** line coverage. **CI gate:** `pyproject.toml` uses `--cov-fail-under=89`, `branch = false`, `omit` for `static/treesitter_parser.py`, and `parallel = true` — run `uv run pytest tests/ -q --cov=py/cogant` for live counts. Earlier package-hardening snapshot: 8,980 passing (9,011 total), 95.11% coverage. Historical v0.5.0 (2026-04-10) snapshot: 2,129 tests passing, 83.42% coverage.
