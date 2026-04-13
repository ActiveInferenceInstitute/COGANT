# Known Limitations (v0.5.0 + wave-21)

Last updated: 2026-04-13. Limitations are ordered by impact.
See `feature_backlog.md` for the planned fix target for each item.

---

## Active Limitations

### 1. Language Support: Python and JS/TS Only

Java, Rust, C/C++, Go, Ruby, and other languages have no parser.
The tree-sitter substrate is in place; adding parsers requires grammar wiring + language-specific rules.

**Workaround:** Manually annotate cross-language boundary nodes using the YAML rule DSL.
**Target fix:** Java + Rust parsers planned for v0.6.x.

---

### 2. Static Analysis Only (No Runtime Traces)

`ConfidenceTier.RUNTIME_ONLY` and `STATIC_PLUS_RUNTIME` paths exist in the confidence model
but are not yet populated. All evidence is derived from AST/tree-sitter analysis, not execution.

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

Translation rules use type annotations where present. Un-annotated Python code (legacy Django,
Flask scripts, data science notebooks) has lower rule confidence due to missing type evidence.

**Impact:** `ObservationRule` and `ActionRule` false negatives increase without type hints.

**Workaround:** Add `from __future__ import annotations` + minimal type hints to critical paths.

**Target fix:** Intra-procedural type inference engine planned for v0.6.x.

---

### 5. Dulwich Scaling Cliff

At ~1.80 edges/node ratio, Dulwich-derived graphs hit a performance cliff (~380s, 8.5 GB RAM).
This is documented in CHANGELOG.md and has a tracking test (`tests/unit/test_markov_performance_gaps.py`).

**Workaround:** Use `cogant translate --incremental <git-ref>` (19.6× no-change speedup).
Split large monorepos by module: `cogant translate --include src/core/`.

**Target fix:** Streaming graph construction + alias analysis (reduces e/n ratio) planned for v0.6.x.

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
the generated file. Canonical v0.5.0 values: 2,129 passing, 83.42% coverage.

---

## Recently Resolved Limitations

| Limitation | Fixed in | How |
|-----------|---------|-----|
| Single-language (Python only) | v0.4.0 | JS/TS tree-sitter parser added |
| No round-trip | v0.2.0 | `cogant.reverse` + `cogant roundtrip` added |
| Round-trip ε < 1.0 | v0.5.0 | POLICY/CONTEXT stub emission; 23/23 ISOMORPHIC |
| No incremental analysis | v0.5.0 | `--incremental <git-ref>` + `incremental_since` |
| No static analysis | wave-21 | `cogant.static` module: complexity, coupling, dead code, Halstead |
| No visualization beyond HTML | wave-21 | `cogant.viz`: PDF, PNG, Mermaid, SVG, 8-page report |
| Basic export only (JSON, GraphML) | wave-21 | 9 formats: JSON, GraphML, Parquet, SVG, PNG, PDF, Mermaid, DOT, JSONLINES |
| No type system for protocols | wave-21 | 9 `@runtime_checkable` Protocols, 49 .pyi stubs |
| No network/graph analysis | wave-21 | `GraphAnalyzer`: centrality, community, SCC |
| No streaming / WebSocket API | wave-21 | `WS /ws/translate` + `translate_batch()` |
