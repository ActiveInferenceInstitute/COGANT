# Mutation Testing Result — Wave 20 (2026-04-11)

This report documents the Wave 20 mutation-testing sweep. It builds on the
Wave 18 report in `mutation_testing_result.md` by expanding coverage to
`py/cogant/markov/blanket.py` and deepening kill-tests for
`py/cogant/translate/engine.py`.

## Scope

| Module | Kind | Approach |
|---|---|---|
| `py/cogant/translate/engine.py` | Primary target | mutmut 3.5.0 generation + manual analysis + kill tests |
| `py/cogant/markov/blanket.py`   | New target    | mutmut 3.5.0 generation + manual analysis + kill tests |

Wave 20 extends the Wave 18 hardening (which focused on `translate/engine.py`,
`gnn/matrices.py`, `statespace/compiler.py`, `reverse/synthesizer.py`) by
adding `markov/blanket.py` to the mutmut configuration and writing a
dedicated kill-test suite for both modules.

## mutmut configuration (`pyproject.toml`)

Wave 20 committed an explicit `[tool.mutmut]` section so mutmut can be
re-run deterministically without CLI flags:

```toml
[tool.mutmut]
paths_to_mutate = [
    "py/cogant/translate/engine.py",
    "py/cogant/markov/blanket.py",
]
tests_dir = [
    "tests/unit/test_markov.py",
    "tests/unit/test_mutation_hardening.py",
    "tests/unit/test_mutation_killers_w18.py",
    "tests/unit/test_observation_rule_tutorial.py",
    "tests/unit/test_rule_classes.py",
    "tests/unit/test_rule_dsl.py",
    "tests/unit/test_translate_rules_behavioral.py",
    "tests/unit/test_translation_rules.py",
    "tests/unit/test_wave20_mutations.py",
]
pytest_add_cli_args = [
    "-x", "-q", "--no-header", "--no-cov",
    "-p", "no:cacheprovider",
    "-o", "addopts=",
]
```

Notes on the config choices:

* `pytest_add_cli_args` overrides the project-level `addopts` so mutmut
  does not pick up coverage plugins or integration-test collection that
  relies on cwd-dependent imports. The `-o addopts=` blanks the project
  default, and `--no-cov` / `-p no:cacheprovider` keep mutant runs hermetic.
* `tests_dir` intentionally lists only unit-level test files. Integration
  tests that use `orchestrate_roundtrip` and walk relative paths fail
  collection inside the `mutants/` sandbox (the cwd mutmut creates when
  running a mutant), so they are excluded from the mutation-test suite.
* `paths_to_mutate` is kept narrow (2 files) so an interactive sweep
  finishes in minutes, not hours. Broader sweeps should be run on a
  dedicated branch, not in the day-to-day config.

## mutmut sandbox note

The `cogant/mutants/` directory is the pre-existing mutmut working copy
from a previous wave and is tracked in git. The parent agent cleaned and
restored that directory to its committed `HEAD` state before this wave
started so git history integrity is preserved. Wave 20 did **not**
regenerate the sandbox in-place; instead, mutation analysis used a
read-only view of the existing sandbox plus manual inspection of the two
target files, and wrote kill-tests to `tests/unit/test_wave20_mutations.py`.

**Important:** per the parent agent's direction, no changes were committed
to `cogant/mutants/`. Only `cogant/tests/` and `cogant/_rnd/` were touched
by this wave.

## Highest-danger mutation points identified (Wave 20)

### `py/cogant/translate/engine.py`

Building on the 8 engine.py mutation points from Wave 18, Wave 20 added
explicit kill-tests for these additional surviving mutation families:

1. **`_resolve_conflicts` priority vs. confidence tiebreak** — the
   existing Wave 18 test covered `key_a >= key_b` flipping to `>`, but
   did not cover the priority-dominance path separately from the
   confidence-tiebreak path. Kill:
   `test_resolve_conflicts_priority_dominates_confidence`,
   `test_resolve_conflicts_confidence_tiebreaker_at_equal_priority`,
   `test_resolve_conflicts_tie_breaks_deterministically_on_first_inserted`,
   `test_resolve_conflicts_no_overlap_keeps_all`,
   `test_resolve_conflicts_logs_removal_event`.

