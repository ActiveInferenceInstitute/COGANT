# COGANT Scaling Analysis

## Current Status

The checked-in external-repository fixture still records dulwich as the stress
case: 8601 nodes, 15441 edges, 380.02 seconds wall time, and 8510.9 MB peak RSS
in `cogant/evaluation/real_world_eval_summary.json`.

Several scaling fixes have since landed in the implementation and need a fresh
external-repository fixture run before the public performance table should be
updated. The post-fix regression target is dulwich under 120 seconds with
bounded GNN package size.

## Known Scaling Controls

| Area | Current mitigation | Source file |
|---|---|---|
| B tensor size | Cap transition tensor entries and record truncation metadata | `py/cogant/gnn/matrices.py` |
| Markdown domain lists | Truncate long domain lists in state-space tables | `py/cogant/gnn/formatter/structural.py` |
| Connected components | Build adjacency once for O(\|V\| + \|E\|) traversal | `py/cogant/graph/builder.py` |
| Dataflow AST parsing | Cache parsed ASTs per file | `py/cogant/api/orchestration.py` |
| Inheritance edge lookup | Use class-name index instead of repeated scans | `py/cogant/api/orchestration.py` |

## Current Claim Boundary

The project can claim that the checked-in dulwich fixture completed and exposed
a scaling bottleneck. It should not claim a refreshed dulwich runtime or memory
number until `REAL_WORLD_EVAL.md` and
`cogant/evaluation/real_world_eval_summary.json` are rerun together.

## Required Refresh

Run the external fixture against the same eight repositories and commit:

- refreshed `cogant/evaluation/real_world_eval_summary.json`;
- refreshed `cogant/evaluation/real_world_eval_results.json` if the companion
  summary shape changes;
- updated `REAL_WORLD_EVAL.md` table;
- updated scaling target here if the measured dulwich result changes.

Minimum acceptance criteria:

- every repository exits 0;
- every bundle exists;
- every markdown export exists;
- required GNN sections are populated;
- A/B/C/D blocks are non-empty;
- dulwich result is reported with wall time, peak RSS, package size, and any
  truncation metadata.
