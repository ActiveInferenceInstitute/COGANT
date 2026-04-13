# Notation Supplement

This supplement is the **canonical reference for every mathematical symbol, acronym, and formal object** used across the COGANT manuscript. When a symbol appears in multiple sections, this table resolves any apparent conflict — if the manuscript prose and this supplement disagree, update the prose to match the definitions here. Where entries are derived from code, the canonical source is the Python module listed in the Notes column; if the code is authoritative, so is the module.

Cross-references use the equation, definition, and theorem numbers from the main sections and appendices. Section numbers follow manuscript discovery order (see `AGENTS.md`).

---

## G.1 Program graph symbols

| Symbol | LaTeX | Meaning | First defined | Notes |
|--------|-------|---------|---------------|-------|
| $G$ | `$G$` | Program graph | §2.2 Def. 1 | Tuple $(V, E, \lambda_V, \lambda_E, \tau)$ |
| $V$ | `$V$` | Finite set of program nodes | §2.2 Def. 1 | Modules, classes, methods, functions, … |
| $E$ | `$E$` | Finite set of typed directed edges; $E \subseteq V \times V \times K$ | §2.2 Def. 1 | Drawn from edge-kind alphabet $K$ |
| $K$ | `$K$` | Edge-kind alphabet (18 kinds) | §2.2 Def. 1 | See G.8 for full enumeration |
| $\mathcal{N}$ | `$\mathcal{N}$` | Node-kind alphabet (18 kinds) | §2.2 Def. 1 | See G.8 for full enumeration |
| $\lambda_V$ | `$\lambda_V$` | Node-kind labelling function; $\lambda_V : V \to \mathcal{N}$ | §2.2 Def. 1 | |
| $\lambda_E$ | `$\lambda_E$` | Edge-kind labelling function; $\lambda_E : E \to K$ | §2.2 Def. 1 | Trivial projection onto edge kind |
| $\tau$ | `$\tau$` | Type annotation map; $\tau : V \to (T \cup \{\bot\})$ | §2.2 Def. 1 | $\bot$ when no annotation available |
| $T$ | `$T$` | Set of type strings recovered from front end | §2.2 Def. 1 | |
| $\bot$ | `$\bot$` | Missing/unavailable type annotation | §2.2 Def. 1 | Lattice bottom |
| $\phi$ | `$\phi$` | Graph isomorphism bijection; $\phi : V_1 \to V_2$ | §2.2 (Eq. \ref{eq:typed-iso}) | Accepted when it preserves adjacency |
| $G_1, G_2$ | `$G_1, G_2$` | Two program graphs under structural comparison | §2.2 (Eq. \ref{eq:typed-iso}) | |
| $N^{\text{in}}(v)$ | `$N^{\text{in}}(v)$` | In-neighbour set of node $v$; $\{u : (u,v,k) \in E\}$ | §2.2 Def. 4 | Computed in $O(\|V\|+\|E\|)$ |
| $N^{\text{out}}(v)$ | `$N^{\text{out}}(v)$` | Out-neighbour set of node $v$; $\{u : (v,u,k) \in E\}$ | §2.2 Def. 4 | |
| $S$ | `$S$` | Seed set for Markov blanket partition; $S \subseteq V$ | §2.2 Def. 4 | Selected by one of five strategies |
| $\Pi_{G,S}$ | `$\Pi_{G,S}$` | Markov blanket partition function; $\Pi_{G,S} : V \to \{\mu, s, a, \eta\}$ | §2.2 Def. 4 (Eq. \ref{eq:markov-partition}) | Total and mutually exclusive (Theorem 2) |
| $\mu$ | `$\mu$` | Internal (autonomous) node role | §2.2 Def. 4 | In seed; all neighbours also in seed |
| $s$ | `$s$` | Sensory node role | §2.2 Def. 4 | In seed; receives input from outside seed |
| $a$ | `$a$` | Active node role | §2.2 Def. 4 | In seed; sends output outside seed |
| $\eta$ | `$\eta$` | External node role | §2.2 Def. 4 | Not in seed |

---

## G.2 Translation engine symbols

