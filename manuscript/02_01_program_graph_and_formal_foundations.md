# Program graph and formal foundations {#sec:02-01-program-graph-and-formal-foundations}

**Terminology.** Throughout Section 2, **GNN** means **Generalized Notation Notation** (Active Inference Institute bundle format), not graph neural networks; see @sec:01-introduction.

## Program graph {#sec:02-01-program-graph}

Let $G = (V, E)$ denote a directed graph whose vertices $V$ represent program entities and whose edges $E$ represent relationships. COGANT assigns each node a **kind** (for example function, variable, type) and a **semantic role** (for example definition versus use). Each node and edge may carry:

- A **stable identifier** for persistence across runs when hashing allows.
- **Type strings** and attributes recovered from the front end.
- A **confidence** score in $[0,1]$ and **provenance** metadata (source code, type system, control flow, heuristic, external tool).

This follows the same philosophical line as code property graphs that fuse AST, control flow, and data flow into one analyzable structure [@yamaguchi2014modeling], but orients the representation toward **Generalized Notation Notation (GNN) export** and, optionally, tensorized views of the same graph: node kinds and roles map to discrete indices in both forms, and optional embeddings can augment features as described in `../cogant/docs/export/README.md`.

### Structural equivalence

Two program graphs $G_1 = (V_1, E_1)$ and $G_2 = (V_2, E_2)$ are usefully compared via typed graph isomorphism: a bijection $\phi : V_1 \to V_2$ preserving edge structure and relevant labels supports deduplication and cross-repository linking when interfaces align.

\begin{equation}
\label{eq:typed-iso}
(u, v) \in E_1 \iff (\phi(u), \phi(v)) \in E_2
\end{equation}

Equation \ref{eq:typed-iso} formalizes the structural invariant we check during deduplication and cross-repository linking: a candidate bijection $\phi$ is accepted only when every edge in $G_1$ has a corresponding edge between the images of its endpoints in $G_2$ (and vice versa), so that label-preserving matches strictly preserve the adjacency structure of both program graphs.

## Formal definitions {#sec:02-01-formal-definitions}

This subsection makes the objects manipulated by the pipeline mathematically explicit. The definitions are stated for the shipped v{{VERSION}} engine; where the AST front end targets a structural subset of the full edge taxonomy, the scope is noted with a forward reference to @sec:06-experimental-setup. A complete index of all symbols, equation labels, theorems, and acronyms introduced in this section and throughout the manuscript is in the Notation Supplement (`98_notation_supplement.md`, Groups G.1–G.9).

**Definition 1 (Program graph).** A **program graph** is a tuple $G = (V, E, \lambda_V, \lambda_E, \tau)$ where

- $V$ is a finite set of program nodes (modules, classes, methods, functions, and --- on languages where the front end emits them --- variables and control-flow sites);
- $E \subseteq V \times V \times K$ is a finite set of typed directed edges drawn from the edge-kind alphabet $K \supseteq \{\text{READS}, \text{WRITES}, \text{CALLS}, \text{CONTAINS}, \text{INHERITS}, \text{IMPORTS}, \text{OBSERVES}, \text{MUTATES}, \text{DEPENDS\_ON}\}$;
- $\lambda_V : V \to \mathcal{N}$ labels each node with a node kind $\mathcal{N} \supseteq \{\text{MODULE}, \text{CLASS}, \text{METHOD}, \text{FUNCTION}, \text{CONFIGURATION}, \ldots\}$;
- $\lambda_E : E \to K$ is the (trivial) projection onto the edge kind;
- $\tau : V \to (T \cup \{\bot\})$ maps each node to a type annotation recovered from the front end or to $\bot$ when no annotation is available.

The shipped Python front end populates the kinds $\{\text{MODULE}, \text{CLASS}, \text{METHOD}, \text{FUNCTION}\}$ and the edge kinds $\{\text{CALLS}, \text{CONTAINS}, \text{READS}, \text{WRITES}, \text{IMPORTS}, \text{INHERITS}\}$; the remaining kinds in $\mathcal{N}$ and $K$ are declared in `cogant.schemas.core` but currently emitted only when other parsers or dynamic enrichment stages fire. The empirical distribution on the six packaged fixtures is recorded in @tbl:repo-pipeline-metrics and @tbl:fixture-graph-metrics in @sec:06-experimental-setup.

