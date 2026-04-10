> **Archive:** Superseded by numbered fragments in `manuscript/`; excluded from combined PDF. Do not update this file for publication.

# Methodology: Program Graphs and Intermediate Representations

## Program graph

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

## Formal definitions

This subsection makes the objects manipulated by the pipeline mathematically explicit. The definitions are stated for the shipped v0.5.x engine; where the implementation differs from the general form (for example because an edge kind is not yet emitted by the Python front end), the difference is noted with a forward reference to Section 6.

**Definition 1 (Program graph).** A **program graph** is a tuple $G = (V, E, \lambda_V, \lambda_E, \tau)$ where

- $V$ is a finite set of program nodes (modules, classes, methods, functions, and --- on languages where the front end emits them --- variables and control-flow sites);
- $E \subseteq V \times V \times K$ is a finite set of typed directed edges drawn from the edge-kind alphabet $K \supseteq \{\text{READS}, \text{WRITES}, \text{CALLS}, \text{CONTAINS}, \text{INHERITS}, \text{IMPORTS}, \text{OBSERVES}, \text{MUTATES}, \text{DEPENDS\_ON}\}$;
- $\lambda_V : V \to \mathcal{N}$ labels each node with a node kind $\mathcal{N} \supseteq \{\text{MODULE}, \text{CLASS}, \text{METHOD}, \text{FUNCTION}, \text{CONFIGURATION}, \ldots\}$;
- $\lambda_E : E \to K$ is the (trivial) projection onto the edge kind;
- $\tau : V \to (T \cup \{\bot\})$ maps each node to a type annotation recovered from the front end or to $\bot$ when no annotation is available.

The shipped Python front end populates the kinds $\{\text{MODULE}, \text{CLASS}, \text{METHOD}, \text{FUNCTION}\}$ and the edge kinds $\{\text{CALLS}, \text{CONTAINS}, \text{READS}, \text{WRITES}, \text{IMPORTS}, \text{INHERITS}\}$; the remaining kinds in $\mathcal{N}$ and $K$ are declared in `cogant.schemas.core` but currently emitted only when other parsers or dynamic enrichment stages fire. The empirical distribution on the six packaged fixtures is recorded in Tables 4 and 5 of Section 6.

**Definition 2 (Translation rule).** A **translation rule** is a quadruple $r = (\varphi_r, \kappa_r, w_r, p_r)$ where

- $\varphi_r : \mathcal{G} \to 2^{\mathcal{F}}$ is a computable predicate that, given a program graph $G \in \mathcal{G}$, returns a (possibly empty) set of matched fragments $\mathcal{F}$ --- each fragment a finite tuple of node ids and optional edge ids;
- $\kappa_r \in \mathcal{K}_M$ is the mapping kind the rule assigns on success, drawn from the mapping-kind alphabet $\mathcal{K}_M = \{\text{HIDDEN\_STATE}, \text{OBSERVATION}, \text{ACTION}, \text{POLICY}, \text{CONSTRAINT}, \text{PREFERENCE}, \text{CONTEXT}, \text{DATA\_FLOW}, \text{ERROR\_HANDLING}, \text{CIRCUIT\_BREAKER}, \text{ORCHESTRATION}\}$;
- $w_r \in (0, 1]$ is the base confidence weight attached to mappings produced by $r$;
- $p_r \in \mathbb{Z}$ is the rule priority consulted during conflict resolution (Algorithm 2).

Concretely, each `TranslationRule` subclass in `../cogant/py/cogant/translate/rules/` exposes $\varphi_r$ as the `matches(graph, query)` method, encodes $\kappa_r$ in the `mapping_kind` property, embeds $w_r$ in the `confidence_score` field of the returned `SemanticMapping`, and exposes $p_r$ through the `priority` property. The nineteen shipped rules span five families: five structural rules (`ReadOnlyInput`, `MutatingSubsystem`, `Inheritance`, `Containment`, `DataPipeline`), five semantic rules (`Observation`, `Action`, `Policy`, `Preference`, `Context`), two control rules (`Config`, `FeatureFlag`), three behavioural rules (`Orchestrator`, `TestAssertion`, `EventBus`), and four resilience rules (`RetryPattern`, `ErrorBoundary`, `SingletonAccess`, `CircuitBreaker`).

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