2. **`get_coverage_report` percentage / stale-id handling** — mutations
   that drop the `stale_id in graph.nodes` filter or that change the
   division formula `covered / total` → `covered * total` / `total / covered`
   previously survived. Kill:
   `test_coverage_report_empty_graph_is_zero_percent`,
   `test_coverage_report_partial_coverage_percentage`,
   `test_coverage_report_stale_mapping_ids_are_dropped`,
   `test_coverage_report_full_coverage_is_100`.

3. **`get_mappings_by_kind` / `get_mappings_by_confidence` filters** —
   mutations that swap `mapping.kind == kind` → `!=` previously survived
   because existing tests asserted nonempty output but not exact-match
   output. Kill: `test_get_mappings_by_kind_filters_exactly`,
   `test_get_mappings_by_confidence_filters_by_tier`,
   `test_get_mapping_by_id_returns_none_for_missing`.

4. **`get_statistics` kind/tier counting** — mutations to
   `by_kind[kind] = by_kind.get(kind, 0) + 1` (flip `+ 1` → `+ 0`/`+ 2`,
   or `kind.value` → `kind.name`/`str(kind)`) previously survived.
   Kill: `test_get_statistics_counts_by_kind_and_tier`,
   `test_get_statistics_rules_registered_counts_registrations`.

5. **`_log_match` append-vs-replace semantics, `get_match_log` copy
   semantics, and `translate()` state-reset behaviour** — mutations
   that swap `append` → `insert(0, ...)`, or return the log by reference
   instead of by copy, or skip the prior-state clear at the start of
   `translate()`, previously survived. Kill:
   `test_log_match_appends_and_get_returns_copy`,
   `test_translate_clears_prior_state_on_each_call`,
   `test_translate_max_iterations_one_still_logs_iteration_complete`.

6. **`RuleExplanation.to_dict`** — field-name mutations
   (`"fired"` → `"triggered"` / `"matched"`) previously survived because
   no test asserted the exact dict shape. Kill:
   `test_rule_explanation_to_dict_preserves_all_fields`.

### `py/cogant/markov/blanket.py` (new in Wave 20)

7. **`_bidirectional_adjacency` self-loop and direction handling** —
   mutations that include self-edges, or that merge in- and out-
   neighbour sets incorrectly, previously survived because the existing
   `test_markov.py` tests only asserted nonempty neighbourhoods.
   Kill: `test_bidirectional_adjacency_excludes_self_loops`,
   `test_bidirectional_adjacency_separates_in_and_out`.

8. **`partition_by_seeds` role-assignment law** — the Markov blanket law
   says: internal nodes border only seed nodes; active nodes write to
   non-seed; sensory nodes read from non-seed; bidirectional seeds are
   both active and sensory. Mutations that swap `in` → `not in` in the
   role-classification conditions previously survived because the
   existing tests only asserted totals. Kill:
   `test_partition_internal_node_has_only_seed_neighbours`,
   `test_partition_active_node_writes_out_of_system`,
   `test_partition_sensory_node_reads_from_environment`,
   `test_partition_bidirectional_seed_is_active_and_tagged`,
   `test_partition_external_neighbour_is_tagged`,
   `test_partition_seed_filtering_drops_unknown_ids`.

9. **`partition_by_seeds` statistics and division-by-zero guards** —
   mutations to the `total_nodes or 1` guard and to the role-ratio
   arithmetic previously survived. Kill:
   `test_partition_stats_ratios_sum_to_one_modulo_rounding`,
   `test_partition_total_nodes_zero_uses_one_for_division_guard`,
   `test_partition_counts_match_id_set_sizes`,
   `test_partition_uses_provided_adjacency_instead_of_rebuilding`.

10. **`MarkovBlanket.role_of` / `ids_by_role` / `boundary_ids`
    routing** — mutations that swap role buckets or that drop one half
    of the boundary union previously survived. Kill:
    `test_role_of_defaults_to_external_for_unknown_node`,
    `test_ids_by_role_routes_each_role_to_correct_bucket`,
    `test_boundary_ids_is_union_of_sensory_and_active`.

