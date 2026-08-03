# Known Limitations (v0.6 Snapshot)

Last updated: 2026-08-02. Limitations are ordered by impact.
See `feature_backlog.md` for the planned fix target for each item.

---

## Active Limitations

### 1. Language Support: Parsers for Python/JS/TS Plus Experimental Rust/Go

Registered parsers cover Python (CPython `ast`), JavaScript / TypeScript
(tree-sitter-preferred with a structural fallback), and experimental structural
parsers for Rust and Go. Java, C/C++, Ruby, PHP, and other languages have no
parser, though file enumeration recognizes their extensions.

**Workaround:** Manually annotate cross-language boundary nodes using the YAML rule DSL.
**Target fix:** Java parser planned (see `feature_backlog.md`).

---

### 2. No Self-Generated Runtime Traces

COGANT does not execute the analyzed code. The `dynamic` stage can enrich the
graph with runtime evidence (coverage databases, execution traces) when such data
is supplied, and `ConfidenceTier.RUNTIME_ONLY` / `STATIC_PLUS_RUNTIME` tiers
reflect that evidence, but no runtime data is produced by the pipeline itself.

**Impact:** Dynamic dispatch, monkey-patching, and probabilistic runtime branching are not modeled.
OBSERVATION false negatives occur when a value is conditionally observed only at runtime.

**Workaround:** Use `PipelineConfig.incremental_since` with coverage data to indirectly capture
execution paths (changed lines = hot paths).

**Target fix:** Dynamic analysis integration planned for v0.7.x.

---

### 3. Single-Repository Analysis

`ProgramGraph` models one repo at a time. Cross-service relationships (microservices, monorepos
with multiple packages) are invisible to the Markov blanket partition.

**Workaround:** Run `cogant translate` separately per repo; merge Parquet exports for joint analysis.

**Target fix:** Multi-root `ProgramGraph` + `INTER_REPO` edge kind planned for v0.7.x.

---

### 4. Limited Type Inference

Translation rules use type annotations where present. Un-annotated Python code (Django,
Flask scripts, data science notebooks) has lower rule confidence due to missing type evidence.

**Impact:** `ObservationRule` and `ActionRule` false negatives increase without type hints.

**Workaround:** Add `from __future__ import annotations` + minimal type hints to critical paths.

**Target fix:** Intra-procedural type inference engine planned for v0.6.x.

---

### 5. Dulwich Edge-Density Regression Risk

Recorded Dulwich-derived graphs at ~1.80 edges/node hit a performance cliff
(~380s, 8.5 GB RAM). Wave-15 fixes reduced the documented run to ~65s and a
206 MB generated package, so this is now a regression watch item rather than a
current v1.0 blocker.

**Workaround:** Use `cogant translate --incremental <git-ref>` (19.6× no-change speedup).
Split large monorepos by module: `cogant translate --include src/core/`.

**Target fix:** Keep Dulwich-class fixtures in the performance suite and add streaming graph/export
paths for larger held-out repositories.

---

### 6. No IDE Integration

No VSCode, JetBrains, or other IDE plugin. COGANT is CLI + Python API only.

**Workaround:** Use `cogant visualize` to generate PNG/PDF/HTML reports for manual review.

**Target fix:** VSCode extension planned for v1.0 (depends on API freeze).

---

### 7. Alias Analysis Missing

Assignment aliasing (`x = y`) creates spurious WRITES edges. This inflates node degree
and can cause `MutatingSubsystemRule` false positives.

**Target fix:** Alias analysis planned for v0.6.x.

---

### 8. Sandbox Environment Constraints

In restricted environments (sandboxed containers), the following may not work:
- `uv` Python download blocked by GitHub CDN timeouts → use `python3 -m py_compile` for syntax checking
- `.git/index.lock` immutable → use `GIT_INDEX_FILE=/tmp/alt_index` plumbing workaround
- GitHub network access blocked → push via authenticated git credential or SSH outside sandbox

These are environment constraints, not COGANT bugs.

---

### 9. `METRICS.yaml` Regeneration Pitfall

If `regenerate_metrics.py` is run from the wrong directory or without optional deps,
`test_count_passing` can land at 0. Always verify the value is non-zero before trusting
the generated file. Confirm live with `uv run pytest tests/ -q --cov=py/cogant` from the package root and compare the result to `evaluation/METRICS.yaml` before using manuscript-facing counts.

---

## Recently Resolved Limitations

| Limitation | Fixed in | How |
|-----------|---------|-----|
| Single-language (Python only) | v0.4.0 | JS/TS tree-sitter parser added |
| No round-trip | current | `cogant.reverse` + `cogant roundtrip` added |
| Roundtrip role preservation below 1.0 | Current native ledger | Resolved for the current in-sample ledger: metrics record 25/25 role-preserved targets and 0 drift targets; strict structural isomorphism is tracked separately at 1/25, confined to `roundtrip_strict_minimal`. |
| No incremental analysis | current | `--incremental <git-ref>` + `incremental_since` |
| No static analysis | April 2026 hardening | `cogant.static` module: complexity, coupling, dead code, Halstead |
| No visualization beyond HTML | April 2026 hardening | `cogant.viz`: PDF, PNG, Mermaid, SVG, 8-page report |
| Basic export only (JSON, GraphML) | April 2026 hardening | 9 formats: JSON, GraphML, Parquet, SVG, PNG, PDF, Mermaid, DOT, JSONLINES |
| No type system for protocols | April 2026 hardening | 14 `@runtime_checkable` Protocols, 231 .pyi stubs |
| No network/graph analysis | April 2026 hardening | `GraphAnalyzer`: centrality, community, SCC |
| No streaming / WebSocket API | April 2026 hardening | `WS /ws/translate` + `translate_batch()` |
