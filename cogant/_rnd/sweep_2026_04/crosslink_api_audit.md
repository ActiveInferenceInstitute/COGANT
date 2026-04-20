# Wave 19 — Crosslink: API → Examples / Cookbook / Tutorials

**Agent:** `crosslink-api-to-examples-agent`
**Date:** 2026-04-10
**Status:** complete

## Goal

Every public class / function documented in `docs/api/` must link to at
least one zoo example, cookbook recipe, or tutorial that uses it.

## Audit summary

Inspected all 30 pages under `docs/api/`. Of the 9 priority pages in
the task list, **0 had an "Examples" or "See also" section** before this
sweep (only `docs/api/see_also.md` itself, which is a shared footer).

| API page | Existing Examples? | Action |
| --- | --- | --- |
| `docs/api/overview.md` | no | added Examples section (zoo + 2 cookbook + 1 tutorial) |
| `docs/api/quick_start.md` | no | added Examples section (2 zoo + 2 cookbook + 2 tutorial) |
| `docs/api/pipelinerunner_api.md` | no | added Examples section (2 zoo + 3 cookbook + 2 tutorial) |
| `docs/api/gnn.md` | no | added Examples section (3 zoo + 2 cookbook + 1 tutorial) |
| `docs/api/reverse.md` | no | added Examples section (3 zoo + 2 cookbook + 1 tutorial) |
| `docs/api/runtime.md` | no | added Examples section (3 zoo + 1 cookbook + 1 tutorial) |
| `docs/api/statespace.md` | no | added Examples section (3 zoo + 2 cookbook + 1 tutorial) |
| `docs/api/translate.md` | no | added Examples section (6 zoo + 3 cookbook + 1 tutorial) |
| `docs/api/static.md` | no | added Examples section (3 zoo + 2 cookbook + 1 tutorial) |

## New cookbook stubs

Three new cookbook recipes created (real content stubs, not placeholders):

1. `docs/cookbook/analyze_a_flask_app.md` — short copy-pasteable Flask
   recipe; defers to Tutorial 3 for the full narrative. Includes CLI
   commands, the bundle file table, and the programmatic equivalent.
2. `docs/cookbook/custom_translation_rules.md` — five-step recipe
   (pick family / subclass / register / test / ship); defers to Tutorial 4
   for the full read-only-cache walkthrough.
3. `docs/cookbook/interpret_gnn_output.md` — five-step recipe for reading
   A / B / C / D from a real bundle; defers to Tutorial 5 for the
   `p(o, s, a)` factorization narrative.

## Link integrity

All 38 link targets verified to exist on disk via filesystem check
(see commit message). Zero broken links introduced.

## Path conventions

- API → zoo: `../../examples/zoo/<name>/` (matches existing precedent in `docs/api/see_also.md`).
- API → cookbook: `../cookbook/<file>.md`.
- API → tutorials: `../tutorials/<file>.md`.
- Cookbook → tutorials: `../tutorials/<file>.md`.
- Cookbook → API: `../api/<file>.md`.
- Cookbook → cookbook: `<file>.md` (sibling).

## Files modified

```
docs/api/overview.md
docs/api/quick_start.md
docs/api/pipelinerunner_api.md
docs/api/gnn.md
docs/api/reverse.md
docs/api/runtime.md
docs/api/statespace.md
docs/api/translate.md
docs/api/static.md
```

## Files created

```
docs/cookbook/analyze_a_flask_app.md
docs/cookbook/custom_translation_rules.md
docs/cookbook/interpret_gnn_output.md
_rnd/sweep_2026_04/crosslink_api_audit.md
```

## Binding rules honored

- ✅ No `manuscript/` edits.
- ✅ All links resolve (filesystem-verified — see `b13` rerun in session log).
- ✅ Cookbook stubs are real content, not placeholders (each ~50–80 lines).
- ✅ Will commit before exit.

## Out of scope (future sweeps)

The remaining 21 API pages under `docs/api/` (`bundle_api.md`,
`confidence_model_api.md`, `dynamic_analysis_api.md`,
`dynamic_enrichment_api.md`, `error_handling.md`, `markov.md`,
`plugin_api.md`, `reviewapi.md`, `scoring_api.md`, `session_api.md`,
`simulate.md`, `visualization_api.md`, etc.) also lack Examples sections.
A follow-up wave should crosslink those once their primary public
symbols are stable.
