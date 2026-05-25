# Notation supplement {#sec:98-notation-supplement}

This supplement is the **canonical reference for manuscript-level mathematical symbols, acronyms, and formal objects** used across the COGANT manuscript. When a symbol appears in multiple sections, this table resolves any apparent conflict — if the manuscript prose and this supplement disagree, update the prose to match the definitions here. Where entries are derived from code, the canonical source is the Python module listed in the Notes column; if the code is authoritative, so is the module.

Cross-references use automatic manuscript identifiers for equations, definitions, scoped formal claims, and appendices. Rendered numbering follows manuscript discovery order; source files never rely on hand-written numbers.

---

## Program graph symbols {#sec:98-program-graph-symbols}

| Symbol | LaTeX | Meaning | First defined | Notes |
|--------|-------|---------|---------------|-------|
| $G$ | `$G$` | Program graph | @sec:def-program-graph | Tuple $(V, E, \lambda_V, \lambda_E, \tau)$ |
| $V$ | `$V$` | Finite set of program nodes | @sec:def-program-graph | Modules, classes, methods, functions, … |
| $E$ | `$E$` | Finite set of typed directed edges; $E \subseteq V \times V \times K$ | @sec:def-program-graph | Drawn from edge-kind alphabet $K$ |
| $K$ | `$K$` | Edge-kind alphabet (18 kinds) | @sec:def-program-graph | See @sec:98-node-edge-kind-enumerations for full enumeration |
| $\mathcal{N}$ | `$\mathcal{N}$` | Node-kind alphabet (18 kinds) | @sec:def-program-graph | See @sec:98-node-edge-kind-enumerations for full enumeration |
| $\lambda_V$ | `$\lambda_V$` | Node-kind labelling function; $\lambda_V : V \to \mathcal{N}$ | @sec:def-program-graph | |
| $\lambda_E$ | `$\lambda_E$` | Edge-kind labelling function; $\lambda_E : E \to K$ | @sec:def-program-graph | Trivial projection onto edge kind |
| $\tau$ | `$\tau$` | Type annotation map; $\tau : V \to (T \cup \{\bot\})$ | @sec:def-program-graph | $\bot$ when no annotation available |
| $T$ | `$T$` | Set of type strings recovered from front end | @sec:def-program-graph | |
| $\bot$ | `$\bot$` | Missing/unavailable type annotation | @sec:def-program-graph | Lattice bottom |
| $\phi$ | `$\phi$` | Graph isomorphism bijection; $\phi : V_1 \to V_2$ | @eq:typed-iso | Accepted when it preserves adjacency |
| $G_1, G_2$ | `$G_1, G_2$` | Two program graphs under structural comparison | @eq:typed-iso | |
| $N^{\text{in}}(v)$ | `$N^{\text{in}}(v)$` | In-neighbour set of node $v$; $\{u : (u,v,k) \in E\}$ | @sec:def-markov-blanket-partition | Computed in $O(\|V\|+\|E\|)$ |
| $N^{\text{out}}(v)$ | `$N^{\text{out}}(v)$` | Out-neighbour set of node $v$; $\{u : (v,u,k) \in E\}$ | @sec:def-markov-blanket-partition | |
| $S$ | `$S$` | Seed set for Markov blanket partition; $S \subseteq V$ | @sec:def-markov-blanket-partition | Selected by one of five strategies |
| $\Pi_{G,S}$ | `$\Pi_{G,S}$` | Structural Markov-blanket partition function; $\Pi_{G,S} : V \to \{\mu, s, a, \eta\}$ | @sec:def-markov-blanket-partition (@eq:markov-partition) | Total and mutually exclusive; no conditional-independence claim (@sec:thm-markov-blanket-completeness) |
| $\mu$ | `$\mu$` | Internal (autonomous) node role | @sec:def-markov-blanket-partition | In seed; all neighbours also in seed |
| $s$ | `$s$` | Sensory node role | @sec:def-markov-blanket-partition | In seed; receives input from outside seed |
| $a$ | `$a$` | Active node role | @sec:def-markov-blanket-partition | In seed; sends output outside seed |
| $\eta$ | `$\eta$` | External node role | @sec:def-markov-blanket-partition | Not in seed |

---

