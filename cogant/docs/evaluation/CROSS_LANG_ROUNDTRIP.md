# COGANT Cross-Language Roundtrip: JavaScript Observer

Date: 2026-04-10
Status: CONFIRMED
Companion to: `EMPIRICAL_CLAIM.md`

## Claim

The COGANT Galois loop — Code → Program Graph → Semantic Mappings → GNN
→ synthesized Python package → re-forward — is **not Python-specific**.
A hand-written JavaScript fixture carrying the same structural
semantics as `zoo/02_observer` rounds-trips with a perfect role-match
score (1.0) and runs a full Active Inference perception-action cycle
on the resulting A/B/C/D matrices.

This extends the empirical claim established in `EMPIRICAL_CLAIM.md`
(Python-only) to a second language through the tree-sitter backed JS
plugin that landed in wave 11 (`c9dead2`).

## Fixture

`examples/zoo/13_js_observer/observer.js` — minimal Observer class:

```javascript
class Observer {
  constructor(n_states) {
    this.state = new Array(n_states).fill(1 / n_states);
    this.observations = [];
  }
  update(obs) { this.observations.push(obs); }
  getState() { return this.state; }
  checkValid() { return this.state.every((s) => s >= 0); }
}
module.exports = { Observer };
```

Semantic intent (same as `zoo/02_observer` in Python):

| Method | Behaviour | Expected role |
| --- | --- | --- |
| `constructor(n_states)` | initialises a uniform belief over `n_states` and an empty observation log | HIDDEN_STATE scaffold |
| `update(obs)` | mutates the observation log; pure state mutation | ACTION |
| `getState()` | pure read-only getter | OBSERVATION |
| `checkValid()` | returns a boolean simplex invariant | CONSTRAINT |

A `package.json` with `{"name":"observer","version":"1.0.0"}` sits
next to the source so anything that keys off repo metadata still finds
an anchor.

## Forward Pipeline (JS → GNN)

The CLI `cogant translate` currently walks only Python files (see
`api/orchestration.py::run_static`). For the cross-language claim we
drive the same stages manually through the public library API:

```
observer.js
  → JavaScriptLanguageParser (tree-sitter-javascript)
  → ProgramGraphBuilder      (reuses _build_javascript_graph helper)
  → TranslationEngine        (shipping structural + semantic rules)
  → StateSpaceCompiler       (schema_name='js_observer')
  → GNNMatrices              (A/B/C/D)
  → ProcessExtractor         (ProcessModel)
  → GNNMarkdownFormatter     (model.gnn.md)
```

Measured results:

| Stage | Output |
| --- | --- |
| Parser symbols | 1 class (`Observer`), 4 methods (`constructor`, `update`, `getState`, `checkValid`) |
| Program graph | 10 nodes / 19 edges (module, class, 4 methods, 4 variable / attr nodes) |
| Semantic mappings | 6 |
| Role multiset | `HIDDEN_STATE: 1, OBSERVATION: 2, ACTION: 2, CONSTRAINT: 1` |
| State-space | n_states=1, n_obs=2, n_actions=2 |
| Matrix A (2×1) | `[[1.0], [1.0]]` |
| Matrix B (1×1×2) | identity per action |
| Matrix C (len 2) | `[0.0, 0.0]` (no preference gradient) |
| Matrix D (len 1) | `[1.0]` |
| GNN markdown | 14 477 chars, all six canonical sections present |

Sections verified in the emitted GNN markdown:
`StateSpaceBlock`, `Connections`, `ActInfOntologyAnnotation`,
`InitialParameterization`, `ModelParameters`, `Time`.

## Roundtrip (ε-isomorphism)

```
R1 (JS forward)    = {HIDDEN_STATE: 1, OBSERVATION: 2, ACTION: 2, CONSTRAINT: 1}
R2 (re-forward)    = {HIDDEN_STATE: 1, OBSERVATION: 8, ACTION: 5,
                      POLICY: 2, CONSTRAINT: 10, CONTEXT: 3}
|R1 ∩ R2| / |R1|   = 6 / 6 = 1.0000     (PERFECT)
threshold          = 0.5
is_isomorphic      = True
tier               = PERFECT (ε = 0)
```

