from cogant.static import (
    SymbolExtractor, ImportAnalyzer, CallGraphBuilder,
    TypeInferencer, DataFlowAnalyzer
)

extractor = SymbolExtractor(repo_root)
symbols = extractor.extract_from_file(Path("example.py"))

analyzer = ImportAnalyzer(repo_root)
imports = analyzer.analyze_file(Path("example.py"))

builder = CallGraphBuilder(repo_root)
calls = builder.extract_calls_from_file(Path("example.py"))

inferencer = TypeInferencer(repo_root)
types = inferencer.infer_types_from_file(Path("example.py"))

flow_analyzer = DataFlowAnalyzer(repo_root)
flows = flow_analyzer.analyze_file(Path("example.py"))