## Translation engine symbols {#sec:98-translation-engine-symbols}

| Symbol | LaTeX | Meaning | First defined | Notes |
|--------|-------|---------|---------------|-------|
| $r$ | `$r$` | Translation rule quadruple $({\varphi_r, \kappa_r, w_r, p_r})$ | @sec:def-translation-rule | {{TRANSLATION_RULES}} shipped rules in 5 families (5+5+3+4+5); `METRICS.yaml` `pipeline.translation_rules` |
| $\varphi_r$ | `$\varphi_r$` | Rule match predicate; $\varphi_r : \mathcal{G} \to 2^{\mathcal{F}}$ | @sec:def-translation-rule | `matches(graph, query)` in code |
| $\mathcal{G}$ | `$\mathcal{G}$` | Universe of finite program graphs | @sec:def-translation-rule | |
| $\mathcal{F}$ | `$\mathcal{F}$` | Fragment space (finite tuples of node/edge ids) | @sec:def-translation-rule | |
| $\kappa_r$ | `$\kappa_r$` | Mapping kind assigned by rule $r$ | @sec:def-translation-rule | Element of $\mathcal{K}_M$; see @sec:98-active-inference-roles |
| $\mathcal{K}_M$ | `$\mathcal{K}_M$` | Formal mapping-kind alphabet (11 kinds; code `MappingKind` enum has 14, incl. 3 non-formal implementation kinds) | @sec:def-translation-rule | See @sec:98-active-inference-roles for full enumeration |
| $w_r$ | `$w_r$` | Base confidence weight of rule $r$; $w_r \in (0, 1]$ | @sec:def-translation-rule | |
| $p_r$ | `$p_r$` | Rule priority; $p_r \in \mathbb{Z}$ | @sec:def-translation-rule | Higher wins in conflict resolution |
| $R$ | `$R$` | Finite rule set; $|R|$ equals the shipped rule count | @sec:def-fixpoint-semantics | Injected as {{TRANSLATION_RULES}}; `METRICS.yaml` `pipeline.translation_rules` |
| $\mathcal{M}$ | `$\mathcal{M}$` | Universe of possible semantic mappings on $G$ under $R$ | @sec:def-fixpoint-semantics | $\|\mathcal{M}\| \leq n \cdot \|\mathcal{K}_M\|$ |
| $F_{G,R}$ | `$F_{G,R}$` | Rule-application operator; $F_{G,R} : 2^{\mathcal{M}} \to 2^{\mathcal{M}}$ | @sec:def-fixpoint-semantics (@eq:fixpoint-operator) | Monotone on $(2^{\mathcal{M}}, \subseteq)$ |
| $T^{*}(G)$ | `$T^{*}(G)$` | Translation of $G$ under $R$; least fixpoint $\bigsqcup_{k \geq 0} F_{G,R}^k(\emptyset)$ | @sec:def-fixpoint-semantics (@eq:least-fixpoint) | |
| $K$ | `$K$` | Iteration cap; default $K = 10$ | @sec:thm-fixpoint-termination | `max_iterations` in `engine.py` |
| $n$ | `$n$` | Number of nodes in program graph; $n = \|V\|$ | @sec:thm-fixpoint-termination | |
| $k$ | `$k$` | Number of rules; $k = \|R\|$ | @sec:thm-fixpoint-termination | |
| $(p(\mu), c(\mu))$ | `$(p(\mu), c(\mu))$` | Conflict-resolution key: (priority, confidence) for mapping $\mu$ | @sec:def-translation-rule, @sec:alg-conflict-resolution | Higher priority wins; confidence breaks ties |
| $\rho$ | `$\rho$` | Role-multiset functor $\rho : \mathbf{Prog} \to \mathbf{Mset}(\text{Roles})$ | @sec:S03-role-multiset-functor | Counts role assignments per node |

---

## Confidence model symbols {#sec:98-confidence-symbols}

