# Static Analysis API Reference

## Overview

The static analysis module (`cogant.static`) provides pre-graph code fact extraction: complexity metrics, coupling analysis, dead code detection, and code metrics. All analyzers follow a consistent pattern: parse Python source, extract facts, return typed dataclass reports.

## ComplexityAnalyzer

Computes cyclomatic and cognitive complexity for Python functions and methods.

### Cyclomatic Complexity

Counts decision points:
- if/elif: +1 each
- for/while/AsyncFor: +1 each
- except handlers: +1 each
- boolean operators (and/or): +1 per operator
- ternary (IfExp): +1 each
- Base: 1 (straight-line code)

**Interpretation:**
- 1-3: Simple, low risk
- 4-7: Moderate complexity
- 8-10: High complexity, testing recommended
- > 10: Very high, refactor recommended

### Cognitive Complexity

Penalizes nesting depth + decision points:
- Each decision (if, for, while, except) scores 1 point
- Nesting depth penalty: max(0, depth - 1) additional points per decision
- Try blocks score 1 + each except handler scores 1

**Interpretation:**
- 1-5: Simple
- 6-15: Moderate (may warrant review)
- > 15: Complex, refactor recommended

### Methods

```python
class ComplexityAnalyzer:
    def __init__(self) -> None:
        """Initialize analyzer."""

    def analyze(
        self,
        source: str,
        file_path: Path
    ) -> ComplexityReport:
        """
        Analyze source code for complexity metrics.

        Args:
            source: Python source code string
            file_path: Path for reference (used in report)

        Returns:
            ComplexityReport with per-function metrics

        Raises:
            None (errors captured in report.errors)
        """

    def analyze_file(
        self,
        file_path: Path
    ) -> ComplexityReport:
        """
        Analyze a Python file.

        Args:
            file_path: Path to Python source file

        Returns:
            ComplexityReport with per-function metrics

        Raises:
            None (file I/O errors captured in report.errors)
        """
```

### ComplexityReport

```python
@dataclass
class ComplexityReport:
    file_path: Path
    """Source file path."""

    entries: list[ComplexityEntry] = field(default_factory=list)
    """Per-function complexity entries."""

    average_cyclomatic: float = 0.0
    """Average cyclomatic complexity across all functions."""

    average_cognitive: float = 0.0
    """Average cognitive complexity across all functions."""

    max_cyclomatic: int = 0
    """Maximum cyclomatic complexity in module."""

    max_cognitive: int = 0
    """Maximum cognitive complexity in module."""

    errors: list[str] = field(default_factory=list)
    """Syntax errors or analysis errors."""

    def get_hotspots(threshold: int = 10) -> list[ComplexityEntry]:
        """
        Get functions exceeding complexity threshold.

        Args:
            threshold: Cyclomatic complexity threshold (default: 10)

        Returns:
            Sorted list of ComplexityEntry (highest first)
        """
```

### ComplexityEntry

```python
@dataclass
class ComplexityEntry:
    name: str
    """Function/method name."""

    qualified_name: str
    """Fully qualified name (e.g., 'MyClass.my_method')."""

    kind: str
    """'function' or 'method'."""

    file_path: Path
    """Source file path."""

    line_start: int
    """Starting line number (1-indexed)."""

    line_end: int
    """Ending line number (1-indexed)."""

    cyclomatic_complexity: int
    """Cyclomatic complexity score (>= 1)."""

    cognitive_complexity: int
    """Cognitive complexity score (>= 0)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata (e.g., {'is_async': True})."""
```

## CouplingAnalyzer

Analyzes module coupling and stability using Martin metrics.

### Martin Metrics

**Afferent Coupling (Ca):** Count of modules that depend on this module (incoming)

**Efferent Coupling (Ce):** Count of modules this module depends on (outgoing)

**Instability (I):** `I = Ce / (Ca + Ce)`
- Range: [0, 1]
- I = 0: Maximally stable (many dependents, few dependencies)
- I = 1: Maximally unstable (no dependents, many dependencies)

**Abstractness (A):** `A = abstract_classes / total_classes`
- Range: [0, 1]
- A = 0: Concrete (all classes are implementations)
- A = 1: Abstract (all classes are abstract/interfaces)

**Distance from Main Sequence (D):** `D = |A + I - 1|`
- Range: [0, 1]
- D = 0: On main sequence (ideal balance of stability vs abstraction)
- D > 0.3: Zone of pain or uselessness (design smell)

**Zone of Pain:** High concrete + high instability (D > 0.3, I > 0.8)
- Difficult to modify; high risk changes
- Often: leaf modules with many dependents

**Zone of Uselessness:** High abstract + low instability (D > 0.3, I < 0.2)
- Over-designed; not used
- Often: unused base classes or interfaces

