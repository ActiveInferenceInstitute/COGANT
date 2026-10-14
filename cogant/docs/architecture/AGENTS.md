# AGENTS.md — Architecture Module

This directory houses the deeply modularized documentation for the **Architecture** aspects of the COGANT translation engine.

## Integration boundary with the upstream GNN toolchain

COGANT is a 10-stage repository → GNN bundle compiler. After the validate
stage, the bundle can be handed to the Active Inference Institute
**generalized-notation-notation** package (optional ``upstream`` extra, pinned
to the GNN 4.1.0 release line; import package ``gnn``) via two independent
surfaces:

| Surface | Driver | Default | Failure mode |
|---------|--------|---------|--------------|
| Single-file ``validate_gnn_syntax`` (level ``standard``) | ``cogant.gnn.upstream_bridge`` (``run_upstream_validate_gnn`` / ``upstream_*`` helpers); called from ``GNNValidator.validate_package`` | **off** (enable: ``upstream_gnn=True``, ``PipelineConfig.upstream_gnn_validation=True``, or ``COGANT_ENABLE_UPSTREAM_GNN=1`` when the caller passes ``upstream_gnn=None``; ``--no-upstream-gnn`` forces off) | verdict on ``ValidationResult.details["upstream_gnn"]``; upstream errors (or ``CAPABILITY_UNAVAILABLE`` when requested but missing) join ``ValidationResult.errors``; never fails the pipeline's validate stage |
| 25-step pipeline | ``cogant.gnn.upstream_bridge.pipeline.run_upstream_pipeline`` issuing one ``python -m gnn.main --only-steps …`` invocation | **off** (enable: ``--upstream-gnn-pipeline``); when enabled, steps 1 (``setup``), 2 (``tests``), 11 (``render``), and 12 (``execute``) are skipped by default | per-step results in ``bundle.artifacts['upstream_pipeline_steps' / 'upstream_pipeline_summary']``; warnings on the validate stage; never fails the stage |

Both surfaces are **advisory**: they extend COGANT's diagnostics with the
upstream toolchain but never change the deterministic 10-stage outputs.
``cogant upstream-gnn <package_dir>`` re-runs the 25-step pass against an
existing ``gnn_package/`` without re-analysing the source repository. See
``py/cogant/gnn/upstream_bridge/AGENTS.md`` for the per-step catalogue and
configuration surface.

## Maintenance Rules

*   **Granularity**: Keep articles focused. Do not reintroduce monolithic, multi-context files.
*   **Cross-Linking**: When referencing other modules, link to their respective `../module_name/README.md` indexes.
