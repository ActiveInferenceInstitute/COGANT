# Glossary

> **What this page is:** Alphabetized definitions of every domain term used across COGANT — codebase, docs, and R&D notes — with module paths where the term is implemented.
>
> **Prerequisites:** None — designed for lookup, not linear reading.
>
> **Reading time:** ~5 minutes per lookup (or skim for one term)
>
> **Next steps:** [Core concepts](core_concepts.md) · [Active Inference for programmers](../concepts/active_inference.md) · [What is a GNN?](../concepts/gnn.md)

Alphabetized definitions of every domain term used across the COGANT codebase, docs, and
R&D notes. Where a term is implemented as a concrete Python object, the module path is given.

## Canonical conventions

The following spellings are **canonical** across COGANT documentation. Variants are wrong
and should be normalized on sight:

- Semantic roles are written **all caps**: `HIDDEN_STATE`, `OBSERVATION`, `ACTION`, `POLICY`,
  `CONSTRAINT`, `CONTEXT`. Lowercase prose forms ("the observation", "an action") are
  reserved for the underlying Active Inference concept, not the COGANT role label.
- Matrix names use a single capital letter, a space, and the lowercase noun: `A matrix`,
  `B matrix`, `C matrix`, `D matrix`. Never `A_matrix`, `a_matrix`, or `A-matrix`.
- The pipeline halves are `forward pipeline` and `reverse pipeline`. The bare phrases
  `forward pass` / `reverse pass` are reserved for the categorical / functorial framing in
  `evaluation/ISOMORPHISM_THEOREM.md`.
- `fixpoint` is one word. Never `fix-point` or `fixed point`.
- `ε` (epsilon) is the **role-preservation fidelity** of a roundtrip: `ε = |roles_preserved| / |roles_original|`. It is a ratio in `[0, 1]`, where `ε = 1.0` is a perfect roundtrip and `ε ≥ 0.8` is the ISOMORPHIC threshold. Canonical values live in `cogant/evaluation/METRICS.yaml`; current benchmark is 23/23 ISOMORPHIC, mean ε = 1.0.
- Roundtrip-fidelity tiers are `ISOMORPHIC`, `APPROXIMATE`, `DIVERGENT` (all caps).
- `Markov blanket` (uppercase M, lowercase b in prose; capitalized only in headings).
- `Galois connection` (uppercase G, lowercase c in prose; capitalized only in headings).
- `ε-bounded adjunction` (lowercase ε, hyphen, lowercase a).
- `GNN` **always** means *Generalized Notation Notation* (Active Inference Institute), never
  Graph Neural Network.
- Class / type names are CamelCase single tokens: `PackagePlan`, `ProgramGraph`,
  `ReverseGNNModel`. Never `package_plan`, `program_graph`, or `reverse_gnn_model`.

## A

**A matrix** — Likelihood matrix `P(o | s)`, shape `[n_obs × n_states]`. Encodes how hidden
states produce observations. The canonical spelling is `A matrix` (single capital letter,
space, lowercase noun); do **not** write `A_matrix`, `a_matrix`, or `A-matrix`. See
[`py/cogant/gnn/matrices.py`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/gnn/matrices.py).

**ACTION** — Semantic role for code that mutates hidden state. Detected by `ActionRule`.
The canonical capitalization is **ACTION** (all caps) when referring to the role; lowercase
"action" is reserved for the Active-Inference-theoretic action interpretation. Examples:
setter methods, `handle_request`, `dispatch`, event publishers. Maps to the **u** variables
in the GNN export.

**Action** — In Active Inference: the agent's active intervention on its environment. In
COGANT: any code patterning marked `ACTION`. See **ACTION**.

**Active Inference** — A framework from computational neuroscience (Friston et al.) in which
agents are modeled as probabilistic machines that minimize variational free energy. The
unifying theory that motivates COGANT's entire pipeline.

**Active Inference Institute (AII)** — The upstream maintainer of the GNN reference
specification COGANT targets. <https://activeinference.org/>.

**`ActInfOntologyAnnotation`** — One of the 19 sections in a GNN markdown file. Maps each
declared variable to an Active Inference ontology term (e.g. `HiddenStateFactor0`,
`PolicyVector`).

## B

**B matrix** — Transition tensor `P(s' | s, a)`, shape `[n_states × n_states × n_actions]`.
Encodes how actions change hidden state. Column-stochastic per AII convention. Falls back
to identity-per-action when the program graph has no `WRITES` evidence. Canonical spelling
is `B matrix`; do **not** write `B_matrix` or `b_matrix`.

**Blanket** — See **Markov blanket**.