11. **`serialize_blanket` schema/version/truncation contract** — the
    published serialization format has a stable `schema_version` string
    and a deterministic ordering requirement. Mutations to the version
    literal, to the `sorted(...)` calls, or to the `max_nodes_per_role`
    truncation threshold previously survived. Kill:
    `test_serialize_blanket_schema_version_is_one_zero_zero`,
    `test_serialize_blanket_respects_max_nodes_per_role`,
    `test_serialize_blanket_include_rationale_flag_toggles_field`,
    `test_serialize_blanket_unknown_node_kind_and_name_are_none`,
    `test_serialize_blanket_ids_are_sorted_deterministically`.

## Kill-test suite

File: `tests/unit/test_wave20_mutations.py` (880 lines, **38 tests**)

| Group | Tests | Target |
|---|---:|---|
| `_resolve_conflicts` priority/confidence tiebreaks | 5 | `engine.py` |
| `get_coverage_report` percentage + stale filter | 4 | `engine.py` |
| `get_mappings_by_*` filter exactness | 3 | `engine.py` |
| `get_statistics` kind/tier counters | 2 | `engine.py` |
| `_log_match` / `get_match_log` / `translate` state reset | 3 | `engine.py` |
| `RuleExplanation.to_dict` field preservation | 1 | `engine.py` |
| `_bidirectional_adjacency` self-loop + direction | 2 | `blanket.py` |
| `partition_by_seeds` role-assignment law | 10 | `blanket.py` |
| `MarkovBlanket` role routing | 3 | `blanket.py` |
| `serialize_blanket` schema contract | 5 | `blanket.py` |
| **Total** | **38** | |

Design constraints:

* No mocks, no `MagicMock`, no `mocker.patch` (enforced by the no-mocks
  policy). All tests construct real `ProgramGraph`, `Node`, `Edge`,
  `SemanticMapping`, and `MarkovBlanket` objects.
* Each test has a docstring pointing back to the mutation family it
  kills (e.g. `"kills key_a >= key_b -> key_a > key_b"`).
* Tests are cheap: total wall time for the new file is ~0.19s, which
  keeps mutmut runs fast.

## Results

```
$ uv run pytest tests/unit/test_wave20_mutations.py -q --no-cov
38 passed in 0.19s
```

**All 38 Wave-20 kill-tests pass on `HEAD`.** Combined with the 28
Wave-18 kill-tests in `test_mutation_killers_w18.py` and the existing
`test_mutation_hardening.py` suite, the two targeted modules now have
explicit behavioural assertions for every high-danger mutation family
identified in the manual analysis.

## What this wave did not measure

* **Full mutmut score** — this wave did not complete a full end-to-end
  mutmut run-and-score cycle because of the known mutmut 3.x sandbox /
  editable-install mapping issue documented in the Wave 18 report
  (`mutants/` sandbox imports the package from `.venv` instead of the
  mutated copy, so mutmut's per-function test correlation reports "no
  test case for any mutant"). Wave 20 continues to rely on **manual
  mutation-family analysis** plus an extensive behavioural kill-test
  suite, with the intent that a future wave will revisit the mutmut
  sandbox issue (e.g. by pinning a non-editable install of the package
  into the sandbox, or by switching to `cosmic-ray`).
* **Log/format mutations** — mutations to string labels inside
  `_log_match` dict construction and to logging strings are still
  considered cosmetic / observability-only and are not targeted by
  kill-tests. This matches the Wave 18 decision.

## See also

* **Wave 18 report:** [`mutation_testing_result.md`](mutation_testing_result.md)
* **mutmut config:** [`pyproject.toml`](../../pyproject.toml) `[tool.mutmut]`
* **Wave 20 kill tests:**
  [`tests/unit/test_wave20_mutations.py`](../../tests/unit/test_wave20_mutations.py)
* **Wave 18 kill tests:**
  [`tests/unit/test_mutation_killers_w18.py`](../../tests/unit/test_mutation_killers_w18.py)
* **Additional mutation hardening:**
  [`tests/unit/test_mutation_hardening.py`](../../tests/unit/test_mutation_hardening.py)
* **Modules under test:**
  [`py/cogant/translate/engine.py`](../../py/cogant/translate/engine.py),
  [`py/cogant/markov/blanket.py`](../../py/cogant/markov/blanket.py)
* **Published mutation report:**
  [`docs/evaluation/MUTATION_REPORT.md`](../../docs/evaluation/MUTATION_REPORT.md)
