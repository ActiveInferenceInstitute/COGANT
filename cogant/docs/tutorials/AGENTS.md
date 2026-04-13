# AGENTS.md — Tutorials module

Step-by-step, hands-on walkthroughs of COGANT workflows. Each tutorial is
longer and more pedagogical than a cookbook recipe: it teaches a concept
while running commands, rather than just executing a procedure. Later
tutorials build on vocabulary introduced in earlier ones.

## Purpose and ownership

Tutorials are the "teach me how to use this tool" layer of the docs. They
are expected to hold a reader's hand more than the cookbook and to spend
more prose on *why* than on *what*. Owned by whoever last shipped a
user-facing change large enough to invalidate the existing walkthroughs.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC, recommended reading order, status of legacy files | When a tutorial is added, renumbered, or deprecated |
| `AGENTS.md` | This file — maintenance rules | When the numbering policy, the legacy-file policy, or ownership changes |
| `01_quickstart.md` | Install + first scan on a tiny sample | When install or first-scan flow changes |
| `02_small_repo_walkthrough.md` | Every pipeline stage on a small Python repo | When the pipeline stage list or stage outputs change |
| `03_flask_walkthrough.md` | COGANT against a real-world Flask application | When the Flask fixture or CLI flags for the run change |
| `04_custom_rules.md` | Authoring and registering custom translation rules | When the custom-rules API changes |
| `05_gnn_interpretation.md` | Reading, debugging, and visualizing a generated GNN | When the GNN schema or visualization helpers change |
| `06_reverse_mode.md` | Synthesizing runnable code from a GNN markdown file | When the reverse-mode CLI or synthesis API changes |
| `07_plugin_authoring.md` | Building a parser/rule/validator/exporter plugin | When the plugin contracts change |
| `calculator.md` | **Legacy.** Tiny calculator example referenced by other tutorials | Kept stable for inbound links; see "Legacy files" below |
| `flask.md` | **Legacy.** Auxiliary Flask example sources and notes | Kept stable for inbound links; see "Legacy files" below |

## Legacy files

`calculator.md` and `flask.md` predate the `NN_slug.md` numbering scheme.
They are not formal tutorials — they are worked examples that some of
the numbered tutorials reference. They are **kept, not promoted and not
deprecated**:

- **Kept** because external content (blog posts, conference talks,
  slide decks) links to them by slug and we do not want to break those
  links.
- **Not promoted** because the numbered tutorials are the canonical
  teaching sequence; we do not want two overlapping spines.
- **Not deprecated** because they still serve as compact, reusable worked
  examples that the numbered tutorials link to.

If either file becomes genuinely obsolete — for example, if the
calculator example moves wholesale into `examples/zoo/` — leave a short
stub here pointing at the new location rather than deleting the file.

## Adding a new tutorial

1. Pick the next free `NN` prefix (current max is `07`). Reserve your
   number with a draft PR to avoid collisions.
2. Use a short, lower-case, underscore-separated slug
   (`08_incremental_workflow.md`).
3. Open with learning outcomes ("By the end of this tutorial you will
   be able to...") and a prerequisites list.
4. Structure as numbered steps with prose paragraphs between them. Every
   step should advance the reader's mental model, not just execute a
   command.
5. Add a row to the `## Contents` table in `README.md` and place the
   tutorial in `## Recommended Reading Order` if it belongs in the spine.

## Known gotchas

- Tutorials and `../cookbook/` recipes overlap deliberately. Rule of
  thumb: if the content is >20 minutes of hands-on time or spends more
  than 30 percent of its words on explanation, it belongs here. Otherwise
  it belongs in the cookbook.
- `../notebooks/` mirrors several of these tutorials as Jupyter
  notebooks. Keep the content in agreement — if you change a step here,
  re-run the matching notebook and regenerate its `.md` export.
