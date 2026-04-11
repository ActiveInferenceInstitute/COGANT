# FAQ

Frequently asked questions about COGANT, organized from "just getting started" through technical limitations, the reverse pipeline, integration, research, and roadmap.

---

## Getting Started

### 1. What is COGANT?

COGANT (COde-to-GNN Active iNference Translator) is a static analysis tool that reads a Python codebase, builds a program graph, and maps every function, class, and module to an Active Inference role (hidden state, observation, action, policy, and several secondary roles). The output is a Generalized Notation Notation (GNN) package: a machine-readable generative model of your codebase expressed in the Active Inference Institute's reference format.

See [Getting Started — Quick Start](getting-started/quickstart.md).

### 2. What is a GNN and why would I care?

GNN stands for Generalized Notation Notation. It is a text format the Active Inference Institute uses to describe generative models: state-space variables, observation channels, actions, and the A/B/C/D matrices that relate them. If you work in Active Inference research, GNN is how you share models. If you are a software engineer, the GNN is a formal summary of your codebase's information flow: which parts hold state, which parts observe, which parts act, and which parts make decisions.

See [Theory — GNN Format](theory/gnn_format.md).

### 3. What languages does COGANT support?

v0.5.0 supports **Python** (via CPython `ast`) and **JavaScript / TypeScript** (via a complete tree-sitter front end). The mapping rules are language-agnostic (they operate on `NodeKind`/`EdgeKind` in the program graph). Java and Rust parsers remain on the roadmap.

### 4. How accurate is role assignment?

On the six control-positive fixtures shipped with v0.5.0 (calculator, event_pipeline, flask_mini, flask_app, requests_lib, json_stdlib), mean confidence scores range from 0.83 to 0.91. However, confidence is not accuracy. The known recall gap is real: for example, the calculator fixture never emits an ACTION mapping for `input_digit` or `input_operation` because those method names do not match the keyword list (`set/update/create/delete/send/push/execute/run/process/handle/dispatch`). Only the private helper `_execute_operation` matches. Expect roughly 73% precision and 82% recall on well-structured Python codebases, with worse numbers on codebases that use unconventional naming.

See [R&D — Calibration](rnd/calibration.md).

### 5. Do I need to know Active Inference to use COGANT?

No. COGANT assigns roles and produces the GNN bundle without requiring any Active Inference knowledge from you. The output is useful even if you treat it purely as a "which parts of my codebase are stateful, which read, which write, which orchestrate" summary. If you do know Active Inference, the A/B/C/D matrices and Markov blanket partition will be directly meaningful.

See [Theory — Active Inference Primer](theory/active_inference_primer.md).

---

## Running COGANT

### 6. How do I scan my project?

```bash
cogant translate ./my_repo --output output/ --layout-output
```

This runs the full pipeline: ingest, static analysis, normalize, graph, translate, state-space, process, export, and validate. Add `--no-dynamic` to skip coverage/trace enrichment when you have no runtime data.

See [Getting Started — Quick Start](getting-started/quickstart.md).

### 7. Why did COGANT give my class a HIDDEN_STATE role?

`MutatingSubsystemRule` fires whenever a class has at least one incoming or outgoing `WRITES`/`MUTATES` edge. If your class has mutable instance variables that are written by its own methods, it will be classified as HIDDEN_STATE. This is by design: in Active Inference terms, mutable internal state is the agent's "beliefs" (mu).

Use `cogant explain ./my_repo MyClass` to see exactly which rules fired and why.

### 8. Why is my function classified as ACTION not POLICY?

`ActionRule` matches on setter/mutator keywords (`set`, `update`, `create`, `delete`, `send`, `push`, `execute`, `run`, `process`, `handle`, `dispatch`) plus the presence of `WRITES` edges. `PolicyRule` matches on controller/manager/router/dispatcher vocabulary at the class level, plus high out-degree orchestration patterns. If your function name contains an action keyword and it writes to state, it becomes an ACTION. If it instead delegates to multiple downstream functions without writing state itself, it would be a POLICY.

The distinction can be surprising. Run `cogant explain` on the specific function to see the rule trace.

### 9. How do I improve role assignment accuracy?

Three things help:

