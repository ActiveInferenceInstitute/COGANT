# Architecture

> Internal architecture of COGANT: the layered pipeline (ingest -> normalize -> graph -> translate -> score -> review -> export), the data model, and the cross-cutting concerns (concurrency, memory, performance, error handling, security). Read this section if you are modifying COGANT itself, integrating it deeply, or auditing how a result was produced. End users should usually start in [../api/](../api/), [../tutorials/](../tutorials/), or [../concepts/](../concepts/) instead.

## Contents

### Orientation

| Page | Description | Level |
|------|-------------|-------|
| [Overview](overview.md) | One-page architectural summary | Beginner |
| [System Overview](system_overview.md) | Layered system diagram and component relationships | Beginner |
| [On This Page](on_this_page.md) | Conventions used across the architecture docs | Reference |
| [Pipeline Module Index](pipeline_module_index.md) | Cross-reference of pipeline modules to source files | Reference |
| [COGANT Pipeline Index](cogant_pipeline_index.md) | Master index of pipeline-related documents | Reference |
| [Detailed Pipeline Guide](detailed_pipeline_guide.md) | Long-form walkthrough of the pipeline | Intermediate |
| [Component Details](component_details.md) | Per-component design notes | Intermediate |
| [See Also](see_also.md) | Cross-links to related documentation | Beginner |

### Cross-cutting concerns

| Page | Description | Level |
|------|-------------|-------|
| [Data Flow](data_flow.md) | How data moves between stages | Intermediate |
| [Concurrency and Parallelism](concurrency_parallelism.md) | Thread / process model and parallel-execution strategy | Advanced |
| [Memory Management](memory_management.md) | Memory ownership and budget per stage | Advanced |
| [Error Handling](error_handling.md) | Exception strategy and recovery | Intermediate |
| [Performance](performance.md) | Performance characteristics and tuning levers | Intermediate |
| [Configuration System](configuration_system.md) | Layered configuration model | Intermediate |
| [Testing Strategy](testing_strategy.md) | How COGANT itself is tested | Intermediate |
| [Extensibility](extensibility.md) | Where extension points live in the architecture | Intermediate |
| [Security Considerations](security_considerations.md) | Architectural security posture | Intermediate |

### Pipeline stages (canonical 6 + ingest)

| Page | Description | Level |
|------|-------------|-------|
| [1. Normalize](1_normalize.md) | Stage 1: normalize language-specific facts to canonical form | Intermediate |
| [2. Build Graph](2_build_graph.md) | Stage 2: build the program graph from normalized facts | Intermediate |
| [3. Translate](3_translate.md) | Stage 3: rule-based translation to Active Inference roles | Intermediate |
| [4. Score](4_score.md) | Stage 4: confidence scoring of translated nodes | Intermediate |
| [5. Review](5_review.md) | Stage 5: human-in-the-loop review and curation | Intermediate |
| [6. Export](6_export.md) | Stage 6: emit the final GNN package and audit trail | Intermediate |
| [Detailed Graph Engine](detailed_graph_engine.md) | Internals of the graph engine that powers stages 2-3 | Advanced |
| [Graph Engine Summary](graph_engine_summary.md) | Compressed reference for the graph engine | Reference |
| [COGANT Engine Implementation Summary](cogant_engine_implementation_summary.md) | Implementation snapshot of the engine | Reference |
| [COGANT Graph Construction, Normalization, and Translation Engine](cogant_graph_construction_normalization_and_translation_engine.md) | Long-form engine description | Advanced |
| [COGANT Ingest and Static Analysis Pipeline](cogant_ingest_and_static_analysis_pipeline.md) | Long-form ingest + static analysis description | Advanced |

### Stage-by-stage step references

These finer-grained pages document individual operations inside each stage. Useful when debugging a specific call site; not required reading for the big picture.

