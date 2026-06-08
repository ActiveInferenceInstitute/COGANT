# Robustness Evaluation

Robustness artifacts for transformation-based checks of COGANT output.

| File | Role |
|---|---|
| `harness.py` | Runs robustness probes over selected fixtures. |
| `transforms.py` | Defines deterministic source transformations. |
| `robustness_results.json` | Generated machine-readable results. |
| `robustness_table.md` | Generated Markdown summary table. |

Regenerate results before citing them in docs or manuscript prose. Treat JSON
and Markdown outputs as generated artifacts; update the harness or transforms
first when behavior changes.