$A$ is derived from $\{\text{READS}, \text{OBSERVES}, \text{DEPENDS\_ON}\}$ edges between observation and hidden-state nodes; $B$ is derived from $\{\text{WRITES}, \text{MUTATES}\}$ edges from action to hidden-state nodes, with identity fallback when an action writes nothing; $C$ is derived from the signed confidence scores of CONSTRAINT/PREFERENCE mappings adjacent to each observation; and $D$ is derived from CONFIGURATION-neighbour bias on hidden-state variables or falls back to a uniform prior. The derivation is performed by `GNNMatrices` in `../cogant/py/cogant/gnn/matrices.py` and uses no numerical dependencies beyond the Python standard library. Rows (for $A$) and columns (for $B$) and the vectors $D$ are normalised to valid probability distributions using the high-direct / low-indirect mass defaults $(0.9, 0.1)$ imported from the upstream PyMDP placeholder convention; the $C$ vector is a log-preference and is not normalised.

### Theorems

**Theorem 1 (Fixpoint termination).** Let $G = (V, E, \lambda_V, \lambda_E, \tau)$ be a finite program graph with $|V| = n$, let $R$ be a finite rule set with $|R| = k$, and let $F_{G,R}$ be the rule-application operator of Definition 3. Then the Kleene chain
$$
\emptyset \;\subseteq\; F_{G,R}(\emptyset) \;\subseteq\; F_{G,R}^{2}(\emptyset) \;\subseteq\; \cdots
$$
stabilises in at most $|\mathcal{M}|$ iterations, where $|\mathcal{M}| \leq n \cdot |\mathcal{K}_M|$ is an upper bound on the number of distinct mapping ids any rule set can produce on $G$. In particular, the shipped engine with its default cap $K = 10$ converges on every fixture in $\{$`calculator`, `event_pipeline`, `flask_mini`, `flask_app`, `requests_lib`, `json_stdlib`$\}$ within the cap.

*Proof sketch.* Each application step either adds at least one new mapping id to the accumulating set $S$ or leaves $S$ unchanged; the engine's explicit `mapping.id not in self.mappings` guard (`engine.py` lines 299--303) is what enforces the monotone-plus-bounded invariant. Because $F_{G,R}$ is monotone on the finite lattice $(2^{\mathcal{M}}, \subseteq)$ and bounded above by $\mathcal{M}$, the Kleene chain is an ascending chain in a finite lattice and therefore stabilises in at most $|\mathcal{M}|$ steps. The stabilisation point is, by construction, the least fixpoint of $F_{G,R}$ above $\emptyset$. The worst-case bound $n \cdot |\mathcal{K}_M|$ is attained when every node receives at most one mapping of each kind, which is the maximum any rule set can inject before the conflict-resolution step prunes overlaps. Empirically every packaged fixture converges in a single pass because the shipped rules are disjoint on the node kinds they target: Tables 4 and 6 of Section 6 record `mappings_total` values that equal the sum of per-kind counts, which is only possible if no node was touched twice. $\blacksquare$

**Theorem 2 (Markov blanket completeness).** For any program graph $G = (V, E, \lambda_V, \lambda_E, \tau)$ with $V \neq \emptyset$ and any seed set $S \subseteq V$, the partition $\Pi_{G, S}$ of Definition 4 is **total** (every $v \in V$ receives exactly one role) and **mutually exclusive** (no $v$ is assigned two roles).

*Proof sketch.* Totality: the case split in Equation \ref{eq:markov-partition} exhausts the boolean product $(v \in S) \times (N^{\text{out}}(v) \setminus S = \emptyset) \times (N^{\text{in}}(v) \setminus S = \emptyset)$. If $v \notin S$ the fourth case applies. If $v \in S$ there are three subcases depending on whether $v$ has external out-neighbours, external in-neighbours only, or no external neighbours at all; the engine resolves the "both external in and external out" subcase to `ACTIVE` by convention, matching lines 205--211 of `blanket.py`. Every $v \in V$ therefore matches exactly one branch, so $\Pi$ is a total function. Mutual exclusivity: the branches are pairwise disjoint because they condition on mutually exclusive predicates on $(v \in S, N^{\text{in}}(v) \setminus S, N^{\text{out}}(v) \setminus S)$. The implementation materialises the four role sets `internal`, `sensory`, `active`, `external` as disjoint Python sets and writes into exactly one on each iteration of the main loop, so the in-memory invariant matches the mathematical one. $\blacksquare$