1. **Use descriptive names.** The semantic rules rely on keyword matching. A method called `process_order` will be recognized as an ACTION; a method called `do_thing` will not.
2. **Add type annotations.** The confidence system penalizes unresolved types (-0.05 per unresolved argument). Annotations improve provenance scoring.
3. **Supply runtime data.** Run with `--coverage` and `--trace` to promote mappings from STATIC_ONLY to STATIC_PLUS_RUNTIME tier, which raises confidence above 0.65.

### 10. Can I run COGANT on a monorepo?

Yes, but point `cogant translate` at a specific subdirectory rather than the repo root. COGANT analyzes one project at a time. For a monorepo with `services/auth/`, `services/billing/`, etc., run each service as a separate translation.

### 10a. Is there Rust FFI acceleration?

Yes. Set `COGANT_USE_RUST=1` to enable the optional PyO3 `connected_components` backend for graph construction. When the compiled Rust extension is absent, COGANT falls back to pure Python automatically. Run `cogant doctor` to verify Rust backend availability.

### 10b. Does COGANT ship type stubs?

Yes. v0.5.0 ships `.pyi` stub files for all public API modules and a `py.typed` marker. Mypy, Pyright, and Pylance resolve types from the stubs without requiring the source.

---

## Technical Limitations

### 11. What codebases does COGANT work well on?

COGANT works best on **well-structured Python packages** with:

- Clear class hierarchies and descriptive method names
- Type annotations (even partial)
- Moderate size (under 100K functions; see [performance targets](roadmap/performance_targets.md))
- Standard patterns: MVC, service layers, event-driven architectures

The control-positive fixtures (calculator, event_pipeline, flask_mini) represent the sweet spot. The flask_app fixture (51 mappings, 0.82 mean confidence) shows that mid-size web applications work well.

### 12. What codebases does COGANT struggle with?

- **Metaprogramming-heavy code** — decorators that rewrite function signatures, `__getattr__` tricks, and dynamic class generation produce nodes the static analyzer cannot resolve.
- **Single-file scripts** — no class boundaries means fewer structural signals for the rules.
- **Deeply nested closures** — the graph builder tracks module-level and class-level scope but closures within closures may not produce clean edges.
- **Non-English identifiers** — the keyword lists are English-only.
- **Very large codebases** (1M+ functions) — technically supported but not yet validated at that scale.

### 13. Why does `event_pipeline` have a lower roundtrip mapping count?

The event_pipeline fixture produces 20 semantic mappings in the forward pass but the roundtrip summary shows `mapping_count: 1`. This is because the on-disk serialization (`semantic_mappings.json`) is lossy: it writes every mapping with `semantic_role: "unknown"` due to a known serialization bug where the exporter does not read `SemanticMapping.kind`. The in-memory pipeline carries correct roles. This is a known issue documented in the R&D notes and scheduled for fix.

