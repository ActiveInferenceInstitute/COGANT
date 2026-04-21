# Agents — py/cogant/static

## Owner
Static Analysis

## What Is the Static Module

The `static/` module performs **pre-graph code fact extraction** — the second stage of the 10-stage COGANT pipeline. It takes Python source code and derives language-specific facts: symbols (functions, classes, variables), imports, calls, types, and data flow. These facts feed into `normalize/` (stage 2) and ultimately `graph/` (stage 3), where they become nodes and edges in a `ProgramGraph`.

Static analysis runs **without runtime information**: no trace data, no dynamic instrumentation. It relies purely on AST parsing, symbol table construction, and heuristic type inference. Results are deterministic and reproducible.

## Pipeline Integration

```
stage 1: ingest/        → SourceFile
    ↓
stage 2: static/        → SymbolInfo, ImportEdge, CallEdge, TypeInfo, DataFlowEdge
    ↓
stage 2.5: normalize/   → LanguageFact
    ↓
stage 3: graph/         → ProgramGraph (nodes + edges)
    ↓
stage 4-10: translate, statespace, export, validate, ...
```

The static module is the **bridge between raw source and graph representation**. All downstream analyses depend on the quality and completeness of static facts.

## Core Components

### Existing Modules (7 files)

**parser.py** — `PythonASTParser`
- Parses Python source via `ast.parse()` (Python 3.11+)
- Entry point: `parse_file(path) -> ast.Module` and `parse_string(source) -> ast.Module`
- Handles syntax errors gracefully; logs diagnostics
- Used by all downstream analyzers

**symbols.py** — `SymbolExtractor`
- Builds per-file symbol tables with qualified names and stable IDs
- Extracts: functions, methods, classes, variables, constants, imports
- Assigns `kind` (e.g. "function", "method", "class", "variable")
- Computes `qualified_name` (e.g. "MyClass.my_method")
- Outputs: `SymbolInfo` records (name, kind, location, type, is_public)

**imports.py** — `ImportAnalyzer`
- Classifies imports: stdlib, third-party, local, relative
- Resolves import paths against repo root structure
- Tracks: import source, import target, import kind (from/import)
- Outputs: `ImportEdge` records
- Builds global dependency graph for later coupling analysis

**calls.py** — `CallGraphBuilder`
- Extracts caller-callee relationships from function calls
- Tracks: call site location, target function, argument count
- Identifies method calls and receiver types (heuristic)
- Outputs: `CallEdge` records
- Optional: method dispatch analysis (static only, imprecise)

**types.py** — `TypeInferencer`
- Combines annotations (Python 3.11+ type hints) and assignment analysis
- Infers variable types from assignments and function returns
- Outputs: `TypeInfo` records (name, inferred_type, confidence)
- Confidence < 1.0 for heuristic-only inferences

**dataflow.py** — `DataFlowAnalyzer`
- Tracks variable reads, writes, and data dependencies
- Builds data flow graphs within functions (reaching definitions)
- Identifies: definition, use, kill (reassignment)
- Outputs: `DataFlowEdge` records (READ, WRITE, CONTROL_FLOW)

**treesitter_parser.py** — `TreeSitterParser`
- Optional JavaScript/TypeScript support via tree-sitter
- Fallback to JavaScript grammar if `tree-sitter-javascript` unavailable
- Gated by language detection in pipeline
- Future: support for Rust, Go

### New Modules (4 files)

**complexity.py** — `ComplexityAnalyzer`
- **Cyclomatic Complexity**: counts decision points (if, elif, for, while, except, boolean ops, ternary)
- **Cognitive Complexity**: adds nesting depth penalty + decision points
- Per-function and per-file aggregates
- Outputs: `ComplexityEntry` (per-symbol) and `ComplexityReport` (per-file)
- Method: `analyze(source, file_path) -> ComplexityReport`
- Method: `analyze_file(file_path) -> ComplexityReport`

**coupling.py** — `CouplingAnalyzer`
- **Martin Metrics**: instability (I = Ce/(Ca+Ce)), abstractness (A), distance from main sequence (D = |A+I-1|)
- **Afferent Coupling (Ca)**: count of modules depending on this one
- **Efferent Coupling (Ce)**: count of modules this one depends on
- Zone of pain: high concrete + high instability (maintainability risk)
- Zone of uselessness: high abstract + low instability (over-designed)
- Outputs: `ModuleCouplingMetrics` (per-module) and `CouplingReport` (per-package)
- Method: `analyze(import_graph, abstract_classes, concrete_classes) -> CouplingReport`