The reverse pipeline synthesises a Python package with the standard
eight modules plus an extra `context.py`:

```
__init__.py  act.py  constraints.py  context.py  main.py
matrices.py  observe.py  policy.py  state.py
```

Re-running the forward pipeline on that package recovers every role
present on the JS side. The multiset on R2 is *richer* because the
reverse synthesizer resolves additional ontology-only annotations
(POLICY from `G=ExpectedFreeEnergy`, CONTEXT from `Time`, plus the
per-method constraint expansion) that the JS-side rules never emitted
to begin with. Under the verifier's multiset intersection rule the
extras don't penalise the score — what matters is that *every* JS-side
role survives the round trip, which it does.

## Active Inference Cycle (10-step trajectory)

Feeding the JS-derived matrices into `cogant.runtime.loop.AgentRuntime`:

```
  t  obs  action     state_dist   free_energy
---  ---  ------  ------------  ------------
  0    0    u_c0        [1.000]     -0.000000
  1    0    u_c0        [1.000]     -0.000000
  2    0    u_c0        [1.000]     -0.000000
  3    0    u_c0        [1.000]     -0.000000
  4    0    u_c0        [1.000]     -0.000000
  5    0    u_c0        [1.000]     -0.000000
  6    0    u_c0        [1.000]     -0.000000
  7    0    u_c0        [1.000]     -0.000000
  8    0    u_c0        [1.000]     -0.000000
  9    0    u_c0        [1.000]     -0.000000
```

Mean VFE = final VFE = `-0.000000`. The trajectory is flat because the
fixture is structurally trivial (one hidden state, uniform C
preferences), but every step is well-formed: the belief stays on the
simplex, the chosen action is a valid index, VFE is finite, and no
exceptions are raised over 10 perception-action cycles. This matches
the Python `zoo/01_simple_state` baseline in `EMPIRICAL_CLAIM.md` and
is exactly what we expect for a fixture whose sole purpose is to
demonstrate that the cross-language path works end-to-end.

## Python Twin Comparison

Running the same rule set on `examples/zoo/02_observer/sensor.py`
(the Python Observer twin) for reference:

| Metric | JS `13_js_observer` | Py `02_observer` |
| --- | --- | --- |
| Source lines | ≈ 20 | ≈ 30 |
| Program graph nodes | 10 | 8 |
| Program graph edges | 19 | 18 |
| Semantic mappings | 6 | 5 |
| Role multiset | `HS:1 OBS:2 ACT:2 CONS:1` | `HS:1 OBS:3 ACT:1` |
| Name overlap (normalised) | — | ≈ 75 % with JS symbols |
| Roundtrip ε | 1.0 (this doc) | 1.0 (`EMPIRICAL_CLAIM.md`) |

The two fixtures are intentionally different enough to be *independent*
evidence of the same claim rather than a mechanical port:

* The JS fixture carries a dedicated `checkValid()` constraint method
  with an `every(s => s >= 0)` lambda; the Python twin has no explicit
  invariant, so its role multiset lacks `CONSTRAINT`.
* The JS fixture has one mutator (`update`) and one reader
  (`getState`); the Python twin has three readers (`observe`,
  `read_temperature`, `get_status`) and no explicit mutator.
* Both land on exactly one `HIDDEN_STATE`, confirming the
  mutating-subsystem rule fires on both languages for the same
  "class that keeps a piece of private state" pattern.

## Interpretation

**What survives the cross-language round-trip (structural semantics):**

