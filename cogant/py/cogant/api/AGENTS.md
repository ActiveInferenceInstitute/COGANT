# Agents — py/cogant/api

## Owner

Runtime Lead

## Responsibilities

Provide stable, user-facing Python API entry points for codebase analysis. Orchestrate pipeline execution across all subsystems (ingest, static, normalize, graph, translate, statespace, process, export, validate). Manage Session lifecycle and Bundle assembly. Enable interactive curation workflows through ReviewAPI. Shield users from internal schema changes and module dependencies.

## Extending

Implement new pipeline stages by adding functions to orchestration.py following the pattern of run_ingest, run_static, etc. Add stage handlers to PipelineRunner._stage_* methods. Register new ReviewableMapping subtypes to support domain-specific curation. Extend Bundle accessors and render methods for custom export formats.

## Coordination

Exposes unified interfaces from ingest/, static/, normalize/, graph/, translate/, statespace/, process/, dynamic/, export/, and validate/ modules. Session delegates to orchestration functions; PipelineRunner calls stage handlers which in turn call orchestration. ReviewAPI wraps translate stage results for curation. All API types are contracts; breaking changes require Architecture Lead approval.

## Files

session.py: Session class manages target, workspace, and intermediate artifacts (syntax_tree, trace_bundle, program_graph, gnn_model, state_space, process_model). Lazy-initializes Bundle and orchestrates ingest, static, normalize, graph, translate, statespace, process, export stages.

orchestration.py: Low-level pipeline functions (run_ingest through run_validate) that load bundles, execute analysis stages, and accumulate results. Contains TranslationEngine setup, helper serialization functions, and error handling. **run_export** writes flat JSON artifacts to the output directory and, when program graph, state-space model, process model, and dict-shaped **\_semantic_mappings** are present, builds **gnn_package/** via **GNNPackageBuilder**. **run_validate** runs schema checks on the program graph and, if **\_gnn_package_dir** was set during export, attaches GNN validator results.

pipeline.py: PipelineConfig dataclass and PipelineRunner class. Runner has stage handlers mapping stage names to orchestration calls. Run method iterates stages, catches errors per stage, and supports layout_output post-processing.

bundle.py: Bundle dataclass wraps artifacts, stage_results, errors, metadata. Provides accessors (repo_summary, program_graph, state_space_model, process_model, gnn_markdown, validation_report). Implements render_site, to_json, save_json for export.

review.py: ReviewAPI class loads bundles, extracts ReviewableMapping objects, and tracks accept/reject/edit decisions. Methods include load_bundle, present_mapping, accept_mapping, reject_mapping, edit_mapping, get_review_summary, save_curated_bundle, and status queries.

__init__.py: Exports Session, PipelineRunner, PipelineConfig, Bundle, ReviewAPI, ReviewableMapping.