**dead_code.py** — `DeadCodeDetector`
- Identifies unused imports, functions, variables, and unreachable code blocks
- **Confidence scoring**: 0.95 for imports (high certainty), 0.8 for functions (may be called dynamically), 0.7 for variables
- Filters private symbols only (starts with `_`) to reduce false positives
- Scope context: module, function, class
- Outputs: `DeadCodeEntry` (per-finding) and `DeadCodeReport` (per-file)
- Method: `analyze(source, file_path) -> DeadCodeReport`
- Method: `get_certain_entries() -> List[DeadCodeEntry]` (confidence >= 0.9)

**metrics.py** — `MetricsAnalyzer`
- **Code Metrics**: lines of code, logical lines, comments, blank lines, docstring coverage
- **Halstead Metrics**: vocabulary (n1+n2), length (N1+N2), volume (N*log2(n)), difficulty, effort
- Counts: unique operators (n1), unique operands (n2), total operators (N1), total operands (N2)
- Docstring coverage: % of public symbols with docstrings
- Outputs: `CodeMetrics` and `HalsteadMetrics` dataclasses
- Methods: `compute(source) -> CodeMetrics`, `halstead(source) -> HalsteadMetrics`
- Method: `analyze_file(file_path) -> Tuple[CodeMetrics, HalsteadMetrics]`

## Data Representations

All outputs are **dataclasses** (immutable after construction) with fields documented via docstrings. All paths are `Path` objects (pathlib); all locations are 1-indexed line numbers from Python AST.

### Existing Records

```python
@dataclass
class SymbolInfo:
    name: str
    qualified_name: str
    kind: str  # 'function', 'method', 'class', 'variable', ...
    file_path: Path
    line_start: int
    line_end: int
    is_public: bool
    type_hint: str | None
    docstring: str | None

@dataclass
class ImportEdge:
    source_module: str
    target_module: str
    import_kind: str  # 'from', 'import'
    line_num: int

@dataclass
class CallEdge:
    caller_id: str
    callee_id: str
    line_num: int
    argument_count: int | None
```

### New Records

```python
@dataclass
class ComplexityEntry:
    name: str
    qualified_name: str
    kind: str
    file_path: Path
    line_start: int
    line_end: int
    cyclomatic_complexity: int
    cognitive_complexity: int
    metadata: dict[str, Any]

@dataclass
class ComplexityReport:
    file_path: Path
    entries: list[ComplexityEntry]
    average_cyclomatic: float
    average_cognitive: float
    max_cyclomatic: int
    max_cognitive: int
    errors: list[str]

    def get_hotspots(threshold: int = 10) -> list[ComplexityEntry]

@dataclass
class ModuleCouplingMetrics:
    module_name: str
    file_path: Path
    afferent_coupling: int
    efferent_coupling: int
    instability: float  # I = Ce / (Ca + Ce)
    abstractness: float  # A = abstract_classes / total_classes
    distance_from_main_sequence: float  # D = |A + I - 1|
    abstract_classes: int
    concrete_classes: int
    dependencies: set[str]
    dependents: set[str]
    metadata: dict[str, Any]

@dataclass
class CouplingReport:
    package_name: str
    modules: list[ModuleCouplingMetrics]
    average_instability: float
    average_abstractness: float
    average_distance: float
    errors: list[str]

    def get_unstable_modules(threshold: float = 0.8) -> list[ModuleCouplingMetrics]
    def get_zone_of_pain() -> list[ModuleCouplingMetrics]
    def get_zone_of_uselessness() -> list[ModuleCouplingMetrics]

@dataclass
class DeadCodeEntry:
    symbol_name: str
    file_path: Path
    line_num: int
    kind: str  # 'UNUSED_IMPORT', 'UNUSED_FUNCTION', 'UNUSED_VARIABLE', 'UNREACHABLE'
    scope: str  # 'module', 'class_name', 'function_name'
    confidence: float  # [0.0, 1.0]
    metadata: dict[str, Any]

@dataclass
class DeadCodeReport:
    file_path: Path
    entries: list[DeadCodeEntry]
    unused_imports: int
    unused_functions: int
    unused_variables: int
    unreachable_statements: int
    errors: list[str]

    def get_certain_entries() -> list[DeadCodeEntry]

@dataclass
class CodeMetrics:
    lines_of_code: int
    logical_lines: int
    comment_lines: int
    blank_lines: int
    docstring_coverage: float  # [0.0, 1.0]
    public_symbols: int
    documented_symbols: int

@dataclass
class HalsteadMetrics:
    unique_operators: int
    unique_operands: int
    total_operators: int
    total_operands: int
    vocabulary: int  # n1 + n2
    length: int  # N1 + N2
    volume: float  # N * log2(n)
    difficulty: float  # (n1/2) * (N2/n2)
    effort: float  # difficulty * volume
```

