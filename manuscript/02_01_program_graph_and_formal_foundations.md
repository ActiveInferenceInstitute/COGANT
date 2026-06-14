# Program graph and formal foundations {#sec:02-01-program-graph-and-formal-foundations}

**Terminology.** Throughout @sec:02-01-program-graph-and-formal-foundations, **GNN** means **Generalized Notation Notation** (Active Inference Institute bundle format), not graph neural networks; see @sec:01-introduction.

## Program graph {#sec:02-01-program-graph}

Let $G = (V, E)$ denote a directed graph whose vertices $V$ represent program entities and whose edges $E$ represent relationships. COGANT assigns each node a **kind** (for example function, variable, type) and a **semantic role** (for example definition versus use). Each node and edge may carry:

- A **stable identifier** for persistence across runs when hashing allows.
- **Type strings** and attributes recovered from the front end.
- A **confidence** score in $[0,1]$ and **provenance** metadata (source code, type system, control flow, heuristic, external tool).

This follows the same philosophical line as code property graphs that fuse AST, control flow, and data flow into one analyzable structure [@yamaguchi2014modeling], but orients the representation toward **Generalized Notation Notation (GNN) export** and, optionally, tensorized views of the same graph: node kinds and roles map to discrete indices in both forms, and optional embeddings can augment features as described in `../cogant/docs/export/README.md`.

### Structural equivalence

Two program graphs $G_1 = (V_1, E_1)$ and $G_2 = (V_2, E_2)$ are usefully compared via typed graph isomorphism: a bijection $\phi : V_1 \to V_2$ preserving edge structure and relevant labels supports deduplication and cross-repository linking when interfaces align.