### Methods

```python
class CouplingAnalyzer:
    def __init__(self) -> None:
        """Initialize analyzer."""

    def analyze(
        self,
        import_graph: dict[str, set[str]],
        abstract_classes: dict[str, int] | None = None,
        concrete_classes: dict[str, int] | None = None,
        package_name: str = "unknown"
    ) -> CouplingReport:
        """
        Analyze module coupling metrics.

        Args:
            import_graph: Dict mapping module name to set of modules it imports
            abstract_classes: Optional dict mapping module to abstract class count
            concrete_classes: Optional dict mapping module to concrete class count
            package_name: Package name for report

        Returns:
            CouplingReport with per-module metrics
        """
```

### CouplingReport

```python
@dataclass
class CouplingReport:
    package_name: str
    """Package name."""

    modules: list[ModuleCouplingMetrics] = field(default_factory=list)
    """Per-module coupling metrics."""

    average_instability: float = 0.0
    """Average instability across all modules."""

    average_abstractness: float = 0.0
    """Average abstractness across all modules."""

    average_distance: float = 0.0
    """Average distance from main sequence."""

    errors: list[str] = field(default_factory=list)
    """Analysis errors."""

    def get_unstable_modules(threshold: float = 0.8) -> list[ModuleCouplingMetrics]:
        """
        Get modules with high instability.

        Args:
            threshold: Instability threshold (default: 0.8)

        Returns:
            Sorted list of unstable modules (highest first)
        """

    def get_zone_of_pain() -> list[ModuleCouplingMetrics]:
        """
        Get modules in zone of pain (high concrete + high instability).

        Returns:
            Modules where D > 0.3 and I > 0.8
        """

    def get_zone_of_uselessness() -> list[ModuleCouplingMetrics]:
        """
        Get modules in zone of uselessness (high abstract + low instability).

        Returns:
            Modules where D > 0.3 and I < 0.2
        """
```

### ModuleCouplingMetrics

```python
@dataclass
class ModuleCouplingMetrics:
    module_name: str
    """Module name."""

    file_path: Path
    """Source file path."""

    afferent_coupling: int = 0
    """Ca: count of modules depending on this one."""

    efferent_coupling: int = 0
    """Ce: count of modules this one depends on."""

    instability: float = 0.0
    """I = Ce / (Ca + Ce); range [0, 1]."""

    abstractness: float = 0.0
    """A = abstract_classes / total_classes; range [0, 1]."""

    distance_from_main_sequence: float = 0.0
    """D = |A + I - 1|; ideal is 0."""

    abstract_classes: int = 0
    """Count of abstract classes/interfaces."""

    concrete_classes: int = 0
    """Count of concrete classes."""

    dependencies: set[str] = field(default_factory=set)
    """Set of modules this module imports."""

    dependents: set[str] = field(default_factory=set)
    """Set of modules that import this module."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""
```

## DeadCodeAnalyzer

Detects unused imports, functions, variables, and unreachable code blocks.

### Confidence Scoring

- **0.95** (High): Unused imports — very confident; may be false positives if reexported
- **0.8** (Medium): Unused private functions — may be called via reflection/string names
- **0.7** (Low): Unused private variables — may be used elsewhere or in external libraries

Use `report.get_certain_entries()` to filter for confidence >= 0.9.

### Analysis Scope

- Filters private symbols only (starts with `_`) to reduce false positives
- Scope context: module, function, class
- Kind: UNUSED_IMPORT, UNUSED_FUNCTION, UNUSED_VARIABLE, UNREACHABLE

### Methods

```python
class DeadCodeAnalyzer:
    def __init__(self) -> None:
        """Initialize analyzer."""

    def analyze(
        self,
        source: str,
        file_path: Path
    ) -> DeadCodeReport:
        """
        Analyze source for dead code.

        Args:
            source: Python source code string
            file_path: Path for reference

        Returns:
            DeadCodeReport with findings
        """

    def analyze_file(
        self,
        file_path: Path
    ) -> DeadCodeReport:
        """
        Analyze a Python file for dead code.

        Args:
            file_path: Path to Python source file

        Returns:
            DeadCodeReport with findings
        """
```

### DeadCodeReport

```python
@dataclass
class DeadCodeReport:
    file_path: Path
    """Source file path."""

    entries: list[DeadCodeEntry] = field(default_factory=list)
    """Dead code findings."""

    unused_imports: int = 0
    """Count of unused imports."""

    unused_functions: int = 0
    """Count of unused functions."""

    unused_variables: int = 0
    """Count of unused variables."""

    unreachable_statements: int = 0
    """Count of unreachable code blocks."""

    errors: list[str] = field(default_factory=list)
    """Analysis errors."""

    def get_certain_entries() -> list[DeadCodeEntry]:
        """
        Get entries with high confidence (>= 0.9).

        Returns:
            List of high-confidence dead code entries
        """
```

