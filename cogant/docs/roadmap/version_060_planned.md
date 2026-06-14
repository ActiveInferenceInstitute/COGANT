# Version 0.6.x — Planned

**Theme: Language breadth and streaming scale**
**Status:** Planning | **Target window:** Q2–Q3 2026

This document scopes the v0.6.x minor series. All items are planned, not committed.
Scope is subject to revision based on actual current usage patterns and community feedback.

---

## Goals

1. Extend the language surface to Java and Rust — the two largest gaps for enterprise and systems users.
2. Eliminate the memory/time scaling cliff for large repos via streaming export and incremental graph construction.
3. Improve translation confidence by adding intra-procedural type inference and alias analysis.
4. Consolidate internal quality: stubgen CI, dataclass slots, vocabulary deduplication.

---

## Scheduled Work

### L1 — Java Parser (tree-sitter) {#l1}

**Effort:** L | **Owner:** parsers team | **Blocks:** nothing; enables L3

Java is the #1 language in enterprise codebases that most benefit from Active Inference modeling.
Spring / JPA / Guice patterns map cleanly onto HIDDEN_STATE / POLICY / OBSERVATION roles.

- [ ] `cogant/parsers/java.py`: `JavaParser`, `JavaSymbolExtractor`
  - Parse `class`, `interface`, `enum`, `record` declarations
  - Extract field, method, constructor symbols with type annotations
  - Handle `@Autowired`, `@Service`, `@Repository`, `@Entity` annotations
- [ ] `cogant/translate/rules/java_rules.py`: Java-specific rule family
  - `SpringBeanRule` → HIDDEN_STATE (Spring-managed state beans)
  - `JPAEntityRule` → HIDDEN_STATE (JPA persistent entities)
  - `RESTControllerRule` → OBSERVATION (REST endpoints as observations)
  - `EventListenerRule` → ACTION (event handler methods)
- [ ] Cross-language roundtrip test: Java Observer pattern → GNN → Python synthesized code → GNN; assert `s_role >= 0.8`
- [ ] `examples/zoo/14_java_spring_mini/`: minimal Spring Boot example as ground truth fixture
- [ ] `tests/unit/test_parser_java.py`: 40+ unit tests covering all Java AST node types
- [ ] `tests/integration/test_java_pipeline.py`: full forward pipeline on Spring Boot fixture

### L2 — Rust Parser (tree-sitter)

**Effort:** M | **Owner:** parsers team | **Blocks:** nothing; enables L3

Rust's ownership/borrowing semantics map naturally onto Active Inference precision weighting.
`&mut` access → WRITES edge; `Arc<Mutex<>>` wrapping → HIDDEN_STATE with high confidence.

- [ ] `cogant/parsers/rust_parser.py`: `RustParser`, `RustSymbolExtractor`
  - Parse `fn`, `struct`, `enum`, `impl`, `trait` declarations
  - Extract lifetime annotations (informational only, not used for rules yet)
  - Handle `use` imports, `pub` visibility modifiers
- [ ] `cogant/translate/rules/rust_rules.py`
  - `RustOwnershipRule` → HIDDEN_STATE (exclusively-owned mutable state)
  - `RustTraitImplRule` → OBSERVATION/ACTION (trait method implementations)
  - `RustAsyncRule` → POLICY (async fn / tokio task spawning patterns)
- [ ] `examples/zoo/15_rust_actor/`: minimal Rust actor system (tokio channels) as fixture
- [ ] Cross-language Java + Rust roundtrip integration test

### L3 — Streaming Export for Large Graphs (>100k nodes)

**Effort:** M | **Owner:** export team | **Blocks:** none; fixes scaling cliff

The Dulwich benchmark reveals memory pressure at ~1.8 e/n ratio. Streaming writers avoid
building full in-memory structures.

- [ ] `cogant/export/streaming/parquet.py`: `StreamingParquetExporter`
  - Chunked `RecordBatchWriter` via PyArrow; configurable `chunk_size` (default: 10,000 nodes)
  - Preserves all metadata columns and role annotations
- [ ] `cogant/export/streaming/graphml.py`: `StreamingGraphMLExporter`
  - Two-pass: emit all `<node>` elements first, then all `<edge>` elements
  - Avoids loading the full graph into memory simultaneously
- [ ] `cogant/export/streaming/jsonlines.py`: `StreamingJSONLinesExporter`
  - Per-node/per-edge line flush; configurable buffer size
- [ ] `BundleExporter.export_streaming()` entry point that auto-selects streaming vs. in-memory
- [ ] Benchmark suite: 10k, 50k, 100k, 500k synthetic graphs; assert memory < 2 GB at 500k nodes
- [ ] `cogant export --streaming` CLI flag

### L4 — Intra-Procedural Type Inference {#l4}

**Effort:** L | **Owner:** static analysis team | **Blocks:** L5 (alias analysis benefits from types)

