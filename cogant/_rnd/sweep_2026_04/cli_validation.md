# Wave 19 — CLI Command Validation Report

**Agent:** `validate-all-cli-commands-agent`
**Date:** 2026-04-10
**Subrepo:** `projects_in_progress/cogant/cogant`
**Branch:** `claude/blissful-noether`

## Scope

Walked every `cogant <subcommand>` invocation in `docs/**/*.md`, compared each
against the actual `cogant --help` and per-subcommand `--help` output, ran
representative commands against the `examples/zoo/01_simple_state` fixture,
and fixed concrete drift in the docs (no manuscript edits).

## Authoritative CLI Surface (verified 2026-04-10)

Top-level subcommands actually registered by the Typer app — **21 total**:

```
init  doctor  scan  extract-static  extract-dynamic  graph  translate
statespace  process  export-gnn  render  viz  validate  diff  changed
explain  benchmark  reverse  roundtrip  plugin  migrate
```

Subcommands that **do not exist** despite occasional doc mentions:

| Phantom command          | Reality                                                       |
| ------------------------ | ------------------------------------------------------------- |
| `cogant analyze`         | Use `cogant translate`. The `--incremental` flag lives there. |
| `cogant export`          | Use `cogant export-gnn` (positional `BUNDLE_PATH`).           |
| `cogant forward`         | Forward pass IS `cogant translate`. (Only one prose mention.) |
| `cogant validate --json` | `validate` has only `--help`; no JSON output flag.            |
| `cogant viz --diagram`   | `viz` only takes a `RUN_DIR` and `--help`. No `--diagram`.    |

## Smoke Tests Against `examples/zoo/01_simple_state`

| Command                                                              | Result                              |
| -------------------------------------------------------------------- | ----------------------------------- |
| `cogant scan examples/zoo/01_simple_state/`                          | OK — Rich summary table             |
| `cogant translate examples/zoo/01_simple_state --output … --no-dynamic` | OK — all 10 stages green, bundle.json + gnn_package/ written |
| `cogant explain examples/zoo/01_simple_state BeliefState`           | OK — rule trace printed             |
| `cogant explain output/.../bundle.json BeliefState`                 | **FAILS** — explain takes a repo dir, not a bundle. Doc was wrong (now fixed). |
| `cogant validate <run_dir>`                                          | OK — score 100.0/100                |
| `cogant validate <run_dir> --json`                                   | **FAILS** — `No such option: --json` (now fixed in docs). |
| `cogant render bundle.json --output …`                              | OK — HTML site                      |
| `cogant export-gnn bundle.json --output … --format markdown`        | OK — `bundle.md` written            |
| `cogant translate --skip dynamic,process --output …`                | OK — both stages skipped, rest succeed |
| `cogant translate --skip ingest,export --output …`                  | **CRIPPLES PIPELINE** — every dependent stage fails with `ingest stage must run before X`. Doc example was misleading (now fixed). |
| `cogant diff <bundle_a.json> <bundle_b.json>`                       | OK — legacy shallow diff             |
| `cogant diff <run_dir_a> <run_dir_b>`                               | **CRASHES** — `AttributeError: 'str' object has no attribute 'get'` in `cogant.scoring.drift.compute_structural_drift`. NOT a doc bug; logged below. |

## Drift Fixed in Docs

