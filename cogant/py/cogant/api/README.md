# API — Stable Python Entry Points

High-level Python interfaces for end-to-end codebase analysis, pipeline orchestration, and result curation. All public types are exported from `cogant.api.__init__.py`.

Session manages pipeline state and intermediate artifacts (syntax trees, graphs, models). PipelineRunner orchestrates the full analysis pipeline in sequence. Bundle wraps all artifacts with convenient accessors and export methods. ReviewAPI enables interactive curation of analysis results.

## Classes and Functions

Session: Manages pipeline lifecycle and intermediate results for a codebase analysis session. Provides methods to extract static analysis, build program graphs, translate to GNN, compile state spaces, and export all artifacts. Tracks syntax trees, trace bundles, program graphs, GNN models, state spaces, and process models.

PipelineRunner: Orchestrates the full analysis pipeline with configurable stages (ingest, static, normalize, graph, dynamic, translate, statespace, process, export, validate). Delegates to orchestration module functions for each stage and accumulates results in a Bundle.

PipelineConfig: Configuration dataclass for pipeline execution, specifying which stages to run, which to skip, plugin configurations, output directory, dry-run mode, and post-export layout options.

Bundle: Container for all analysis artifacts and stage results. Provides accessors for repo summary, program graph, state space model, process model, GNN markdown, and validation report. Can render interactive HTML sites and export to JSON.

ReviewableMapping: Single semantic mapping available for review, with id, source, target, confidence score, evidence, and reviewer status (pending, accepted, rejected, edited).

ReviewAPI: Interactive curation interface for reviewing and editing semantic mappings extracted from analysis results. Supports loading bundles, presenting mappings, accepting/rejecting/editing mappings, and saving curated bundles.

orchestration module: Low-level pipeline stage functions called by PipelineRunner and Session. Functions include run_ingest (load and parse target), run_static (extract AST and symbols), run_normalize (canonicalize language-specific facts), run_graph (build typed program graph), run_translate (apply translation rules to produce semantic mappings), run_statespace (compile state space model), run_process (extract execution model), run_dynamic (enrich graph with coverage/trace data), run_export (write artifacts to disk), and run_validate (run schema validation checks).

## Usage Example

```python
from cogant.api import Session, PipelineRunner, PipelineConfig

# High-level: Session-based workflow
session = Session.from_target("./my_repo")
session.extract_static()
session.build_graph()
session.translate_to_gnn()
session.compile_state_space()
session.export_all("output/")

# Alternative: PipelineRunner with custom config
config = PipelineConfig(output_dir="output/", layout_output=True)
runner = PipelineRunner()
bundle = runner.run("./my_repo", config)
bundle.save_json("output/bundle.json")

# Review and curation
review_api = ReviewAPI()
review_api.load_bundle("output/bundle.json")
for mapping in review_api.get_pending_mappings():
    print(f"{mapping.source} -> {mapping.target}")
review_api.accept_mapping(mapping.id, notes="Verified")
review_api.save_curated_bundle("output/curated.json")
```

## Dependencies

Imports from ingest (RepoIngester, RepoSnapshot), graph (ProgramGraphBuilder), schemas (NodeKind, ProgramGraph, SemanticMapping), normalize (CanonicalNormalizer, LanguageFact), static (PythonASTParser), translate (TranslationEngine, ConfidenceModel, ReviewManager, translation rules), statespace (StateSpaceCompiler), process (ProcessExtractor), and validate (SchemaValidator). Also uses Typer, Rich, and standard library.
