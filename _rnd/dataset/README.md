---
dataset: cogant-ml-v0.1
version: 0.1.0
date: 2026-04-09
license: MIT
language:
  - code
  - en
tags:
  - code
  - program-graph
  - active-inference
  - gnn
  - semantic-role-classification
task_categories:
  - node-classification
  - graph-classification
size_categories:
  - n<1K
---

# COGANT ML Dataset (v0.1.0)

A structured collection of `(repository, program_graph, semantic_mappings, GNN)`
triples extracted by the [COGANT](../../) codebase-to-GNN translation engine
from six Python repositories. Every program graph node is labeled with an
Active Inference semantic role (`HIDDEN_STATE`, `OBSERVATION`, `ACTION`,
`POLICY`, `CONSTRAINT`, `CONTEXT`, or `UNMAPPED`) and joined with the
deterministic `A`/`B`/`C`/`D` matrices produced by COGANT's GNN compiler.

The dataset is intended to support three research uses:

1. **Train** lightweight node-classification models that predict Active
   Inference roles from code-structural and lexical features.
2. **Evaluate** COGANT translation quality against human judgments by
   layering expert labels on top of the rule-derived labels ship here.
3. **Reproduce** every quantitative result in the COGANT manuscript: the
   generator re-runs the full pipeline, no post-hoc editing.

## Files

| File | Description | Rows |
|---|---|---|
| `instances.jsonl` | One JSON object per repository (graph stats, GNN shape, split). | 6 |
| `nodes.jsonl`     | One JSON object per program-graph node (features + role). | 286 |
| `instances/{name}.json` | Full per-repo bundle (instance metadata, all nodes, all edges). | 6 |
| `dataset_summary.json` | Aggregate counts and split assignment. | 1 |
| `generate_dataset.py`  | Deterministic generator script (rerun with `python _rnd/dataset/generate_dataset.py`). | - |

## Statistics

Generated on `2026-04-09` with `cogant==0.1.0`.

### Instance level

| split | repos | nodes | edges | mappings |
|---|---|---|---|---|
| train | 2 | 35  | 61  | 32  |
| val   | 2 | 55  | 74  | 44  |
| test  | 2 | 196 | 306 | 124 |
| **all** | **6** | **286** | **441** | **200** |

### Role distribution (node-level)

| Role | Count | % |
|---|---|---|
| `ACTION`       | 83 | 29.0% |
| `UNMAPPED`     | 84 | 29.4% |
| `OBSERVATION`  | 69 | 24.1% |
| `HIDDEN_STATE` | 27 |  9.4% |
| `POLICY`       | 16 |  5.6% |
| `CONTEXT`      |  5 |  1.7% |
| `CONSTRAINT`   |  2 |  0.7% |

`UNMAPPED` is the residual class: program graph nodes that no translation rule
matched. Practitioners may treat it as an explicit "background" class or drop
it for closed-set classification.

### Per-repo summary

| repo | split | nodes | edges | mappings | A shape | B shape |
|---|---|---|---|---|---|---|
| calculator     | train | 12  | 25  | 11 | [3, 1]   | [1, 1, 6]   |
| event_pipeline | train | 23  | 36  | 21 | [9, 1]   | [1, 1, 11]  |
| flask_mini     | val   | 26  | 40  | 25 | [2, 3]   | [3, 3, 20]  |
| json_stdlib    | val   | 29  | 34  | 19 | [1, 3]   | [3, 3, 15]  |
| flask_app      | test  | 98  | 154 | 67 | [21, 9]  | [9, 9, 31]  |
| requests_lib   | test  | 98  | 152 | 57 | [33, 8]  | [8, 8, 16]  |

## Schema

### `nodes.jsonl` (node-level)

One line per program graph node.

| Field | Type | Description |
|---|---|---|
| `repo_id`               | str   | Repository short name (e.g. `calculator`). |
| `node_id`               | str   | Stable deterministic node hash from COGANT. |
| `node_name`             | str   | Short human-readable name (symbol). |
| `node_qualified_name`   | str   | Fully-qualified name (`module.Class.method`). |
| `node_kind`             | str   | One of `module`, `class`, `method`, `function`. |
| `node_path`             | str   | Source file path (relative to repo root). |
| `assigned_role`         | str   | Supervision target: `HIDDEN_STATE`, `OBSERVATION`, `ACTION`, `POLICY`, `CONSTRAINT`, `CONTEXT`, or `UNMAPPED`. |
| `mapping_id`            | str\|null | Semantic mapping ID that assigned the role (null when `UNMAPPED`). |
| `confidence_score`      | float | COGANT `ConfidenceModel` score in `[0, 1]`. |
| `in_degree`             | int   | Incoming edges in the program graph. |
| `out_degree`            | int   | Outgoing edges in the program graph. |
| `writes_count`          | int   | Outgoing `WRITES` edges (dataflow). |
| `reads_count`           | int   | Outgoing `READS` edges (dataflow). |
| `calls_count`           | int   | Outgoing `CALLS` edges. |
| `depends_on_count`      | int   | Outgoing `DEPENDS_ON` edges. |
| `contains_out_count`    | int   | Outgoing `CONTAINS` edges (containment). |
| `has_type_annotation`   | bool  | Parser reports a type annotation (reserved; currently always `false`). |
| `is_method`             | bool  | Node is a class method (vs free function or module). |
| `is_async`              | bool  | Reserved for async-detection (currently always `false`). |
| `name_has_action_keyword` | bool | Name starts with or contains one of COGANT's 24 action verbs. |
| `lines_of_code`         | int   | Span derived from `source_range` metadata (0 if unknown). |
| `rule_fired`            | str   | Which COGANT translation rule produced the label (derived from mapping ID prefix). |
| `split`                 | str   | `train`, `val`, or `test`. |