**Mapping kinds vs graph roles.** Translation rules emit `SemanticMapping` records whose `kind` field uses `MappingKind` from `cogant.schemas.semantic`. The seven names highlighted in the abstract are the Active Inference subset of that enum; additional `MappingKind` members (`DATA_FLOW`, `CONTROL_FLOW`, `ORCHESTRATION`, …) cover non-AI structural patterns. Separately, `SemanticRole` in `cogant.schemas.semantic_mapping` enumerates a broader set of graph-level role labels (for example `PARAMETER`, `CONFIGURATION`); `METRICS.yaml` `ir_schema.active_inf_role_count` tracks the seven-name AI subset verified against `MappingKind`.

**Definition 2 (Translation rule).** A **translation rule** is a quadruple $r = (\varphi_r, \kappa_r, w_r, p_r)$ where

- $\varphi_r : \mathcal{G} \to 2^{\mathcal{F}}$ is a computable predicate that, given a program graph $G \in \mathcal{G}$, returns a (possibly empty) set of matched fragments $\mathcal{F}$ --- each fragment a finite tuple of node ids and optional edge ids;
- $\kappa_r \in \mathcal{K}_M$ is the mapping kind the rule assigns on success, drawn from the mapping-kind alphabet $\mathcal{K}_M = \{\text{HIDDEN\_STATE}, \text{OBSERVATION}, \text{ACTION}, \text{POLICY}, \text{CONSTRAINT}, \text{PREFERENCE}, \text{CONTEXT}, \text{DATA\_FLOW}, \text{ERROR\_HANDLING}, \text{CIRCUIT\_BREAKER}, \text{ORCHESTRATION}\}$;
- $w_r \in (0, 1]$ is the base confidence weight attached to mappings produced by $r$;
- $p_r \in \mathbb{Z}$ is the rule priority consulted during conflict resolution (Algorithm 2).

Concretely, each `TranslationRule` subclass in `../cogant/py/cogant/translate/rules/` exposes $\varphi_r$ as the `matches(graph, query)` method, encodes $\kappa_r$ in the `mapping_kind` property, embeds $w_r$ in the `confidence_score` field of the returned `SemanticMapping`, and exposes $p_r$ through the `priority` property. The {{TRANSLATION_RULES}} shipped rules span five families: five structural rules (`ReadOnlyInput`, `MutatingSubsystem`, `Inheritance`, `Containment`, `DataPipeline`), five semantic rules (`Observation`, `Action`, `Policy`, `Preference`, `Context`), three control rules (`Config`, `FeatureFlag`, `Parameter`), four behavioural rules (`Orchestrator`, `TestAssertion`, `EventBus`, `StateMachine`), and five resilience rules (`RetryPattern`, `ErrorBoundary`, `SingletonAccess`, `CircuitBreaker`, `RateLimiter`). The three wave-21 additions (`Parameter`, `StateMachine`, `RateLimiter`) were introduced to capture tunable hyperparameters, finite-state-machine workflows, and rate-limiting policies that the original nineteen rules did not cover.

**Definition 3 (Fixpoint semantics).** Let $\mathcal{M}$ be the (finite) set of all possible semantic mappings that any finite composition of rules in $R$ could emit on a fixed graph $G$. Define the rule-application operator $F_{G,R} : 2^{\mathcal{M}} \to 2^{\mathcal{M}}$ by
\begin{equation}
\label{eq:fixpoint-operator}
F_{G,R}(S) \;=\; S \,\cup\, \bigl\{\, r.\text{apply}(G, f) \,\bigm|\, r \in R,\ f \in \varphi_r(G),\ r.\text{apply}(G, f) \neq \bot \,\bigr\}.
\end{equation}
The **translation** of $G$ under $R$ is the least fixpoint
\begin{equation}
\label{eq:least-fixpoint}
T^{*}(G) \;=\; \bigsqcup_{k \geq 0} F_{G,R}^{k}(\emptyset) \;=\; \lim_{k \to \infty} F_{G,R}^{k}(\emptyset),
\end{equation}
computed iteratively by `TranslationEngine.translate()` and then post-processed by `_resolve_conflicts()` (Algorithm 2). The post-processing step applies an anti-monotone pruning to the fixpoint, and is therefore specified outside of $F_{G,R}$ rather than folded into it.