| Symbol | LaTeX | Meaning | First defined | Notes |
|--------|-------|---------|---------------|-------|
| $r$ | `$r$` | Translation rule quadruple $({\varphi_r, \kappa_r, w_r, p_r})$ | §2.2 Def. 2 | 22 shipped rules in 5 families (5+5+3+4+5; three added in wave-21) |
| $\varphi_r$ | `$\varphi_r$` | Rule match predicate; $\varphi_r : \mathcal{G} \to 2^{\mathcal{F}}$ | §2.2 Def. 2 | `matches(graph, query)` in code |
| $\mathcal{G}$ | `$\mathcal{G}$` | Universe of finite program graphs | §2.2 Def. 2 | |
| $\mathcal{F}$ | `$\mathcal{F}$` | Fragment space (finite tuples of node/edge ids) | §2.2 Def. 2 | |
| $\kappa_r$ | `$\kappa_r$` | Mapping kind assigned by rule $r$ | §2.2 Def. 2 | Element of $\mathcal{K}_M$; see G.7 |
| $\mathcal{K}_M$ | `$\mathcal{K}_M$` | Mapping-kind alphabet (11 kinds) | §2.2 Def. 2 | See G.7 for full enumeration |
| $w_r$ | `$w_r$` | Base confidence weight of rule $r$; $w_r \in (0, 1]$ | §2.2 Def. 2 | |
| $p_r$ | `$p_r$` | Rule priority; $p_r \in \mathbb{Z}$ | §2.2 Def. 2 | Higher wins in conflict resolution |
| $R$ | `$R$` | Finite rule set; $|R| = 19$ for the shipped engine | §2.2 Def. 3 | |
| $\mathcal{M}$ | `$\mathcal{M}$` | Universe of possible semantic mappings on $G$ under $R$ | §2.2 Def. 3 | $\|\mathcal{M}\| \leq n \cdot \|\mathcal{K}_M\|$ |
| $F_{G,R}$ | `$F_{G,R}$` | Rule-application operator; $F_{G,R} : 2^{\mathcal{M}} \to 2^{\mathcal{M}}$ | §2.2 Def. 3 (Eq. \ref{eq:fixpoint-operator}) | Monotone on $(2^{\mathcal{M}}, \subseteq)$ |
| $T^{*}(G)$ | `$T^{*}(G)$` | Translation of $G$ under $R$; least fixpoint $\bigsqcup_{k \geq 0} F_{G,R}^k(\emptyset)$ | §2.2 Def. 3 (Eq. \ref{eq:least-fixpoint}) | |
| $K$ | `$K$` | Iteration cap; default $K = 10$ | §2.2, Theorem 1 | `max_iterations` in `engine.py` |
| $n$ | `$n$` | Number of nodes in program graph; $n = \|V\|$ | §2.2 Theorem 1 | |
| $k$ | `$k$` | Number of rules; $k = \|R\|$ | §2.2 Theorem 1 | |
| $(p(\mu), c(\mu))$ | `$(p(\mu), c(\mu))$` | Conflict-resolution key: (priority, confidence) for mapping $\mu$ | §2.2 Def. 2, Alg. 2 | Higher priority wins; confidence breaks ties |
| $\rho$ | `$\rho$` | Role-multiset functor $\rho : \mathbf{Prog} \to \mathbf{Mset}(\text{Roles})$ | App. C §C.3 | Counts role assignments per node |

---

## G.3 Confidence model symbols

| Symbol | LaTeX | Meaning | First defined | Notes |
|--------|-------|---------|---------------|-------|
| $c$ | `$c$` | Confidence score; $c \in [0, 1]$ | §2.3 (Eq. \ref{eq:confidence-core}) | `ConfidenceModel` in `translate/confidence.py` |
| $\bar{e}$ | `$\bar{e}$` | Mean evidence confidence over provenance records | §2.3 (Eq. \ref{eq:confidence-core}) | |
| $\delta_d$ | `$\delta_d$` | Evidence-diversity bonus (bounded, scaled) | §2.3 (Eq. \ref{eq:confidence-core}) | Raised by dynamic enrichment |
| $\kappa$ | `$\kappa$` | Parser certainty factor; applied multiplicatively | §2.3 (Eq. \ref{eq:confidence-core}) | $\kappa \in [0, 1]$ |
| $\pi$ | `$\pi$` | Aggregate conflict penalties (subtracted post-scaling) | §2.3 (Eq. \ref{eq:confidence-core}) | Not to be confused with policy $\pi$ in §D |
| $\varepsilon$ | `$\varepsilon$` | Numerical tolerance for stochasticity checks; $\varepsilon = 10^{-9}$ (normalisation), $10^{-6}$ (validation) | §2.2 Theorem 3 | `validate_shapes()` in `gnn/matrices.py` |

**Confidence tier thresholds** (`determine_confidence_tier` in `translate/confidence.py`):