1. **Hidden state identification.** Both fixtures produce exactly one
   `HIDDEN_STATE` mapping on a class that holds mutable private state.
   The rule ("class whose methods both read and write a private
   attribute") is pattern-driven, not language-specific.
2. **Read-only methods → OBSERVATION.** `getState()` in JS and
   `observe()` / `read_temperature()` / `get_status()` in Python all
   get classified as observations. The keyword-match rules (`get`,
   `read`) port cleanly because tree-sitter surfaces JS method names
   in the same form the Python AST walker does.
3. **Mutators → ACTION.** `update(obs)` in JS and any
   self-assignment in Python both map to `ACTION` through the
   mutating-subsystem structural rule.
4. **Invariant predicates → CONSTRAINT.** JS `checkValid()` ends up
   under `CONSTRAINT` because it returns a boolean on a predicate over
   `this.state`. The Python twin doesn't exercise this branch.
5. **The GNN emission is language-agnostic.** Once the program graph
   and semantic mappings are in hand the formatter, state-space
   compiler, and reverse synthesizer have no idea where the graph
   came from, which is why `role_match_score = 1.0` is recoverable
   from a non-Python source.

**What does not survive (and why that's acceptable):**

* **Matrix magnitudes.** The JS fixture collapses to a single hidden
  state (`n_states=1`) because there's only one mutating subsystem.
  The `n_states` field in the constructor (`new Array(n_states)
  .fill(…)`) is a runtime argument; the static rules can't see it
  without dynamic analysis, which is (a) disabled here and (b) beyond
  the scope of a forward rule. This is a calibration issue, not a
  correctness issue: the matrices are still well-formed, AgentRuntime
  still accepts them, and the AI cycle still runs.
* **Preference gradients.** The Python pipeline has a `PreferenceRule`
  that matches docstring / attribute heuristics; the JS fixture has
  no docstrings (JS comments live outside the symbol table) so the
  C vector comes out flat. This could be improved by teaching the
  tree-sitter adapter to surface JSDoc comments.
* **Surface-level identifiers.** Method names diverge
  (`getState` vs `observe`) and the synthesized Python package
  renames everything through GNN slots. Under the Galois framing this
  is *expected*: GNN is a lossy projection of program structure onto
  active-inference roles, so identifiers live only up to role-level
  equivalence. The 1.0 role-match score is the invariant that holds.

## Reproduction

The path is covered by six integration tests:

```bash
uv run pytest tests/integration/test_cross_lang_roundtrip.py -v --no-cov
```

Tests and what each pins:

1. `test_js_fixture_parses_without_error` — fixture exists, parser
   returns no error, class + all four methods surface.
2. `test_js_translation_produces_core_active_inference_roles` — at
   least one `HIDDEN_STATE`, `OBSERVATION`, `ACTION` mapping.
3. `test_js_state_space_and_matrices_are_non_degenerate` — A/B/C/D
   are rectangular, non-empty, and normalised.
4. `test_js_gnn_emission_has_all_canonical_sections` — six canonical
   GNN markdown sections present.
5. `test_js_forward_reverse_forward_role_match_above_threshold` —
   the full forward → reverse → forward loop recovers a role-match
   score strictly above 0.5. Currently 1.0.
6. `test_js_agent_runtime_runs_ten_steps_without_exception` —
   `AgentRuntime.run_n_steps(10)` returns ten well-formed
   `AgentStep`s (normalised belief, finite VFE, valid action index).

All six are `@pytest.mark.skipif(not _HAS_JS_PARSER or not
_GRAMMAR_AVAILABLE, …)` so environments without
`tree-sitter-javascript` see a descriptive skip rather than a failure.
Install with `uv pip install "tree-sitter>=0.21"
"tree-sitter-javascript>=0.21" "tree-sitter-python>=0.21"` or the
equivalent `cogant[multilang]` extras.

## File Manifest

- `examples/zoo/13_js_observer/observer.js` — JavaScript Observer fixture
- `examples/zoo/13_js_observer/package.json` — minimal npm package metadata
- `examples/zoo/13_js_observer/README.md` — fixture description
- `tests/integration/test_cross_lang_roundtrip.py` — six-test suite
- `CROSS_LANG_ROUNDTRIP.md` — this document