**Theorem 3 (Matrix validity).** If $|\mathbf{O}| \geq 1$, $|\mathbf{V}| \geq 1$, and $|\mathbf{A}| \geq 1$, then the matrices $(A, B, C, D)$ produced by `GNNMatrices.compute_A/B/C/D` satisfy the stochastic conditions of Definition 5 within a numerical tolerance of $10^{-6}$.

*Proof sketch.* Rows of $A$ are produced in Equation (\ref{eq:matrices-defn}) with explicit normalisation (`_normalize_row()` at `matrices.py` line 277), which divides by the row sum when it exceeds $\varepsilon = 10^{-9}$ and returns a uniform row otherwise. Columns of each action slice $B[:,:,k]$ are produced by the same helper on lines 334--348, with an identity fallback ensuring the resulting column is never all-zero. The prior $D$ is built as a weighted vector of confidence scores and passed through `_normalize_vector()`, again with a uniform fallback when all weights are below $\varepsilon$. The implementation therefore establishes the sum-to-one invariant by construction, and `validate_shapes()` (lines 554--603) enforces a tolerance of $10^{-6}$ on every computed matrix before the pipeline accepts the bundle; all six packaged fixtures pass `GNNValidator` with zero errors (Table 7), which is observationally the same statement as Theorem 3 on those fixtures. The $C$ vector is a log-preference and is exempt from the sum-to-one requirement. $\blacksquare$

## Progressive IRs

Processing proceeds through a sequence of representations (see `../cogant/docs/reference/implementation_status.md`):

1. **Repo IR** — entities and relationships extracted from parsers.
2. **Program graph IR** — consolidated graph with deduplication and metadata.
3. **Semantic mapping IR** — output of the translation rule engine.
4. **State space IR** — variables, actions, transitions, observations.
5. **Process model IR** — higher-level control patterns where implemented.
6. **Validation IR** — coverage, confidence analysis, schema checks.

Not every stage is equally complete for every repository; [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md) marks partial areas (translation rules, state space, Rust acceleration) explicitly. COGANT's program graph sits in the same conceptual space as compiler intermediate representations such as LLVM [@lattner2004llvm] and MLIR [@lattner2021mlir], but targets behavioral extraction and export for downstream learning rather than code generation or optimization.

## Translation rules

The **translation** stage applies declarative rules that refine roles, attach labels, and adjust confidence. Concurrency targets and layering are described in `../cogant/docs/architecture/README.md`. The rule engine composes passes over the graph in a **fixpoint loop**: rules are re-applied until no new semantic mappings emerge or a configurable iteration cap is reached. The fixpoint loop follows the classical formulation of program analysis as fixpoint computation over a lattice of abstract states [@cousot1977abstract]; in our setting the lattice is the set of semantic mappings partially ordered by inclusion, and the monotone operator is the composition of all registered rule applications. In the shipped implementation, each pass applies rules in descending `rule.priority`, and conflict resolution later compares `(rule_priority, confidence_score)` tuples when two mappings overlap, following the principle that edit representations should be composable [@yin2019learning].

### Fixpoint iteration, conflict resolution, and coverage

The shipped `TranslationEngine` in `../cogant/py/cogant/translate/engine.py` realizes the fixpoint loop concretely. Each iteration walks every registered rule once: the engine calls `rule.matches(graph, query)` to collect candidate fragments, then calls `rule.apply(graph, match)` on each, accumulating any resulting `SemanticMapping` objects keyed by their stable IDs. A per-pass counter tracks mappings that were genuinely new (not already present in the running set), and the loop terminates as soon as a pass completes with zero additions. The engine logs each iteration boundary through an internal match log, so the number of passes required to reach a fixed point is directly observable in the post-run diagnostics. The default iteration cap is `max_iterations = 10`; in testing, most repositories converge well before that bound, and the cap exists primarily as a safety valve against pathological rule sets that could otherwise oscillate indefinitely.

After fixpoint termination, the engine invokes `_resolve_conflicts()` to reconcile mappings whose `graph_fragment_node_ids` sets overlap. For each overlapping pair the engine retains the mapping with the larger `(rule_priority, confidence_score)` key and discards the other, logging a `conflict_resolved` event that records the losing ID, the winning ID, and the specific overlap set. A companion entry point, `translate_with_confidence()`, runs the standard fixpoint loop, rescores every surviving mapping through the `ConfidenceModel`, and then re-resolves conflicts so that any ordering shifts induced by rescoring are honored.