Un-annotated Python is common. Hindley-Milner-lite propagation inside function bodies would reduce
OBSERVATION false negatives for codebases without type annotations (Django, Flask, scripts).

- [ ] `cogant/static/type_inference.py`: `TypeInferrer`
  - `infer_function(node: ast.FunctionDef) -> dict[str, type | None]`
  - Literal type propagation (int, str, bool, None)
  - Return-type narrowing via control flow (isinstance guards)
  - Attribute access chain resolution (`.name`, `.value`, `.data`)
  - Assignment chain following (`x = y.z; return x` → same type as `y.z`)
- [ ] Integration with `ComplexityAnalyzer`: annotate inferred types in `ComplexityEntry`
- [ ] Integration with `ObservationRule` / `ActionRule`: use inferred types as additional heuristic evidence
- [ ] `tests/unit/test_static_type_inference.py`: 50+ unit tests
- [ ] Benchmark: annotation coverage improvement on `flask_app` fixture (measure before/after)

### L5 — Alias Analysis {#l5}

**Effort:** M | **Owner:** graph team | **Blocks:** none

Assignment aliasing (`x = y`) creates false WRITES edges because the translator sees `x` written
when it's really just a reference. Flow-insensitive alias sets remove these spurious edges and
improve precision of `MutatingSubsystemRule` and `DataPipelineRule`.

- [ ] `cogant/static/alias.py`: `AliasAnalyzer`
  - `compute_alias_sets(graph: ProgramGraph) -> dict[NodeId, set[NodeId]]`
  - Flow-insensitive: merge alias sets at assignment statements
  - Propagate through `READS`/`WRITES` edges in the graph
- [ ] `ProgramGraph.prune_alias_edges()`: remove WRITES edges where source is an alias of target
- [ ] Integration with `translate/engine.py`: run alias analysis before fixpoint iteration
- [ ] `tests/unit/test_alias_analysis.py`: 30+ unit tests with synthetic aliasing patterns
- [ ] Property test: alias pruning preserves graph connectivity (no disconnected components)

### L6 — Internal Refactoring Batch (Streamlining)

These non-feature improvements reduce long-term maintenance cost.

**R3: Decouple viz matplotlib imports** (see feature_backlog.md#R3)
- [ ] Audit all module-level `import matplotlib`, `import PIL`, `import reportlab`
- [ ] Wrap each in `try/except ImportError` with `cogant[viz]` hint
- [ ] Add `pytest.importorskip` guards to all affected test files

**R4: Shared translation vocabulary** (see feature_backlog.md#R4)
- [ ] `cogant/translate/vocabulary.py`: `OBSERVATION_KEYWORDS`, `ACTION_VERBS`, `STATE_NOUNS`, etc.
- [ ] Refactor all 22 rule `matches()` methods to use shared vocabulary
- [ ] Property test: no keyword appears in two competing role lists

**R6: `@dataclass(slots=True)` upgrade** (see feature_backlog.md#R6)
- [ ] Enable `slots=True` on key dataclasses: `SemanticMapping`, `NodeAttrs`, `EdgeAttrs`, `AgentConfig`, `EpisodeMetrics`
- [ ] Benchmark memory reduction on `flask_app` fixture

**R7: Stubgen CI check** (see feature_backlog.md#R7)
- [ ] `make gen-stubs` target: `mypy --stubgen --package cogant -o stubs/`
- [ ] CI job: diff checked-in stubs vs generated; fail on unexpected delta

---

## Out of Scope for v0.6.x

- Dynamic analysis / trace integration (v0.7.x — see feature_backlog.md#4)
- Cross-repository analysis (v0.7.x — too architecturally invasive to fit in 0.6.x)
- VSCode extension (depends on v1.0 API freeze)
- Public API freeze (v1.0 only)

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Java grammar completeness (annotations, generics, lambdas) | Medium | Scope to core subset; use tree-sitter-java's test corpus as oracle |
| Type inference creates performance regression | Low | Gate behind `--with-type-inference` flag; benchmark before enabling by default |
| Alias analysis changes rule confidence scores on existing fixtures | Medium | Capture pre/post ε diff; require no regression on 23-fixture suite |
| Streaming export API incompatible with bundle manifest | Low | Design `StreamingBundleManifest` as a subset of `BundleManifest` |

---

## Success Criteria

- [ ] Java + Rust parsers pass their respective fixture roundtrips with `s_role >= 0.8`
- [ ] Streaming export: 500k-node graph completes in <5 min with <2 GB peak memory
- [ ] Type inference: annotation coverage improvement measurable on at least one unannotated fixture
- [ ] All ruff violations: 0; mypy --strict: 0 errors
- [ ] Test count: >2,500 passing; coverage: ≥85%
- [ ] No regression on existing 23-fixture roundtrip suite (ε still 1.0)