| Tier | Threshold | Evidence requirement |
|------|-----------|---------------------|
| `STATIC_PLUS_RUNTIME` | $c \geq 0.65$, both static and dynamic evidence | Highest; promoted from STATIC\_ONLY after enrichment |
| `STATIC_ONLY` | $c \geq 0.5$, static evidence only | Default for unenriched runs |
| `RUNTIME_ONLY` | $c \geq 0.4$, dynamic evidence only | No corroborating static rule match |
| `HUMAN_REVIEWED` | $c \geq 0.9$, with human-review evidence marker | Manually curated mappings |

---

## G.4 A/B/C/D matrix symbols

| Symbol | LaTeX | Meaning | First defined | Notes |
|--------|-------|---------|---------------|-------|
| $\mathbf{V}$ | `$\mathbf{V}$` | Set of hidden-state variables | §2.2 Def. 5 | Identified from WRITES edges |
| $\mathbf{O}$ | `$\mathbf{O}$` | Set of observation modalities | §2.2 Def. 5 | From OBSERVATION-kind mappings |
| $\mathbf{A}$ | `$\mathbf{A}$` | Set of actions (control states) | §2.2 Def. 5 | From ACTION-kind mappings |
| $A$ | `$A$` | Likelihood matrix; $A \in \mathbb{R}^{|\mathbf{O}| \times |\mathbf{V}|}$ | §2.2 Def. 5 (Eq. \ref{eq:matrices-defn}) | $A_{ij} = P(o_i \mid s_j)$; columns sum to 1 |
| $B$ | `$B$` | State-transition tensor; $B \in \mathbb{R}^{|\mathbf{V}| \times |\mathbf{V}| \times |\mathbf{A}|}$ | §2.2 Def. 5 (Eq. \ref{eq:matrices-defn}) | $B_{ijk} = P(s'_i \mid s_j, a_k)$; columns sum to 1 |
| $C$ | `$C$` | Log-preference vector; $C \in \mathbb{R}^{|\mathbf{O}|}$ | §2.2 Def. 5 (Eq. \ref{eq:matrices-defn}) | $C_i = \log \tilde{P}(o_i)$; not normalised |
| $D$ | `$D$` | Prior over initial hidden states; $D \in \mathbb{R}^{|\mathbf{V}|}$ | §2.2 Def. 5 (Eq. \ref{eq:matrices-defn}) | $D_j = P(s_j \mid t=0)$; sums to 1 |
| $s_j$ | `$s_j$` | Hidden state $j$ | App. D §D.1 | Element of $S = \{s_1, \ldots, s_{|S|}\}$ |
| $o_i$ | `$o_i$` | Observation $i$ | App. D §D.1 | Element of $O = \{o_1, \ldots, o_{|O|}\}$ |
| $a_k$ | `$a_k$` | Action / control state $k$ | App. D §D.1 | Element of $A \subseteq \{1, \ldots, |A|\}$ |
| $\pi$ | `$\pi$` | Policy; finite action sequence $(a_0, \ldots, a_{T-1}) \in A^T$ | App. D §D.1 | Not to be confused with conflict penalty $\pi$ in §G.3 |
| $T$ | `$T$` | Planning horizon (number of time steps) | App. D §D.1 | |
| $Q(s)$ | `$Q(s)$` | Approximate posterior over hidden states | App. D §D.2 | Variational distribution |
| $P(o, s)$ | `$P(o, s)$` | Joint generative model; $= A[o,s] \cdot D[s]$ | App. D §D.2 | |
| $F[Q]$ | `$F[Q]$` | Variational free energy (VFE) | App. D §D.2 | $F[Q] = \mathbb{E}_{Q(s)}[\log Q(s) - \log P(o,s)]$ |
| $G(\pi)$ | `$G(\pi)$` | Expected free energy (EFE) for policy $\pi$ | App. D §D.7 | $G(\pi) = \sum_\tau [\text{risk}(\pi,\tau) + \text{ambiguity}(\pi,\tau)]$ |
| $H[Q(s)]$ | `$H[Q(s)]$` | Shannon entropy of approximate posterior | App. D §D.2 | Ambiguity term in VFE decomposition |
| $\alpha$ | `$\alpha$` | D-update learning rate; default $\alpha = 0.9$ | App. D §D.6 | `update_prior_from_episodes(alpha=0.9)` |
| $D^{(k)}$ | `$D^{(k)}$` | Prior after $k$ learning episodes | App. D §D.6 | Converges geometrically with ratio $\alpha$ |

---

## G.5 Category-theory and Galois connection symbols

| Symbol | LaTeX | Meaning | First defined | Notes |
|--------|-------|---------|---------------|-------|
| **Prog** | `**Prog**` | Category of typed Python program graphs | App. C §C.1 | Morphisms are label-preserving graph homomorphisms |
| **GNN** | `**GNN**` | Category of GNN v1.1 bundles | App. C §C.1 | Morphisms are role-preserving bundle embeddings |
| $\mathbf{Mset}$ | `$\mathbf{Mset}$` | Category of multisets | App. C §C.3 | Target of role-multiset functor $\rho$ |
| $F$ | `$F$` | Forward functor; $F : \mathbf{Prog} \to \mathbf{GNN}$ | App. C §C.2 | Realised by `cogant translate` |
| $R$ | `$R$` | Reverse functor; $R : \mathbf{GNN} \to \mathbf{Prog}$ | App. C §C.2 | Realised by `cogant reverse` then re-parse |
| $\rho$ | `$\rho$` | Role-multiset functor; maps $G$ to its role distribution | App. C §C.3 | $\rho : \mathbf{Prog} \to \mathbf{Mset}(\text{Roles})$ |
| $\rho_\text{norm}$ | `$\rho_\text{norm}$` | Normalised role distribution (probability vector over Roles) | App. C §C.5 | Used in JS-distance formula |
| $\varepsilon(P, R(F(P)))$ | `$\varepsilon(P, R(F(P)))$` | Roundtrip divergence; JS distance between normalised role distributions | App. C §C.5 (Theorem C.2) | Lower is better; ISOMORPHIC iff $\varepsilon \geq 0.8$ |
| $\text{JS}$ | `$\text{JS}$` | Jensen–Shannon distance | App. C §C.5 | Symmetric; $\text{JS} \in [0, 1]$ |
| $\text{multiset\_sim}(a, b)$ | `$\text{multiset\_sim}(a,b)$` | Per-role multiset similarity; $\min(a,b)/\max(a,b)$ | App. C §C.4 | Averaged over roles to yield global score |
| $\text{scaffold}_r$ | `$\text{scaffold}_r$` | Fixed role-$r$ count contributed by reverse synthesizer scaffolding | App. C §C.4, C.5 | Wave-16 POLICY/CONTEXT fix reduces this for policy-bearing targets |
| $\varepsilon_\text{worst}$ | `$\varepsilon_\text{worst}$` | Worst-case approximation gap; depends only on rule table and synthesizer | App. C §C.4 | Bounded; approaches 0 for large programs |
| $\leq_\text{GNN}$ | `$\leq_\text{GNN}$` | Pointwise bundle subset order in **GNN** | App. C §C.1 | Each bundle section is subset-ordered |
| $\leq_\text{Prog}$ | `$\leq_\text{Prog}$` | Pointwise graph subset order in **Prog** | App. C §C.1 | $G \leq G'$ iff $V \subseteq V'$, $E \subseteq E'$ |

**ε-isomorphism classification thresholds** (from `METRICS.yaml`):

| Label | Threshold | Meaning |
|-------|-----------|---------|
| `ISOMORPHIC` | $\text{multiset\_sim} \geq 0.8$ | Origin role distribution survives roundtrip at ≥ 80% |
| `APPROXIMATE` | $0.5 \leq \text{multiset\_sim} < 0.8$ | Partial role preservation |
| `DIVERGENT` | $\text{multiset\_sim} < 0.5$ | Significant role loss in roundtrip |

---

## G.6 Equation and theorem index

### Equations

| Label | Location | Description |
|-------|----------|-------------|
| `eq:typed-iso` | §2.2 | Typed graph isomorphism: $(u,v)\in E_1 \iff (\phi(u),\phi(v))\in E_2$ |
| `eq:fixpoint-operator` | §2.2 Def. 3 | Rule-application operator $F_{G,R}(S) = S \cup \{\ldots\}$ |
| `eq:kleene-chain` | §2.2 Theorem 1 | Kleene ascending chain $\emptyset \subseteq F_{G,R}(\emptyset) \subseteq \cdots$ |
| `eq:least-fixpoint` | §2.2 Def. 3 | Least fixpoint $T^*(G) = \bigsqcup_{k\geq 0} F_{G,R}^k(\emptyset)$ |
| `eq:markov-partition` | §2.2 Def. 4 | Four-way partition $\Pi_{G,S}(v) \in \{\mu, s, a, \eta\}$ |
| `eq:matrices-defn` | §2.2 Def. 5 | A/B/C/D generative-model matrix definitions |
| `eq:confidence-core` | §2.3 | Confidence formula $c = \max(0, \min(1, (\bar{e}+\delta_d)\cdot\kappa - \pi))$ |

### Algorithms

| Label | Location | Description |
|-------|----------|-------------|
| Algorithm 1 | §2.2 | Translation fixpoint loop (`TranslationEngine.translate()`) |
| Algorithm 2 | §2.2 | Conflict resolution (`_resolve_conflicts()`, sorted by $(p_r, c)$) |

### Theorems and propositions

| Label | Location | Description |
|-------|----------|-------------|
| Theorem 1 | §2.2 | **Fixpoint termination** — Kleene chain stabilises in $\leq n \cdot |\mathcal{K}_M|$ steps |
| Theorem 2 | §2.2 | **Markov blanket completeness** — $\Pi_{G,S}$ is total and mutually exclusive |
| Theorem 3 | §2.2 | **Matrix validity** — $A$, $B$, $D$ satisfy stochasticity within $10^{-6}$ |
| Proposition C.1 | App. C §C.4 | **ε-approximate Galois connection** — $(F, R)$ pair satisfies approximate adjunction |
| Theorem C.2 | App. C §C.5 | **ε-Isomorphism** — roundtrip divergence equals JS distance between normalised role distributions |
| Proposition C.3 | App. C §C.6 | **ISOMORPHIC threshold** — $\text{multiset\_sim} \geq 0.8$ corresponds to origin population ≥ 80% of synth |

---

## G.7 Active Inference roles and mapping kinds

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

**Full $\mathcal{K}_M$** (11 kinds): HIDDEN\_STATE, OBSERVATION, ACTION, POLICY, PREFERENCE, CONSTRAINT, CONTEXT, DATA\_FLOW, ERROR\_HANDLING, CIRCUIT\_BREAKER, ORCHESTRATION.

---

## G.8 Node and edge kind enumerations

These are the canonical members of `cogant.schemas.core.NodeKind` and `EdgeKind` as of v{{VERSION}}. The manuscript section §2.2 Definition 1 notes that the Python front end currently emits a subset (MODULE, CLASS, METHOD, FUNCTION for node kinds; CALLS, CONTAINS, READS, WRITES, IMPORTS, INHERITS for edge kinds); the remaining kinds are declared in the schema and emitted by other parsers or dynamic enrichment.

### NodeKind (18 members)

`REPO`, `MODULE`, `FILE`, `CLASS`, `FUNCTION`, `METHOD`, `VARIABLE`, `ENDPOINT`, `EVENT`, `PARAMETER`, `RETURN_VALUE`, `DATA_STRUCTURE`, `CONFIGURATION`, `FEATURE_FLAG`, `TEST`, `ASSERTION`, `POLICY`, `ACTION`

### EdgeKind (18 members)

`CONTAINS`, `IMPORTS`, `INHERITS`, `IMPLEMENTS`, `DEPENDS_ON`, `READS`, `WRITES`, `RETURNS`, `CALLS`, `THROWS`, `CATCHES`, `YIELDS`, `OBSERVES`, `MUTATES`, `GUARDS`, `TRIGGERS`, `EVIDENCE_FROM_STATIC`, `EVIDENCE_FROM_DYNAMIC`

---

## G.9 Acronyms

| Acronym | Expansion | Where used |
|---------|-----------|-----------|
| GNN | Generalized Notation Notation (Active Inference Institute specification) | Throughout — **not** Graph Neural Network |
| COGANT | Codebase-to-GNN Translation engine | Throughout |
| VFE | Variational Free Energy | §2.3, App. D §D.2 |
| EFE | Expected Free Energy | App. D §D.7 |
| POMDP | Partially Observable Markov Decision Process | §2.3, App. D §D.1 |
| IR | Intermediate Representation | §3, §6 |
| AST | Abstract Syntax Tree | §3, §6.2 |
| CFG | Control Flow Graph | §2.2, §6.2 |
| DFG | Data Flow Graph | §2.2 |
| CPG | Code Property Graph | §2.2, §8 |
| AII | Active Inference Institute | §1, §6 |
| KL | Kullback–Leibler (divergence) | App. D §D.2 |
| JS | Jensen–Shannon (distance/divergence) | App. C §C.5 |
| SCA | Static Code Analysis | §8 |
| GNN (pkg) | PyG / DGL graph neural network packages | §8 — context disambiguates |
| PyMDP | Python implementation of active inference | §2.3, App. D |

---

*This supplement is maintained as `98_notation_supplement.md` in the manuscript directory. The `98_` prefix places it in the glossary discovery bucket (see `AGENTS.md` §Section ordering), after all main narrative sections and appendices. Update this file whenever a new symbol is introduced in the manuscript or a definition is revised.*