Translation coverage -- the fraction of graph nodes that received at least one semantic mapping -- is reported by `get_coverage_report(graph)`. It returns the total node count, the number of covered nodes, the number of uncovered nodes, a `coverage_percent` value rounded to two decimal places, and the sorted list of uncovered node IDs. The uncovered list is intentionally emitted verbatim so that downstream tooling can target unmapped regions for manual review or rule extension, rather than burying the gap behind a single aggregate number [@allamanis2018survey].

\begin{algorithm}
\caption{Fixpoint translation engine}
\label{alg:fixpoint}
\KwIn{Program graph $G = (V, E)$; rule set $R$; maximum iterations $K$ (default 10)}
\KwOut{Set of semantic mappings $\mathcal{M}$ keyed by stable ID}
$\mathcal{M} \leftarrow \emptyset$\;
\For{$k \leftarrow 1$ \KwTo $K$}{
    $n_{\text{new}} \leftarrow 0$\;
    \ForEach{rule $r \in R$ sorted by $\text{priority}(r)$ descending}{
        \ForEach{match $m \in r.\text{matches}(G)$}{
            $\mu \leftarrow r.\text{apply}(G, m)$\;
            \If{$\mu \neq \bot$ \textbf{and} $\mu.\text{id} \notin \mathcal{M}$}{
                $\mathcal{M} \leftarrow \mathcal{M} \cup \{\mu\}$\;
                $n_{\text{new}} \leftarrow n_{\text{new}} + 1$\;
            }
        }
    }
    \If{$n_{\text{new}} = 0$}{
        \textbf{break} \tcp*{fixed point reached}
    }
}
$\mathcal{M} \leftarrow \textsc{ResolveConflicts}(\mathcal{M})$\;
\Return $\mathcal{M}$\;
\end{algorithm}

Algorithm \ref{alg:fixpoint} summarizes the engine. Termination is guaranteed because each iteration either produces at least one new mapping (whose stable ID is then fixed in $\mathcal{M}$) or terminates by the break condition; the outer $K$ bound serves as a safety valve for pathological rule sets.

\begin{algorithm}
\caption{Priority-ordered conflict resolution}
\label{alg:conflict}
\KwIn{Mapping set $\mathcal{M}$; priority function $p(\cdot)$}
\KwOut{Reduced mapping set with no overlapping fragments}
Build inverted index $\mathcal{I}: V \to 2^{\mathcal{M}}$ from node IDs to mappings touching them\;
$\mathcal{C} \leftarrow \emptyset$ \tcp*{conflict pairs}
\ForEach{node $v$ with $|\mathcal{I}(v)| \geq 2$}{
    \ForEach{$(\mu_a, \mu_b) \in \binom{\mathcal{I}(v)}{2}$}{
        $\mathcal{C} \leftarrow \mathcal{C} \cup \{(\mu_a, \mu_b)\}$\;
    }
}
$\mathcal{R} \leftarrow \emptyset$ \tcp*{removal set}
\ForEach{$(\mu_a, \mu_b) \in \mathcal{C}$}{
    \If{$\mu_a \in \mathcal{R}$ \textbf{or} $\mu_b \in \mathcal{R}$}{\textbf{continue}}
    $k_a \leftarrow (p(\mu_a), c(\mu_a))$; $k_b \leftarrow (p(\mu_b), c(\mu_b))$\;
    \eIf{$k_a \geq k_b$}{$\mathcal{R} \leftarrow \mathcal{R} \cup \{\mu_b\}$}{$\mathcal{R} \leftarrow \mathcal{R} \cup \{\mu_a\}$}
}
\Return $\mathcal{M} \setminus \mathcal{R}$\;
\end{algorithm}

Algorithm \ref{alg:conflict} detects conflicts via an inverted index in $O(\sum_v |\mathcal{I}(v)|^2)$ worst-case time, which is substantially faster than the naive all-pairs scan for graphs where most nodes carry at most one mapping.

## Confidence Scoring and Evidence Tiers

The shipped `ConfidenceModel` in `../cogant/py/cogant/translate/confidence.py` computes a scalar score in $[0,1]$ from:

- Average confidence over provenance records.
- An evidence-diversity term (scaled, capped).
- A parser certainty factor applied multiplicatively.
- Conflict penalties subtracted after scaling.

