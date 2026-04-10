# Evaluation artifacts

Machine-readable benchmarks, third-party repo mirrors for roundtrip tests, dashboards, and
pipeline outputs. This tree is **not** part of the installable Python package (`py/cogant/`);
it ships with the repository for reproducibility and R&D traceability.

| Path | Role |
| --- | --- |
| [`dataset/`](dataset/) | Roundtrip JSONL, HuggingFace-style dataset card, `regenerate.py` |
| [`eval_repos/`](eval_repos/) | Pinned third-party libraries for evaluation (retain upstream `LICENSE` files) |
| [`dashboards/`](dashboards/) | Static HTML dashboards (e.g. benchmark charts) |
| [`figures/`](figures/) | Figure generators and metrics snapshots used by docs and manuscript |
| [`run_eval.py`](run_eval.py) | Real-world pipeline evaluation driver |

Narrative write-ups (R&D log, calibration notes, release analyses) live under
[`docs/evaluation/`](../docs/evaluation/README.md).
