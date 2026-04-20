# AGENTS.md — Architecture Module

This directory houses the deeply modularized documentation for the **Architecture** aspects of the COGANT translation engine.

## Integration boundary with the upstream GNN toolchain

COGANT is a 10-stage repository → GNN bundle compiler. After the validate
stage, the bundle can be handed to the Active Inference Institute
**generalized-notation-notation** package via two independent surfaces:

| Surface | Driver | Default | Failure mode |
|---------|--------|---------|--------------|
| Single-file ``validate_gnn`` | ``cogant.gnn.upstream_bridge`` (``upstream_*`` helpers); called from ``GNNValidator.validate_package`` | **on** (disable: ``--no-upstream-gnn`` / ``COGANT_DISABLE_UPSTREAM_GNN=1``) | warnings on ``ValidationResult.details["upstream_gnn"]``; never fails the stage |
| 25-step pipeline | ``cogant.gnn.upstream_bridge.pipeline.run_upstream_pipeline`` driving ``src.main.execute_pipeline_step`` | **off** (enable: ``--upstream-gnn-pipeline``); when enabled, steps 11 (``render``) and 12 (``execute``) are skipped by default | per-step results in ``bundle.artifacts['upstream_pipeline_steps' / 'upstream_pipeline_summary']``; warnings on the validate stage; never fails the stage |

Both surfaces are **advisory**: they extend COGANT's diagnostics with the
upstream toolchain but never change the deterministic 10-stage outputs.
``cogant upstream-gnn <package_dir>`` re-runs the 25-step pass against an
existing ``gnn_package/`` without re-analysing the source repository. See
``py/cogant/gnn/upstream_bridge/AGENTS.md`` for the per-step catalogue and
configuration surface.

## Maintenance Rules

*   **Granularity**: Keep articles focused. Do not reintroduce monolithic, multi-context files.
*   **Cross-Linking**: When referencing other modules, link to their respective `../module_name/README.md` indexes.