| Symbol | LaTeX | Meaning | First defined | Notes |
|--------|-------|---------|---------------|-------|
| $c$ | `$c$` | Confidence score; $c \in [0, 1]$ | @sec:02-03-confidence-scoring (@eq:confidence-core) | `ConfidenceModel` in `translate/confidence.py` |
| $\bar{e}$ | `$\bar{e}$` | Mean evidence confidence over provenance records | @sec:02-03-confidence-scoring (@eq:confidence-core) | |
| $\delta_d$ | `$\delta_d$` | Evidence-diversity bonus (bounded, scaled) | @sec:02-03-confidence-scoring (@eq:confidence-core) | Raised by dynamic enrichment |
| $\kappa$ | `$\kappa$` | Parser certainty factor; applied multiplicatively | @sec:02-03-confidence-scoring (@eq:confidence-core) | $\kappa \in [0, 1]$ |
| $\pi$ | `$\pi$` | Aggregate conflict penalties (subtracted post-scaling) | @sec:02-03-confidence-scoring (@eq:confidence-core) | Not to be confused with policy $\pi$ in @sec:S04-appendix-inference-mathematics |
| $\varepsilon$ | `$\varepsilon$` | Numerical tolerance for stochasticity checks; $\varepsilon = 10^{-9}$ (normalisation), $10^{-6}$ (validation) | @sec:thm-matrix-validity | `validate_shapes()` in `gnn/matrices.py` |
| $\xi$ | `$\xi$` | Evidence-labelled assertion tuple $(x, \kappa_\xi, c_\xi, \mathcal{P}_\xi)$ | @sec:def-evidence-labelled-assertion | Operational assertion emitted by translation, validation, review, or provenance tooling |
| $x$ | `$x$` | Target of an evidence-labelled assertion | @sec:def-evidence-labelled-assertion | Node, edge, or finite fragment |
| $\kappa_\xi$ | `$\kappa_\xi$` | Assertion kind for $\xi$ | @sec:def-evidence-labelled-assertion | Mapping kind, validation predicate, or structural property |
| $c_\xi$ | `$c_\xi$` | Confidence attached to assertion $\xi$ | @sec:def-evidence-labelled-assertion | Computed by @eq:confidence-core |
| $\mathcal{P}_\xi$ | `$\mathcal{P}_\xi$` | Finite provenance/evidence set for $\xi$ | @sec:def-evidence-labelled-assertion | Rule names, parser outputs, dynamic traces, reviewer markers, schema checks |
| $\preceq_e$ | `$\preceq_e$` | Evidence preorder over same-target assertions | @sec:def-evidence-labelled-assertion (@eq:evidence-preorder) | More recorded evidence/support, not higher semantic truth probability |

**Confidence tier thresholds** (`determine_confidence_tier` in `translate/confidence.py`):

| Tier | Threshold | Evidence requirement |
|------|-----------|---------------------|
| `STATIC_PLUS_RUNTIME` | $c \geq 0.65$, both static and dynamic evidence | Highest; promoted from STATIC\_ONLY after enrichment |
| `STATIC_ONLY` | $c \geq 0.5$, static evidence only | Default for unenriched runs |
| `RUNTIME_ONLY` | $c \geq 0.4$, dynamic evidence only | No corroborating static rule match |
| `HUMAN_REVIEWED` | $c \geq 0.9$, with human-review evidence marker | Manually curated mappings |

The current distribution of emitted score tiers for the calculator fixture is
shown in @fig:cogant-confidence-calibration
(@sec:04-examples-and-failure-modes) alongside rule contributions, conflicts,
and reviewer-annotation coverage. In the shipped calculator artifact, reviewed
rows are absent, so the figure is a review-readiness view rather than a
calibration curve. Buckets near $c = 0.5$ remain operationally important
because threshold movement in that band can change the state-space surface.

---

## A/B/C/D matrix symbols {#sec:98-abcd-matrix-symbols}

