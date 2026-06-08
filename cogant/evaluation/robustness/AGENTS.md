# AGENTS.md - Robustness Evaluation

This folder contains robustness-check scripts plus their generated outputs.

Rules:

- Keep deterministic probe logic in `harness.py` and `transforms.py`.
- Do not hand-edit `robustness_results.json` or `robustness_table.md` to change
  conclusions; regenerate them from the harness.
- Keep claims narrow: these probes test selected transformations, not full
  semantic equivalence of arbitrary repositories.
- After edits, run the robustness harness and the relevant manuscript/docs
  audits before citing results.
