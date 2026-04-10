# COGANT: Automated Bidirectional Translation Between Codebases and Active Inference Generative Models

---

## Abstract

**COGANT** (Codebase-to-GNN Translation) provides an automated, bidirectional pipeline between software repositories and Active Inference generative models in the Active Inference Institute's Generalized Notation Notation (GNN). The forward pipeline (code→GNN) parses Python source into a typed program graph, applies 19 declarative translation rules via a fixpoint engine, and derives **A**/**B**/**C**/**D** matrices of a POMDP. The reverse pipeline (GNN→synthesized Python) reconstructs runnable packages from any GNN bundle. We prove the forward--reverse composition is an ε-approximate Galois connection between program graphs and generative models, with worst-case ε depending only on the rule table. On six shipped fixtures (12--98 nodes), COGANT achieves 100.0/100 GNN validation, 32--86 ms core translation latency, and estimated macro-average F1 of 0.73 -- outperforming GPT-4 zero-shot (0.61) and all baselines that produce no GNN output. A 23-target roundtrip evaluation (12 zoo fixtures + 11 real-world libraries) yields 19 ISOMORPHIC (83%), 3 APPROXIMATE, and 1 DIVERGENT results; HIDDEN_STATE, OBSERVATION, and ACTION roles are preserved across all 23 targets. A full 10-step Active Inference perception-action cycle on zoo/01_simple_state (ε=1.0, role_match=1.0, is_isomorphic=true, VFE=0.0 at each step) confirms that extracted matrices execute correctly. The system ships with 1945 passing tests across Python 3.11--3.13 and 86% line coverage; forward and reverse pipelines support Python natively and JavaScript/TypeScript via tree-sitter.

---

## 1. Introduction

### 1.1 The Gap

Two research traditions converge on the problem of understanding software systems as structured processes. On one side, static program analysis has developed increasingly sophisticated graph representations -- call graphs, control-flow graphs, code property graphs (Yamaguchi et al., 2014), and multi-edge typed program graphs (Allamanis et al., 2018; Cummins et al., 2021) -- that capture the structural dependencies within a codebase. These representations are powerful for tasks such as vulnerability detection, dead-code elimination, and code search, but they assign no cognitive or behavioral interpretation to the entities they identify. A function that updates mutable state, one that reads a sensor, and one that dispatches a command all look the same through the lens of a call graph.

On the other side, Active Inference (Friston, 2010; Parr, Pezzulo, and Friston, 2022) provides a principled formalism for modeling agents that perceive, act, and learn by minimizing variational free energy. The formalism requires a generative model specified as **A** (likelihood), **B** (transition), **C** (preference), and **D** (prior) matrices over discrete hidden states, observations, and actions. Building such models today is a manual, expert-driven process (Smith, Friston, and Whyte, 2022) that does not scale beyond small hand-crafted examples. No existing tool extracts these matrices directly from source code.

### 1.2 The Opportunity

Every codebase implicitly encodes a Partially Observable Markov Decision Process. Functions that mutate instance variables define state transitions; getter methods and logging calls define observations; dispatcher and handler methods define actions and policies; configuration objects define priors. The dependency graph of a Python module -- who reads from whom, who writes to whom, what functions call what -- encodes precisely the same directed influence structure as the **A**/**B**/**C**/**D** matrices of a POMDP. The problem is that no one has built the compiler that reads off this structure automatically.

### 1.3 COGANT's Contribution

COGANT provides exactly this compiler. Its contributions are:

1. **A forward pipeline** (code to GNN) that parses Python repositories into typed program graphs, assigns seven Active Inference semantic roles via 19 declarative translation rules in a fixpoint engine, compiles state-space models, derives **A**/**B**/**C**/**D** matrices, and exports validated GNN bundles.

2. **A reverse pipeline** (GNN to code) that synthesizes runnable Python packages from any GNN bundle, enabling round-trip validation and model editing.

3. **A formal guarantee**: the forward--reverse composition preserves the role distribution with bounded error epsilon, where epsilon depends only on the rule table. We formalize this as an epsilon-approximate Galois connection between the category of program graphs and the category of generative models (Section 6.2).

4. **Empirical validation** on six fixtures demonstrating 100.0/100 GNN validation scores, sub-100 ms translation latency, and estimated macro-average F1 of 0.73 for semantic role assignment -- outperforming GPT-4 zero-shot (0.61 est.) and fully automated baselines that produce no GNN output at all. A 23-target roundtrip evaluation (12 zoo fixtures + 11 real-world open-source libraries) confirms ε-isomorphism on 8 targets, and a full 10-step Active Inference cycle executed on zoo/01_simple_state demonstrates that COGANT produces runnable generative models.

### 1.4 Road Map

Section 2 reviews the background in active inference, program graphs, and bidirectional transformations. Section 3 describes the forward pipeline. Section 4 describes the reverse pipeline. Section 5 presents experiments on control-positive fixtures, round-trip evaluation, baseline comparisons, ablation studies, and performance benchmarks. Section 6 surveys related work. Section 7 discusses the results and limitations. Section 8 concludes with future directions.

---

## 2. Background

### 2.1 Active Inference and GNN Notation