**Definition 4 (Markov blanket partition).** Given a program graph $G = (V, E, \lambda_V, \lambda_E, \tau)$ and a **seed set** $S \subseteq V$ selected by one of the five strategies in `MarkovBlanketExtractor` (`explicit`, `module`, `kind`, `auto`, `mapping_kind`), the **Markov blanket partition** $\Pi_{G, S} : V \to \{\mu, s, a, \eta\}$ is defined on the undirected projection of $G$ as follows. Let $N^{\text{in}}(v) = \{u : (u, v, k) \in E\}$ and $N^{\text{out}}(v) = \{u : (v, u, k) \in E\}$. Then
\begin{equation}
\label{eq:markov-partition}
\Pi_{G,S}(v) \;=\;
\begin{cases}
\mu & \text{if } v \in S \text{ and } (N^{\text{in}}(v) \cup N^{\text{out}}(v)) \subseteq S, \\
a   & \text{if } v \in S \text{ and } N^{\text{out}}(v) \setminus S \neq \emptyset, \\
s   & \text{if } v \in S \text{ and } N^{\text{out}}(v) \subseteq S \text{ and } N^{\text{in}}(v) \setminus S \neq \emptyset, \\
\eta & \text{if } v \notin S.
\end{cases}
\end{equation}
The four-way case split is realised verbatim by `partition_by_seeds()` in `../cogant/py/cogant/markov/blanket.py`: the function precomputes the in/out adjacency of every node in $O(|V| + |E|)$ time via `_bidirectional_adjacency()`, then walks $V$ once and assigns each node to exactly one of $\mu$, $s$, $a$, $\eta$. Bidirectional boundary nodes (those with both external in- and out-neighbours) are assigned to $a$ by convention, and are additionally tagged with a `bidirectional` metadata flag so that downstream consumers can recover the distinction.

**Definition 5 (A/B/C/D matrices).** Given a translation $T^{*}(G)$ and a compiled state-space $(\mathbf{V}, \mathbf{O}, \mathbf{A})$ of hidden-state variables, observation modalities, and actions, the **generative-model matrices** of COGANT are

