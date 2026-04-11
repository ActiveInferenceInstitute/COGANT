# Tutorial / Notebook Validation Report

**Wave:** 19 (`validate-all-tutorials-agent`)
**Date:** 2026-04-10
**Project:** COGANT
**Branch:** `main`
**Working dir:** `/Users/4d/Documents/GitHub/template/projects_in_progress/cogant/cogant`

## Goal

Execute every Jupyter notebook under `docs/notebooks/` end-to-end, commit the executed
outputs back into the repo, and verify the companion `.md` tutorials still parse cleanly.

## Environment Setup Required

The notebooks could not be executed against the existing `cogant` checkout out-of-the-box
because `nbconvert` and an in-venv `ipykernel` were not registered. The following
one-time bootstrap was performed (no source files were modified):

1. **Installed Jupyter stack into the project venv** (`.venv/`):
   ```bash
   uv pip install ipykernel jupyter nbconvert matplotlib pandas
   ```
   Without `matplotlib`, notebook 01 fails at the role-distribution pie-chart cell.
2. **Registered a venv-bound kernelspec** so nbconvert binds the notebook to the
   `cogant`-aware Python rather than the user-global `miniforge` interpreter:
   ```bash
   .venv/bin/python -m ipykernel install --user --name cogant-venv \
       --display-name "Python (cogant venv)"
   ```
3. **Set the notebook execution `cwd` to the project root** so the relative
   fixture paths (`examples/control_positive/calculator/`, …) resolve. The
   notebooks ship with a guard that explicitly says *"Run from the cogant/
   directory"*; nbconvert otherwise sets cwd to the notebook's own directory.
   This was achieved by driving execution through `nbclient.NotebookClient`
   with `resources={'metadata': {'path': str(PROJECT_ROOT)}}`.

The runner script lives at `/tmp/run_notebooks.py` for this session — it is
not committed because it lives in `_rnd/`-discardable territory and the same
flow can be reproduced with the recipe above.

## Notebooks Executed

| # | Notebook | Status | Notes |
|---|---|---|---|
| 1 | `01_forward_pipeline.ipynb` | PASS | Calculator fixture → ProgramGraph; pie chart + DataFrame render. |
| 2 | `02_explore_gnn.ipynb` | PASS | Forward → GNN translation. |
| 3 | `03_reverse_synthesis.ipynb` | PASS | Reverse parser round-trip. |
| 4 | `04_roundtrip.ipynb` | PASS | Forward + reverse end-to-end equivalence. |
| 5 | `05_custom_rules.ipynb` | PASS | YAML DSL → compiled ruleset. |
| 6 | `06_plugin_authoring.ipynb` | PASS | `PluginRegistry` walkthrough. |
| 7 | `07_real_world_flask.ipynb` | PASS | Real-world Flask example. |
| 8 | `08_constraint_authoring.ipynb` | PASS | Constraint authoring walkthrough. |
| 9 | `09_plugin_authoring.ipynb` | PASS | `MiniJsPlugin` regex plugin. |
| 10 | `10_rule_dsl.ipynb` | PASS | Rule DSL compilation. |
| 11 | `11_inference_learning.ipynb` | PASS | Inference / learning zoo example. |
| 12 | `12_cross_language.ipynb` | PASS | JS plugin + tree-sitter parser. |

**Result: 12 / 12 notebooks executed cleanly.**

All executed notebooks were written back in-place, so the committed `.ipynb`
files now carry the latest cell outputs (figures embedded as base64 PNGs,
DataFrame text dumps, etc.).

## Companion `.md` Tutorials

Files in `docs/notebooks/*.md`:

```
01_forward_pipeline.md
02_explore_gnn.md
03_reverse_synthesis.md
04_roundtrip.md
05_custom_rules.md
06_plugin_authoring.md
README.md
AGENTS.md
```

A grep for fenced ``` ```python ``` blocks across every `.md` companion
returned **zero matches** — these files are short prose stubs that point
back at the matching `.ipynb`. There is therefore no executable Python
inside the companion docs to validate, and they are not modified by this
sweep. (Notebooks 07–12 do not have a `.md` companion at all.)

## Files Modified

- `docs/notebooks/01_forward_pipeline.ipynb` — re-executed, outputs refreshed
- `docs/notebooks/02_explore_gnn.ipynb` — re-executed, outputs refreshed
- `docs/notebooks/03_reverse_synthesis.ipynb` — re-executed, outputs refreshed
- `docs/notebooks/04_roundtrip.ipynb` — re-executed, outputs refreshed
- `docs/notebooks/05_custom_rules.ipynb` — re-executed, outputs refreshed
- `docs/notebooks/06_plugin_authoring.ipynb` — re-executed, outputs refreshed
- `docs/notebooks/07_real_world_flask.ipynb` — re-executed, outputs refreshed
- `docs/notebooks/08_constraint_authoring.ipynb` — re-executed, outputs refreshed
- `docs/notebooks/09_plugin_authoring.ipynb` — re-executed, outputs refreshed
- `docs/notebooks/10_rule_dsl.ipynb` — re-executed, outputs refreshed
- `docs/notebooks/11_inference_learning.ipynb` — re-executed, outputs refreshed
- `docs/notebooks/12_cross_language.ipynb` — re-executed, outputs refreshed
- `_rnd/sweep_2026_04/tutorial_validation.md` — this report

**No `manuscript/` files touched.** No notebook source cells edited; only
output cells changed via re-execution.

## Suggested Follow-ups (for future waves)

1. Add `ipykernel`, `nbconvert`, `matplotlib`, and `pandas` to a `[dev]` /
   `[notebooks]` extras group in `pyproject.toml` so a fresh `uv sync --all-extras`
   gives a notebook-ready environment without the bootstrap above.
2. Drop a small CI helper (e.g. `scripts/run_notebooks.py`) that drives
   `nbclient.NotebookClient` with the project-root cwd, mirroring the runner
   used here, so notebooks can be re-executed deterministically in CI.
3. Consider flipping the existing `--ExecutePreprocessor.cwd` invocation in
   each notebook's docstring to a recipe that points at `nbclient` directly
   (the `nbconvert --ExecutePreprocessor.cwd=...` flag is silently dropped on
   the version of nbconvert shipped here, which is what made the first
   bootstrap attempt fail).