\begin{equation}
\label{eq:confidence-core}
c = \max\left(0,\ \min\left(1,\ (\bar{e} + \delta_d)\cdot \kappa - \pi\right)\right)
\end{equation}

Here $\bar{e}$ is the mean evidence confidence, $\delta_d$ is the diversity bonus (bounded), $\kappa$ is parser certainty, and $\pi$ aggregates conflict penalties. **Tiers** (for example static-only versus static-plus-runtime) are assigned from score thresholds and evidence source tags (`determine_confidence_tier`); see the same module for named thresholds and enum values. The manuscript does not duplicate those literals so they cannot drift from code.

## State space and behavior

Where traces or coverage are available, **dynamic** extraction feeds the state-space compiler. The goal is a compact behavioral model: states, actions, transitions, and observations that sit alongside the static graph for tasks that require execution-sensitive features. The tuple $(S, A, T, O)$ of variables, actions, transitions, and observation modalities mirrors the structure of a partially observed Markov decision process as used in discrete active inference [@parr2022active; @dacosta2020active; @smith2022stepbystep], and at the level of reachable state/transition graphs it also resembles the Kripke structures traditionally used in model checking [@clarke1999model], without attempting to discharge temporal-logic obligations. PyMDP [@heins2022pymdp] is one such downstream consumer that executes the compiled state-spaces as discrete active inference simulations over the exported Generalized Notation Notation bundles.

The shipped `StateSpaceCompiler` in `../cogant/py/cogant/statespace/compiler.py` constructs this model in several coordinated passes driven by the semantic mappings and the underlying program graph.

**State variables** are identified by a `StateVariableExtractor` that traverses graph nodes carrying READS and WRITES edges: any node that participates in a write is a candidate hidden-state variable, and its type, cardinality, and initial confidence are derived from the node's recovered type string and the provenance of the rules that produced the associated mapping.

**Actions** are extracted from semantic mappings of kind `ACTION`, with parameters read from node metadata (typically the parser-recovered function signature), effects traced through outgoing WRITES edges on the controller node, and preconditions derived from parameter lists, docstring directives, and explicit metadata entries. For method-kind actions, the compiler also walks CONTAINS edges back to the enclosing class so that instance-level state mutations are attributed to the correct controller, mirroring how code property graphs fuse structural and data-flow views [@yamaguchi2014modeling].

**Transitions** are inferred by a cross-reference pass (`_cross_reference_actions_and_variables`) that, for each action, partitions its adjacent variables into reads and writes based on edge kind (WRITES and MUTATES yielding writes; READS and OBSERVES yielding reads). The resulting `Transition` object records a `source_state` in which every touched variable is marked `"pre"` and a `target_state` in which written variables advance to `"post"` while read-only variables remain `"pre"`; this simple pre/post convention keeps the model faithful to the static evidence without overcommitting to symbolic value domains that cannot be recovered from AST analysis alone.

Trigger attribution follows incoming TRIGGERS and CALLS edges so that orchestration flow is preserved in the behavioral model.

**Observation modalities** are built from semantic mappings of kind `OBSERVATION`: each associated node becomes an `ObservationModality` whose modality type (`log`, `metric`, `event`, `sensor`, or a generic fallback) is inferred from the mapping's description and the node's name, giving the GNN export a typed observation channel aligned with the OBSERVES edges in the program graph.

The **temporal regime** of the model is determined by a companion `TemporalAnalyzer`. It classifies nodes as asynchronous when their metadata carries `is_async`/`async` flags or their names match patterns such as `async`, `callback`, `promise`, or `future`, and as event-related when their kind is `EVENT` or their names match `event`, `handler`, `listener`, or `trigger`. Temporal orderings are then extracted from CALLS and TRIGGERS edges, with each edge classified as `parallel` (when either endpoint is async) or `sequential` otherwise, and event patterns are assembled from triggers-in / triggers-out pairs around each event node.

A final decision rule selects among `SYNCHRONOUS`, `ASYNCHRONOUS`, `EVENT_DRIVEN`, and `HYBRID`: the presence of event triggers and patterns combined with async handlers yields `HYBRID`; event triggers alone yield `EVENT_DRIVEN`; an async fraction above 30 percent or the presence of async handlers yields `ASYNCHRONOUS`; and all remaining cases default to `SYNCHRONOUS`. This regime is attached to the `StateSpaceModel` metadata so downstream consumers know which execution model the transition graph assumes.