| File | Old | New |
| ---- | --- | --- |
| `docs/changelog.md:11` | `cogant analyze --incremental <git-ref>` | `cogant translate --incremental <git-ref>` |
| `CHANGELOG.md:33` (root)   | `cogant analyze --incremental <git-ref>` | `cogant translate --incremental <git-ref>` |
| `docs/evaluation/INCREMENTAL_BENCHMARK.md:3` | `cogant analyze --incremental <commit>` | `cogant translate --incremental <commit>` |
| `docs/evaluation/RELEASE_NOTES_v0.5.0.md:33` | `cogant analyze --incremental <git-ref>` | `cogant translate --incremental <git-ref>` |
| `docs/getting-started/installation.md:55` | `# Typer app registers 14 subcommands` | `# Typer app registers 21 top-level subcommands` |
| `docs/guides/getting_started.md:122` | `cogant explain output/simple_state/bundle.json BeliefState` | `cogant explain examples/zoo/01_simple_state BeliefState` |
| `docs/guides/getting_started.md:205` | `cogant validate output/simple_state --json \| jq '.epsilon, .isomorphic'` | `cogant validate output/simple_state` |
| `docs/tutorials/02_small_repo_walkthrough.md:157` | `cogant viz output/event_pipeline --diagram blanket --output …/diagrams/` | `cogant viz output/event_pipeline` |
| `docs/tutorials/05_gnn_interpretation.md:190` | `cogant viz output/<project> --diagram graph` | `cogant viz output/<project>` (with corrected description) |
| `docs/cli/commands.md:89` | `cogant translate ./my_repo --output output/ --skip ingest,export` | `cogant translate ./my_repo --output output/ --skip dynamic,export` |
| `docs/learning-paths/new-user.md:23` | `Verify with \`cogant --version\`` | `Verify with \`cogant doctor\`` (the Typer app exposes only `--help`, `--install-completion`, `--show-completion`; there is no `--version` flag) |
| `docs/concepts/roundtrip.md:152` | `Running \`cogant forward\` on this synthesized code` | `Running \`cogant translate\` on this synthesized code` (forward pass IS `cogant translate`; no `forward` subcommand exists) |
| `docs/playground.html:389` (JS comment) | `\`cogant analyze\` → graph.json + .gnn` | `\`cogant translate\` → bundle.json + gnn_package/` |
| `docs/playground.html:791` (UI alert string) | `Run \`cogant analyze <path>\` locally for live parsing` | `Run \`cogant translate <path>\` locally for live parsing` |

## Drift NOT fixed (out of scope or low risk)

* **`docs/guides/getting_started.md` §2 file tree** — claims `output/simple_state/`
  contains `mappings.json`, `markov_blanket.json`, and `reports/validation.json`
  at top level. Reality: top level has `bundle.json`, `gnn_model.json`,
  `program_graph.json`, `process_model.json`, `state_space.json`, and a
  `gnn_package/` directory containing `model.gnn.md`, `markov_blanket.json`,
  `model.gnn.json`, etc. (no top-level `reports/`). Out of scope: prose edit,
  not a CLI command.
* **`docs/cli/commands.md`** "statespace" / "graph" examples write `--output
  statespace.json` / `--output graph.json` — accepted but `--output` for those
  commands is documented in `--help` as "informational only" and does not
  actually write the file. Doc is technically not wrong (the flag exists), so
  left alone.
* **`docs/api/installation.md`** mentions `py/requirements.txt` and `py/cogant/`
  — verified `py/cogant/` directory still exists. OK.
* **`docs/tutorials/06_reverse_mode.md:21`** uses the phrase "A cogant forward run"
  in descriptive prose (no backticks, no command). This is an English description
  of the forward translation pipeline, not a CLI invocation. Left as prose.

## Code Bugs Surfaced (filed for follow-up — not fixed by this agent)

1. **`cogant.scoring.drift.compute_structural_drift`** — crashes on real
   `program_graph.json` data with `AttributeError: 'str' object has no attribute
   'get'`. The code assumes `nodes` is a list of dicts, but the actual
   serialized format apparently contains string ids. This blocks `cogant diff
   <run_dir_a> <run_dir_b>`, which is the path documented in `cli_reference.md`,
   `cookbook/04_custom_threshold.md`, `cookbook/07_reverse_custom.md`,
   `cookbook/08_ci_integration.md`, `cookbook/13_incremental.md`, and
   `cookbook/19_extend_rules.md`. **High impact**: every cookbook drift recipe
   is currently broken at runtime. Recommend a separate Wave 19 fix.

2. **`cogant graph --output FILE` and `cogant statespace --output FILE`** are
   documented as "informational only" in `--help`. Either implement them or
   drop the flag. Several cookbook examples imply they write files.

## Files Touched by This Agent

First pass (also produced in parallel by sibling agents and already in HEAD via
commits 2e2b095 and earlier):

```
CHANGELOG.md
docs/changelog.md
docs/cli/commands.md
docs/evaluation/INCREMENTAL_BENCHMARK.md
docs/evaluation/RELEASE_NOTES_v0.5.0.md
docs/getting-started/installation.md
docs/guides/getting_started.md
docs/tutorials/02_small_repo_walkthrough.md
docs/tutorials/05_gnn_interpretation.md
_rnd/sweep_2026_04/cli_validation.md  (this file)
```

Second pass (additional drift discovered, committed by this agent):

```
docs/concepts/roundtrip.md
docs/learning-paths/new-user.md
docs/playground.html
_rnd/sweep_2026_04/cli_validation.md  (extended)
```

No `manuscript/` files were modified.
