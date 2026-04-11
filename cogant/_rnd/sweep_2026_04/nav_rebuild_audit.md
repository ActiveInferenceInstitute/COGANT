# Wave 19 — mkdocs.yml Nav Rebuild Audit

**Agent:** `rebuild-nav-agent` (final agent in Wave 19)
**Date:** 2026-04-10
**Branch:** `main`
**Working dir:** `projects_in_progress/cogant/cogant`

## Trigger

After all other Wave 19 agents committed (`coherence`, `signposting`, `crosslink`,
`validate`, `meta`), this agent rebuilds `mkdocs.yml` so every `.md` file under
`docs/` is reachable from the navigation.

## Wave-19 Commits Observed Before Rebuild (12)

```
31bf572 docs(w19/signposting): add page headers (what-this-is, prerequisites, reading-time, next-steps)
4eca25d docs(w19/coherence): re-verify metric coherence — 23/23 ISOMORPHIC, 4979 tests, 86.8% cov, v0.5.0
3ec4dfd docs(w19/crosslink): R&D docs → published docs + module cross-references
2e2b095 docs(w19/signposting): section indexes with contents tables and reading order
f0501e7 docs(w19/validate): execute Jupyter notebooks and commit with outputs
40862a9 docs(w19/validate): API signature drift fixes — docs match inspect.signature output
23a0cd9 docs(w19/signposting): mkdocs nav audit + learning paths (5 personas)
44fd198 docs(w19/crosslink): API docs → examples/cookbook/tutorial cross-references
9cf9a8b docs(w19/coherence): terminology normalization — canonical role names, GNN acronym fixes, glossary
a106bb0 docs(w19/meta): R&D_LOG wave-19 entry — coherence+signposting+crosslinking+validation
32d3abb docs(w19/crosslink): tutorials → theory/concepts back-links
d1168f1 docs(w19/validate): fix dead internal links across docs
```

8-commit threshold met → proceeded with rebuild.

## Method

1. Enumerated every `docs/**/*.md` (excluding `AGENTS.md`): **377 files**.
2. Parsed `mkdocs.yml` `nav:` block via regex on `:` / quoted-string YAML
   value forms to recover the existing in-nav references: **294 files**.
3. Computed the set difference: **83 docs missing from nav**.
4. Categorized the missing files by line count and path:
   - **20 real architecture pages** (≥30 lines, plus `architecture/README.md`)
   - **60 architecture symbol snippets** (<30 lines, leftover symbol-level
     fragments — kept rather than orphaned, but grouped under a dedicated
     subsection so they don't dominate the sidebar)
   - **3 cookbook how-tos** (`analyze_a_flask_app.md`,
     `custom_translation_rules.md`, `interpret_gnn_output.md`)
5. Edited `mkdocs.yml`:
   - Added `Section Index: architecture/README.md` at the top of the
     `Architecture:` section.
   - Added two new sub-groups under `Architecture:` —
     **Pipeline Walkthroughs** (5 long-form summaries) and
     **Pipeline Steps (Detail)** (14 step-level pages).
   - Added a third sub-group **Symbol Snippets** with all 60 short
     code-snippet stubs, alphabetized.
   - Appended the 3 missing cookbook entries beneath
     `cookbook/20_dataset.md`.
6. Validated YAML: `python3 -c "import yaml; yaml.safe_load(open('mkdocs.yml'))"`
   → parses cleanly; nav has **25 top-level sections** and **377 leaf entries**.
7. Re-ran the diff: **0 unnavigated docs**.
8. Confirmed `Learning Paths:` section (added by `signposting-nav-agent`) is
   still present with all 5 persona entries:
   `new-user.md`, `api-consumer.md`, `theory-reader.md`, `plugin-author.md`,
   `contributor.md`.

## Before / After

| Metric                              | Before | After |
|-------------------------------------|--------|-------|
| Total `.md` files under `docs/`     | 377    | 377   |
| `.md` files reachable from `nav:`   | 294    | 377   |
| Unnavigated `.md` files             | 83     | 0     |
| Nav top-level sections              | 24*    | 25    |
| `Learning Paths` persona entries    | 5      | 5     |

\* Pre-rebuild section count includes `Learning Paths` (created earlier in
the wave by the signposting agent). The new top-level count of 25 reflects no
new top-level groups added by this agent — only new sub-sections inside
`Architecture:`.

## Constraints Honored

- **No `manuscript/` edits.** This agent only touched `mkdocs.yml` and this
  audit file under `_rnd/sweep_2026_04/`.
- **Valid YAML after edits.** Verified with `yaml.safe_load`.
- **Stage only own files.** `git add` is scoped to `mkdocs.yml` and `_rnd/`;
  uncommitted work from other concurrent agents is left untouched.
- **Idempotent.** Re-running the diff after the edit yields zero missing files.

## Caveats

- The 60 symbol-level snippets in `architecture/` (e.g. `add_edge.md`,
  `parse_cargotoml.md`) are clearly auto-extracted code fragments from a
  prior pass — most are 3-20 lines with no surrounding prose. Adding them
  to nav makes them discoverable, but they would benefit from a future
  pass that either (a) inlines them into their parent narrative pages and
  deletes the standalone files, or (b) gives each one a real description
  section. Filed informally for a future Wave.
- A handful of the long-form architecture pages have somewhat redundant
  titles (e.g. `cogant_engine_implementation_summary.md` vs
  `cogant_graph_construction_normalization_and_translation_engine.md`).
  Consolidation is also a future-Wave concern.
