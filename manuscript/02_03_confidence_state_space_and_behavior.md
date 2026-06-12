# Confidence scoring, evidence tiers, and state-space compilation {#sec:02-03-confidence-state-space-and-behavior}

## Confidence scoring and evidence tiers {#sec:02-03-confidence-scoring}

The shipped `ConfidenceModel` in `../cogant/py/cogant/translate/confidence.py` computes a scalar score in $[0,1]$ from:

- Average confidence over provenance records.
- An evidence-diversity term (scaled, capped).
- A parser certainty factor applied multiplicatively.
- Conflict penalties subtracted after scaling.

$$
c = \max\left(0,\ \min\left(1,\ (\bar{e} + \delta_d)\cdot \kappa - \pi\right)\right)
$$ {#eq:confidence-core}

Here $\bar{e}$ is the mean evidence confidence, $\delta_d$ is the diversity bonus (bounded), $\kappa$ is parser certainty, and $\pi$ aggregates conflict penalties. **Tiers** (for example static-only versus static-plus-runtime) are assigned from score thresholds and evidence source tags (`determine_confidence_tier`); see the same module for named thresholds and enum values. The manuscript does not duplicate those literals so they cannot drift from code.

The score should be interpreted operationally rather than metaphysically: it is a review-priority score over extracted assertions, not a Bayesian posterior over the true semantics of the program and not an empirically calibrated probability in the reliability-diagram sense [@guo2017calibration]. Its value is that every component is inspectable and trace-backed -- provenance source, parser certainty, rule specificity, conflict penalty, reviewer outcome -- so a high score means "stronger executable evidence for this mapping under the current front end," not "the repository has been proven correct." This distinction keeps COGANT compatible with provenance-oriented artifact review [@moreau2013prov] and with the manuscript's broader claim-ledger discipline, while leaving formal posterior semantics and empirical calibration to future work.

## State space and behavior {#sec:02-03-state-space-and-behavior}

Where traces or coverage are available, **dynamic** extraction feeds the state-space compiler. The goal is a compact behavioral model: states, actions, transitions, and observations that sit alongside the static graph for tasks that require execution-sensitive features. The tuple $(S, A, T, O)$ of variables, actions, transitions, and observation modalities mirrors the structure of a partially observed Markov decision process [@kaelbling1998planning] as used in discrete active inference [@parr2022active; @dacosta2020active; @smith2022stepbystep], and at the level of reachable state/transition graphs it also resembles the Kripke structures traditionally used in model checking [@clarke1999model], without attempting to discharge temporal-logic obligations. PyMDP [@heins2022pymdp] is one such downstream consumer that executes the compiled state-spaces as discrete active inference simulations over the exported Generalized Notation Notation bundles.

The shipped `StateSpaceCompiler` in `../cogant/py/cogant/statespace/compiler.py` constructs this model in several coordinated passes driven by the semantic mappings and the underlying program graph.

**State variables** are identified by a `StateVariableExtractor` that traverses graph nodes carrying READS and WRITES edges: any node that participates in a write is a candidate hidden-state variable, and its type, cardinality, and initial confidence are derived from the node's recovered type string and the provenance of the rules that produced the associated mapping.

**Actions** are extracted from semantic mappings of kind `ACTION`, with parameters read from node metadata (typically the parser-recovered function signature), effects traced through outgoing WRITES edges on the controller node, and preconditions derived from parameter lists, docstring directives, and explicit metadata entries. For method-kind actions, the compiler also walks CONTAINS edges back to the enclosing class so that instance-level state mutations are attributed to the correct controller, mirroring how code property graphs fuse structural and data-flow views [@yamaguchi2014modeling].

**Transitions** are inferred by a cross-reference pass (`_cross_reference_actions_and_variables`) that, for each action, partitions its adjacent variables into reads and writes based on edge kind (WRITES and MUTATES yielding writes; READS and OBSERVES yielding reads). The resulting `Transition` object records a `source_state` in which every touched variable is marked `"pre"` and a `target_state` in which written variables advance to `"post"` while read-only variables remain `"pre"`; this simple pre/post convention keeps the model aligned with the static evidence without overcommitting to symbolic value domains that cannot be recovered from AST analysis alone.

Trigger attribution follows incoming TRIGGERS and CALLS edges so that orchestration flow is preserved in the behavioral model.

**Observation modalities** are built from semantic mappings of kind `OBSERVATION`: each associated node becomes an `ObservationModality` whose modality type (`log`, `metric`, `event`, `sensor`, or generic observation channel) is inferred from the mapping's description and the node's name, giving the GNN export a typed observation channel aligned with the OBSERVES edges in the program graph.

The **temporal regime** of the model is determined by a companion `TemporalAnalyzer`. It classifies nodes as asynchronous when their metadata carries `is_async`/`async` flags or their names match patterns such as `async`, `callback`, `promise`, or `future`, and as event-related when their kind is `EVENT` or their names match `event`, `handler`, `listener`, or `trigger`. Temporal orderings are then extracted from CALLS and TRIGGERS edges, with each edge classified as `parallel` (when either endpoint is async) or `sequential` otherwise, and event patterns are assembled from triggers-in / triggers-out pairs around each event node.

A final decision rule selects among `SYNCHRONOUS`, `ASYNCHRONOUS`, `EVENT_DRIVEN`, and `HYBRID`: the presence of event triggers and patterns combined with async handlers yields `HYBRID`; event triggers alone yield `EVENT_DRIVEN`; an async fraction above 30 percent or the presence of async handlers yields `ASYNCHRONOUS`; and all remaining cases default to `SYNCHRONOUS`. This regime is attached to the `StateSpaceModel` metadata so downstream consumers know which execution model the transition graph assumes.

When coverage and traces are available, `enrich_graph()` in `../cogant/py/cogant/dynamic/enrichment.py` feeds additional evidence into this pipeline. Coverage enrichment matches `.coverage` SQLite databases or Cobertura XML reports against nodes whose `path` and `source_range` overlap covered lines, attaching `coverage_hits` and, where branch data is available, `branch_coverage` metadata. Trace enrichment parses Chrome DevTools traces, writes `call_count`, `avg_duration_ms`, and `is_hot_path` onto matching callable nodes, and adds or reweights dynamic CALLS edges tagged with `evidence_sources=["dynamic_trace"]`.

Both steps also append `dynamic_coverage` and `dynamic_trace` markers to the program graph's evidence sources. The confidence model consumes these markers directly: any mapping whose evidence set now contains both static and dynamic entries becomes eligible for promotion from the `STATIC_ONLY` tier to `STATIC_PLUS_RUNTIME`, and hot-path and branch-coverage metadata raise the underlying score through the diversity bonus $\delta_d$ in @eq:confidence-core. This is the mechanism by which executing the target program, even partially, converts static heuristics into corroborated behavioral facts without rerunning the upstream rule engine [@allamanis2018survey].

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