\begin{align}
\label{eq:matrices-defn}
A &\in \mathbb{R}^{|\mathbf{O}| \times |\mathbf{V}|},    &A_{ij} &= P(o_i \mid s_j), & \sum_i A_{ij} &= 1, \\
B &\in \mathbb{R}^{|\mathbf{V}| \times |\mathbf{V}| \times |\mathbf{A}|}, & B_{i j k} &= P(s'_i \mid s_j, a_k), & \sum_i B_{ijk} &= 1, \\
C &\in \mathbb{R}^{|\mathbf{O}|}, & C_i &= \log \tilde{P}(o_i), & \\
D &\in \mathbb{R}^{|\mathbf{V}|}, & D_j &= P(s_j \mid t = 0), & \sum_j D_j &= 1.
\end{align}

$A$ is derived from $\{\text{READS}, \text{OBSERVES}, \text{DEPENDS\_ON}\}$ edges between observation and hidden-state nodes; $B$ is derived from $\{\text{WRITES}, \text{MUTATES}\}$ edges from action to hidden-state nodes, with identity fallback when an action writes nothing; $C$ is derived from the signed confidence scores of CONSTRAINT/PREFERENCE mappings adjacent to each observation; and $D$ is derived from CONFIGURATION-neighbour bias on hidden-state variables or falls back to a uniform prior. The derivation is performed by `GNNMatrices` in `../cogant/py/cogant/gnn/matrices.py` and uses no numerical dependencies beyond the Python standard library. Rows (for $A$) and columns (for $B$) and the vectors $D$ are normalised to valid probability distributions using the high-direct / low-indirect mass defaults $(0.9, 0.1)$ defined in `GNNMatrices._normalize`; the $C$ vector is a log-preference and is not normalised.

### Theorems

**Theorem 1 (Fixpoint termination).** Let $G = (V, E, \lambda_V, \lambda_E, \tau)$ be a finite program graph with $|V| = n$, let $R$ be a finite rule set with $|R| = k$, and let $F_{G,R}$ be the rule-application operator of Definition 3. Then the Kleene chain
\begin{equation}
\label{eq:kleene-chain}
\emptyset \;\subseteq\; F_{G,R}(\emptyset) \;\subseteq\; F_{G,R}^{2}(\emptyset) \;\subseteq\; \cdots
\end{equation}
stabilises in at most $|\mathcal{M}|$ iterations, where $|\mathcal{M}| \leq n \cdot |\mathcal{K}_M|$ is an upper bound on the number of distinct mapping ids any rule set can produce on $G$. In particular, the shipped engine with its default cap $K = 10$ converges on every fixture in $\{$`calculator`, `event_pipeline`, `flask_mini`, `flask_app`, `requests_lib`, `json_stdlib`$\}$ within the cap.

*Proof sketch.* Each application step either adds at least one new mapping id to the accumulating set $S$ or leaves $S$ unchanged; the engine's idempotence guard in `TranslationEngine.translate` (skip when `mapping.id` is already in `self.mappings`) enforces the monotone-plus-bounded invariant. Because $F_{G,R}$ is monotone on the finite lattice $(2^{\mathcal{M}}, \subseteq)$ and bounded above by $\mathcal{M}$, the Kleene chain is an ascending chain in a finite lattice and therefore stabilises in at most $|\mathcal{M}|$ steps. The stabilisation point is, by construction, the least fixpoint of $F_{G,R}$ above $\emptyset$. The worst-case bound $n \cdot |\mathcal{K}_M|$ is attained when every node receives at most one mapping of each kind, which is the maximum any rule set can inject before the conflict-resolution step prunes overlaps. Empirically every packaged fixture converges in a single pass because the shipped rules are disjoint on the node kinds they target: @tbl:repo-pipeline-metrics and @tbl:state-space-compilation in @sec:06-03-performance-and-fixture-metrics record `mappings_total` values that equal the sum of per-kind counts, which is only possible if no node was touched twice. $\blacksquare$

**Theorem 2 (Markov blanket completeness).** For any program graph $G = (V, E, \lambda_V, \lambda_E, \tau)$ with $V \neq \emptyset$ and any seed set $S \subseteq V$, the partition $\Pi_{G, S}$ of Definition 4 is **total** (every $v \in V$ receives exactly one role) and **mutually exclusive** (no $v$ is assigned two roles).

*Proof sketch.* Totality: the case split in Equation \ref{eq:markov-partition} exhausts the boolean product $(v \in S) \times (N^{\text{out}}(v) \setminus S = \emptyset) \times (N^{\text{in}}(v) \setminus S = \emptyset)$. If $v \notin S$ the fourth case applies. If $v \in S$ there are three subcases depending on whether $v$ has external out-neighbours, external in-neighbours only, or no external neighbours at all; the engine resolves the "both external in and external out" subcase to `ACTIVE` by convention, matching the bidirectional case branch in `partition_by_seeds()` in `cogant.markov.blanket`. Every $v \in V$ therefore matches exactly one branch, so $\Pi$ is a total function. Mutual exclusivity: the branches are pairwise disjoint because they condition on mutually exclusive predicates on $(v \in S, N^{\text{in}}(v) \setminus S, N^{\text{out}}(v) \setminus S)$. The implementation materialises the four role sets `internal`, `sensory`, `active`, `external` as disjoint Python sets and writes into exactly one on each iteration of the main loop, so the in-memory invariant matches the mathematical one. $\blacksquare$

**Theorem 3 (Matrix validity).** If $|\mathbf{O}| \geq 1$, $|\mathbf{V}| \geq 1$, and $|\mathbf{A}| \geq 1$, then the matrices $(A, B, C, D)$ produced by `GNNMatrices.compute_A/B/C/D` satisfy the stochastic conditions of Definition 5 within a numerical tolerance of $10^{-6}$.

*Proof sketch.* Rows of $A$ are produced in Equation (\ref{eq:matrices-defn}) with explicit normalisation in `GNNMatrices` (`_normalize_row`), which divides by the row sum when it exceeds $\varepsilon = 10^{-9}$ and returns a uniform row otherwise. Columns of each action slice $B[:,:,k]$ are produced by the same helper with an identity fallback ensuring the resulting column is never all-zero. The prior $D$ is built as a weighted vector of confidence scores and passed through `_normalize_vector()`, again with a uniform fallback when all weights are below $\varepsilon$. The implementation therefore establishes the sum-to-one invariant by construction, and `GNNMatrices.validate_shapes` enforces a tolerance of $10^{-6}$ on every computed matrix before the pipeline accepts the bundle; all six packaged fixtures pass `GNNValidator` with zero errors (@tbl:repo-pipeline-metrics), which is observationally the same statement as Theorem 3 on those fixtures. The $C$ vector is a log-preference and is exempt from the sum-to-one requirement. $\blacksquare$

## See also (MkDocs)

System layers and pipeline data flow: [`../cogant/docs/architecture/README.md`](../cogant/docs/architecture/README.md). Formal isomorphism / round-trip theory: [`../cogant/docs/theory/isomorphism.md`](../cogant/docs/theory/isomorphism.md), [`../cogant/docs/theory/roundtrip.md`](../cogant/docs/theory/roundtrip.md).