### DeadCodeEntry

```python
@dataclass
class DeadCodeEntry:
    symbol_name: str
    """Name of unused/unreachable symbol."""

    file_path: Path
    """Source file path."""

    line_num: int
    """Line number where symbol is defined (1-indexed)."""

    kind: str
    """Kind: UNUSED_IMPORT, UNUSED_FUNCTION, UNUSED_VARIABLE, UNREACHABLE."""

    scope: str = "module"
    """Scope context: module, class_name, function_name."""

    confidence: float = 1.0
    """Confidence score [0.0, 1.0]; 1.0 = certain."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""
```

## MetricsAnalyzer

Computes code metrics and Halstead complexity metrics.

### Code Metrics

- **Lines of Code (LOC):** Total lines excluding blank lines and comments
- **Logical Lines:** Count of AST statements
- **Comment Lines:** Lines starting with `#`
- **Blank Lines:** Empty lines
- **Docstring Coverage:** Percentage of public symbols with docstrings [0.0, 1.0]
- **Public Symbols:** Count of non-underscore functions, classes, methods
- **Documented Symbols:** Count of public symbols with docstrings

### Halstead Metrics

**Vocabulary (n):** Unique operators (n1) + unique operands (n2)

**Length (N):** Total operators (N1) + total operands (N2)

**Volume (V):** `V = N * log2(n)` — program volume in bits

**Difficulty (D):** `D = (n1/2) * (N2/n2)` — difficulty of implementation

**Effort (E):** `E = D * V` — estimated effort to write/understand program

**Interpretation:**
- Volume: larger programs have higher volume
- Difficulty: more operand reuse → lower difficulty
- Effort: estimated hours to implement (roughly E / 10 = hours)

### Methods

```python
class MetricsAnalyzer:
    def __init__(self) -> None:
        """Initialize analyzer."""

    def compute(
        self,
        source: str
    ) -> CodeMetrics:
        """
        Compute code metrics from source.

        Args:
            source: Python source code string

        Returns:
            CodeMetrics instance
        """

    def halstead(
        self,
        source: str
    ) -> HalsteadMetrics:
        """
        Compute Halstead metrics from source.

        Args:
            source: Python source code string

        Returns:
            HalsteadMetrics instance
        """

    def analyze_file(
        self,
        file_path: Path
    ) -> tuple[CodeMetrics, HalsteadMetrics]:
        """
        Analyze a Python file for all metrics.

        Args:
            file_path: Path to Python source file

        Returns:
            Tuple of (CodeMetrics, HalsteadMetrics)
        """
```

### CodeMetrics

```python
@dataclass
class CodeMetrics:
    lines_of_code: int
    """Total lines of code (excluding blank and comments)."""

    logical_lines: int
    """Logical lines of code (AST statements)."""

    comment_lines: int
    """Lines containing comments."""

    blank_lines: int
    """Blank lines."""

    docstring_coverage: float
    """Percentage of public symbols with docstrings [0.0, 1.0]."""

    public_symbols: int
    """Count of public symbols."""

    documented_symbols: int
    """Count of documented public symbols."""
```

### HalsteadMetrics

```python
@dataclass
class HalsteadMetrics:
    unique_operators: int
    """n1: count of unique operators."""

    unique_operands: int
    """n2: count of unique operands."""

    total_operators: int
    """N1: total count of operators."""

    total_operands: int
    """N2: total count of operands."""

    vocabulary: int
    """n = n1 + n2: vocabulary size."""

    length: int
    """N = N1 + N2: program length."""

    volume: float
    """V = N * log2(n): program volume."""

    difficulty: float
    """D = (n1/2) * (N2/n2): difficulty."""

    effort: float
    """E = D * V: effort to implement."""

    @classmethod
    def compute(cls, source: str) -> "HalsteadMetrics":
        """
        Compute Halstead metrics from source code.

        Args:
            source: Python source code

        Returns:
            HalsteadMetrics instance
        """
```

## Error Handling

All analyzers follow consistent error handling:

```python
report = analyzer.analyze(source, file_path)

# Check for errors
if report.errors:
    for error in report.errors:
        logger.warning(f"Analysis error: {error}")

# Results are still usable even with partial errors
# (e.g., syntax error in one file, but metrics computed for rest)
```

Common error messages:
- `"Syntax error: ..."` — Source code is not valid Python
- `"Failed to read file: ..."` — File I/O error

## See Also

- `py/cogant/static/AGENTS.md` — Agent guide with usage patterns
- `py/cogant/static/README.md` — Module overview
- `py/cogant/graph/` — Consumes static analysis results