$$
(u, v) \in E_1 \iff (\phi(u), \phi(v)) \in E_2
$$ {#eq:typed-iso}

@eq:typed-iso formalizes the structural invariant we check during deduplication and cross-repository linking: a candidate bijection $\phi$ is accepted only when every edge in $G_1$ has a corresponding edge between the images of its endpoints in $G_2$ (and vice versa), so that label-preserving matches strictly preserve the adjacency structure of both program graphs.

## Formal definitions {#sec:02-01-formal-definitions}

This subsection makes the objects manipulated by the pipeline mathematically explicit. The definitions are stated for the shipped v{{VERSION}} engine; where the AST front end targets a structural subset of the full edge taxonomy, the scope is noted with a forward reference to @sec:06-experimental-setup. The Notation Supplement (`98_notation_supplement.md`, Groups G.1–G.9) indexes the manuscript's symbols, equation labels, scoped formal claims, and acronyms.

The formal choices below are intentionally conservative. They borrow the finite-graph and monotone-fixpoint vocabulary of classical data-flow analysis and fixed-point theory [@tarski1955lattice; @kildall1973unified; @cousot1977abstract], but COGANT does not claim the precision of a whole-program compiler analysis: the graph is the artifact the implemented front ends can recover, and the semantic mappings are reviewable assertions over that artifact.

### Definition: Program graph {#sec:def-program-graph}

A **program graph** is a tuple $G = (V, E, \lambda_V, \lambda_E, \tau)$ where

- $V$ is a finite set of program nodes (modules, classes, methods, functions, and --- on languages where the front end emits them --- variables and control-flow sites);
- $E \subseteq V \times V \times K$ is a finite set of typed directed edges drawn from the edge-kind alphabet $K \supseteq \{\text{READS}, \text{WRITES}, \text{CALLS}, \text{CONTAINS}, \text{INHERITS}, \text{IMPORTS}, \text{OBSERVES}, \text{MUTATES}, \text{DEPENDS\_ON}\}$;
- $\lambda_V : V \to \mathcal{N}$ labels each node with a node kind $\mathcal{N} \supseteq \{\text{MODULE}, \text{CLASS}, \text{METHOD}, \text{FUNCTION}, \text{CONFIGURATION}, \ldots\}$;
- $\lambda_E : E \to K$ is the (trivial) projection onto the edge kind;
- $\tau : V \to (T \cup \{\bot\})$ maps each node to a type annotation recovered from the front end or to $\bot$ when no annotation is available.

The shipped Python front end populates the kinds $\{\text{MODULE}, \text{CLASS}, \text{METHOD}, \text{FUNCTION}\}$ and the edge kinds $\{\text{CALLS}, \text{CONTAINS}, \text{READS}, \text{WRITES}, \text{IMPORTS}, \text{INHERITS}\}$; the remaining kinds in $\mathcal{N}$ and $K$ are declared in `cogant.schemas.core` but currently emitted only when other parsers or dynamic enrichment stages fire. The empirical distribution on the six packaged fixtures is recorded in @tbl:repo-pipeline-metrics and @tbl:fixture-graph-metrics in @sec:06-experimental-setup.

**Mapping kinds vs graph roles.** Translation rules emit `SemanticMapping` records whose `kind` field uses `MappingKind` from `cogant.schemas.semantic`. The seven names highlighted in the abstract are the Active Inference subset of that enum; additional `MappingKind` members (`DATA_FLOW`, `CONTROL_FLOW`, `ORCHESTRATION`, …) cover non-AI structural patterns. Separately, `SemanticRole` in `cogant.schemas.semantic_mapping` enumerates a broader set of graph-level role labels (for example `PARAMETER`, `CONFIGURATION`); `METRICS.yaml` `ir_schema.active_inf_role_count` tracks the seven-name AI subset verified against `MappingKind`.

### Definition: Evidence-labelled assertion {#sec:def-evidence-labelled-assertion}

An extracted assertion is a tuple $\xi = (x, \kappa_\xi, c_\xi, \mathcal{P}_\xi)$ where $x$ is the node, edge, or finite fragment being asserted about; $\kappa_\xi$ is the mapping kind, validation predicate, or structural property being asserted; $c_\xi \in [0,1]$ is the confidence score computed by @eq:confidence-core; and $\mathcal{P}_\xi$ is a finite provenance set containing rule names, parser outputs, trace/coverage sources, reviewer markers, or schema-validation records. For assertions over the same target and assertion kind, define the evidence preorder

$$
\xi_1 \preceq_e \xi_2
\quad\Longleftrightarrow\quad
c_{\xi_1} \leq c_{\xi_2}
\;\land\;
\mathcal{P}_{\xi_1} \subseteq \mathcal{P}_{\xi_2}.
$$ {#eq:evidence-preorder}

This order is operational rather than semantic: $\xi_2$ is better supported by recorded COGANT evidence than $\xi_1$, but the relation is not a probability that the asserted program meaning is true. The distinction parallels the database-provenance split between **why** provenance (which source facts contributed to an output) and **where** provenance (which source locations supplied copied values) [@buneman2001whyWhere]: COGANT records why a mapping fired and where its supporting fragment lives, while leaving semantic truth to review, tests, or downstream formal analysis. This lets the claim ledger and PROV-aligned artifact records [@moreau2013prov] explain why an assertion was emitted without turning structural validation into a correctness proof.

The algebraic scope is deliberately smaller than provenance semiring semantics [@green2007provenance]. COGANT does not define provenance-polynomial addition/multiplication or claim semiring universality; the formal results below rely only on finite-set union for accumulating provenance records, monotone growth of mapping identifiers before conflict resolution, and deterministic priority/score pruning after the fixpoint. In particular, no theorem in this manuscript depends on semiring distributivity or completeness.

### Definition: Translation rule {#sec:def-translation-rule}

A **translation rule** is a quadruple $r = (\varphi_r, \kappa_r, w_r, p_r)$ where

- $\varphi_r : \mathcal{G} \to 2^{\mathcal{F}}$ is a computable predicate that, given a program graph $G \in \mathcal{G}$, returns a (possibly empty) set of matched fragments $\mathcal{F}$ --- each fragment a finite tuple of node ids and optional edge ids;
- $\kappa_r \in \mathcal{K}_M$ is the mapping kind the rule assigns on success, drawn from the mapping-kind alphabet $\mathcal{K}_M = \{\text{HIDDEN\_STATE}, \text{OBSERVATION}, \text{ACTION}, \text{POLICY}, \text{CONSTRAINT}, \text{PREFERENCE}, \text{CONTEXT}, \text{DATA\_FLOW}, \text{ERROR\_HANDLING}, \text{CIRCUIT\_BREAKER}, \text{ORCHESTRATION}\}$;
- $w_r \in (0, 1]$ is the base confidence weight attached to mappings produced by $r$;
- $p_r \in \mathbb{Z}$ is the rule priority consulted during conflict resolution (@sec:alg-conflict-resolution).

Concretely, each `TranslationRule` subclass in `../cogant/py/cogant/translate/rules/` exposes $\varphi_r$ as the `matches(graph, query)` method, encodes $\kappa_r$ in the `mapping_kind` property, embeds $w_r$ in the `confidence_score` field of the returned `SemanticMapping`, and exposes $p_r$ through the `priority` property. The {{TRANSLATION_RULES}} shipped rules span five families: five structural rules (`ReadOnlyInput`, `MutatingSubsystem`, `Inheritance`, `Containment`, `DataPipeline`), five semantic rules (`Observation`, `Action`, `Policy`, `Preference`, `Context`), three control rules (`Config`, `FeatureFlag`, `Parameter`), four behavioural rules (`Orchestrator`, `TestAssertion`, `EventBus`, `StateMachine`), and five resilience rules (`RetryPattern`, `ErrorBoundary`, `SingletonAccess`, `CircuitBreaker`, `RateLimiter`). The later additions `Parameter`, `StateMachine`, and `RateLimiter` capture tunable hyperparameters, finite-state-machine workflows, and rate-limiting policies that the original rule set did not cover.

### Definition: Fixpoint semantics {#sec:def-fixpoint-semantics}

Let $\mathcal{M}$ be the (finite) set of all possible semantic mappings that any finite composition of rules in $R$ could emit on a fixed graph $G$. Define the rule-application operator $F_{G,R} : 2^{\mathcal{M}} \to 2^{\mathcal{M}}$ by

$$
F_{G,R}(S) \;=\; S \,\cup\, \bigl\{\, r.\text{apply}(G, f) \,\bigm|\, r \in R,\ f \in \varphi_r(G),\ r.\text{apply}(G, f) \neq \bot \,\bigr\}.
$$ {#eq:fixpoint-operator}

The **translation** of $G$ under $R$ is the least fixpoint

$$
T^{*}(G) \;=\; \bigsqcup_{k \geq 0} F_{G,R}^{k}(\emptyset) \;=\; \lim_{k \to \infty} F_{G,R}^{k}(\emptyset),
$$ {#eq:least-fixpoint}

computed iteratively by `TranslationEngine.translate()` and then post-processed by `_resolve_conflicts()` (@sec:alg-conflict-resolution). The post-processing step applies an anti-monotone pruning to the fixpoint, and is therefore specified outside of $F_{G,R}$ rather than folded into it.

### Definition: Markov blanket partition {#sec:def-markov-blanket-partition}

Given a program graph $G = (V, E, \lambda_V, \lambda_E, \tau)$ and a **seed set** $S \subseteq V$ selected by one of the five strategies in `MarkovBlanketExtractor` (`explicit`, `module`, `kind`, `auto`, `mapping_kind`), the **Markov blanket partition** $\Pi_{G, S} : V \to \{\mu, s, a, \eta\}$ is an engineering adaptation of graphical-model Markov blankets [@pearl1988probabilistic] and the active-inference blanket vocabulary [@kirchhoff2018markov], with the critique literature treated as a scope constraint rather than as settled metaphysics [@biehl2021technical; @bruineberg2022emperor]. Here "Markov blanket" names the role vocabulary and interface cut; it does **not** assert a Bayesian network over program nodes, conditional-independence separation, or a causal model of the source program. It is defined on the undirected projection of $G$ as follows. Let $N^{\text{in}}(v) = \{u : (u, v, k) \in E\}$ and $N^{\text{out}}(v) = \{u : (v, u, k) \in E\}$. Then

$$
\begin{aligned}
\Pi_{G,S}(v) \;=\;
\begin{cases}
\mu & \text{if } v \in S \text{ and } (N^{\text{in}}(v) \cup N^{\text{out}}(v)) \subseteq S, \\
a   & \text{if } v \in S \text{ and } N^{\text{out}}(v) \setminus S \neq \emptyset, \\
s   & \text{if } v \in S \text{ and } N^{\text{out}}(v) \subseteq S \text{ and } N^{\text{in}}(v) \setminus S \neq \emptyset, \\
\eta & \text{if } v \notin S.
\end{cases}
\end{aligned}
$$ {#eq:markov-partition}

The four-way case split is realised verbatim by `partition_by_seeds()` in `../cogant/py/cogant/markov/blanket.py`: the function precomputes the in/out adjacency of every node in $O(|V| + |E|)$ time via `_bidirectional_adjacency()`, then walks $V$ once and assigns each node to exactly one of $\mu$, $s$, $a$, $\eta$. Bidirectional boundary nodes (those with both external in- and out-neighbours) are assigned to $a$ by convention, and are additionally tagged with a `bidirectional` metadata flag so that downstream consumers can recover the distinction.

### Definition: A/B/C/D matrices {#sec:def-abcd-matrices}

Given a translation $T^{*}(G)$ and a compiled state-space $(\mathbf{V}, \mathbf{O}, \mathbf{A})$ of hidden-state variables, observation modalities, and actions, the **generative-model matrices** of COGANT are

$$
\begin{aligned}
A &\in \mathbb{R}^{|\mathbf{O}| \times |\mathbf{V}|},    &A_{ij} &= P(o_i \mid s_j), & \sum_i A_{ij} &= 1, \\
B &\in \mathbb{R}^{|\mathbf{V}| \times |\mathbf{V}| \times |\mathbf{A}|}, & B_{i j k} &= P(s'_i \mid s_j, a_k), & \sum_i B_{ijk} &= 1, \\
C &\in \mathbb{R}^{|\mathbf{O}|}, & C_i &= \log \tilde{P}(o_i), & \\
D &\in \mathbb{R}^{|\mathbf{V}|}, & D_j &= P(s_j \mid t = 0), & \sum_j D_j &= 1.
\end{aligned}
$$ {#eq:matrices-defn}

$A$ is derived from $\{\text{READS}, \text{OBSERVES}, \text{DEPENDS\_ON}\}$ edges between observation and hidden-state nodes; $B$ is derived from $\{\text{WRITES}, \text{MUTATES}\}$ edges from action to hidden-state nodes, with an identity degraded-output default when an action writes nothing; $C$ is derived from the signed confidence scores of CONSTRAINT/PREFERENCE mappings adjacent to each observation; and $D$ is derived from CONFIGURATION-neighbour bias on hidden-state variables or uses a uniform prior. The derivation is performed by `GNNMatrices` in `../cogant/py/cogant/gnn/matrices.py` and uses no numerical dependencies beyond the Python standard library. Columns of $A$, columns of each $B$ action slice, and the vector $D$ are normalised to valid probability distributions using the high-direct / low-indirect mass defaults $(0.9, 0.1)$ defined as the module-level `_DEFAULT_DIRECT_MASS` / `_DEFAULT_INDIRECT_MASS` constants in `matrices.py`; the $C$ vector is a log-preference and is not normalised. This convention matches $A_{ij}=P(o_i\mid s_j)$: for each fixed hidden state $s_j$, the observation distribution sums over $i$.

### Scoped Formal Claims

### Proposition: Fixpoint termination {#sec:thm-fixpoint-termination}

Let $G = (V, E, \lambda_V, \lambda_E, \tau)$ be a finite program graph with $|V| = n$, let $R$ be a finite rule set with $|R| = k$, and let $F_{G,R}$ be the rule-application operator of @sec:def-fixpoint-semantics. Then the Kleene chain

$$
\emptyset \;\subseteq\; F_{G,R}(\emptyset) \;\subseteq\; F_{G,R}^{2}(\emptyset) \;\subseteq\; \cdots
$$ {#eq:kleene-chain}

stabilises in at most $|\mathcal{M}|$ iterations, where $|\mathcal{M}| \leq n \cdot |\mathcal{K}_M|$ is an upper bound on the number of distinct mapping ids any rule set can produce on $G$. In particular, the shipped engine with its default cap $K = 10$ converges on every fixture in $\{$`calculator`, `event_pipeline`, `flask_mini`, `flask_app`, `requests_lib`, `json_stdlib`$\}$ within the cap.

*Proof sketch.* Each application step either adds at least one new mapping id to the accumulating set $S$ or leaves $S$ unchanged; the engine's idempotence guard in `TranslationEngine.translate` (skip when `mapping.id` is already in `self.mappings`) enforces the monotone-plus-bounded invariant. Because $F_{G,R}$ is monotone on the finite lattice $(2^{\mathcal{M}}, \subseteq)$ and bounded above by $\mathcal{M}$, the Knaster--Tarski fixed-point theorem [@tarski1955lattice] implies fixed points exist and the Kleene chain here is an ascending chain in a finite lattice. It therefore stabilises in at most $|\mathcal{M}|$ steps. The stabilisation point is, by construction, the least fixpoint of $F_{G,R}$ above $\emptyset$. The worst-case bound $n \cdot |\mathcal{K}_M|$ is a conservative implementation bound: stable mapping IDs encode the target node/fragment and mapping kind, and any duplicate ID is ignored before conflict resolution. The packaged fixtures are an empirical sanity check rather than a proof of rule-family disjointness: the engine logs a final zero-new-mapping pass and @tbl:repo-pipeline-metrics / @tbl:state-space-compilation in @sec:06-03-performance-and-fixture-metrics report the resulting mapping counts and validation status. $\blacksquare$

### Implementation invariant: Markov blanket partition totality {#sec:thm-markov-blanket-completeness}

For any program graph $G = (V, E, \lambda_V, \lambda_E, \tau)$ with $V \neq \emptyset$ and any seed set $S \subseteq V$, the seed-induced structural partition $\Pi_{G, S}$ of @sec:def-markov-blanket-partition is **total** (every $v \in V$ receives exactly one role) and **mutually exclusive** (no $v$ is assigned two roles). This invariant is about the implemented partitioner, not about probabilistic Markov-blanket semantics.

*Proof sketch.* Totality: the case split in @eq:markov-partition exhausts the boolean product $(v \in S) \times (N^{\text{out}}(v) \setminus S = \emptyset) \times (N^{\text{in}}(v) \setminus S = \emptyset)$. If $v \notin S$ the fourth case applies. If $v \in S$ there are three subcases depending on whether $v$ has external out-neighbours, external in-neighbours only, or no external neighbours at all; the engine resolves the "both external in and external out" subcase to `ACTIVE` by convention, matching the bidirectional case branch in `partition_by_seeds()` in `cogant.markov.blanket`. Every $v \in V$ therefore matches exactly one branch, so $\Pi$ is a total function. Mutual exclusivity: the branches are pairwise disjoint because they condition on mutually exclusive predicates on $(v \in S, N^{\text{in}}(v) \setminus S, N^{\text{out}}(v) \setminus S)$. The implementation materialises the four role sets `internal`, `sensory`, `active`, `external` as disjoint Python sets and writes into exactly one on each iteration of the main loop, so the in-memory invariant matches the mathematical one. $\blacksquare$

### Proposition: Matrix validity {#sec:thm-matrix-validity}

If $|\mathbf{O}| \geq 1$, $|\mathbf{V}| \geq 1$, and $|\mathbf{A}| \geq 1$, then the matrices $(A, B, C, D)$ produced by `GNNMatrices.compute_A/B/C/D` satisfy the stochastic conditions of @sec:def-abcd-matrices within a numerical tolerance of $10^{-6}$.

*Proof sketch.* Columns of $A$ are produced in @eq:matrices-defn with explicit normalisation in `GNNMatrices.compute_A`: for each hidden-state column, the implementation divides by the column sum when it exceeds $\varepsilon = 10^{-9}$ and returns a uniform observation distribution otherwise. Columns of each action slice $B[:,:,k]$ are produced by the same simplex-normalisation helper with an identity default ensuring the resulting column is never all-zero. The prior $D$ is built as a weighted vector of confidence scores and passed through `_normalize_vector()`, again with a uniform default when all weights are below $\varepsilon$. The implementation therefore establishes the sum-to-one invariant by construction; `GNNMatrices.validate_shapes` checks A/B/D stochasticity for computed matrices, and `GNNValidator.validate_matrices()` gates exported bundles with the same tolerance before the package can validate. All six packaged fixtures pass `GNNValidator` with zero errors (@tbl:repo-pipeline-metrics), which is fixture-level implementation evidence rather than an independent semantic proof. The $C$ vector is a log-preference and is exempt from the sum-to-one requirement. $\blacksquare$