### `instances.jsonl` (instance-level)

One line per repository. Key groups:

- `instance_id`, `repo_id`, `repo_path`, `date_processed`, `cogant_version`, `split`
- `graph`: `{node_count, edge_count, node_kinds, node_roles, edge_types}`
- `mappings`: `{count, kinds, mean_confidence}`
- `gnn`: `{A_shape, B_shape, C_len, D_len, n_states, n_obs, n_actions, A_sparsity, D_entropy}`
- `state_space`: `{variables, observations, actions, schema_name}`
- `process_model`: `{stages, connections}`
- `source`: `{files, lines}`
- `edges`: list of `{edge_id, source_id, target_id, kind, weight}`

### `instances/{name}.json` (full bundle)

Each per-repo file is a JSON object with:

```json
{
  "instance":  { ...instance record... },
  "nodes":     [ ...node rows for this repo... ]
}
```

This is the file you want for joint graph-level + node-level supervised
learning where both structure (edges) and labels are needed at once.

## Splits

Deterministic assignment by whole repository (not by node) to preserve the
stylistic differences between fixtures, which is what few-shot code-LM
studies typically care about:

- **train** (2 repos): `calculator`, `event_pipeline`
- **val**   (2 repos): `flask_mini`, `json_stdlib`
- **test**  (2 repos): `flask_app`, `requests_lib`

The node counts are unbalanced (train 35 / val 55 / test 196) because the
two real-world test repos are much larger than the control-positive train
fixtures. Do not stratify by node count -- the point is to measure
generalization across independent codebases.

## Usage

```python
import json

# Node-level
nodes = [json.loads(line) for line in open("_rnd/dataset/nodes.jsonl")]
train_nodes = [n for n in nodes if n["split"] == "train"]
print(f"train nodes: {len(train_nodes)}")

# Instance-level
instances = [json.loads(line) for line in open("_rnd/dataset/instances.jsonl")]
for inst in instances:
    print(inst["repo_id"], inst["graph"]["node_count"], inst["gnn"]["A_shape"])

# Full per-repo bundle (nodes + edges + GNN shape)
with open("_rnd/dataset/instances/calculator.json") as f:
    bundle = json.load(f)
print(len(bundle["nodes"]), len(bundle["instance"]["edges"]))
```

## Reproducibility

```bash
cd projects_in_progress/cogant
python _rnd/dataset/generate_dataset.py
```

The generator is fully deterministic: no RNG seeds, no wall-clock timestamps
inside the feature rows (only inside the `date_processed` and `generated_at`
metadata strings), no mocks. Every number is computed by running COGANT on
the fixtures in `cogant/examples/`. Rerunning the generator on the same
COGANT version should produce byte-identical `nodes.jsonl` and
`instances.jsonl` modulo the timestamp fields.

## Citation

If you use this dataset please cite the COGANT manuscript:

```bibtex
@techreport{cogant2026,
  title   = {COGANT: Codebase-to-GNN Translation for Active Inference},
  author  = {COGANT Contributors},
  year    = {2026},
  version = {0.1.0-alpha},
  url     = {https://github.com/.../cogant}
}
```

## Limitations

- **Python only**: JavaScript / TypeScript graph ingestion is present in the
  COGANT codebase but not yet wired into the dataset generator.
- **Rule-derived labels**: every `assigned_role` comes from a COGANT
  translation rule -- it is a structured pseudo-label, not a human label.
  Agreement with expert annotators is not yet measured on this corpus.
- **Small corpus (6 repos)**: suitable for few-shot / transfer-learning
  studies and for unit-testing downstream models, but too small for
  high-variance training of deep GNNs from scratch. Extension to the full
  20-repo COGANT benchmark corpus is planned for v0.2.
- **Label skew**: `ACTION` and `OBSERVATION` dominate the non-`UNMAPPED`
  rows; `CONSTRAINT` has only 2 instances. Report per-class precision /
  recall, never only macro accuracy.
- **Feature columns**: `has_type_annotation` and `is_async` are reserved
  fields that are always `false` in v0.1; they will be populated by the
  richer `PythonASTParser` pass planned for v0.2.

## License

MIT. The source fixtures under `cogant/examples/` carry their own upstream
licenses (requests_lib and json_stdlib are adaptations of permissively
licensed code); see each fixture's `README.md` for attribution.
