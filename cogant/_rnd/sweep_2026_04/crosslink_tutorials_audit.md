# Wave 19 — Crosslink tutorials → theory/concepts back-links

**Agent:** `crosslink-tutorials-to-theory-agent`
**Date:** 2026-04-10
**Scope:** Add inline "Theory background" callouts to every tutorial and notebook page so
readers always have a one-click path back to the concept / reference page that explains *why*
the tutorial works the way it does.

## Binding rules honored

- No edits under `manuscript/`. Confirmed by inspection — all edits are under `docs/tutorials/`
  and `docs/notebooks/`.
- All link targets verified to resolve (11/11) before commit. See "Link verification" below.
- Single commit with the conventional `docs(w19/crosslink): …` message.

## Files edited (15 total)

### Numbered tutorials (`docs/tutorials/0[1-7]_*.md`)

| File | Theory anchors added |
| --- | --- |
| `01_quickstart.md` | `concepts/gnn.md`, `concepts/role_assignment.md` |
| `02_small_repo_walkthrough.md` | `concepts/program_graph.md`, `concepts/markov_blanket.md` |
| `03_flask_walkthrough.md` | `concepts/role_assignment.md`, `concepts/markov_blanket.md`, `concepts/program_graph.md` |
| `04_custom_rules.md` | `reference/translation_rules.md`, `rules/overview.md`, `rules/custom_rules.md` |
| `05_gnn_interpretation.md` | `concepts/active_inference.md`, `concepts/gnn.md` |
| `06_reverse_mode.md` | `concepts/roundtrip.md`, `api/reverse.md` |
| `07_plugin_authoring.md` | `api/plugin_api.md`, `rules/overview.md` |

### Legacy tutorials

| File | Theory anchors added |
| --- | --- |
| `tutorials/calculator.md` | `concepts/program_graph.md`, `concepts/role_assignment.md`, `concepts/markov_blanket.md`, `concepts/gnn.md` |
| `tutorials/flask.md` | `concepts/role_assignment.md`, `concepts/markov_blanket.md`, `concepts/program_graph.md`, `concepts/gnn.md` |

### Notebook stubs (`docs/notebooks/*.md`)

| File | Theory anchors added |
| --- | --- |
| `README.md` | All six per-notebook anchor sets in one indexed list |
| `01_forward_pipeline.md` | `concepts/program_graph.md`, `concepts/role_assignment.md` |
| `02_explore_gnn.md` | `concepts/gnn.md`, `concepts/active_inference.md` |
| `03_reverse_synthesis.md` | `concepts/roundtrip.md`, `api/reverse.md` |
| `04_roundtrip.md` | `concepts/roundtrip.md`, `concepts/markov_blanket.md` |
| `05_custom_rules.md` | `reference/translation_rules.md`, `rules/overview.md`, `rules/custom_rules.md` |
| `06_plugin_authoring.md` | `api/plugin_api.md`, `rules/overview.md` |

## Pattern used

Each page received a `> **Theory background:** …` blockquote callout placed immediately after
the page's existing intro / goal blockquote (or, for notebook stubs, after the "Coming soon"
paragraph). This places the back-link above the first technical section so readers cannot miss
it, but does not displace existing front-matter such as "What this page is" headers added by
sibling Wave-19 agents.

Example pattern (from `01_quickstart.md`):

```markdown
> **Theory background:** This tutorial produces a [GNN (Generalized Notation Notation)](../concepts/gnn.md)
> bundle from source code. The pipeline assigns Active Inference roles to graph nodes via the
> [role assignment system](../concepts/role_assignment.md). If you have never seen these terms
> before, skim those two pages first — five minutes is enough to follow this tutorial after.
```

All links use the relative form `../concepts/<page>.md` (or `../api/`, `../reference/`,
`../rules/`) which resolves correctly from both `docs/tutorials/` and `docs/notebooks/`.

## Link verification

Verified via filesystem existence check immediately before commit:

```
OK docs/concepts/gnn.md
OK docs/concepts/role_assignment.md
OK docs/concepts/program_graph.md
OK docs/concepts/markov_blanket.md
OK docs/concepts/active_inference.md
OK docs/concepts/roundtrip.md
OK docs/api/reverse.md
OK docs/api/plugin_api.md
OK docs/reference/translation_rules.md
OK docs/rules/overview.md
OK docs/rules/custom_rules.md
```

11 / 11 link targets resolve. Zero broken links introduced.

## Notes for downstream waves

- The notebook `*.md` files are still "Coming soon" stubs. When the executable `.ipynb`
  notebooks land, the same theory back-links should be reproduced as a markdown cell at the top
  of each notebook.
- `tutorials/AGENTS.md` and `tutorials/README.md` were intentionally left untouched — they are
  navigation indices, not tutorial pages, and a different wave is responsible for their cross-
  references.
- A parallel Wave-19 agent independently added "What this page is / Prerequisites / Reading
  time / Next steps" front-matter blocks to several numbered tutorials. The Theory background
  callouts added here sit immediately below those front-matter blocks and continue to function
  as intended; no rework needed.
