# Static Analysis Architecture

## Overview

The static analysis module (`cogant.static`) extracts code facts **before graph construction**. It is stage 2 of the 10-stage pipeline, consuming raw Python source files and producing typed, immutable fact records (symbols, imports, calls, types, data flow, complexity, coupling, dead code, metrics).

**Design principle**: Deterministic, no runtime data. All facts are derived from AST (Abstract Syntax Tree) parsing and heuristic analysis. Same source → same facts (reproducible).

## Data Flow

```
                      Stage 1: ingest/
                             ↓
                      Source Files
                             ↓
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
    parser.py         [AST analysis pipeline]
        ↓                     ↓                     ↓
        └─→ PythonASTParser ──┴─→ AST Nodes
                              ↓
        ┌─────────────────────┼──────────────────────────────────────┐
        ↓                     ↓                     ↓                 ↓
    symbols.py          imports.py            calls.py           types.py
    ↓                    ↓                     ↓                   ↓
SymbolInfo        ImportEdge/ImportAnalyzer  CallEdge/Builder     TypeInfo
        ↓                     ↓                     ↓                 ↓
        └─────────────────────┼──────────────────────────────────────┘
                              ↓
                    dataflow.py (DataFlowAnalyzer)
                              ↓
                         DataFlowEdge
                              ↓
        ┌─────────────────────┼──────────────────────────────────────┐
        ↓                     ↓                     ↓                 ↓
  complexity.py         coupling.py           dead_code.py       metrics.py
  ↓                     ↓                     ↓                   ↓
ComplexityReport  CouplingReport        DeadCodeReport      CodeMetrics
                                                            HalsteadMetrics
                              ↓
                    [All facts combined]
                              ↓
                       Stage 3: normalize/
                              ↓
                        LanguageFact (canonical)
                              ↓
                       Stage 4: graph/
                              ↓
                      ProgramGraph (nodes + edges)
```

## Key Modules

### Foundation: Parsers & Extractors

**parser.py: PythonASTParser**
- Entry point: `parse_file(path)` or `parse_string(source)`
- Uses CPython `ast` module (Python 3.11+)
- Graceful error handling: logs syntax errors, returns empty AST on failure
- No caching; each parse is independent (stateless)

**symbols.py: SymbolExtractor**
- Builds per-file symbol tables with qualified names (e.g., "MyClass.my_method")
- Extracts: functions, methods, classes, variables, constants
- Assigns stable IDs (based on qualified name + location)
- Outputs: `SymbolInfo` records
- Key facts: `name`, `kind`, `qualified_name`, `is_public`, `line_start`, `line_end`, `type_hint`, `docstring`

**imports.py: ImportAnalyzer**
- Classifies imports: stdlib (e.g., `os`, `sys`), third-party (e.g., `numpy`), local (e.g., `my_module`)
- Resolves import paths against repo root (optional)
- Outputs: `ImportEdge` records (source_module, target_module, import_kind)
- Builds global dependency graph (used by coupling analysis)

**calls.py: CallGraphBuilder**
- Extracts function/method calls from call expressions
- Tracks: caller location, callee reference, argument count
- Heuristic method dispatch (static only; imprecise)
- Outputs: `CallEdge` records

**types.py: TypeInferencer**
- Combines annotations (Python 3.11+ type hints) with assignment analysis
- Infers variable types from assignments, function returns
- Outputs: `TypeInfo` records with confidence scores
- Confidence < 1.0 for heuristic-only inferences

**dataflow.py: DataFlowAnalyzer**
- Tracks variable reads, writes, and data dependencies
- Builds intra-procedural data flow graphs (reaching definitions)
- Identifies: definition (def), use (use), kill (reassign)
- Outputs: `DataFlowEdge` records (READ, WRITE, CONTROL_FLOW)
- No inter-procedural analysis (too expensive)

### Analysis: Metrics & Quality

**complexity.py: ComplexityAnalyzer**
- **Cyclomatic Complexity (CC)**: counts decision points (if, elif, for, while, except, boolean ops, ternary)
- **Cognitive Complexity**: adds nesting depth penalty + decision points
- Per-function and per-file aggregates
- Outputs: `ComplexityEntry` (per-symbol), `ComplexityReport` (per-file)
- No AST traversal limit; processes all code

**coupling.py: CouplingAnalyzer**
- **Martin Metrics**: Instability (I), Abstractness (A), Distance from Main Sequence (D = |A+I-1|)
- Afferent Coupling (Ca): count of dependents
- Efferent Coupling (Ce): count of dependencies
- Zone of pain: high concrete + high instability (D > 0.3, I > 0.8)
- Zone of uselessness: high abstract + low instability (D > 0.3, I < 0.2)
- Outputs: `ModuleCouplingMetrics` (per-module), `CouplingReport` (per-package)
- Requires pre-built import graph from ImportAnalyzer

**dead_code.py: DeadCodeDetector**
- Identifies unused imports, functions, variables, unreachable statements
- Confidence scoring: 0.95 (imports), 0.8 (functions), 0.7 (variables)
- Filters private symbols only (starts with `_`) to reduce false positives
- Outputs: `DeadCodeEntry` (per-finding), `DeadCodeReport` (per-file)
- Method: `get_certain_entries()` filters for confidence >= 0.9

**metrics.py: MetricsAnalyzer**
- **Code Metrics**: LOC, logical lines, comments, blanks, docstring coverage
- **Halstead Metrics**: vocabulary, length, volume, difficulty, effort
- Counts unique/total operators and operands from AST
- Outputs: `CodeMetrics`, `HalsteadMetrics` dataclasses
- Fast: ~10-50ms per file