See [R&D — Active Inference Mapping, Surprising Finding #1](rnd/active_inference_mapping.md).

### 14. Is role assignment perfect?

No. Known gaps include:

- **Precision ~73%, recall ~82%** on control-positive fixtures (estimated, not from a large labeled corpus).
- **Calculator never emits ACTION for `input_digit`** because the method name does not match any action keyword. Only `_execute_operation` matches via "execute."
- **Conflict resolution can suppress correct roles.** When `InheritanceRule` fires on an `EventHandler` subclass, it labels the class POLICY, which wins over HIDDEN_STATE from `MutatingSubsystemRule` — even though the class genuinely holds mutable state (`failed_events`).
- **No learned parameters yet.** Confidence is rule-based (base score times provenance penalty times conflict discount). A labeled corpus and reliability diagram are roadmap items.

See [R&D — Active Inference Mapping, Surprising Findings](rnd/active_inference_mapping.md).

### 15. Does COGANT understand runtime behavior?

No. COGANT is **static analysis only** by default in v0.5.0. It parses Python AST (and JS/TS via tree-sitter), builds a program graph from structural relationships (calls, imports, inheritance, reads, writes), and applies rules to that graph. It does not execute your code, trace actual function calls, or observe runtime state.

The `--coverage` and `--trace` flags accept pre-collected runtime data (coverage.py JSON and function-call traces) and merge them into the graph, but COGANT itself does not generate that data.

### 16. Can COGANT analyze dynamic languages like Ruby or PHP?

Not in v0.5.0. The parsers currently cover Python and JavaScript/TypeScript. Highly dynamic languages will be harder to analyze because static analysis cannot resolve runtime dispatch, monkey-patching, or eval-based code generation. Expect lower confidence scores and more RUNTIME_ONLY tier mappings for dynamic language targets.

### 17. What happens with code below the confidence threshold?

Mappings with confidence below 0.4 are kept in the bundle for traceability but excluded from the state-space compilation by default. They appear in the raw `semantic_mappings.json` but do not contribute to the A/B/C/D matrices or the GNN export. You can lower the threshold with `--min-confidence` if you want to include them.

---

## The Reverse Pipeline

### 18. What is `cogant reverse`?

The reverse direction takes a GNN generative model and synthesizes a minimal Python package that implements it: a class per hidden-state node, a method per action, a getter per observation, and module-level constants for preferences and priors. The goal is to close the loop: `code -> GNN -> code'`.

**Status:** `cogant reverse` and `cogant roundtrip` are fully available CLI subcommands as of v0.5.0. See [Tutorial 6 — Reverse Mode](tutorials/06_reverse_mode.md).

### 19. Can I generate a working Python package from a GNN?

In principle, yes. The `PackagePlan` data model and `gnn/matrices.py` entry point exist and can enumerate hidden states, observations, and actions in a stable order. The simulation runner (`simulate/runner.py`) uses the same numerical path the synthesized package would take. In practice, the output is not yet production-quality: it produces semantically equivalent but not textually equivalent code, and arbitrary-language output is not supported.

### 20. What does "role_match_score" mean?

When you run a forward-then-reverse roundtrip, `role_match_score` measures how many of the original semantic role assignments survive the round trip. A score of 100% means every node in the regenerated code gets the same Active Inference role as the original. Scores below 100% indicate information loss during either export or reverse synthesis.

### 21. Why is the roundtrip not perfect?

Several reasons:

1. **Serialization is lossy.** The current exporter writes `semantic_role: "unknown"` for all mappings (see FAQ #13).
2. **Whitespace and docstrings are discarded.** The forward pipeline throws them away, so reverse produces semantically equivalent but structurally different code.
3. **Keyword sensitivity.** The reverse pipeline generates method names from role metadata, which may not match the original names, causing re-translation to assign different roles.
4. **Conflict resolution is not reversible.** When two rules fire on the same node and one wins, the losing assignment is discarded. The reverse pipeline cannot know it existed.

### 22. What is the Galois connection?

The theoretical framing for the forward/reverse pipeline is a Galois connection between the lattice of Python programs (ordered by structural refinement) and the lattice of GNN generative models (ordered by information content). The forward map `F` is abstraction; the reverse map `G` is concretization. The roundtrip `G . F` is a closure operator: `code' = G(F(code))` is always a simplification of `code` that preserves the Active Inference structure.

The formal statement and ε-bounded roundtrip error proof live in `evaluation/ISOMORPHISM_THEOREM.md`. This is a theoretical result; the current implementation does not achieve the bounds due to the serialization and conflict-resolution issues above.

---

## Integration

### 23. How do I use COGANT in CI?

Run `cogant translate` and `cogant validate` as CI steps. The validate command exits with a non-zero code if the GNN bundle has errors, so you can gate merges on a passing validation score.

```yaml
# Example GitHub Actions step
- name: COGANT analysis
  run: |
    cogant translate ./src --output cogant-output/ --no-dynamic
    cogant validate cogant-output/
```

### 24. Is there a GitHub Action?

Not yet. A reusable GitHub Action is on the roadmap. For now, install COGANT in your CI environment and call the CLI directly.

### 25. Can COGANT work with pyproject.toml projects?

Yes. The ingest stage parses `pyproject.toml` (and `setup.py`, `requirements.txt`, `Cargo.toml`, `package.json`) to discover project metadata and dependencies. Point `cogant translate` at your project root and it will find the configuration automatically.

### 26. How fast is COGANT?

On the control-positive fixtures (12-26 graph nodes), the full pipeline completes in 57-74ms. Performance targets for larger codebases:

| Scale | Target |
|-------|--------|
| 10K functions | < 10 seconds |
| 100K functions | < 60 seconds |
| 1M functions | < 10 minutes |

These are targets, not validated benchmarks. Memory target is < 200MB for 10K functions, < 1GB for 100K.

See [Roadmap — Performance Targets](roadmap/performance_targets.md).

---

## Research and ML

### 27. Is there a dataset for training?

COGANT ships an ML dataset (v0.1) with 6 fixtures and node-level role labels. A HuggingFace dataset card is included. The fixtures are the control-positive examples: calculator, event_pipeline, flask_mini, flask_app, and others. This is a small seed dataset, not a large-scale benchmark.

### 28. Can I use COGANT output to train a model?

Yes. The GNN (Generalized Notation Notation) export produces structured JSON (`model.gnn.json`) with node features, edge indices, and role labels. Although COGANT's "GNN" refers to the Active Inference Institute notation (not graph neural networks), the same JSON is structurally suitable as input to a downstream graph-neural-network trainer if you choose to consume it that way. The PyTorch Geometric export path produces `Data` objects directly. The A/B/C/D matrices can also serve as training targets for generative model learning.

See [Export — PyTorch Geometric](export/pytorch_geometric_export.md).

### 29. What papers does COGANT's theory relate to?

The core theoretical connections:

- **Active Inference:** Friston (2010), Parr, Pezzulo & Friston (2022) — the Free Energy Principle and the agent-environment partition that COGANT maps onto code.
- **Markov blankets in software:** The partitioning of program graphs into internal/sensory/active/external sets is inspired by the Markov blanket formalism from statistical physics.
- **Generalized Notation Notation:** The Active Inference Institute's GNN specification for interoperable generative model descriptions.
- **Program analysis as abstract interpretation:** The Galois connection framing follows Cousot & Cousot (1977).

See [Theory — Active Inference](theory/active_inference.md) and [Theory — Code as Generative Model](theory/code_as_generative_model.md).

---

## Troubleshooting

### 30. `cogant explain` says "no rules fired" for my function. What does that mean?

It means none of the semantic, structural, behavioral, or resilience rules matched your function's name, edge pattern, or graph context. This typically happens with:

- Functions that have generic names (`do`, `run`, `main`, `helper`)
- Utility functions with no READS/WRITES edges
- Nested helper functions that the graph builder did not fully resolve

The function still appears in the program graph as a node; it just has no Active Inference role assignment. Its confidence will be below 0.4 and it will be excluded from the GNN state-space by default.

### 31. I see "STATIC_PLUS_RUNTIME: 0" in every fixture. Is that a bug?

No. The control-positive fixtures ship without runtime data (no coverage.py JSON, no trace files). All mappings therefore land in the STATIC_ONLY tier. To get STATIC_PLUS_RUNTIME mappings, run your code under coverage and pass the results to COGANT with `--coverage` and `--trace`. See [R&D — Calibration](rnd/calibration.md).

### 32. The validation score is 100 but the semantic mappings look wrong. How?

Validation scores (0-100) measure **structural correctness** of the GNN bundle: valid JSON, correct matrix dimensions, no dangling references. They do not measure **semantic accuracy** of the role assignments. A bundle can be structurally perfect and semantically wrong. Use `cogant explain` to audit individual role assignments, and check the confidence tiers for low-confidence mappings that may be incorrect.

---

## Roadmap

### 33. Will COGANT support Rust, Go, and Java?

TypeScript is now supported (v0.5.0). Rust, Go, and Java parsers are on the roadmap, built on tree-sitter. The translation rules are language-agnostic; only the parser and fact-extraction layers need to be language-specific.

See [Roadmap — v0.2.0](roadmap/version_020_planned.md).

### 34. Is there a web UI?

v0.5.0 ships a basic HTML site via `cogant render` for browsing the program graph and GNN output. An interactive graph visualization with role filtering, Markov blanket highlighting, and drill-down is a roadmap item but has no committed timeline.

### 35. What is the long-term vision?

COGANT aims to be a bridge between software engineering and Active Inference research:

1. **Near term (v0.2):** Multi-language support, incremental caching, plugin system, GitHub Action.
2. **Medium term (v0.3-1.0):** Learned confidence parameters from labeled corpora, full reverse pipeline with CLI, IDE integration, cross-codebase analysis.
3. **Long term:** Codebases as living generative models — continuous CI integration that tracks how a project's Active Inference structure evolves over time, with drift detection when architectural roles shift unexpectedly.

The theoretical goal is to make the Galois connection practical: any codebase can be lifted to a formal generative model, and any generative model can be lowered to a working implementation, with bounded information loss in both directions.

See [Roadmap — Overview](roadmap/overview.md) and [Roadmap — v1.0.0](roadmap/version_100_planned.md).