## Common Usage Patterns

### Analyze a Single File

```python
from pathlib import Path
from cogant.static.complexity import ComplexityAnalyzer
from cogant.static.coupling import CouplingAnalyzer
from cogant.static.dead_code import DeadCodeAnalyzer
from cogant.static.metrics import MetricsAnalyzer

file_path = Path("my_module.py")

# Complexity
complexity_analyzer = ComplexityAnalyzer()
complexity_report = complexity_analyzer.analyze_file(file_path)
print(f"Average cyclomatic: {complexity_report.average_cyclomatic}")
for hotspot in complexity_report.get_hotspots(threshold=10):
    print(f"  {hotspot.qualified_name}: CC={hotspot.cyclomatic_complexity}")

# Dead code
dead_analyzer = DeadCodeAnalyzer()
dead_report = dead_analyzer.analyze_file(file_path)
for entry in dead_report.get_certain_entries():
    print(f"  Line {entry.line_num}: {entry.symbol_name} ({entry.kind})")

# Metrics
metrics_analyzer = MetricsAnalyzer()
code_metrics, halstead = metrics_analyzer.analyze_file(file_path)
print(f"LOC: {code_metrics.lines_of_code}")
print(f"Docstring coverage: {code_metrics.docstring_coverage:.1%}")
print(f"Halstead effort: {halstead.effort:.1f}")
```

### Analyze Module Coupling

```python
from cogant.static.coupling import CouplingAnalyzer
from pathlib import Path

# Build import graph from static analysis results
import_graph = {
    "mypackage.models": {"mypackage.utils", "sqlalchemy"},
    "mypackage.utils": {"mypackage.constants"},
    "mypackage.constants": set(),
}

# Add class counts
abstract_classes = {
    "mypackage.models": 1,  # BaseModel
    "mypackage.utils": 0,
    "mypackage.constants": 0,
}
concrete_classes = {
    "mypackage.models": 3,  # User, Post, Comment
    "mypackage.utils": 2,  # Logger, Formatter
    "mypackage.constants": 5,  # TIMEOUT, MAX_RETRIES, ...
}

analyzer = CouplingAnalyzer()
report = analyzer.analyze(
    import_graph=import_graph,
    abstract_classes=abstract_classes,
    concrete_classes=concrete_classes,
    package_name="mypackage"
)

# Identify high-risk modules
for module in report.get_zone_of_pain():
    print(f"Zone of pain: {module.module_name}")
    print(f"  Instability: {module.instability:.2f} (high)")
    print(f"  Distance: {module.distance_from_main_sequence:.2f}")

for module in report.get_unstable_modules(threshold=0.7):
    print(f"Unstable: {module.module_name}")
```

### Find Functions with High Cognitive Complexity

```python
from cogant.static.complexity import ComplexityAnalyzer
from pathlib import Path

analyzer = ComplexityAnalyzer()
source = Path("complex_file.py").read_text()
report = analyzer.analyze(source, Path("complex_file.py"))

# Sort by cognitive complexity
sorted_funcs = sorted(
    report.entries,
    key=lambda e: e.cognitive_complexity,
    reverse=True
)

print("Top 5 most cognitively complex functions:")
for entry in sorted_funcs[:5]:
    print(f"  {entry.qualified_name}: {entry.cognitive_complexity}")
```

### Detect Dead Code with Filtering