**`BlanketRole`** — Enum in `py/cogant/markov/blanket.py` with four values: `INTERNAL`,
`SENSORY`, `ACTIVE`, `EXTERNAL`. The four roles that partition every graph node.

**Bracket notation** — The variable-declaration syntax used in GNN `StateSpaceBlock`:
`name[dim1,dim2,type=...]`.

## C

**C matrix** / **C vector** — Log-preference over observations, shape `[n_obs]`. Positive
means preferred, negative means aversive. Softmax is taken over `-C` when computing expected
free energy. Canonical spelling is `C matrix` (or `C vector` when the modality count is 1);
do **not** write `C_matrix` or `c_matrix`.

**Calibration** — The open R&D plan for empirically validating COGANT's confidence scores
against hand-labelled ground truth. See `../evaluation/CALIBRATION.md`.

**CIRCUIT_BREAKER** — Semantic role for code that guards a failure-prone call site with a
retry/backoff/fallback pattern. Detected by `CircuitBreakerRule`.

**COGANT** — "Codebase-to-GNN" translation engine. The package documented here.

**Confidence tier** — One of `HIGH`, `MEDIUM`, `LOW`, `VERY_LOW` assigned by
`ConfidenceModel` based on the rule's base score and available evidence. See
`py/cogant/schemas/semantic.py::ConfidenceTier`.

