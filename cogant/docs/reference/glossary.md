# Glossary

Alphabetized definitions of every domain term used across the COGANT codebase, docs, and
R&D notes. Where a term is implemented as a concrete Python object, the module path is given.

## A

**A matrix** — Likelihood matrix `P(o | s)`, shape `[n_obs × n_states]`. Encodes how hidden
states produce observations. See [`py/cogant/gnn/matrices.py`](../../py/cogant/gnn/matrices.py).

**Action** — An Active Inference role for code that mutates hidden state. Detected by
`ActionRule`. Examples: setter methods, `handle_request`, `dispatch`, event publishers.
Maps to the **u** variables in the GNN export.

**Active Inference** — A framework from computational neuroscience (Friston et al.) in which
agents are modeled as probabilistic machines that minimize variational free energy. The
unifying theory that motivates COGANT's entire pipeline.

**Active Inference Institute (AII)** — The upstream maintainer of the GNN reference
specification COGANT targets. <https://activeinference.org/>.

**`ActInfOntologyAnnotation`** — One of the 18 sections in a GNN markdown file. Maps each
declared variable to an Active Inference ontology term (e.g. `HiddenStateFactor0`,
`PolicyVector`).

## B

**B matrix** — Transition tensor `P(s' | s, a)`, shape `[n_states × n_states × n_actions]`.
Encodes how actions change hidden state. Column-stochastic per AII convention. Falls back
to identity-per-action when the program graph has no `WRITES` evidence.

**Blanket** — See **Markov blanket**.

**`BlanketRole`** — Enum in `py/cogant/markov/blanket.py` with four values: `INTERNAL`,
`SENSORY`, `ACTIVE`, `EXTERNAL`. The four roles that partition every graph node.

**Bracket notation** — The variable-declaration syntax used in GNN `StateSpaceBlock`:
`name[dim1,dim2,type=...]`.

## C

**C vector** — Log-preference over observations, shape `[n_obs]`. Positive means preferred,
negative means aversive. Softmax is taken over `-C` when computing expected free energy.

**Calibration** — The open R&D plan for empirically validating COGANT's confidence scores
against hand-labelled ground truth. See `_rnd/CALIBRATION.md`.

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
`PreferenceRule` and `TestAssertionRule`. Contributes to the C vector.

**CONTAINS** — An `EdgeKind` representing lexical containment: a module contains a class,
a class contains its methods, and so on.

**`ContainmentRule`** — A translation rule that emits `CONTAINMENT` mappings for pairs of
nodes joined by a `CONTAINS` edge.

**Control rules** — The `control.py` rule family. Contains `ConfigRule` and `FeatureFlagRule`.

## D

**D vector** — Initial-state prior `P(s_0)`, shape `[n_states]`. Uniform fallback when no
`CONFIGURATION` nodes exist.

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

**Expected free energy (EFE)** — A forward-looking free-energy functional used to score
candidate action sequences (policies) in Active Inference. The planner picks the policy with
the lowest EFE.

**External state** — The η component of a Markov blanket: everything outside the system of
interest. Node role `BlanketRole.EXTERNAL`.

## F

**FEP** — See **Free Energy Principle**.

**Fixpoint engine** — The rule-application loop inside `TranslationEngine.translate()`. It
runs every registered rule until no new mappings are produced (convergence) or
`max_iterations` is reached.

**Free Energy Principle** — The theoretical claim that all self-organizing systems can be
described as minimizing variational free energy. Karl Friston's foundational framework.

## G

**GNN** — **Generalized Notation Notation**. The Active Inference Institute's reference
text format for generative-model specifications. Not to be confused with *Graph Neural
Network*. COGANT's GNN output is a directory with a bracket-notation markdown file plus
machine-readable JSON twins.

**`GNNMatrices`** — Class in `py/cogant/gnn/matrices.py`. Wraps a `ProgramGraph`, a list of
`SemanticMapping`, and a `StateSpaceModel`, and derives the A / B / C / D matrices on
demand.

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

**Isomorphism** — The formal claim that a program and its generative-model interpretation
carry the same information, so the forward and reverse COGANT pipelines should be inverses
up to whitespace and naming. See `_rnd/ISOMORPHISM_THEOREM.md`.

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

**`ObservationRule`** — Semantic rule that tags getters and read-only functions as
`OBSERVATION`. Keyword set: `get`, `read`, `fetch`, `query`, `display`, `show`, `status`,
`info`, `list`.

**Observation** — In Active Inference: the sensory signal an agent receives. In COGANT:
any code patterning marked `OBSERVATION`. Maps to the **s** variables in the GNN export.

**Ontology annotation** — The mapping from GNN variable names to Active Inference ontology
terms. Section 8 of the GNN markdown.

## P

**`PackagePlan`** — Prototype dataclass in `py/cogant/reverse/__init__.py` describing the
directory layout of a synthesized Python package. The reverse direction of the pipeline.

**`ParseResult`** — Container returned by a `LanguagePlugin.parse_file()` call. Carries
`nodes`, `edges`, and `diagnostics`.

**PDG** — Program Dependence Graph. See **Program graph**.

**POLICY** — Semantic role for handler / controller / router classes and retry / circuit-
breaker patterns. Detected by `PolicyRule`, `RetryPatternRule`, and some applications of
`InheritanceRule`.

**Preference** — Positive entry in the C vector, or equivalently a `PREFERENCE` mapping.
The Active Inference equivalent of a goal.

**Priority** — Each `TranslationRule` has an integer priority. Higher priorities win
conflicts. Confidence is the tiebreaker when priorities are equal.

**Program graph** — The canonical intermediate representation produced by the graph stage.
A typed, directed property graph with `NodeKind`-labelled nodes and `EdgeKind`-labelled
edges. Instance of `py/cogant/schemas/graph.py::ProgramGraph`.

**Provenance** — Source-level attribution for every non-trivial mapping or matrix entry.
Recorded as file:line:col spans and stored in `provenance.json` in the GNN package.

## R

**`RetryPatternRule`** — Resilience-family rule that tags retry / backoff code with
`POLICY` and `CIRCUIT_BREAKER` mappings.

**Resilience rules** — The `resilience.py` rule family. Includes `RetryPatternRule`,
`ErrorBoundaryRule`, `SingletonAccessRule`, `CircuitBreakerRule`.

**Reverse mode** — The GNN → code direction of the pipeline. Prototype only in v0.1.0.
See [Tutorial 6](../tutorials/06_reverse_mode.md).

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
- [`py/cogant/schemas/`](../../py/cogant/schemas/) — the authoritative type definitions.