| Page | Stage | Description |
|------|-------|-------------|
| [Step 1: Ingest Repository](step_1_ingest_repository.md) | Ingest | Repository ingest entry point |
| [Ingest a Local Repository](ingest_a_local_repository.md) | Ingest | Local-path ingest path |
| [Ingest a Remote Git Repository](ingest_a_remote_git_repository.md) | Ingest | Remote git ingest path |
| [Enumerate All Source Files](enumerate_all_source_files.md) | Ingest | File-walking strategy |
| [Parse Python setup.py](parse_python_setuppy.md) | Ingest | Manifest parser |
| [Parse requirements.txt](parse_requirementstxt.md) | Ingest | Manifest parser |
| [Parse pyproject.toml](parse_pyprojecttoml.md) | Ingest | Manifest parser |
| [Parse package.json](parse_packagejson.md) | Ingest | Manifest parser |
| [Parse Cargo.toml](parse_cargotoml.md) | Ingest | Manifest parser |
| [Parse from File](parse_from_file.md) | Ingest | Generic file parser entry |
| [Parse from String](parse_from_string.md) | Ingest | Generic string parser entry |
| [Step 2: Analyze Each Python File](step_2_analyze_each_python_file.md) | Analyze | Per-file static analysis |
| [Extract from File](extract_from_file.md) | Analyze | Symbol extractor (file) |
| [Extract from Source](extract_from_source.md) | Analyze | Symbol extractor (source) |
| [Extract Symbols](extract_symbols.md) | Analyze | Symbol-extraction details |
| [Analyze File](analyze_file.md) | Analyze | File-level analysis |
| [Analyze Source](analyze_source.md) | Analyze | Source-level analysis |
| [Analyze Imports](analyze_imports.md) | Analyze | Import resolution |
| [Build Call Graph](build_call_graph.md) | Analyze | Call-graph construction |
| [Infer Types](infer_types.md) | Analyze | Type inference |
| [Infer from File](infer_from_file.md) | Analyze | Inference (file entry) |
| [Infer from Source](infer_from_source.md) | Analyze | Inference (source entry) |
| [Analyze Data Flow](analyze_data_flow.md) | Analyze | Data-flow analysis |
| [Step 1: Normalize Language-Specific Facts](step_1_normalize_language_specific_facts.md) | Normalize | Normalize entry |
| [Language-Specific Fact](language_specific_fact.md) | Normalize | Per-language fact model |
| [Normalize to Canonical Form](normalize_to_canonical_form.md) | Normalize | Canonicalization |
| [Generate Stable IDs](generate_stable_ids.md) | Normalize | Stable identifier scheme |
| [Same Inputs = Same ID (Deterministic)](same_inputs_same_id_deterministic.md) | Normalize | Determinism guarantee |
| [Hash Statistics](totalidentities_n_uniquehashinputs_m_typemodule_x.md) | Normalize | Hash-input statistics example |
| [NodeKind == CLASS](normalizednodekind_nodekindclass.md) | Normalize | NodeKind enumeration example |
| [Normalized Metadata](normalizedmetadata_contains_visibility_decorators_etc.md) | Normalize | Metadata payload example |
| [Step 2: Build Graph from Normalized Facts](step_2_build_graph_from_normalized_facts.md) | Build Graph | Build-graph entry |
| [Step 3: Build Program Graph from Extracted Information](step_3_build_program_graph_from_extracted_information.md) | Build Graph | Program-graph construction |
| [Convert to Node](convert_to_node.md) | Build Graph | Fact-to-node conversion |
| [Add Nodes](add_nodes.md) | Build Graph | Node insertion |
| [Add Edge](add_edge.md) | Build Graph | Edge insertion |
| [Add Edges from Analysis Results](add_edges_from_analysis_results.md) | Build Graph | Bulk edge insertion |
| [Step 3: Merge with Dynamic Analysis Results](step_3_merge_with_dynamic_analysis_results_if_available.md) | Build Graph | Static + dynamic merge |
| [Merge Static and Dynamic Graphs](merge_static_and_dynamic_graphs.md) | Build Graph | Merge details |
| [Query](query.md) | Build Graph | Graph query API |
| [Graph Statistics](totalnodes_2_totaledges_1_connectedcomponents_1.md) | Build Graph | Graph statistics example |
| [Finalize](finalize.md) | Build Graph | Finalization step |
| [Filter](filter.md) | Build Graph | Graph filtering |
| [Centrality](centrality.md) | Build Graph | Centrality metrics |
| [Path Finding](path_finding.md) | Build Graph | Path-finding utilities |
| [Components and Cycles](components_and_cycles.md) | Build Graph | SCC / cycle detection |
| [Dependencies](dependencies.md) | Build Graph | Dependency extraction |
| [Step 4: Translate Using Rules](step_4_translate_using_rules.md) | Translate | Translate entry |
| [Register Rules](register_rules.md) | Translate | Rule-registration API |
| [...Register 6 More Rules](register_6_more_rules.md) | Translate | Rule-registration example |
| [Translate](translate.md) | Translate | Translation operation |
| [Analyze](analyze.md) | Translate | Post-translate analysis |
| [Step 5: Score by Confidence](step_5_score_by_confidence.md) | Score | Score entry |
| [Score Mappings](score_mappings.md) | Score | Mapping scoring |
| [Filter by Confidence](filter_by_confidence.md) | Score | Confidence filtering |
| [Identify Issues](identify_issues.md) | Score | Issue identification |
| [Report](report.md) | Score | Score-stage report |
| [Total Scored](totalscored_n.md) | Score | Score statistic example |
| [Average Confidence](averageconfidence_xxx.md) | Score | Score statistic example |
| [Tier Distribution](tierdistribution.md) | Score | Tier statistic example |
| [Step 6: Human Review and Curation](step_6_human_review_and_curation.md) | Review | Review entry |
| [Review Process (Interactive)](review_process_interactive.md) | Review | Interactive review flow |
| [Add for Review](add_for_review.md) | Review | Queue an item for review |
| [Accept](accept.md) | Review | Accept a reviewed item |
| [Split](split.md) | Review | Split a reviewed item |
| [Step 7: Export Final Mappings](step_7_export_final_mappings.md) | Export | Export entry |
| [Export](export.md) | Export | Export operation |
| [Audit](audit.md) | Export | Export audit trail |
| [Access Results](access_results.md) | Export | Reading exported results |
| [Use final_mappings for GNN Training](use_finalmappings_for_gnn_training.md) | Export | Downstream GNN-training use case |

## Recommended Reading Order

1. [Overview](overview.md) — one-page summary of the architecture.
2. [System Overview](system_overview.md) — see the layered diagram.
3. [Detailed Pipeline Guide](detailed_pipeline_guide.md) — long-form pipeline walkthrough.
4. The six canonical stage pages in order: [1. Normalize](1_normalize.md), [2. Build Graph](2_build_graph.md), [3. Translate](3_translate.md), [4. Score](4_score.md), [5. Review](5_review.md), [6. Export](6_export.md).
5. [Detailed Graph Engine](detailed_graph_engine.md) — internals of the engine that powers stages 2 and 3.
6. The cross-cutting concerns table when you start touching real code: [Data Flow](data_flow.md), [Error Handling](error_handling.md), [Performance](performance.md), [Configuration System](configuration_system.md), [Testing Strategy](testing_strategy.md), [Extensibility](extensibility.md), [Security Considerations](security_considerations.md).
7. The stage-by-stage step references only when debugging a specific call site.

Agent notes: [AGENTS.md](AGENTS.md) - Hub: [../index.md](../index.md)