**Connection** — A directed edge in the GNN `Connections` section, e.g. `x_f0 > s_f0` ("the
hidden state emits the observation"). Not to be confused with an `EdgeKind` in the program
graph.

**CONSTRAINT** — Semantic role for validators, assertions, and tests. Detected by
`PreferenceRule` and `TestAssertionRule`. Contributes to the C matrix. The canonical
capitalization is **CONSTRAINT** (all caps); the historical reverse-pipeline planner prefix
`cnst_` is a stale internal artifact, not a canonical spelling — synthesizer output is
normalized to `check_*`.

**CONTEXT** — Semantic role for configuration, feature flags, and global state that
parameterize the system. Maps to the **D matrix** (initial-state prior) in the GNN export.
The canonical capitalization is **CONTEXT** (all caps).

**CONTAINS** — An `EdgeKind` representing lexical containment: a module contains a class,
a class contains its methods, and so on.

**`ContainmentRule`** — A translation rule that emits `CONTAINMENT` mappings for pairs of
nodes joined by a `CONTAINS` edge.

**Control rules** — The `control.py` rule family. Contains `ConfigRule`, `FeatureFlagRule`, and `ParameterRule`.

## D

**D matrix** / **D vector** — Initial-state prior `P(s_0)`, shape `[n_states]`. Uniform
fallback when no `CONFIGURATION` nodes exist. Canonical spelling is `D matrix` (or
`D vector`); do **not** write `D_matrix` or `d_matrix`.

**DAG** — Directed Acyclic Graph. The COGANT pipeline is expressed as a DAG of stages, each
with declared inputs and outputs.

**Determinism** — A hard invariant of the COGANT pipeline: given identical inputs and
configuration, every stage produces byte-identical output (modulo timestamps that are
stripped during validation).

## E

**`EdgeKind`** — Closed enum in `py/cogant/schemas/core.py`. Values include `CALLS`,
`CONTAINS`, `READS`, `WRITES`, `IMPORTS`, `INHERITS`, `OBSERVES`, `DEPENDS_ON`, `MUTATES`,
`CATCHES`, `THROWS`, `GUARDS`. These are the only relationships the graph can represent in
v0.1.0.

**ε** — Role-preservation fidelity (epsilon) of a forward → reverse → forward roundtrip on
a program graph. Defined as `ε = |roles_preserved| / |roles_original|`, so ε ∈ [0, 1] and
`ε = 1.0` is a perfect roundtrip (every original semantic role is recovered). The
ISOMORPHIC threshold is `ε ≥ 0.8`; below that the tiers are APPROXIMATE
(`0.5 ≤ ε < 0.8`) and DIVERGENT (`ε < 0.5`). Canonical current values live in
`cogant/evaluation/METRICS.yaml` (currently 23/23 ISOMORPHIC, mean ε = 1.0). An earlier
pre-wave-14 "error" formulation (where `ε_max = 0` meant exact recovery; see
`evaluation/ISOMORPHISM_THEOREM.md` §4) is preserved for theoretical context only. See also
ε-bounded adjunction.

**ε-bounded adjunction** — The categorical-strength claim that COGANT's forward and reverse
pipelines form a Galois connection whose roundtrip error is bounded by ε(G), with an
explicit upper bound derived from the rule table T. The structure is weaker than a full
adjunction (no unit/counit isomorphism) but stronger than a bare order-preserving map.

**Expected free energy (EFE)** — A forward-looking free-energy functional used to score
candidate action sequences (policies) in Active Inference. The planner picks the policy with
the lowest EFE.

**External state** — The η component of a Markov blanket: everything outside the system of
interest. Node role `BlanketRole.EXTERNAL`.

## F

**FEP** — See **Free Energy Principle**.

**Fixpoint** — A point at which iterated rule application produces no new mappings. The
canonical spelling across COGANT is `fixpoint` (one word). Do **not** write `fix-point` or
`fixed point`. See **Fixpoint engine**.

**Fixpoint engine** — The rule-application loop inside `TranslationEngine.translate()`. It
runs every registered rule until no new mappings are produced (convergence) or
`max_iterations` is reached.

**Forward pipeline** — The source-code → program-graph → semantic-mappings →
state-space-model → GNN package direction of the COGANT pipeline. Implemented under
`cogant.translate` and `cogant.gnn`. The categorical functor is written F : 𝒫 → 𝒢. Do
**not** write "forward pass" in operational documentation; reserve "forward pass" for the
formal categorical / functorial framing in `evaluation/ISOMORPHISM_THEOREM.md`.

**Free Energy Principle** — The theoretical claim that all self-organizing systems can be
described as minimizing variational free energy. Karl Friston's foundational framework.

## G

**Galois connection** — A pair of order-preserving maps (F, R) between two preorders
satisfying F(p) ≤ g  ⇔  p ≤ R(g). Weaker than a full categorical adjunction. COGANT's
forward and reverse pipelines form a Galois connection between program graphs and GNN
state-space models, with roundtrip error bounded by ε. See **ε-bounded adjunction** and
`evaluation/ISOMORPHISM_THEOREM.md`.

**GNN** — **Generalized Notation Notation**. The Active Inference Institute's reference
text format for generative-model specifications. Not to be confused with *Graph Neural
Network*. COGANT's GNN output is a directory with a bracket-notation markdown file plus
machine-readable JSON twins. Throughout this codebase the acronym **GNN always means
Generalized Notation Notation**, never Graph Neural Network. Where the JSON twins happen to
be structurally usable as input to a downstream graph-neural-network trainer, that is a
coincidence of representation, not a claim about COGANT's pipeline.

**`GNNMatrices`** — Class in `py/cogant/gnn/matrices.py`. Wraps a `ProgramGraph`, a list of
`SemanticMapping`, and a `StateSpaceModel`, and derives the **A matrix**, **B matrix**,
**C matrix**, and **D matrix** on demand.

**`GNNValidator`** — Class in `py/cogant/gnn/validator.py`. Scores a GNN package 0–100
against structural, shape, normalization, ontology, and fallback-disclosure checks.

**Generalized Notation Notation** — See **GNN**.

**Graph** — See **Program graph**.

## H

**HIDDEN_STATE** — Semantic role for code that holds mutable state hidden from the rest of
the program. Detected by `MutatingSubsystemRule`. Examples: classes with incoming `WRITES`
edges, caches, buffers, accumulators. Maps to the **x** variables in the GNN export.

**HIGH** — The top `ConfidenceTier`, assigned when a rule matches with direct structural
evidence and no heuristic fallback.

## I

**Ingest** — The first pipeline stage. Discovers files, applies size and exclude policies,
and attaches filesystem provenance.

**`InheritanceRule`** — A rule that tags classes with `INHERITS`-edge evidence. Depending on
the base class name, can assign roles like `POLICY` or `ERROR_HANDLING`.

**Internal state** — The μ component of a Markov blanket: everything inside the system of
interest with no direct external adjacency. Node role `BlanketRole.INTERNAL`.

**ISOMORPHIC** — The strictest of the three roundtrip-fidelity tiers. A roundtrip is
classified `ISOMORPHIC` when ε(G) = 0 — every node role is preserved exactly under the
forward → reverse → forward composition. Compare with **APPROXIMATE** and **DIVERGENT**.

**APPROXIMATE** — The middle roundtrip-fidelity tier. A roundtrip is classified
`APPROXIMATE` when 0 < ε(G) ≤ ε_max — some node roles are ambiguous, but the role-population
distribution is preserved within tolerance.

**DIVERGENT** — The weakest roundtrip-fidelity tier. A roundtrip is classified `DIVERGENT`
when ε(G) > ε_max — the synthesized program no longer reproduces the original role
distribution under re-ingestion. Indicates a structural failure of the rule table.

**Isomorphism** — The formal claim that a program and its generative-model interpretation
carry the same information, so the forward pipeline and reverse pipeline should be inverses
up to whitespace and naming. See `../evaluation/ISOMORPHISM_THEOREM.md`.

## K

**`KeywordMatch`** — A piece of evidence recorded by keyword-based rules like `ObservationRule`
and `ActionRule`. Format: `"keyword match: '<keyword>'"`.

## L

**`LanguagePlugin`** — Abstract base class for a parser plugin. See
`py/cogant/plugins/base.py`. Concrete plugins: `PythonPlugin`, `JavaScriptPlugin`,
`TypeScriptPlugin`.

**Likelihood** — `P(o | s)`. See **A matrix**.

## M

**`MappingKind`** — Enum of semantic roles: `HIDDEN_STATE`, `OBSERVATION`, `ACTION`,
`POLICY`, `CONSTRAINT`, `PREFERENCE`, `CONFIGURATION`, `CONTEXT`, `CIRCUIT_BREAKER`,
`ERROR_HANDLING`, `ORCHESTRATION`, `DATA_FLOW`, `CONTAINMENT`, and a few others. The full
list lives in `py/cogant/schemas/semantic.py`.

**Markov blanket** — The set `(s, a)` of sensory and active states that separates internal
states from external states. A conditional-independence boundary. In software, the dual of
information hiding.

**`MarkovBlanketExtractor`** — Class in `py/cogant/markov/extractor.py` with five
seed-selection strategies: `auto`, `module`, `class`, `subgraph`, `manual`.

**`MarkovBlanketPartitioner`** — Implicit partitioning primitive exposed as the pure
function `partition_by_seeds` in `py/cogant/markov/blanket.py`. Walks the undirected
projection of a `ProgramGraph` and labels every node.

**MEDIUM** — A `ConfidenceTier` assigned when a rule's evidence is partly heuristic (e.g.
the receiver type was inferred by import tracing rather than explicit annotation).

