---
language: en
license: apache-2.0
task_categories:
  - text-generation
  - structured-prediction
tags:
  - active-inference
  - program-analysis
  - GNN
  - POMDP
  - code-understanding
  - roundtrip-evaluation
  - codebase-to-gnn
pretty_name: COGANT Native Roundtrip Evaluation Dataset
size_categories:
  - n<1K
---

# COGANT Native Roundtrip Evaluation Dataset

This dataset records COGANT roundtrip checks over the Python fixture corpus
that ships with the project. Each row is produced by the native v0.6 roundtrip
path:

1. translate a Python fixture to a program graph and GNN package;
2. synthesize a Python package back from the GNN;
3. translate the synthesized package again; and
4. compare the original and synthesized semantic-role multisets plus graph
   and matrix diagnostics.

The authoritative data file is [`roundtrip_results.jsonl`](roundtrip_results.jsonl).
It is regenerated from source fixtures by
[`../../../tools/regenerate_roundtrip_ledger.py`](../../../tools/regenerate_roundtrip_ledger.py)
and summarized into [`../METRICS.yaml`](../METRICS.yaml) by
[`../../../tools/regenerate_metrics.py`](../../../tools/regenerate_metrics.py).
Do not hand-edit row counts or status distributions in prose.

## Corpus

The generator walks these local fixture groups:

| Group | Path | Purpose |
|---|---|---|
| `zoo` | `examples/zoo/` | Small Active Inference/POMDP primitives designed to exercise individual roles and matrix shapes. |
| `control_positive` | `examples/control_positive/` | Role-bearing fixtures with known hidden-state, observation, and action structure. |
| `real_world` | `examples/real_world/` | Small Python packages that resemble real application code while remaining reproducible in the repository. |

JavaScript-only fixtures are skipped by this ledger because the current
roundtrip claim is scoped to the Python front end.

## Schema

Each JSONL row is self-classifying and contains:

| Field | Type | Description |
|---|---|---|
| `rank` | int | Deterministic display rank after sorting by role-preservation score, group, and repo. |
| `group` / `fixture_group` | str | Fixture group: `zoo`, `control_positive`, or `real_world`. |
| `repo` | str | Fixture directory name. |
| `roundtrip_status` | str | One of `STRUCTURALLY_ISOMORPHIC`, `ROLE_PRESERVED`, `DRIFT`, `FAILED`, or `NON_NATIVE`. |
| `role_preservation_score` | float | Native v0.6 role-multiset preservation score in `[0, 1]`. |
| `structurally_isomorphic` | bool | Whether strict structural isomorphism held for the checked representation. |
| `matrix_score` / `structural_score` | float | Matrix and graph-structure comparison scores emitted by the roundtrip verifier. |
| `generated_code_ok` | bool | Whether the synthesized Python package compiled and passed the verifier's code check. |
| `orig_n_hidden`, `orig_n_obs`, `orig_n_actions` | int | Original role counts for hidden states, observations, and actions. |
| `synth_n_hidden`, `synth_n_obs`, `synth_n_actions` | int | Re-forwarded synthesized role counts for the same role families. |
| `shape_match` | object | Per-shape comparison details when available. |
| `node_count`, `edge_count` | int | Original program-graph size. |
| `file_count`, `loc` | int | Python source files and lines counted by the ledger generator. |
| `elapsed_s` | float | Wall-clock seconds for the fixture roundtrip on the local machine. |
| `error` | str | Present only for failed rows. |

`tools/check_metrics_fresh.py` verifies that `METRICS.yaml` matches the live
JSONL distribution and now rejects zero-role `control_positive` rows, because
such rows cannot support a role-preservation claim.

## Reproducibility

From the project root:

```bash
uv run --directory cogant python ../tools/regenerate_roundtrip_ledger.py
uv run --directory cogant python ../tools/regenerate_metrics.py
uv run python tools/check_metrics_fresh.py
```

The ledger is deterministic except for `elapsed_s`, which is a local
wall-clock measurement. Commit refreshed JSONL and YAML together.

## Intended Use

- Regression testing of the forward/reverse/forward COGANT pipeline.
- Corpus-level tracking of role-preservation and drift rows.
- Fixture design review: rows with zero original role counts are not valid
  positive roundtrip evidence.
- Benchmarking alternative reverse-synthesis strategies against the same
  role-preservation schema.

## Limitations

- The ledger is Python-front-end evidence only.
- Role labels are produced by COGANT rules, not by human annotators.
- Role preservation is weaker than semantic equivalence of arbitrary Python
  behavior.
- Wall-clock timings are provided for local diagnostics, not cross-machine
  performance claims.

## Citation

```bibtex
@software{cogant2026,
  title   = {COGANT: Codebase-to-GNN Analysis Tool},
  author  = {Friedman, Daniel Ari},
  year    = {2026},
  url     = {https://github.com/docxology/template},
  version = {0.6.0}
}
```

## License

Apache 2.0. See [`LICENSE`](LICENSE) for the full text. Third-party evaluation
repositories under `../eval_repos/` carry their own upstream licenses.