## Architecture Decisions

### Why AST-Only (No Runtime Data)?

1. **Reproducibility**: Same source → same facts (no flakiness)
2. **Scalability**: Works on all code, not just executed paths
3. **Speed**: No instrumentation or tracing overhead
4. **Deployment**: No need for test harnesses or execution environment

### Why Confidence Scores?

- Heuristic analyses are inherently imprecise (e.g., dead code detection)
- Confidence scores let consumers (validation, export) decide thresholds
- Example: 0.95 (import) vs 0.7 (variable) reflects precision asymmetry

### Why Per-File Aggregates?

- Downstream graph builder needs per-function/per-module facts
- Aggregates (average, max, hotspots) computed by **reports** (ComplexityReport, CouplingReport)
- Enables per-symbol precision + per-file summaries

### Why Separate Complexity/Coupling/DeadCode Modules?

- Independent analyses; no shared state
- Can be run/parallelized separately
- Each produces its own report type
- Reduces coupling between analyzers

## Integration with Graph Builder

The graph builder (`cogant/graph/builder.py`) **consumes static facts** and converts them to nodes/edges:

```python
# Static analyzer produces facts
facts = static_analyzer.extract(source_file)
# Facts include: SymbolInfo, ImportEdge, CallEdge, ComplexityEntry, etc.

# Normalizer converts to canonical form
normalized = normalize(facts)  # → LanguageFact

# Graph builder consumes normalized facts
builder.add_node(fact.to_node())  # Creates Node
for edge in fact.to_edges():
    builder.add_edge(edge.source_id, edge.target_id, edge.kind)  # Creates Edge

# Node metadata includes complexity, coupling, metrics
node.metadata = {
    'cyclomatic_complexity': 8,
    'cognitive_complexity': 5,
    'instability': 0.6,
    'lines_of_code': 45,
    'docstring_coverage': 0.8,
}
```

## Error Handling

All analyzers follow a **degradation pattern**:

```python
report = analyzer.analyze(source, file_path)

if report.errors:
    logger.warning(f"Analysis error in {file_path}: {report.errors}")

# Results are **still usable** (partial) even with errors
# Example: syntax error prevents type inference, but complexity still computed
```

Common error messages:
- `"Syntax error: ..."` → Source code is not valid Python
- `"Failed to read file: ..."` → File I/O error

## Performance Characteristics

| Analyzer | Time/File | Memory | Notes |
|----------|-----------|--------|-------|
| PythonASTParser | ~1-10ms | O(source size) | Fast; AST is efficient |
| SymbolExtractor | ~2-5ms | O(num symbols) | Extracts table |
| ImportAnalyzer | ~1-3ms | O(num imports) | Builds dep graph |
| CallGraphBuilder | ~2-5ms | O(num calls) | AST walk |
| TypeInferencer | ~3-8ms | O(num assignments) | Heuristic pass |
| DataFlowAnalyzer | ~5-15ms | O(variables) | Reaching defs |
| ComplexityAnalyzer | ~2-5ms | O(num functions) | Decision counting |
| CouplingAnalyzer | ~1-2ms | O(modules) | Matrix ops |
| DeadCodeDetector | ~3-8ms | O(symbols) | Usage tracking |
| MetricsAnalyzer | ~1-3ms | O(source lines) | Fast scanning |

**Total per-file**: ~25-75ms (typical Python file, ~200 LOC)

For a 1000-file project:
- Sequential: 25-75 seconds
- Parallel (8 cores): 3-10 seconds

## Extensibility

### Add a New Analysis

1. Create `py/cogant/static/my_analysis.py`
2. Define report dataclass: `@dataclass class MyAnalysisReport:`
3. Implement visitor: `class MyVisitor(ast.NodeVisitor):`
4. Implement analyzer: `class MyAnalyzer:`
5. Add to `__init__.py` exports

**Example:**
```python
@dataclass
class SecurityFinding:
    pattern: str
    location: tuple[int, int]
    severity: str  # 'high', 'medium', 'low'
    confidence: float

@dataclass
class SecurityReport:
    findings: list[SecurityFinding]
    errors: list[str]

class SecurityAnalyzer:
    def analyze(self, source: str, file_path: Path) -> SecurityReport:
        # Find SQL injection patterns, hardcoded credentials, etc.
        pass
```

### Add New Complexity Algorithm

1. Extend `ComplexityVisitor` with new decision point detection
2. Add new metric field to `ComplexityEntry` (e.g., `halstead_effort`)
3. Update aggregates in `ComplexityReport`

### Add Module-Level Analysis

1. Extend `ImportAnalyzer` to compute module statistics
2. Enhance `CouplingAnalyzer` with new metrics (e.g., cohesion scores)
3. Add module-level entries to reports

## Related Modules

- **ingest/** → provides source files to analyze
- **normalize/** → converts facts to canonical form
- **graph/** → consumes normalized facts, builds ProgramGraph
- **validate/** → scores static findings, flags quality issues
- **export/** → serializes reports to JSON, CSV, etc.

## See Also

- `py/cogant/static/AGENTS.md` — Agent responsibilities and workflows
- `py/cogant/static/README.md` — Module-level documentation
- `docs/reference/static_analysis.md` — API reference (this file's companion)
- `py/cogant/schemas/core.py` — Node/Edge/NodeKind/EdgeKind definitions