When coverage and traces are available, `enrich_graph()` in `../cogant/py/cogant/dynamic/enrichment.py` feeds additional evidence into this pipeline. Coverage enrichment matches `.coverage` SQLite databases or Cobertura XML reports against nodes whose `path` and `source_range` overlap covered lines, attaching `coverage_hits` and, where branch data is available, `branch_coverage` metadata. Trace enrichment parses Chrome DevTools traces, writes `call_count`, `avg_duration_ms`, and `is_hot_path` onto matching callable nodes, and adds or reweights dynamic CALLS edges tagged with `evidence_sources=["dynamic_trace"]`.

Both steps also append `dynamic_coverage` and `dynamic_trace` markers to the program graph's evidence sources. The confidence model consumes these markers directly: any mapping whose evidence set now contains both static and dynamic entries becomes eligible for promotion from the `STATIC_ONLY` tier to `STATIC_PLUS_RUNTIME`, and hot-path and branch-coverage metadata raise the underlying score through the diversity bonus $\delta_d$ in Equation \ref{eq:confidence-core}. This is the mechanism by which executing the target program, even partially, converts static heuristics into corroborated behavioral facts without rerunning the upstream rule engine [@allamanis2018survey].

### Worked example: temperature controller

Consider a small Python controller extracted from a HVAC codebase:

```python
class TemperatureController:
    def __init__(self):
        self.current_temp: float = 20.0
        self.target_temp: float = 22.0
        self.heater_on: bool = False

    def set_target(self, t: float) -> None:
        self.target_temp = t

    def read_sensor(self, reading: float) -> None:
        self.current_temp = reading

    def actuate_heater(self) -> None:
        if self.current_temp < self.target_temp:
            self.heater_on = True
        else:
            self.heater_on = False
```

`StateVariableExtractor` identifies three **state variables** from WRITES edges on `__init__` and the three methods: `current_temp` (float, cardinality continuous), `target_temp` (float), and `heater_on` (bool, cardinality 2). Three **actions** are extracted from `ACTION`-kind mappings: `set_target` (writes `target_temp`), `read_sensor` (writes `current_temp`), and `actuate_heater` (reads `current_temp`, `target_temp`; writes `heater_on`). All three actions are attributed to `TemperatureController` via CONTAINS edges.

The cross-reference pass yields three **transitions**. For `actuate_heater` the `source_state` records `{current_temp: "pre", target_temp: "pre", heater_on: "pre"}` and the `target_state` records `{current_temp: "pre", target_temp: "pre", heater_on: "post"}`, capturing that only `heater_on` advances while the read-only variables remain pinned. Because no node carries async flags or event-kind markers and no CALLS or TRIGGERS edges cross into async endpoints, the `TemporalAnalyzer` classifies the model as `SYNCHRONOUS` and attaches that regime to the `StateSpaceModel` metadata.

## GNN export (Generalized Notation Notation)

Exports package the program graph and compiled state-space model into the Active Inference Institute's **Generalized Notation Notation** plus a small set of interop targets:

- **GNN Markdown (`model.gnn.md`)** — canonical, human-readable Generalized Notation Notation organized into the section order defined in `../cogant/docs/export/README.md` (Model Metadata, Repository Metadata, Source Coverage, State Space, Observation Modalities, Actions/Policies, Connections, Factors, Transition Structure, Likelihood Structure, Preferences/Constraints, Time Settings, Parameterization, Ontology Mapping, Provenance, Confidence Scores, Rendering Hints, Validation Notes).
- **GNN JSON (`model.gnn.json`)** — machine-readable equivalent of the markdown sections, plus companion JSON files per section (`state_space.json`, `observations.json`, `actions.json`, `transitions.json`, and so on).
- **Interop exports** — GraphML and Parquet for analysis in Gephi/yEd and DuckDB, and optional tensor views (PyTorch Geometric `Data` objects [@fey2019pyg], DGL graphs, HDF5 tables) for downstream graph neural network training pipelines that consume the program graph as a relational tensor.

Node and edge feature breakdowns, section contracts, and the optional framework targets are specified in `../cogant/docs/export/README.md`; they determine the structure of the emitted notation as well as the effective input dimensionality of any downstream model.

## Error handling philosophy

The implementation distinguishes fatal configuration or parse failures from per-file errors that allow partial results. Validation aggregates warnings and inconsistencies into a report that travels with the bundle. This mirrors the layered error categories documented in the architecture (fatal, error, warning, info).
