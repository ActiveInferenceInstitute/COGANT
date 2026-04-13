# AGENTS.md — Cookbook module

Short, self-contained, copy-paste-friendly recipes for COGANT workflows. Each
recipe answers a single "how do I..." question and runs end-to-end in 2-15
minutes. The cookbook is where readers land when they already know the tool
exists and want to get a specific job done.

## Purpose and ownership

Recipes, not tutorials or reference. If a page grows into a multi-hour
walkthrough, move it to `../tutorials/`. If a page becomes a schema or API
dump, move the reference chunks into `../reference/` or `../api/` and link
back. Owned by whoever is editing the CLI / user-facing workflows.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC, numbering policy, non-numbered recipe registry | Any time a recipe is added, removed, renamed, or changes difficulty |
| `AGENTS.md` | This file — maintenance rules | When numbering, non-numbered-recipe, or ownership policy changes |
| `01_scan_basic.md` – `20_dataset.md` | Numbered recipes, read the README table for descriptions | When the CLI, pipeline, or exporter they demonstrate changes |
| `analyze_a_flask_app.md` | Pre-numbering Flask walkthrough — kept stable for inbound links | When the Flask example itself is moved or the CLI contract changes |
| `custom_translation_rules.md` | Pre-numbering custom-rules recipe — superseded by `19_extend_rules.md` for new work | Only to fix factual errors; new content goes in the numbered recipe |
| `interpret_gnn_output.md` | Pre-numbering GNN interpretation recipe — superseded by `03_explain_node.md` for new work | Only to fix factual errors; new content goes in the numbered recipe |

## Adding a new recipe

1. Pick the next free `NN` prefix (current max is `20`). Reserve your number
   with a draft PR before writing, so two contributors do not collide.
2. Use a short, lower-case, underscore-separated slug (for example
   `21_custom_exporter.md`).
3. Open with a one-sentence statement of the outcome ("By the end of this
   recipe you will..."), followed by prerequisites, steps, and expected
   output. Prefer copy-pasteable shell blocks and `cogant` CLI invocations
   over prose.
4. Add a row to the `## Contents` table in `README.md` and, if the recipe
   belongs in the onboarding spine, mention it in `## Recommended Reading
   Order` as well.
5. Reference the relevant CLI / API / rules pages with `../cli/README.md`,
   `../api/README.md`, `../rules/README.md` rather than re-explaining them.

## Known gotchas

- Three non-numbered recipes (`analyze_a_flask_app.md`,
  `custom_translation_rules.md`, `interpret_gnn_output.md`) overlap
  topically with numbered recipes. Do not delete them — external docs and
  blog posts may link to them by slug. If a consolidation pass happens
  later, keep a stub with a redirect note at minimum.
- The cookbook and `../tutorials/` overlap deliberately: cookbook entries
  are outcome-first and short; tutorial entries are pedagogy-first and long.
  If you cannot decide, write the cookbook recipe first — it is easier to
  promote a recipe into a tutorial than to split a tutorial into recipes.
