# Static — Python AST Parsing and Code Analysis

The static module performs comprehensive static analysis of Python source code. It extracts code structure (classes, functions, variables), builds call graphs, resolves imports, infers types, and analyzes data flow.

## Module Overview

PythonASTParser is the foundation. It parses Python source files using the ast module and builds PythonModule objects containing FunctionDef, ClassDef, ImportDef, and AssignmentDef records with line ranges, decorators, docstrings, and other metadata.

SymbolExtractor converts parsed AST into a flat symbol table. Each SymbolInfo records a unique stable ID, short name, fully qualified name (e.g., module.Class.method), kind (function/class/method/variable), file path, line range, scope, optional parent ID, docstring, and decorators. Multiple symbols may have the same qualified name in different scopes; ID uniqueness is ensured via hashing.

ImportAnalyzer extracts all import statements and classifies them as local (relative to repo), stdlib (Python standard library), or third-party. ImportEdge records source file, imported module name, relative/absolute classification, resolution status, and imported names (for "from X import Y").

CallGraphBuilder extracts function and method calls from code. CallEdge records caller and callee identifiers/names, line number, receiver object (for method calls), and argument strings. Call resolution is attempted but callee_id may be None for unresolved calls.

TypeInferencer extracts and infers type information. TypeInfo records symbol ID and name, kind, inferred type, explicit annotation, mutability flag, and confidence score (0.0-1.0). Inferences combine explicit annotations with type hints extracted from variable assignments and return statements.

DataFlowAnalyzer tracks variable reads, writes, and mutations within functions and across scopes. DataFlowEdge records source/target symbol names, edge type (reads, writes, mutates, depends_on), file path, line number, and context (function/method/module).

## API Reference

PythonASTParser class with methods:
- parse_file(file_path) — Parse Python file and return PythonModule
- parse_string(source, file_path) — Parse source code string and return PythonModule

SymbolExtractor class with methods:
- extract_from_file(file_path) — Extract symbols from file and return SymbolTable
- extract_from_module(module) — Extract symbols from parsed PythonModule

ImportAnalyzer class with methods:
- analyze_file(file_path) — Analyze imports in file and return list of ImportEdge
- analyze_source(source, file_path) — Analyze imports in source code string

CallGraphBuilder class with methods:
- extract_calls_from_file(file_path) — Extract all calls from file and return list of CallEdge
- extract_calls_from_function(func_def) — Extract calls from single function

TypeInferencer class with methods:
- infer_types_from_file(file_path) — Infer types for all symbols in file and return list of TypeInfo

DataFlowAnalyzer class with methods:
- analyze_file(file_path) — Analyze data flow in file and return list of DataFlowEdge

Data classes:
- FunctionDef(name, line_start, line_end, decorators, args, return_annotation, docstring, parent, is_async, metadata) — Function definition
- ClassDef(name, line_start, line_end, bases, decorators, docstring, methods, attributes, metadata) — Class definition
- ImportDef(module_name, is_relative, names, line_num, metadata) — Import statement
- AssignmentDef (variable/value information) — Variable assignment
- PythonModule(file_path, functions, classes, imports, assignments) — Parsed module
- SymbolInfo(id, name, qualified_name, kind, file_path, line_start, line_end, scope, parent_id, doc, decorators, metadata) — Symbol record
- SymbolTable(file_path, symbols, errors) — Collection of extracted symbols
- ImportEdge(id, source_file, module_name, is_relative, is_stdlib, is_third_party, is_local, resolved_file, resolved_module, line_num, imported_names, metadata) — Import relationship
- CallEdge(id, source_file, caller_id, caller_name, callee_name, callee_id, line_num, is_method_call, receiver, args, metadata) — Call relationship
- TypeInfo(symbol_id, symbol_name, symbol_kind, inferred_type, annotation, is_mutable, confidence, metadata) — Type information
- DataFlowEdge(id, source_symbol, target_symbol, edge_type, file_path, line_num, context, metadata) — Data flow relationship