```python
from cogant.static.dead_code import DeadCodeAnalyzer
from pathlib import Path

analyzer = DeadCodeAnalyzer()
report = analyzer.analyze_file(Path("old_module.py"))

# Get only high-confidence findings
certain = report.get_certain_entries()
print(f"Found {len(certain)} high-confidence dead code issues")

# Group by kind
by_kind = {}
for entry in certain:
    by_kind.setdefault(entry.kind, []).append(entry)

for kind, entries in by_kind.items():
    print(f"\n{kind}: {len(entries)}")
    for entry in entries:
        print(f"  Line {entry.line_num}: {entry.symbol_name}")
```

## Integration with Graph Builder

All outputs feed into the pipeline's **normalization and graph construction** stages:

1. **Static facts** (SymbolInfo, ImportEdge, CallEdge, ComplexityEntry, etc.) are produced here
2. **normalize/** converts them to `LanguageFact` records (canonical form)
3. **graph/** consumes LanguageFact and builds `ProgramGraph` nodes and edges
4. **Complexity/Coupling/MetricsAnalyzer** results are stored as **node metadata** in the graph
5. **DeadCodeReport** feeds into **validation/** for code quality checks

The graph construction process is deterministic: same source code → same facts → same graph.

## Responsibilities & Coordination

### Core Responsibilities
- Extract language facts from raw Python source (no runtime data)
- Compute code complexity metrics (cyclomatic, cognitive)
- Analyze module coupling and stability
- Detect dead code with confidence scores
- Provide per-function and per-file aggregates
- Handle errors gracefully; log diagnostics

### Coordination
- **Input**: Raw Python source files from `ingest/`
- **Output**: SymbolInfo, ImportEdge, CallEdge, TypeInfo, DataFlowEdge, ComplexityEntry, CouplingReport, DeadCodeReport, CodeMetrics, HalsteadMetrics
- **Consumed by**: `normalize/` (converts to LanguageFact), `graph/` (builds nodes/edges), `validate/` (code quality checks)
- **Configuration**: `repo_root` from `ingest/Config`
- **No state**: Each module analysis is independent; results are deterministic

## How to Extend

### Add a New AST-Based Analyzer
1. Create a new file `py/cogant/static/myanalyzer.py`
2. Define result dataclasses: `@dataclass class MyAnalysisEntry:` and `@dataclass class MyAnalysisReport:`
3. Implement `ast.NodeVisitor` to extract facts: `class MyVisitor(ast.NodeVisitor):`
4. Implement analyzer class: `class MyAnalyzer: def analyze(self, source, file_path) -> MyAnalysisReport:`
5. Add to `__init__.py` exports and `.pyi` stub
6. Wire into pipeline in `py/cogant/pipeline/config.py` (optional)

### Track New Symbol Kinds
1. Extend `SymbolExtractor.kind` enum or the string set of recognized kinds
2. Update `_extract_symbols()` visitor method to recognize new AST node types
3. Update downstream consumers (graph builder) to handle new kinds

### Add New Import Classification
1. Extend `ImportAnalyzer._classify_import()` logic
2. Add new import_kind strings (e.g., "relative", "namespace_package")
3. Update tests with examples

### Support New Data Flow Patterns
1. Extend `DataFlowAnalyzer` visitor with new `visit_*` methods
2. Add new `edge_type` enum values (READ, WRITE, CONTROL_FLOW, INDIRECT_FLOW)
3. Test on fixtures with the new pattern

## Error Handling & Diagnostics

All analyzers follow a consistent pattern:

```python
report = analyzer.analyze(source, file_path)
if report.errors:
    for error in report.errors:
        logger.warning(f"Analysis error in {file_path}: {error}")
# Results are still usable (partial) even with errors
```

- Syntax errors are caught and logged; analysis returns empty report
- File read errors are logged; analysis returns empty report
- Missing imports are allowed (heuristic assumption)
- Confidences < 1.0 signal heuristic-only results

## See Also

- `py/cogant/static/README.md` — module-level overview
- `py/cogant/graph/` — consumes static facts, builds ProgramGraph
- `py/cogant/validate/` — scores and reviews static findings
- `py/cogant/export/` — exports complexity/coupling/metrics reports to JSON/CSV
