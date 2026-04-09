# Agents — py/cogant/static

## Owner
Static Analysis

## Responsibilities
PythonASTParser drives all Python AST extraction. SymbolExtractor builds per-file symbol tables with qualified names and stable IDs. ImportAnalyzer classifies imports (stdlib, third-party, local) and resolves them against repo structure. CallGraphBuilder extracts caller-callee relationships and method receivers. TypeInferencer combines annotations and assignment analysis for type inference. DataFlowAnalyzer tracks variable reads/writes and data dependencies.

## Coordination
Output: SymbolInfo, ImportEdge, CallEdge, TypeInfo, DataFlowEdge records. Consumed by normalize/ (converts to LanguageFact) and graph/ (adds nodes/edges). Configuration: repo_root from ingest/. No state; each module analysis is independent.

## How to Extend
Add new AST analysis: extend PythonASTParser with visitor methods. Track new symbol kinds: extend SymbolInfo.kind enum and SymbolExtractor._extract_symbols. Add new import classification: extend ImportAnalyzer._classify_import. Support new data flow patterns: extend DataFlowVisitor and edge_type enum.
