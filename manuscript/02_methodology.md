# Methodology: Program Graphs and Intermediate Representations

## Program graph

Let $G = (V, E)$ denote a directed graph whose vertices $V$ represent program entities and whose edges $E$ represent relationships. COGANT assigns each node a **kind** (for example function, variable, type) and a **semantic role** (for example definition versus use). Each node and edge may carry:

- A **stable identifier** for persistence across runs when hashing allows.
- **Type strings** and attributes recovered from the front end.
- A **confidence** score in $[0,1]$ and **provenance** metadata (source code, type system, control flow, heuristic, external tool).

This follows the same philosophical line as code property graphs that fuse AST, control flow, and data flow into one analyzable structure [@yamaguchi2014modeling], but orients the representation toward **Generalized Notation Notation (GNN) export** and, optionally, tensorized views of the same graph: node kinds and roles map to discrete indices in both forms, and optional embeddings can augment features as described in `../cogant/docs/GNN_EXPORT.md`.

### Structural equivalence

Two program graphs $G_1 = (V_1, E_1)$ and $G_2 = (V_2, E_2)$ are usefully compared via typed graph isomorphism: a bijection $\phi : V_1 \to V_2$ preserving edge structure and relevant labels supports deduplication and cross-repository linking when interfaces align.

\begin{equation}
\label{eq:typed-iso}
(u, v) \in E_1 \iff (\phi(u), \phi(v)) \in E_2
\end{equation}

Equation \ref{eq:typed-iso} formalizes the structural invariant we check during deduplication and cross-repository linking: a candidate bijection $\phi$ is accepted only when every edge in $G_1$ has a corresponding edge between the images of its endpoints in $G_2$ (and vice versa), so that label-preserving matches strictly preserve the adjacency structure of both program graphs.

## Progressive IRs

Processing proceeds through a sequence of representations (see `../cogant/docs/SPEC.md`):

1. **Repo IR** — entities and relationships extracted from parsers.
2. **Program graph IR** — consolidated graph with deduplication and metadata.
3. **Semantic mapping IR** — output of the translation rule engine.
4. **State space IR** — variables, actions, transitions, observations.
5. **Process model IR** — higher-level control patterns where implemented.
6. **Validation IR** — coverage, confidence analysis, schema checks.

Not every stage is equally complete for every repository; the SPEC marks partial areas (translation rules, state space, Rust acceleration) explicitly. COGANT's program graph sits in the same conceptual space as compiler intermediate representations such as LLVM [@lattner2004llvm] and MLIR [@lattner2021mlir], but targets behavioral extraction and export for downstream learning rather than code generation or optimization.

## Translation rules

The **translation** stage applies declarative rules that refine roles, attach labels, and adjust confidence. Concurrency targets and layering are described in `../cogant/docs/ARCHITECTURE.md`. The rule engine composes passes over the graph in a **fixpoint loop**: rules are re-applied until no new semantic mappings emerge or a configurable iteration cap is reached. The fixpoint loop follows the classical formulation of program analysis as fixpoint computation over a lattice of abstract states [@cousot1977abstract]; in our setting the lattice is the set of semantic mappings partially ordered by inclusion, and the monotone operator is the composition of all registered rule applications. In the shipped implementation, each pass applies rules in descending `rule.priority`, and conflict resolution later compares `(rule_priority, confidence_score)` tuples when two mappings overlap, following the principle that edit representations should be composable [@yin2019learning].

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

- **GNN Markdown (`model.gnn.md`)** — canonical, human-readable Generalized Notation Notation organized into the section order defined in `../cogant/docs/GNN_EXPORT.md` (Model Metadata, Repository Metadata, Source Coverage, State Space, Observation Modalities, Actions/Policies, Connections, Factors, Transition Structure, Likelihood Structure, Preferences/Constraints, Time Settings, Parameterization, Ontology Mapping, Provenance, Confidence Scores, Rendering Hints, Validation Notes).
- **GNN JSON (`model.gnn.json`)** — machine-readable equivalent of the markdown sections, plus companion JSON files per section (`state_space.json`, `observations.json`, `actions.json`, `transitions.json`, and so on).
- **Interop exports** — GraphML and Parquet for analysis in Gephi/yEd and DuckDB, and optional tensor views (PyTorch Geometric `Data` objects [@fey2019pyg], DGL graphs, HDF5 tables) for downstream graph neural network training pipelines that consume the program graph as a relational tensor.

Node and edge feature breakdowns, section contracts, and the optional framework targets are specified in `../cogant/docs/GNN_EXPORT.md`; they determine the structure of the emitted notation as well as the effective input dimensionality of any downstream model.

## Error handling philosophy

The implementation distinguishes fatal configuration or parse failures from per-file errors that allow partial results. Validation aggregates warnings and inconsistencies into a report that travels with the bundle. This mirrors the layered error categories documented in the architecture (fatal, error, warning, info).