**`MutatingSubsystemRule`** — The structural rule that tags classes with incoming `WRITES`
edges as `HIDDEN_STATE`. Priority 80.

## N

**`NodeKind`** — Closed enum in `py/cogant/schemas/core.py`. v0.1.0 Python front end emits
four kinds: `MODULE`, `CLASS`, `METHOD`, `FUNCTION`. Additional kinds (`VARIABLE`,
`PARAMETER`, `TYPE_REFERENCE`, control-flow nodes) are roadmap P1-2 / P1-3.

## O

**OBSERVATION** — Semantic role for code that produces a read-only signal about hidden
state. Detected by `ObservationRule`. The canonical capitalization is **OBSERVATION** (all
caps) when referring to the role; lowercase "observation" is reserved for the
Active-Inference-theoretic signal interpretation.

**`ObservationRule`** — Semantic rule that tags getters and read-only functions as
`OBSERVATION`. Keyword set: `get`, `read`, `fetch`, `query`, `display`, `show`, `status`,
`info`, `list`.

**Observation** — In Active Inference: the sensory signal an agent receives. In COGANT:
any code patterning marked `OBSERVATION`. Maps to the **s** variables in the GNN export.

**Ontology annotation** — The mapping from GNN variable names to Active Inference ontology
terms. Section 8 of the GNN markdown.

## P

**`PackagePlan`** — Dataclass in `py/cogant/reverse/__init__.py` describing the directory
layout of a synthesized Python package. Produced by the reverse pipeline planner and
consumed by the synthesizer. The canonical spelling is `PackagePlan` (CamelCase, single
token); do not write `package_plan` or `Package Plan` in type-reference contexts.

**`ParseResult`** — Container returned by a `LanguagePlugin.parse_file()` call. Carries
`nodes`, `edges`, and `diagnostics`.

**PDG** — Program Dependence Graph. See **Program graph**.

**POLICY** — Semantic role for handler / controller / router classes and retry / circuit-
breaker patterns. Detected by `PolicyRule`, `RetryPatternRule`, and some applications of
`InheritanceRule`. The canonical capitalization is **POLICY** (all caps); lowercase "policy"
is reserved for the Active-Inference-theoretic action-sequence interpretation.

**Preference** — Positive entry in the C vector, or equivalently a `PREFERENCE` mapping.
The Active Inference equivalent of a goal.

**Priority** — Each `TranslationRule` has an integer priority. Higher priorities win
conflicts. Confidence is the tiebreaker when priorities are equal.

**Program graph** — The canonical intermediate representation produced by the graph stage.
A typed, directed property graph with `NodeKind`-labelled nodes and `EdgeKind`-labelled
edges. Instance of `py/cogant/schemas/graph.py::ProgramGraph`. The type-reference spelling
is `ProgramGraph` (CamelCase, single token); the prose phrase "program graph" is acceptable
when not naming the type. Do not write `program_graph` or `Program Graph` in code or type
contexts.