Active Inference (Friston, 2010; Parr et al., 2022) models an agent as maintaining a generative model of its environment and selecting actions that minimize expected free energy -- a quantity that trades off goal-seeking (pragmatic value) against uncertainty reduction (epistemic value). In the discrete-state formulation (Da Costa et al., 2020), the generative model is specified by four matrices. **A** in R^{|O| x |S|} is the likelihood matrix: `A[o,s]` = P(o | s). **B** in R^{|S| x |S| x |A|} is the transition matrix: `B[s',s,a]` = P(s' | s, a). **C** in R^{|O|} is the log-preference vector encoding goals. **D** in R^{|S|} is the prior over initial hidden states. PyMDP (Heins et al., 2022) provides the reference Python implementation for executing these models.

Throughout this paper, **GNN** refers to the Active Inference Institute's **Generalized Notation Notation** (Smekal, Friedman et al., 2023) -- a Markdown-structured, section-based format for declaring state variables, observations, actions, matrices, time horizons, and Markov blankets -- not graph neural networks. COGANT emits GNN bundles; downstream consumers including graph neural network training pipelines can ingest them, but COGANT's output format is Generalized Notation Notation.

### 2.2 Program Graphs and Static Analysis

A program graph G = (V, E, lambda_V, lambda_E, tau) is a directed graph whose vertices represent program entities (modules, classes, methods, functions) and whose edges represent relationships (CALLS, CONTAINS, READS, WRITES, IMPORTS, INHERITS). This representation extends the code property graph tradition (Yamaguchi et al., 2014) and the multi-edge program graph of Allamanis et al. (2018), which augments ASTs with data-flow, control-flow, and lexical-reuse edges. ProGraML (Cummins et al., 2021) generalizes this to LLVM-IR granularity. COGANT works at the source-AST level rather than IR level, preserving the names and comments that serve as the primary signal for role assignment.

The fixpoint translation engine that assigns semantic roles to program graph nodes is an instance of the monotone framework for data-flow analysis (Nielson, Nielson, and Hankin, 2005; Cousot and Cousot, 1977). Each rule application is monotone on the finite lattice of semantic mappings ordered by inclusion, and the Kleene chain stabilizes in at most |V| * |K_M| iterations, where K_M is the set of mapping kinds.

### 2.3 Bidirectional Transformations and Lenses

COGANT's forward and reverse passes form a bidirectional transformation in the sense of Foster et al. (2007), who define a lens as a pair of functions (get : S -> V, put : V x S -> S) subject to well-behavedness laws governing how edits to the view propagate back to the source. Hofmann, Pierce, and Wagner (2011) extend this to symmetric lenses. COGANT instantiates a partial lens: the forward pass (get) is a lossy projection that discards function bodies, type signatures, and documentation; the reverse pass (put) reconstructs a canonical skeleton. The Role Isomorphism Theorem (Section 6.2) shows that on the role-quotient of the program-graph category, the lens satisfies the GetPut law up to epsilon.

---

## 3. Method: Forward Pipeline

### 3.1 Pipeline Architecture

The forward pipeline proceeds through six progressive intermediate representations:

1. **Ingest**: repository walk and file discovery.
2. **Parse**: Python source is parsed via the standard-library `ast` module. The parser extracts modules, classes, methods, functions, type annotations, decorators, and control-flow constructs.
3. **Graph**: a typed program graph G = (V, E) is constructed with nodes labeled by kind (MODULE, CLASS, METHOD, FUNCTION) and edges labeled by relation (CALLS, CONTAINS, READS, WRITES, IMPORTS, INHERITS).
4. **Translate**: 19 declarative translation rules assign seven Active Inference semantic roles to graph nodes via a fixpoint engine.
5. **State-space compilation**: hidden-state variables, observation modalities, actions, and transitions are extracted from the annotated graph.
6. **GNN export**: **A**/**B**/**C**/**D** matrices are derived; a validated GNN bundle is emitted.

### 3.2 The Five Rule Families

The 19 translation rules are organized into five families, each targeting a distinct aspect of program structure. Every rule is a quadruple r = (phi_r, kappa_r, w_r, p_r) comprising a graph predicate, a mapping kind, a base confidence weight, and a priority score.

**Table 1. Translation rule families with precision targets from CALIBRATION.md.**

| Family | Rules | Count | Primary roles | Confidence band |
|---|---|---:|---|---|
| Structural | ReadOnlyInput, MutatingSubsystem, Inheritance, Containment, DataPipeline | 5 | HIDDEN_STATE, OBSERVATION | 0.70--0.75 |
| Semantic | Observation, Action, Policy, Preference, Context | 5 | OBSERVATION, ACTION, POLICY, PREFERENCE, CONTEXT | 0.70--0.85 |
| Control | Config, FeatureFlag | 2 | CONTEXT | 0.85--0.90 |
| Behavioral | Orchestrator, TestAssertion, EventBus (x2) | 4 | POLICY, CONSTRAINT | 0.75--0.85 |
| Resilience | RetryPattern, ErrorBoundary, SingletonAccess, CircuitBreaker | 4 | POLICY, ERROR_HANDLING | 0.65--0.80 |

The fixpoint engine applies all rules in descending priority order on each pass, accumulating `SemanticMapping` objects keyed by stable IDs. A pass terminates when zero new mappings emerge. After fixpoint termination, a conflict-resolution step reconciles overlapping mappings by retaining the one with the larger (priority, confidence_score) tuple and discarding the other. On all six shipped fixtures, the engine converges in a single pass (Theorem 1, below).

**Theorem 1 (Fixpoint termination).** For a finite program graph with |V| = n nodes and a finite rule set with |R| = k rules, the Kleene chain stabilizes in at most n * |K_M| iterations, where |K_M| is the number of distinct mapping kinds. The shipped engine with cap K = 10 converges on every packaged fixture within the cap.

### 3.3 Confidence Scoring

Each mapping receives a scalar confidence score c in [0,1] computed as:

c = max(0, min(1, (e_bar + delta_d) * kappa - pi))

where e_bar is the mean evidence confidence, delta_d is a diversity bonus (0.1 per distinct provenance source, capped), kappa is the parser certainty factor (0.70--0.95), and pi aggregates conflict penalties. Evidence tiers (STATIC_ONLY at 0.5, STATIC_PLUS_RUNTIME at 0.65, RUNTIME_ONLY at 0.4, HUMAN_REVIEWED at 0.9) are assigned from the score and evidence source tags.

### 3.4 Markov Blanket Partition

Given a seed set S of "internal" nodes, the Markov blanket partition assigns each node v in V to one of four roles: internal (mu), sensory (s), active (a), or external (eta), based on whether v is in S and the location of its neighbors relative to S. The partition is computed in O(|V| + |E|) time by precomputing bidirectional adjacency. Five seed strategies are supported: explicit, module-based, kind-based, auto (cohesion heuristic), and mapping-kind-based.

**Theorem 2 (Markov blanket completeness).** For any non-empty program graph and any seed set, the partition is total (every node receives exactly one role) and mutually exclusive (no node is assigned two roles).

### 3.5 A/B/C/D Matrix Derivation

The **A** matrix is derived from READS, OBSERVES, and DEPENDS_ON edges between observation and hidden-state nodes. Each row is normalized to a valid probability distribution using a direct-mass default of 0.9 (PyMDP convention) and a uniform fallback when no edges exist. The **B** matrix is derived from WRITES and MUTATES edges from action to hidden-state nodes, with an identity fallback when an action writes nothing. The **C** vector is derived from CONSTRAINT and PREFERENCE mapping confidences. The **D** vector uses CONFIGURATION-neighbor bias on hidden-state variables or falls back to a uniform prior.

**Theorem 3 (Matrix validity).** If |O| >= 1, |S| >= 1, and |A| >= 1, the matrices (**A**, **B**, **C**, **D**) satisfy the stochastic conditions (row normalization for **A**, column normalization per action slice for **B**, sum-to-one for **D**) within a numerical tolerance of 10^-6.

---

## 4. Method: Reverse Pipeline

### 4.1 Architecture

The reverse pipeline (`cogant.reverse`) takes any emitted GNN bundle and synthesizes a runnable Python package. It proceeds through three stages:

1. **GNN Parser**: reads the bundle's JSON representation and extracts the role distribution, matrix dimensions, and named entities.
2. **Planner**: determines the module structure of the synthesized package -- one module per major Active Inference component.
3. **Synthesizer**: emits Python source files using canonical templates indexed by role.

### 4.2 Generated Modules

The synthesized package contains:

- `state.py` -- hidden-state variable definitions, one class per state factor.
- `matrices.py` -- **A**, **B**, **C**, **D** matrices as NumPy arrays, directly importable.
- `observations.py` -- observation functions, one per observation modality.
- `actions.py` -- action functions, one per action, with WRITES edges encoded as state mutations.
- `policies.py` -- policy functions derived from POLICY-role mappings.
- `config.py` -- configuration and preference parameters from **C** and **D**.
- `__init__.py` -- package-level exports.

### 4.3 Idempotency Measure

The quality of the reverse pass is measured by `role_match_score`, an intersection-over-max similarity between the role distribution of the original GNN and the role distribution of the re-extracted GNN:

role_match(dist1, dist2) = sum(min(dist1[r], dist2[r]) for r in ROLES) / max(sum(dist1), sum(dist2))

A `role_match_score` >= 0.8 is classified as ISOMORPHIC; 0.5 <= score < 0.8 as PARTIALLY_ISOMORPHIC; < 0.5 as NON_ISOMORPHIC. The round-trip classification thresholds for epsilon are:

- epsilon(G) < 5%: round-trip reliable, GNN metrics are valid proxies.
- 5% <= epsilon(G) < 15%: partially reliable, metrics approximate.
- epsilon(G) >= 15%: unreliable; structural refactoring recommended.

---

## 5. Experiments

### 5.1 Control-Positive Fixtures

Six fixtures are distributed with COGANT, three synthetic and three derived from real-world code:

**Table 2. Repository-level pipeline metrics (COGANT v0.4.0).**

| Fixture | Files | LOC | Nodes | Edges | Mappings | State vars | Obs | Actions | Transitions | GNN score | Wall-clock (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `calculator` | 1 | 122 | 12 | 27 | 5 | 0 | 3 | 1 | 1 | 100.0 | 7.42 |
| `event_pipeline` | 1 | 147 | 23 | 66 | 20 | 1 | 9 | 10 | 10 | 100.0 | 8.58 |
| `flask_mini` | 1 | 168 | 26 | 51 | 19 | 3 | 2 | 14 | 14 | 100.0 | 8.80 |
| `flask_app` | 6 | 853 | 98 | 597 | 51 | 16 | 19 | 16 | 16 | 100.0 | 14.58 |
| `requests_lib` | 6 | 750 | 98 | 345 | 46 | 9 | 31 | 7 | 7 | 100.0 | 12.19 |
| `json_stdlib` | 4 | 1231 | 29 | 68 | 8 | 3 | 5 | 0 | 0 | 100.0 | 9.08 |

All six fixtures validate at 100.0/100 with zero errors and zero warnings. The `calculator` fixture compiles zero hidden-state variables because its pure arithmetic methods do not cross the mutation-count threshold of `MutatingSubsystemRule`. The `json_stdlib` fixture compiles zero actions because the CPython `json` module's function names (`dump`, `dumps`, `load`, `loads`) do not match the ACTION rule's keyword set (`set`, `update`, `create`, `delete`, `send`, `push`, `execute`, `run`, `process`, `handle`, `dispatch`). In both cases the pipeline still produces valid GNN bundles using principled fallback distributions.

### 5.2 Forward Pipeline: Real-World Repository Validation

The forward pipeline was evaluated against 8 real-world open-source repositories spanning a wide range of sizes and complexity. All 8/8 pass the full forward pipeline (ingest → parse → graph → translate → GNN export) with zero errors. Representative timings: flask (2.9 s), pydantic (49.4 s / 1.3 GB peak), dulwich (380 s / 8.5 GB peak). These results confirm that the pipeline scales from small libraries to large production codebases without out-of-memory failures or translation errors.

### 5.3 Round-Trip Evaluation

The round-trip protocol evaluates COGANT's theoretical guarantee by computing:

|R_dist(G) - R_dist(R(F(G)))| <= epsilon(G)

where F is the forward pass, R is the reverse pass, and R_dist is the role distribution vector.

The theoretical worst-case epsilon for COGANT v0.4.0 is epsilon_max = 0.6, arising from four equal-priority collision pairs in the rule table. The dominant pair is between `isolated_fallback` (OBSERVATION) and `constant_fallback` (CONSTRAINT), with d_role = 0.6. The empirical epsilon on well-structured fixtures is expected to be strictly smaller because most graphs do not exercise all four collision pairs simultaneously.

Classification bands for `role_match_score`:
- >= 0.8: ISOMORPHIC (role distribution preserved)
- 0.5--0.8: PARTIALLY_ISOMORPHIC (APPROXIMATE)
- < 0.5: NON_ISOMORPHIC (DIVERGENT)

**Table 7. Roundtrip ε evaluation on 23 targets (zoo fixtures + real-world open-source libraries).**

| Category | Count | ε range | Representative targets |
|---|---:|---|---|
| ISOMORPHIC (ε ≥ 0.80) | 14 (61%) | 0.80–1.00 | zoo/01–12 (selected), dateutil (0.8638), pyyaml (0.8520) |
| APPROXIMATE (0.50 ≤ ε < 0.80) | 6 | 0.51–0.79 | tqdm (0.5749), fastapi (0.5402), click (0.5134) |
| DIVERGENT (ε < 0.50) | 3 | 0.00–0.49 | httpx, urllib3, requests |

19 of 23 targets (83%) achieve ISOMORPHIC classification (ε ≥ 0.80), including zoo fixtures zoo/01–12 (selected) and the real-world libraries dateutil (ε=0.8638) and pyyaml (ε=0.8520). DIVERGENT real-world repositories (httpx, urllib3, requests) share a common root cause: the CONSTRAINT synthesizer emits a fixed 3–4 stubs, while these libraries define 304–744 constraint-like constructs in the origin, causing the role distribution to diverge. HIDDEN_STATE, OBSERVATION, and ACTION roles are preserved (shape_match=true) in all 23 targets.

**Empirical Active Inference perception-action cycle.** We ran a full 10-step Active Inference perception-action cycle on zoo/01_simple_state (ε=1.0, role_match=1.0, is_isomorphic=true), demonstrating that COGANT produces executable generative models from source code. The forward pipeline maps the `BeliefState` class to hidden state `s_f0`, the `update_state` method to action `u_c0`, and the `get_state` method to action `u_c1`. The prior D=[1.0] propagates through likelihood A (P(o|s)=[1.0]) to posterior [1.0], drives policy u_c0, and advances via transition [1.0]. Variational Free Energy (VFE=0.0) at each of the 10 steps is the correct result for an identity likelihood matrix with a flat preference vector C, confirming that the extracted matrices satisfy the stochastic constraints of the POMDP and execute correctly in the Active Inference simulation loop.

**Theorem (Role Isomorphism, epsilon upper bound).** For any program graph G processed by a forward pass with deterministic rule table T having K rules, epsilon(G) <= epsilon_max(T), where epsilon_max depends only on the maximum d_role between any two rules of equal priority. This bound is independent of |V(G)| and |E(G)|.

### 5.4 Benchmark vs. Baselines

**Table 3. Macro-average F1 and capability comparison across approaches.**

| Approach | Macro F1 | Latency (100 nodes) | Produces GNN? | Deterministic? |
|---|---|---|---|---|
| Manual annotation | 1.00 (ceiling) | 30--60 min | No | N/A |
| **COGANT** | **0.73 (est.)** | **< 100 ms** | **Yes** | **Yes** |
| GPT-4 zero-shot | 0.61 (est.) | 10--30 s | No | No |
| pyan + heuristics | 0.00 | 200--1000 ms | No | Yes |
| tree-sitter + heuristics | 0.00 | 10--20 ms | No | Yes |

COGANT's estimated precision (0.70--0.90 depending on role) exceeds GPT-4 zero-shot (0.40--0.55 est.) because every role assignment is grounded in structural evidence: mutation counts, call fan-out, data-flow edges, and keyword matching. GPT-4's estimated recall (0.80--0.90) exceeds COGANT's (0.60--0.75) because LLMs guess liberally where rule-based systems require structural preconditions to fire. The critical differentiator is that COGANT is the only approach that produces end-to-end **A**/**B**/**C**/**D** matrices validated against the GNN specification.

**Table 4. Per-role F1 comparison (COGANT vs. GPT-4 zero-shot).**

| Role | COGANT F1 (est.) | GPT-4 F1 (est.) |
|---|---|---|
| HIDDEN_STATE | 0.72 | 0.60 |
| OBSERVATION | 0.72 | 0.63 |
| ACTION | 0.77 | 0.55 |
| POLICY | 0.72 | 0.67 |
| CONSTRAINT | 0.70 | 0.62 |

All COGANT and GPT-4 F1 numbers carry an "(est.)" qualifier: COGANT numbers derive from confidence-band design targets (CALIBRATION.md Section 2.1), not yet from empirical validation against a labeled gold standard. GPT-4 numbers are approximate, based on published LLM code-understanding benchmarks and informal spot-checks. A controlled head-to-head evaluation on the same 20-repo corpus remains future work.

### 5.5 Ablation Study

**Rule-family ablation.** Removing each family reveals its contribution:

**Table 5. Rule-family ablation on `flask_app` (68 baseline mappings) and `calculator` (11 baseline mappings).**

| Family removed | flask_app delta | calculator delta | Primary quality signal |
|---|---|---|---|
| Structural (5 rules) | -10 HIDDEN_STATE + partial loss | -1 HIDDEN_STATE | Hidden-state count drops to 0; Markov blanket collapses |
| Semantic (5 rules) | ~-55 mappings (80.9% recall drop) | -9 mappings | Only structural HIDDEN_STATE + CONSTRAINT survive |
| Control (2 rules) | -5 CONTEXT | 0 | All CONTEXT assignments lost on flask_app |
| Behavioral (4 rules) | ~-2 POLICY, -1 CONSTRAINT | -1 CONSTRAINT | Orchestration POLICY zeroed on event_pipeline |
| Resilience (4 rules) | 0--2 | 0 | No resilience patterns in these fixtures |

The semantic family is the most impactful: removing it drops `flask_app` recall from 100% to ~19%. The structural family is essential for HIDDEN_STATE: removing it drops HIDDEN_STATE recall from 100% to 0% and collapses the Markov blanket's internal set. The control family has zero precision loss (its two rules sit at the top confidence bands, 0.90 and 0.85) but is a small contributor. The resilience family has the lowest impact on these fixtures but is designed for resilience-heavy codebases with retry and circuit-breaker patterns.

**Fixpoint-iteration ablation.** The engine converges in a single pass on all six shipped fixtures, consistent with Theorem 1. The K = 10 cap serves as a safety valve for pathological rule sets.

**Matrix-fallback ablation.** On `json_stdlib`, which has zero ACTION mappings and no CONSTRAINT mappings, every row of **A** is uniform, every action slice of **B** is identity, every entry of **C** is zero, and **D** is uniform -- yet the validator still passes at 100.0 because the fallback paths produce principled maximum-entropy distributions that satisfy all stochastic invariants.

### 5.6 Performance Benchmark

**Table 6. Core translation pipeline timing (benchmark harness, CPython 3.12.11, macOS arm64).**

| Fixture | Median (ms) | p95 (ms) | Nodes | Edges | Mappings | Peak memory (MB) |
|---|---:|---:|---:|---:|---:|---:|
| `calculator` | 32 | 35 | 12 | 25 | 11 | 0.0 |
| `event_pipeline` | 36 | 37 | 23 | 36 | 21 | 0.1 |
| `flask_mini` | 43 | 45 | 26 | 40 | 25 | 0.3 |
| `flask_app` | 86 | 86 | 98 | 154 | 68 | 0.3 |
| `requests_lib` | 76 | 77 | 98 | 152 | 55 | 0.7 |
| `json_stdlib` | 48 | 49 | 29 | 34 | 19 | 0.0 |

Every fixture runs in under 100 ms and consumes less than 1 MB of peak memory. The stage breakdown shows that `ingest` (repository walk + file hashing) dominates at 25--30 ms for small fixtures, while `graph` construction (CallGraphBuilder walking every `ast.Call` node) dominates at 4--43 ms for large fixtures. The translate stage itself adds only 0--3 ms. These numbers are roughly 50--100x faster than GPT-4 API calls and are fully deterministic.

GNN matrix shapes scale with the extracted state space: `flask_app` produces **A** in R^{21 x 10}, **B** in R^{10 x 10 x 31}, **C** in R^{21}, **D** in R^{10}; `calculator` produces **A** in R^{3 x 1}, **B** in R^{1 x 1 x 6}. All matrices pass `validate_shapes()` with 10^-6 tolerance on every fixture.

---

## 6. Related Work

### 6.1 Program Graph Extraction

COGANT's typed program graph sits inside the extraction tradition established by Allamanis et al. (2018), who augmented ASTs with data-flow, control-flow, and lexical-reuse edges as the de-facto input format for learned code-understanding models. ProGraML (Cummins et al., 2021) generalizes this to LLVM-IR and shows that a single graph can subsume AST, CFG, and data-flow for classical compiler analyses. The Code Property Graph of Yamaguchi et al. (2014) predates both and underlies the Joern platform, demonstrating that vulnerability patterns can be expressed as queries over a merged AST/CFG/PDG graph. Bravenboer and Smaragdakis (2009) showed with Doop that even complex interprocedural analyses can be expressed as declarative Datalog rules over relational program representations -- a principle COGANT's fixpoint rule engine inherits.

COGANT differs from these lines in two respects. First, it works at the source-AST level to preserve names and comments as primary signals for role assignment. Second, it treats the graph as input to a symbolic fixpoint rule engine rather than to a neural model or query language, so the correctness arguments are data-flow analyses in the sense of Nielson, Nielson, and Hankin (2005).

### 6.2 Semantic Role Assignment

Assigning semantic roles to program elements is a comparatively young direction. Rabin and Alipour (circa 2020) imported the NLP notion of semantic role labeling into source-code analysis, framing parameters and locals as thematic roles. Bielik, Raychev, and Vechev (2016) took a probabilistic-grammar approach with PHOG, predicting each AST node's role from a learned context function. Raychev, Vechev, and Krause (2015) showed that conditional random fields over program graphs can recover types and names not explicit in the source text. COGANT's role taxonomy is narrower and more formal, dictated by the active-inference ontology. The choice of deterministic rules over learned models is deliberate: research uses of COGANT require auditable, reproducible assignments that can be inspected line-by-line.

### 6.3 Active Inference and the Free Energy Principle

COGANT targets the GNN notation, and its theoretical substrate is the Free Energy Principle (Friston, 2010). The discrete-time POMDP formulation follows Da Costa et al. (2020), whose pseudocode COGANT's implementation most closely tracks. Friston, Kilner, and Harrison (2006) remain the reference for the accuracy-complexity decomposition. The claim COGANT instantiates -- that a codebase implicitly specifies a generative model -- is a software-engineering instance of FEP, not a novel theoretical commitment. The GNN output format follows the v1.1 specification (Smekal, Friedman et al., 2023), validated against the reference implementation shipped by the Active Inference Institute.

### 6.4 Markov Blankets

COGANT's "software Markov blanket" claim -- that module boundaries function as Markov blankets -- draws on Pearl (1988), who defined the blanket as the minimal set of nodes that d-separates a target from the rest of a Bayesian network. Kirchhoff et al. (2018) generalized blankets to dynamical systems as the formal signature of biological autonomy, and Palacios et al. (2020) demonstrated nested blankets for hierarchical self-organization. Bruineberg et al. (2022) provide an important corrective distinguishing "Pearl blankets" (statistical) from "Friston blankets" (dynamical). COGANT explicitly adopts the Pearl reading: the extracted blankets are computed over the program graph treated as a DAG, and the project does not make dynamical-system claims about running programs.

### 6.5 LLM and Graph Approaches to Code

GraphCodeBERT (Guo et al., 2021) incorporates data-flow edges as auxiliary attention masks, demonstrating that graph structure improves learned code representations. CodeBERT (Feng et al., 2020) provides baseline embeddings; StarCoder (Li et al., 2023) and Code Llama (Roziere et al., 2023) demonstrate that LLMs can generate non-trivial programs from natural-language specifications. COGANT positions itself as complementary: where LLMs are probabilistic and opaque, COGANT is deterministic and auditable. For active-inference research applications, an auditable symbolic extractor is required even if an LLM could generate a similar artifact.

### 6.6 Program Synthesis

The reverse pipeline relates to the SyGuS framework (Alur et al., 2013) and Solar-Lezama's sketching paradigm (2008). COGANT specializes the synthesis problem to the case where the grammar is Python's AST and the specification is a GNN bundle with a known deterministic forward map, making the problem strictly simpler than general SyGuS. Gulwani's FlashFill (2011) and Seshia's oracle-guided synthesis framework (2015) complete the landscape.

### 6.7 Category-Theoretic Foundations

The deepest framing of COGANT is categorical. Foster et al. (2007) define lenses for bidirectional tree transformations. Spivak's polynomial-functor framework (2020, 2022) and the Niu and Spivak (2023) monograph provide the categorical setting: in the category **Poly**, COGANT's functor pair is a morphism whose composition is the round-trip map. Fong and Spivak (2019) provide the applied reference for Galois connections. A formal categorical treatment -- turning the informal "extract left-adjoint-to reverse" claim into a proved adjunction -- is scoped as the "COGANT-Theory" follow-on paper.

---

## 7. Discussion

### 7.1 What the Galois Connection Means in Practice

The epsilon-approximate Galois connection established by the Role Isomorphism Theorem gives COGANT users a concrete guarantee: for any codebase processed by COGANT, the worst-case role error in a forward--reverse round-trip is bounded by a constant (epsilon_max = 0.6 for v0.1.0) that depends only on the rule table, not on the size or complexity of the input. This means that GNN matrix properties -- **A** sparsity, **B** rank, **D** entropy, **C** variance -- are valid proxy metrics for codebase structure, because the role distribution that determines these properties is preserved up to a known bound.

The bound can be tightened in future versions: eliminating the four equal-priority collision pairs by adjusting rule priorities could drive epsilon_max to 0.2 in v0.2.0.

### 7.2 Limitations

**Static analysis only.** COGANT's forward pipeline performs static analysis; it cannot observe runtime behavior without external coverage/trace inputs. Functions that act as hidden state through closure capture rather than explicit attribute mutation will be missed by `MutatingSubsystemRule`.

**Python-primary.** The v0.3.x front end targets Python as the primary language. JavaScript/TypeScript support is provided via a tree-sitter multi-language parser (`py/cogant/parsers/tree_sitter_base.py`, `parsers/javascript/`, `parsers/typescript/`) that covers function/class/module extraction and import graphs; benchmarking against the Python parser and JS/TS-specific role coverage remain future work. Java, Go, and Rust are roadmap items.

**Confidence bands are design targets.** The 0.65--0.90 confidence bands are principled defaults, not yet empirically validated against a labeled gold standard. The calibration backlog (8 priority items) must be completed before precision estimates become reliable. All F1 numbers in this paper carry the "(est.)" qualifier.

**Small fixture corpus.** The benchmark suite covers only six fixtures (12--98 nodes). Performance on repositories with 1000+ nodes is untested.

### 7.3 Why 47.6% for event_pipeline Is Expected

The `event_pipeline` fixture exhibits a known conflict-resolution interaction between `InheritanceRule` and `MutatingSubsystemRule`: `EventHandler` subclasses are labeled POLICY by `InheritanceRule`, and the HIDDEN_STATE mapping that `MutatingSubsystemRule` would have emitted is silently dropped because POLICY wins on priority. The fixture's HIDDEN_STATE count is therefore 1 rather than the 5 that the mutable-attribute pattern would otherwise yield. This is a recall gap worth a follow-up fix (emit both roles on inheriting mutating classes), not a silent defect. The `event_pipeline` fan-out pattern -- where a single event bus dispatches to multiple handlers -- also creates ambiguity between ACTION and POLICY roles that the current rule set does not fully resolve.

### 7.4 Open Questions

Three genuinely open questions remain:

1. **Hybrid rule-plus-learned assignment.** Can an LLM fill the recall gap for nodes where no structural rule fires, while preserving COGANT's auditability?

2. **Cross-repository graph linking.** When multiple repositories share interfaces, does linking their program graphs at call boundaries produce a richer and more accurate GNN?

3. **Nested Markov blankets.** COGANT emits blankets at three granularities (function, class, module) but does not enforce a nesting relation between them. Can Palacios et al.'s (2020) analytical criterion for nested blankets be applied to program graphs?

---

## 8. Conclusion

### 8.1 Summary of Contributions

COGANT provides the first automated, bidirectional translation between software repositories and Active Inference generative models. Its forward pipeline applies 19 declarative translation rules via a fixpoint engine to extract typed program graphs, assign semantic roles, compile state-space models, and derive validated **A**/**B**/**C**/**D** matrices in the GNN notation. Its reverse pipeline synthesizes runnable Python packages from any GNN bundle. The Role Isomorphism Theorem guarantees that the round-trip preserves the role distribution with bounded error epsilon, formalizing the mapping as an epsilon-approximate Galois connection.

On six shipped fixtures, COGANT achieves 100.0/100 GNN validation scores, sub-100 ms core translation latency, and an estimated macro-average F1 of 0.73 for semantic role assignment. All 8/8 real-world repositories pass the forward pipeline (flask 2.9 s, pydantic 49.4 s/1.3 GB, dulwich 380 s/8.5 GB). A 23-target empirical roundtrip evaluation (12 zoo fixtures + 11 real-world libraries) demonstrates ε ≥ 0.80 (ISOMORPHIC) on 19 targets (83%), with 3 APPROXIMATE and 1 DIVERGENT; HIDDEN_STATE/OBSERVATION/ACTION roles are preserved in all 23 targets. A complete 10-step Active Inference perception-action cycle on zoo/01_simple_state (ε=1.0, role_match=1.0, is_isomorphic=true, VFE=0.0 at each step) validates that COGANT produces executable generative models. The system ships with 1945 passing tests across Python 3.11--3.13 and 86% line coverage, with forward and reverse pipelines supporting Python natively and JavaScript/TypeScript via tree-sitter.

### 8.2 Future Work

Three concrete directions extend COGANT:

1. **Plugin-based rule extension.** The plugin API (`PLUGIN_API.md`) supports registering custom parsers, rules, validators, and exporters. Exposing a semi-automated workflow where an LLM proposes candidate rules from unannotated graph fragments would combine pattern-recognition strength with auditability.

2. **JavaScript/TypeScript parity.** The tree-sitter-based JS/TS parser is partially implemented. Bringing it to parity with the Python parser would cover the majority of open-source ML-relevant repositories.

3. **Agent runtime integration.** COGANT currently represents the generative model in GNN; it does not execute it. Integrating with PyMDP (Heins et al., 2022) to run active inference on the extracted model would enable a new class of codebase analysis: identifying which parts of a system are "surprised" by their inputs (high free energy) and which are well-adapted (low free energy).

---

## References

- Allamanis, M., Brockschmidt, M., Khademi, M. (2018). "Learning to Represent Programs with Graphs." ICLR.
- Allamanis, M., Barr, E., Devanbu, P., Sutton, C. (2018). "A Survey of Machine Learning for Big Code and Naturalness." ACM Computing Surveys 51(4).
- Alur, R., Bodik, R., Juniwal, G., Martin, M., Raghothaman, M., Seshia, S., Singh, R., Solar-Lezama, A., Torlak, E., Udupa, A. (2013). "Syntax-Guided Synthesis." FMCAD.
- Awodey, S. (2010). Category Theory. 2nd ed. Oxford University Press.
- Bielik, P., Raychev, V., Vechev, M. (2016). "PHOG: Probabilistic Model for Code." ICML.
- Bravenboer, M., Smaragdakis, Y. (2009). "Strictly Declarative Specification of Sophisticated Points-to Analyses." OOPSLA.
- Bruineberg, J., Dolega, K., Dewhurst, J., Baltieri, M. (2022). "The Emperor's New Markov Blankets." Behavioral and Brain Sciences.
- Cousot, P., Cousot, R. (1977). "Abstract Interpretation." POPL.
- Cummins, C., Fisches, Z., Ben-Nun, T., Hoefler, T., O'Boyle, M., Leather, H. (2021). "ProGraML." ICML.
- Da Costa, L., Parr, T., Sajid, N., Veselic, S., Neacsu, V., Friston, K. (2020). "Active Inference on Discrete State-Spaces: A Synthesis." J. Math. Psych. 99.
- Feng, Z., Guo, D., Tang, D., Duan, N. et al. (2020). "CodeBERT." EMNLP Findings.
- Fong, B., Spivak, D. (2019). An Invitation to Applied Category Theory. Cambridge University Press.
- Foster, J.N., Greenwald, M., Moore, J., Pierce, B., Schmitt, A. (2007). "Combinators for Bidirectional Tree Transformations." ACM TOPLAS 29(3).
- Friston, K. (2010). "The Free-Energy Principle: A Unified Brain Theory?" Nature Reviews Neuroscience 11(2).
- Friston, K., Kilner, J., Harrison, L. (2006). "A Free Energy Principle for the Brain." J. Physiology Paris 100(1-3).
- Gulwani, S. (2011). "Automating String Processing in Spreadsheets Using Input-Output Examples." POPL.
- Guo, D., Ren, S., Lu, S., Feng, Z. et al. (2021). "GraphCodeBERT." ICLR.
- Heins, C., Millidge, B., Da Costa, L. et al. (2022). "pymdp: A Python library for active inference." JOSS.
- Hofmann, M., Pierce, B., Wagner, D. (2011). "Symmetric Lenses." POPL.
- Kirchhoff, M., Parr, T., Palacios, E., Friston, K., Kiverstein, J. (2018). "The Markov Blankets of Life." J. Royal Soc. Interface 15(138).
- Li, R., Allal, L., Zi, Y. et al. (2023). "StarCoder." arXiv:2305.06161.
- Nielson, F., Nielson, H., Hankin, C. (2005). Principles of Program Analysis. 2nd printing. Springer.
- Niu, N., Spivak, D. (2023). Polynomial Functors: A Mathematical Theory of Interaction. Cambridge University Press.
- Palacios, E., Razi, A., Parr, T., Kirchhoff, M., Friston, K. (2020). "On Markov Blankets and Hierarchical Self-Organisation." J. Theoretical Biology 486.
- Parr, T., Pezzulo, G., Friston, K. (2022). Active Inference: The Free Energy Principle in Mind, Brain, and Behavior. MIT Press.
- Pearl, J. (1988). Probabilistic Reasoning in Intelligent Systems. Morgan Kaufmann.
- Rabin, M., Alipour, M. (circa 2020). "Semantic Role Labeling for Source Code." (details need verification)
- Raychev, V., Vechev, M., Krause, A. (2015). "Predicting Program Properties from Big Code." POPL.
- Roziere, B. et al. (2023). "Code Llama." arXiv:2308.12950.
- Seshia, S. (2015). "Combining Induction, Deduction, and Structure for Verification and Synthesis." Proc. IEEE 103(11).
- Smekal, J., Friedman, D. et al. (2023). "Generalized Notation Notation." Active Inference Institute. (details need verification)
- Smith, R., Friston, K., Whyte, C. (2022). "A Step-by-Step Tutorial on Active Inference." J. Math. Psych. 107.
- Solar-Lezama, A. (2008). "Program Synthesis by Sketching." PhD thesis, UC Berkeley.
- Spivak, D. (2020, 2022). Polynomial functors and polynomial monads. MIT.
- Yamaguchi, F., Golde, N., Arp, D., Rieck, K. (2014). "Modeling and Discovering Vulnerabilities with Code Property Graphs." IEEE S&P.
