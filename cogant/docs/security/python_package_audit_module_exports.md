## Python package audit (module exports)

```text
======================================================================
COGANT PROJECT - PYTHON MODULE AUDIT REPORT
======================================================================

AUDIT RESULTS: 21 __init__.py files audited

  ✓ (root)               docstring=True __all__=True
  ✓ api                  docstring=True __all__=True
  ✓ cli                  docstring=True __all__=True
  ✓ config               docstring=True __all__=True
  ✓ dynamic              docstring=True __all__=True
  ✓ export               docstring=True __all__=True
  ✓ gnn                  docstring=True __all__=True
  ✓ graph                docstring=True __all__=True
  ✓ ingest               docstring=True __all__=True
  ✓ normalize            docstring=True __all__=True
  ✓ plugins              docstring=True __all__=True
  ✓ process              docstring=True __all__=True
  ✓ provenance           docstring=True __all__=True
  ✓ schemas              docstring=True __all__=True
  ✓ scoring              docstring=True __all__=True
  ✓ simulate             docstring=True __all__=True
  ✓ statespace           docstring=True __all__=True
  ✓ static               docstring=True __all__=True
  ✓ translate            docstring=True __all__=True
  ✓ validate             docstring=True __all__=True
  ✓ viz                  docstring=True __all__=True

SUMMARY:
  Total files: 21
  Files with docstring: 21/21
  Files with __all__: 21/21
  Fully compliant files: 21/21

IMPORT VERIFICATION:
  ✓ Root package imports successfully
  ✓ Version: 0.1.0
  ✓ Exports: Session, PipelineRunner, Bundle, ProgramGraphBuilder, TranslationEngine, StateSpaceCompiler, GNNMarkdownFormatter, __version__

KEY EXPORTS VERIFIED:
  ✓ cogant.static: PythonASTParser, SymbolExtractor, ImportAnalyzer, CallGraphBuilder, TypeInferencer, DataFlowAnalyzer
  ✓ cogant.translate: TranslationEngine, TranslationRule, ConfidenceModel, ReviewManager
  ✓ cogant.viz: MermaidGenerator, StaticPlotter, BoundaryMapper, GraphVisualizer
  ✓ cogant.export: TypedExporter, BundleExporter, ParquetExporter
  ✓ cogant.gnn: GNNMarkdownFormatter, GNNJSONExporter
  ✓ cogant.statespace: StateSpaceCompiler, StateVariableExtractor, TemporalAnalyzer
  ✓ cogant.graph: ProgramGraphBuilder, GraphQuery, GraphMerger
  ✓ cogant.api: Session, PipelineRunner, Bundle

======================================================================
✓ AUDIT COMPLETE - ALL MODULES PROPERLY CONFIGURED
======================================================================
```