| Symbol | LaTeX | Meaning | First defined | Notes |
|--------|-------|---------|---------------|-------|
| $\mathbf{V}$ | `$\mathbf{V}$` | Set of hidden-state variables | @sec:def-abcd-matrices | Identified from WRITES edges |
| $\mathbf{O}$ | `$\mathbf{O}$` | Set of observation modalities | @sec:def-abcd-matrices | From OBSERVATION-kind mappings |
| $\mathbf{A}$ | `$\mathbf{A}$` | Set of actions (control states) | @sec:def-abcd-matrices | From ACTION-kind mappings |
| $A$ | `$A$` | Likelihood matrix; $A \in \mathbb{R}^{|\mathbf{O}| \times |\mathbf{V}|}$ | @sec:def-abcd-matrices (@eq:matrices-defn) | $A_{ij} = P(o_i \mid s_j)$; columns sum to 1 |
| $B$ | `$B$` | State-transition tensor; $B \in \mathbb{R}^{|\mathbf{V}| \times |\mathbf{V}| \times |\mathbf{A}|}$ | @sec:def-abcd-matrices (@eq:matrices-defn) | $B_{ijk} = P(s'_i \mid s_j, a_k)$; columns sum to 1 |
| $C$ | `$C$` | Log-preference vector; $C \in \mathbb{R}^{|\mathbf{O}|}$ | @sec:def-abcd-matrices (@eq:matrices-defn) | $C_i = \log \tilde{P}(o_i)$; not normalised |
| $D$ | `$D$` | Prior over initial hidden states; $D \in \mathbb{R}^{|\mathbf{V}|}$ | @sec:def-abcd-matrices (@eq:matrices-defn) | $D_j = P(s_j \mid t=0)$; sums to 1 |
| $s_j$ | `$s_j$` | Hidden state $j$ | @sec:S04-pomdp-formulation | Element of $S = \{s_1, \ldots, s_{|S|}\}$ |
| $o_i$ | `$o_i$` | Observation $i$ | @sec:S04-pomdp-formulation | Element of $O = \{o_1, \ldots, o_{|O|}\}$ |
| $a_k$ | `$a_k$` | Action / control state $k$ | @sec:S04-pomdp-formulation | Element of $A \subseteq \{1, \ldots, |A|\}$ |
| $\pi$ | `$\pi$` | Policy; finite action sequence $(a_0, \ldots, a_{T-1}) \in A^T$ | @sec:S04-pomdp-formulation | Not to be confused with conflict penalty $\pi$ in @sec:98-confidence-symbols |
| $T$ | `$T$` | Planning horizon (number of time steps) | @sec:S04-pomdp-formulation | |
| $Q(s)$ | `$Q(s)$` | Approximate posterior over hidden states | @sec:S04-variational-free-energy | Variational distribution |
| $P(o, s)$ | `$P(o, s)$` | Joint generative model; $= A[o,s] \cdot D[s]$ | @sec:S04-variational-free-energy | |
| $F[Q]$ | `$F[Q]$` | Variational free energy (VFE) | @sec:S04-variational-free-energy | $F[Q] = \mathbb{E}_{Q(s)}[\log Q(s) - \log P(o,s)]$ |
| $G(\pi)$ | `$G(\pi)$` | Expected free energy (EFE) for policy $\pi$ | @sec:S04-expected-free-energy | $G(\pi) = \sum_\tau [\text{risk}(\pi,\tau) + \text{ambiguity}(\pi,\tau)]$ |
| $H[Q(s)]$ | `$H[Q(s)]$` | Shannon entropy of approximate posterior | @sec:S04-variational-free-energy | Ambiguity term in VFE decomposition |
| $\alpha$ | `$\alpha$` | A-matrix count-update learning rate in the runtime helper | @sec:S04-d-update-convergence | `update_A_from_counts(learning_rate=...)`; D uses a running posterior mean |
| $D^{(k)}$ | `$D^{(k)}$` | Prior after $k$ learning episodes | @sec:S04-d-update-convergence | Running arithmetic mean of normalized episode posteriors |

---

## Category-theory and Galois-style comparison symbols {#sec:98-category-theory-symbols}

| Symbol | LaTeX | Meaning | First defined | Notes |
|--------|-------|---------|---------------|-------|
| **Prog** | `**Prog**` | Comparison category/preorder quotient of typed Python program graphs | @sec:S03-categories | Morphisms are label-preserving graph homomorphisms; approximate claims use the subset preorder quotient |
| **GNN** | `**GNN**` | Comparison category/preorder quotient of GNN v1.1 bundles | @sec:S03-categories | Morphisms are role-preserving bundle embeddings; approximate claims use bundle-section inclusion |
| $\mathbf{Mset}$ | `$\mathbf{Mset}$` | Category of multisets | @sec:S03-role-multiset-functor | Target vocabulary for role-multiset map $\rho$ |
| $F$ | `$F$` | Forward order-preserving map; $F : \mathbf{Prog} \to \mathbf{GNN}$ on preorder quotients | @sec:S03-forward-reverse-functors | Realised by `cogant translate` |
| $R$ | `$R$` | Reverse order-preserving map; $R : \mathbf{GNN} \to \mathbf{Prog}$ on preorder quotients | @sec:S03-forward-reverse-functors | Realised by `cogant reverse` then re-parse |
| $\rho$ | `$\rho$` | Role-multiset map; maps $G$ to its role distribution | @sec:S03-role-multiset-functor | $\rho : \mathbf{Prog} \to \mathbf{Mset}(\text{Roles})$ |
| $\rho_\text{norm}$ | `$\rho_\text{norm}$` | Normalised role distribution (probability vector over Roles) | @sec:S03-role-preservation-theorem | Used in JS-distance formula |
| $s_\text{role}(P, R(F(P)))$ | `$s_\text{role}(P, R(F(P)))$` | Roundtrip role-preservation score; multiset similarity between role distributions | @sec:S03-role-preservation-theorem (@sec:thm-bounded-role-preservation-gap) | Higher is better; ROLE_PRESERVED when $s_\text{role} \ge {{THRESHOLD_ROLE_PRESERVED}}$ |
| $\text{JS}$ | `$\text{JS}$` | Jensen–Shannon distance | @sec:S03-role-preservation-theorem | Symmetric; $\text{JS} \in [0, 1]$ |
| $\text{multiset\_sim}(a, b)$ | `$\text{multiset\_sim}(a,b)$` | Per-role multiset similarity; $\min(a,b)/\max(a,b)$ | @sec:S03-approximate-adjunction | Averaged over roles to yield global score |
| $\text{scaffold}_r$ | `$\text{scaffold}_r$` | Fixed role-$r$ count contributed by reverse synthesizer scaffolding | @sec:S03-approximate-adjunction, @sec:S03-role-preservation-theorem | Wave-16 POLICY/CONTEXT fix reduces this for policy-bearing targets |
| $\varepsilon_\text{worst}$ | `$\varepsilon_\text{worst}$` | Worst-case approximation gap; depends only on rule table and synthesizer | @sec:S03-approximate-adjunction | Bounded; approaches 0 for large programs |
| $\leq_\text{GNN}$ | `$\leq_\text{GNN}$` | Pointwise bundle subset order in **GNN** | @sec:S03-categories | Each bundle section is subset-ordered |
| $\leq_\text{Prog}$ | `$\leq_\text{Prog}$` | Pointwise graph subset order in **Prog** | @sec:S03-categories | $G \leq G'$ iff $V \subseteq V'$, $E \subseteq E'$ |

**Roundtrip status thresholds** (from `METRICS.yaml`):

| Label | Threshold | Meaning |
|-------|-----------|---------|
| `STRUCTURALLY_ISOMORPHIC` | all invariant-ledger checks pass | Node/edge counts, edge kinds, matrices, GNN sections, generated code, and roles are preserved |
| `ROLE_PRESERVED` | $s_\text{role} \ge {{THRESHOLD_ROLE_PRESERVED}}$ | Origin role distribution survives roundtrip at the configured public threshold or better |
| `DRIFT` | generated code runs but invariants fall below role-preserved tier | Roundtrip completed with measurable semantic or structural drift |
| `FAILED` | compile/import/test or forward pass failed | Roundtrip did not produce a usable regenerated artifact |

---

## Equation and scoped-claim index {#sec:98-equation-theorem-index}

### Equations

| Label | Location | Description |
|-------|----------|-------------|
| `eq:typed-iso` | @eq:typed-iso | Typed graph isomorphism: $(u,v)\in E_1 \iff (\phi(u),\phi(v))\in E_2$ |
| `eq:evidence-preorder` | @eq:evidence-preorder | Evidence preorder: $\xi_1 \preceq_e \xi_2$ iff confidence and provenance support both increase |
| `eq:fixpoint-operator` | @sec:def-fixpoint-semantics | Rule-application operator $F_{G,R}(S) = S \cup \{\ldots\}$ |
| `eq:kleene-chain` | @sec:thm-fixpoint-termination | Kleene ascending chain $\emptyset \subseteq F_{G,R}(\emptyset) \subseteq \cdots$ |
| `eq:least-fixpoint` | @sec:def-fixpoint-semantics | Least fixpoint $T^*(G) = \bigsqcup_{k\geq 0} F_{G,R}^k(\emptyset)$ |
| `eq:markov-partition` | @sec:def-markov-blanket-partition | Four-way partition $\Pi_{G,S}(v) \in \{\mu, s, a, \eta\}$ |
| `eq:matrices-defn` | @sec:def-abcd-matrices | A/B/C/D generative-model matrix definitions |
| `eq:confidence-core` | @sec:02-03-confidence-scoring | Confidence formula $c = \max(0, \min(1, (\bar{e}+\delta_d)\cdot\kappa - \pi))$ |

### Algorithms

| Label | Location | Description |
|-------|----------|-------------|
| Fixpoint translation algorithm | @sec:alg-fixpoint-translation-engine | Translation fixpoint loop (`TranslationEngine.translate()`) |
| Conflict-resolution algorithm | @sec:alg-conflict-resolution | Conflict resolution (`_resolve_conflicts()`, sorted by $(p_r, c)$) |

### Theorems, propositions, conjectures, and scoped invariants

| Label | Location | Description |
|-------|----------|-------------|
| Fixpoint termination theorem | @sec:thm-fixpoint-termination | **Fixpoint termination** — Kleene chain stabilises in $\leq n \cdot |\mathcal{K}_M|$ steps |
| Markov blanket completeness theorem | @sec:thm-markov-blanket-completeness | **Markov blanket completeness** — $\Pi_{G,S}$ is total and mutually exclusive |
| Matrix validity theorem | @sec:thm-matrix-validity | **Matrix validity** — $A$, $B$, $D$ satisfy stochasticity within $10^{-6}$ |
| Approximate Galois conjecture | @sec:prop-approximate-galois | **ε-approximate Galois comparison** — $(F, R)$ pair is conjectured to satisfy a role-quotient approximate adjunction |
| Role-preservation bound | @sec:thm-bounded-role-preservation-gap | **Role preservation** — roundtrip role similarity is a scoped empirical invariant and multiset approximation to JS distance between normalised role distributions |
| Role-preservation-threshold proposition | @sec:prop-role-preservation-threshold | **ROLE_PRESERVED threshold** — $\text{multiset\_sim} \geq {{THRESHOLD_ROLE_PRESERVED}}$ corresponds to the configured public role-preservation floor |

---

## Active Inference roles and mapping kinds {#sec:98-active-inference-roles}

**`MappingKind` vs `SemanticRole`.** Translation rules emit `SemanticMapping.kind` values from the `MappingKind` enum in `cogant.schemas.semantic` (Active Inference subset plus structural kinds; see the table below). **`SemanticRole`** is a separate, larger vocabulary in `semantic_mapping.py` for graph-level annotations; do not conflate the two---formal definitions and the abstract appear in @sec:def-translation-rule and @sec:00-abstract.

### Seven Active Inference roles (elements of $\text{Roles}$)

| Role | Mapping kind | Typical program entity |
|------|--------------|----------------------|
| `HIDDEN_STATE` | HIDDEN\_STATE | Class modelling internal mutable state |
| `OBSERVATION` | OBSERVATION | Read-only input parameter, logging call, sensor method |
| `ACTION` | ACTION | Mutating method, actuator function, API endpoint write |
| `POLICY` | POLICY | Control-flow orchestrator, decision procedure |
| `PREFERENCE` | PREFERENCE | Objective function, metric target, reward signal |
| `CONSTRAINT` | CONSTRAINT | Validator, guard clause, precondition |
| `CONTEXT` | CONTEXT | Configuration object, environment adapter, runtime context |

### Additional mapping kinds (not Active Inference roles)

| Mapping kind | Typical source entity |
|--------------|----------------------|
| `DATA_FLOW` | Pipeline stage, transform function |
| `ERROR_HANDLING` | Exception handler, retry decorator |
| `CIRCUIT_BREAKER` | Fallback pattern, circuit-breaker implementation |
| `ORCHESTRATION` | Top-level workflow coordinator |

**Formal $\mathcal{K}_M$** (the 11 Active-Inference mapping kinds used in the theory): HIDDEN\_STATE, OBSERVATION, ACTION, POLICY, PREFERENCE, CONSTRAINT, CONTEXT, DATA\_FLOW, ERROR\_HANDLING, CIRCUIT\_BREAKER, ORCHESTRATION. The code `MappingKind` enum in `cogant.schemas.semantic` defines **14** members in total --- the 11 formal kinds above plus three implementation kinds (`CONTROL\_FLOW`, `RETRY\_PATTERN`, `FEATURE\_FLAG`) that translation rules may emit but that are outside the formal alphabet $\mathcal{K}_M$.

---

## Node and edge kind enumerations {#sec:98-node-edge-kind-enumerations}

These are the canonical members of `cogant.schemas.core.NodeKind` and `EdgeKind` as of v{{VERSION}}. @sec:def-program-graph notes that the Python front end currently emits a subset (MODULE, CLASS, METHOD, FUNCTION for node kinds; CALLS, CONTAINS, READS, WRITES, IMPORTS, INHERITS for edge kinds); the remaining kinds are declared in the schema and emitted by other parsers or dynamic enrichment.

### NodeKind (18 members)

`REPO`, `MODULE`, `FILE`, `CLASS`, `FUNCTION`, `METHOD`, `VARIABLE`, `ENDPOINT`, `EVENT`, `PARAMETER`, `RETURN_VALUE`, `DATA_STRUCTURE`, `CONFIGURATION`, `FEATURE_FLAG`, `TEST`, `ASSERTION`, `POLICY`, `ACTION`

### EdgeKind (18 members)

`CONTAINS`, `IMPORTS`, `INHERITS`, `IMPLEMENTS`, `DEPENDS_ON`, `READS`, `WRITES`, `RETURNS`, `CALLS`, `THROWS`, `CATCHES`, `YIELDS`, `OBSERVES`, `MUTATES`, `GUARDS`, `TRIGGERS`, `EVIDENCE_FROM_STATIC`, `EVIDENCE_FROM_DYNAMIC`

---

## Acronyms {#sec:98-acronyms}

| Acronym | Expansion | Where used |
|---------|-----------|-----------|
| GNN | Generalized Notation Notation (Active Inference Institute specification) | Throughout — **not** Graph Neural Network |
| COGANT | Codebase-to-GNN Translation engine | Throughout |
| VFE | Variational Free Energy | @sec:S04-appendix-inference-mathematics (@sec:S04-variational-free-energy) |
| EFE | Expected Free Energy | @sec:S04-expected-free-energy |
| POMDP | Partially Observable Markov Decision Process | @sec:02-03-state-space-and-behavior, @sec:S04-appendix-inference-mathematics (@sec:S04-pomdp-formulation) |
| IR | Intermediate Representation | @sec:03-api-and-workflows, @sec:06-experimental-setup |
| AST | Abstract Syntax Tree | @sec:03-api-and-workflows, @sec:06-02-exports-parser-and-ir-stages |
| CFG | Control Flow Graph | @sec:02-01-formal-definitions, @sec:06-02-exports-parser-and-ir-stages |
| DFG | Data Flow Graph | @sec:02-01-formal-definitions |
| CPG | Code Property Graph | @sec:02-01-formal-definitions, @sec:08-scope-and-related-work |
| AII | Active Inference Institute | @sec:01-introduction, @sec:06-experimental-setup |
| KL | Kullback–Leibler (divergence) | @sec:S04-variational-free-energy |
| JS | Jensen–Shannon (distance/divergence) | @sec:S03-role-preservation-theorem |
| SCA | Static Code Analysis | @sec:08-scope-and-related-work |
| GNN (pkg) | PyG / DGL graph neural network packages | @sec:08-scope-and-related-work — context disambiguates |
| PyMDP | Python implementation of active inference | @sec:02-03-state-space-and-behavior, @sec:S04-appendix-inference-mathematics |


*This supplement is maintained as `98_notation_supplement.md` in the manuscript directory. The `98_` prefix places it in the glossary discovery bucket (see `AGENTS.md` for section ordering), after all main narrative sections and appendices. Update this file whenever a new symbol is introduced in the manuscript or a definition is revised.*
