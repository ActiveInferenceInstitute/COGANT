# AGENTS.md - PNG Rendering

This package owns generated PNG figures for program graphs, GNN packages, state
spaces, processes, and summary panels.

Rules:

- Keep rendering deterministic where possible; avoid time- or environment-based
  styling changes.
- Use `matplotlib`'s headless backend in tests and scripts.
- Assert real PNG validity, not only non-empty files.
- When adding or renaming a renderer, update figure registries, manuscript
  references, and renderer-path audits together.
- Do not put manuscript-only prose in renderer code; keep captions in the
  manuscript figure registry or source Markdown.
