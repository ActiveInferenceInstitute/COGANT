# AGENTS.md — Notebooks module

Executable Jupyter notebook walkthroughs of every major COGANT workflow.
Each numbered notebook ships as both an `.ipynb` (runnable) and an `.md`
(rendered for the MkDocs site). The `.md` is a derived artifact — it is
the rendered export of the `.ipynb`, not a hand-written file.

## Purpose and ownership

Notebooks are the "watch it run" layer of the documentation. They exist so
readers can step through a workflow with all intermediate state visible,
which is hard to achieve in a static tutorial or cookbook recipe. Owned
by whoever last shipped a pipeline change large enough to invalidate the
existing notebook outputs.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC, reading order, "how to run" instructions | When a notebook is added, removed, or renumbered |
| `AGENTS.md` | This file — maintenance rules | When the `.ipynb` / `.md` pairing policy or ownership changes |
| `01_forward_pipeline.ipynb` / `.md` | Code → GNN forward pipeline walkthrough | When the forward pipeline or its default config changes |
| `02_explore_gnn.ipynb` / `.md` | Inspecting and visualizing a generated GNN | When the GNN package schema or visualization helpers change |
| `03_reverse_synthesis.ipynb` / `.md` | GNN → code reverse synthesis | When the reverse synthesis API changes |
| `04_roundtrip.ipynb` / `.md` | Full forward + reverse roundtrip with equivalence checks | When the roundtrip invariant or equivalence check changes |
| `05_custom_rules.ipynb` / `.md` | Writing and registering custom translation rules | When the rule registration API changes |
| `06_plugin_authoring.ipynb` / `.md` | Authoring a parser/exporter plugin | When the plugin API changes |
| `07_real_world_flask.ipynb` / `.md` | End-to-end run against a Flask application | When the Flask fixture or expected outputs change |
| `08_constraint_authoring.ipynb` / `.md` | Authoring CONSTRAINT-class rules | When CONSTRAINT rule semantics change |
| `09_plugin_authoring.ipynb` / `.md` | Deeper plugin authoring patterns | When the plugin API exposes new hooks |
| `10_rule_dsl.ipynb` / `.md` | Working with the rule DSL directly | When the rule DSL surface changes |
| `11_inference_learning.ipynb` / `.md` | Learning from review feedback to refine rules | When the learning loop API changes |
| `12_cross_language.ipynb` / `.md` | Cross-language roundtrip and analysis | When a new language is added to the cross-language set |

## Pairing convention

Every notebook is stored as an `.ipynb` / `.md` pair with matching stems.
The `.md` is the rendered export and is checked in so the MkDocs site has
something to display without running Jupyter at build time.

### Regenerating the `.md` export

```bash
uv run jupyter nbconvert --to markdown docs/notebooks/NN_slug.ipynb
```

Run that command after editing any notebook, commit both files in the same
PR, and sanity-check the rendered output in a local `mkdocs serve` before
merging.

## Adding a new notebook

1. Pick the next free `NN` prefix. Reserve your number with a draft PR
   before writing, so two contributors do not collide.
2. Keep the stem lower-case and underscore-separated (`13_new_topic.ipynb`).
3. Start with a markdown cell that states the learning outcome and the
   prerequisites.
4. Use deterministic seeds and small inputs so the notebook runs in under
   a minute on a laptop.
5. Regenerate the `.md` export and commit both files.
6. Add a row to the `## Contents` table in `README.md` and, if appropriate,
   the `## Recommended Reading Order`.

## Known gotchas

- The `.md` export is not hand-edited. If you find yourself wanting to edit
  the `.md` directly, edit the `.ipynb` and regenerate instead. Otherwise
  the two will drift and reviewers cannot trust either.
- Some notebooks here duplicate topics covered in `../tutorials/` (for
  example plugin authoring). That duplication is intentional: tutorials
  are read-only prose; notebooks are hands-on. Keep both in agreement.
- Notebook outputs can be very large; strip heavy binary outputs before
  committing. A rendered `.md` that exceeds a few hundred kilobytes is a
  sign that something should be trimmed.