**Provenance** — Source-level attribution for every non-trivial mapping or matrix entry.
Recorded as file:line:col spans and stored in `provenance.json` in the GNN package.

## R

**`RetryPatternRule`** — Resilience-family rule that tags retry / backoff code with
`POLICY` and `CIRCUIT_BREAKER` mappings.

**Resilience rules** — The `resilience.py` rule family. Includes `RetryPatternRule`,
`ErrorBoundaryRule`, `SingletonAccessRule`, `CircuitBreakerRule`, `RateLimiterRule`.

**Reverse mode** — Synonym for **reverse pipeline**. Prefer "reverse pipeline" in operational
documentation.

**Reverse pipeline** — The GNN → code direction of COGANT. Implemented under
`cogant.reverse` (parser, planner, synthesizer, idempotency checker). The categorical
functor is written R : 𝒢 → 𝒫. Do **not** write "reverse pass" in operational
documentation; reserve "reverse pass" for the formal categorical / functorial framing in
`evaluation/ISOMORPHISM_THEOREM.md`. See [Tutorial 6](../tutorials/06_reverse_mode.md).

**`ReverseGNNModel`** — Wrapper class produced by the reverse pipeline. Holds the parsed
GNN package alongside the planner output (`PackagePlan`) and the metadata needed for the
synthesizer to emit an idempotent Python package. The canonical spelling is
`ReverseGNNModel` (CamelCase, single token); do not write `reverse_gnn_model` or
`Reverse GNN Model`.

**`RoundtripResult`** — Planned dataclass for the output of `cogant roundtrip`. Will carry
the original bundle, the synthesized bundle, and a structural diff. Not yet implemented.

**Rule** — A unit of the translation engine. Inherits from
`cogant.translate.engine.TranslationRule`. Implements `matches`, `apply`, and `explain`.

## S

**SDG** — System Dependence Graph. A generalization of the PDG that accounts for inter-
procedural dependencies. COGANT's `ProgramGraph` is structurally a program-level SDG.

**Semantic mapping** — An assertion that a specific node (or subgraph) in the program graph
plays a specific Active Inference role. Concretely: an instance of
`cogant.schemas.semantic.SemanticMapping`, carrying a `MappingKind`, evidence, confidence,
and provenance.

**Sensory state** — The **s** component of a Markov blanket: boundary nodes with incoming
edges from external states. Node role `BlanketRole.SENSORY`.

**`StateSpaceCompiler`** — Class in `py/cogant/statespace/compiler.py`. Consumes the
translation stage's `SemanticMapping` output and produces a numerical `StateSpaceModel`.

**`StateSpaceModel`** — Dataclass in `py/cogant/statespace/compiler.py`. Contains the
ordered lists of hidden-state variables, observation modalities, actions, transitions,
likelihoods, and preferences that the matrix builder consumes.

**Structural rules** — The `structural.py` rule family. Contains `ReadOnlyInputRule`,
`MutatingSubsystemRule`, `InheritanceRule`, `ContainmentRule`, `DataPipelineRule`.

## T

**`TranslationEngine`** — The fixpoint orchestrator in `py/cogant/translate/engine.py`.
Runs every registered `TranslationRule` until convergence or max-iterations.

**`TranslationRule`** — Abstract base class for a translation rule. See
`cogant.translate.engine.TranslationRule`.

**Tree-sitter** — The parser framework used for JavaScript and TypeScript (and any new
language plugin). <https://tree-sitter.github.io/>.

## V

**Variational free energy (VFE)** — The free-energy functional used for *inference*:
`F = KL[q(s) || p(s | o)] - log p(o)`. Active Inference agents minimize VFE to update their
beliefs about hidden state.

**`ViolationCheck`** — A validator helper that checks one structural invariant of a GNN
package (e.g. "A rows sum to 1.0"). Each check is a pure function returning a pass/fail
and an optional warning message.

## W

**WRITES** — The `EdgeKind` emitted by the graph builder whenever a method assigns to an
attribute. The primary evidence for `MutatingSubsystemRule` and the B matrix.

## See also

- [Active Inference primer](../theory/active_inference_primer.md)
- [Code as a generative model](../theory/code_as_generative_model.md)
- [GNN format reference](../theory/gnn_format_reference.md)
- [`py/cogant/schemas/`](https://github.com/cogant-contributors/cogant/tree/main/cogant/py/cogant/schemas) — the authoritative type definitions.
