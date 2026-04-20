# `tests/fuzz`

Hypothesis-driven fuzz harness that stresses the COGANT pipeline with
synthetic `ProgramGraph` instances. The goal is to catch regressions in
structural invariants that aren't easily covered by hand-written
fixtures.

## Files

| File | Role |
| --- | --- |
| `test_fuzz_invariants.py` | The five structural invariants exercised on every Hypothesis example: role completeness, no-orphan mappings, Markov blanket totality, matrix stochasticity, rule determinism. |
| `__init__.py` | Marker for pytest collection. |

## Conventions

* Inputs are deterministic: every `@given(...)` strategy is built from
  `cogant.schemas.*` types so seeds are reproducible. No mocks — real
  `TranslationEngine`, `MarkovBlanketExtractor`, `StateSpaceCompiler`.
* Tests skip the file-based ingest stage and call
  `ProgramGraphBuilder` in-memory so Hypothesis can explore hundreds
  of shapes per second.
* Soft invariants (e.g. the 50% role-coverage floor) are documented in
  the harness with a `_ROLE_COVERAGE_FLOOR` constant; promote them to
  hard asserts when the rule set catches up.
* `pytest -m property` runs this suite alongside `tests/property/`.

Parent: [`../AGENTS.md`](../AGENTS.md).
