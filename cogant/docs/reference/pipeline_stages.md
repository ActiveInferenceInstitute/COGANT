## Pipeline runner stages

> **Canonical source:** `cogant/evaluation/METRICS.yaml` (`pipeline.stage_count`, `pipeline.runner_stages`), generated from the default `PipelineConfig.stages` list in `py/cogant/api/pipeline.py`.

The `PipelineRunner` executes an ordered list of **runner stages** (currently **10**). This is distinct from the **six-layer conceptual IR progression** (repo → program graph → semantic mapping → state space → process → validation) described in the manuscript and architecture docs—those layers are *artifacts*, not necessarily 1:1 with runner stage boundaries.

Default order:

1. **ingest** — snapshot repository, enumerate files
2. **static** — AST / symbols / per-file extraction
3. **normalize** — canonicalize representations before graph build
4. **graph** — build the typed program graph
5. **dynamic** — optional coverage/trace enrichment
6. **translate** — fixpoint translation rules and semantic roles
7. **statespace** — compile state-space model
8. **process** — process / execution sketch
9. **export** — GNN bundle and companion artifacts
10. **validate** — integrity and schema checks

Markov blanket extraction and GNN matrix formatting run inside the orchestrated pipeline where the implementation wires them (typically around state-space, process, and export). The **reverse** synthesizer (`cogant.reverse`) is a separate workflow from a completed bundle, not a `PipelineRunner` stage in the default list.

Roundtrip evaluation figures (`role_preserved_count`, `strict_isomorphism_count`, mean `role_preservation_score`, and drift/failure counts) are recorded in `cogant/evaluation/METRICS.yaml` and `cogant/docs/evaluation/ROUNDTRIP_EVAL.md`.
