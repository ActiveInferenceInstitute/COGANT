# Agents — py/cogant/ingest

## Owner
Source Ingestion / Repository Analysis

## What Is the Ingest Module

The `ingest/` module is the **first stage of the 10-stage COGANT pipeline**. It discovers and catalogs a software repository, producing a `RepoSnapshot` — a complete inventory of source files, dependencies, and metadata. The module:

1. **Enumerates files** — walks repository tree, respects `.gitignore`, detects test files
2. **Detects languages** — maps file extensions to programming languages
3. **Parses manifests** — extracts dependencies from setup.py, pyproject.toml, package.json, Cargo.toml, etc.
4. **Extracts metadata** — repository name, URL, current commit, author, description
5. **Computes checksums** — optional SHA256 hashes for file integrity

All downstream stages (static analysis, graph construction, translation, synthesis) depend on the accuracy of ingestion. Ingestion is **read-only** — no files are modified or deleted.

## Pipeline Integration

```
Input: Git URL or local directory path
    ↓
stage 1: ingest/
    ├─ RepoIngester       → Repository discovery (clone or read local)
    ├─ FileEnumerator     → File enumeration with .gitignore respect
    ├─ ManifestParser     → Dependency extraction (5 formats)
    └─ LanguageDetector   → Language identification
    ↓
Output: RepoSnapshot (files, dependencies, metadata)
    ↓
stage 2: static/         → AST parsing, symbol extraction, type inference
stage 3: graph/          → ProgramGraph construction (nodes + edges)
... (stages 4-10 downstream)
```

The RepoSnapshot serves as the **contract between ingest and all downstream consumers**. Each consumer independently uses the file inventory and dependency list; ingest never re-runs during pipeline execution (files are stable once ingested).

## Core Components

### RepoIngester — Repository Discovery & Snapshot

**Purpose**: Load a repository (local or remote) and create a complete snapshot.

**Key Methods**:

**`__init__(work_dir: Path | None = None)`**
- Initialize ingester with temporary directory for cloning (default: `/tmp/cogant`)
- Create work_dir if it doesn't exist

**`ingest_local(repo_path: Path, include_test_files=True, compute_checksums=False) -> RepoSnapshot`**
- Ingest a local repository from disk
- Extract metadata (commit, author, timestamp)
- Enumerate all files with language detection
- Parse manifests for dependencies
- Return complete snapshot
- **Args**:
  - `repo_path`: Absolute or relative path to repo root
  - `include_test_files`: Include test files in enumeration (default True)
  - `compute_checksums`: Compute SHA256 hash per file (default False, slower)
- **Returns**: RepoSnapshot with files, dependencies, metadata

**`ingest_remote(repo_url: str, include_test_files=True, shallow=False) -> RepoSnapshot`**
- Clone remote repository (git, https, ssh)
- Create temporary directory under work_dir
- Call ingest_local on clone
- Clean up temporary files after snapshot creation
- **Args**:
  - `repo_url`: Git URL (ssh:// or https://)
  - `include_test_files`: Include tests
  - `shallow`: Use `git clone --depth 1` for speed (default False)
- **Returns**: RepoSnapshot

**`_extract_metadata(repo_path: Path) -> RepoMetadata`**
- Query git commit information (hash, message, author, timestamp)
- Detect primary language from file counts
- Extract .git/config for repository name
- Graceful fallback if .git missing (return RepoMetadata with None fields)

**Data Models**:
```python
@dataclass
class RepoMetadata:
    name: str              # Repository name
    url: str               # Repository URL or local path
    commit_hash: str | None
    commit_message: str | None
    timestamp: datetime | None  # Snapshot time
    author: str | None     # Commit author
    language: str | None   # Primary language (e.g., "python")
    description: str | None

@dataclass
class RepoSnapshot:
    metadata: RepoMetadata
    files: list[FileInfo]
    dependencies: list[Dependency]
    root_path: Path
```

### FileEnumerator — Directory Traversal & File Filtering

**Purpose**: Walk repository tree, respect .gitignore, detect test files, enumerate source files.

**Key Methods**:

**`__init__(repo_root: Path, respect_gitignore=True)`**
- Initialize enumerator for a repository root
- Load .gitignore patterns if respect_gitignore=True

**`enumerate(include_test_files=True, compute_checksums=False) -> list[FileInfo]`**
- Walk repo tree and return all matching files
- Skip directories in IGNORE_PATTERNS (node_modules, .git, __pycache__, etc.)
- Skip files matching .gitignore patterns (if enabled)
- Mark test files (pattern-based detection)
- Compute checksums if requested
- **Returns**: List of FileInfo records (sorted by path)

**`_load_gitignore() -> set[str]`**
- Parse .gitignore file and cache patterns
- Handle comments (#), negation (!pattern), wildcards (*)
- Called once and cached

**`_is_ignored(path: Path) -> bool`**
- Check if path matches any .gitignore pattern
- Check if path contains any IGNORE_PATTERNS directories
- Return True if path should be skipped

**`_detect_language(file_path: Path) -> str | None`**
- Map file extension to language name using LANGUAGE_EXTENSIONS
- Return language string (e.g., "python", "typescript") or None

**`_is_test_file(rel_path: str) -> bool`**
- Check if path matches TEST_PATTERNS (test_, _test.py, tests/, spec/, etc.)
- Return True if file is a test file

**Constants**:
```python
LANGUAGE_EXTENSIONS = {
    "python": {".py", ".pyx", ".pyi"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
    "typescript": {".ts", ".tsx"},
    "rust": {".rs"},
    "go": {".go"},
    "java": {".java"},
    "cpp": {".cpp", ".cc", ".cxx", ".h", ".hpp", ".c"},
    "csharp": {".cs"},
    "ruby": {".rb"},
    "php": {".php"},
}

TEST_PATTERNS = {
    "test_",
    "_test.py",
    "_spec.py",
    "tests/",
    "test/",
    "__tests__/",
    "spec/",
}

IGNORE_PATTERNS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "target",
    "dist",
    "build",
    ".egg-info",
    ".pytest_cache",
    ".tox",
    ".mypy_cache",
    ".idea",
    ".vscode",
    ".DS_Store",
    "*.egg",
    "*.whl",
}
```

**Data Model**:
```python
@dataclass
class FileInfo:
    path: Path             # Absolute path
    relative_path: str     # Path relative to repo root
    language: str | None   # Detected language
    size_bytes: int        # File size in bytes
    is_test: bool = False  # Is this a test file?
    checksum: str | None   # SHA256 checksum (optional)
```

### ManifestParser — Dependency Extraction

**Purpose**: Parse multiple dependency manifest formats and extract packages + versions.

**Key Methods**:

**`parse_repo(repo_path: Path) -> tuple[dict[str, Any], list[Dependency]]`**
- Auto-detect manifest file in repo root
- Try formats in order: pyproject.toml, setup.py, requirements.txt, package.json, Cargo.toml
- Return (metadata dict, dependencies list)
- **Returns**: Tuple of (metadata, dependencies)

**`parse_pyproject_toml(path: Path) -> tuple[dict, list[Dependency]]`**
- Parse pyproject.toml (TOML format)
- Extract poetry, setuptools, flit, pdm sections
- Return project metadata and dependencies
- Handles [tool.poetry.dependencies], [project.dependencies], [tool.pdm.dev-dependencies], etc.

**`parse_setup_py(path: Path) -> tuple[dict, list[Dependency]]`**
- Parse setup.py (Python AST-based extraction)
- Extract install_requires, tests_require, extras_require
- Return package metadata and dependencies
- Handles setuptools and distutils

**`parse_requirements_txt(path: Path) -> tuple[dict, list[Dependency]]`**
- Parse requirements.txt (line-by-line format)
- Extract name, version, environment markers
- Return simple metadata and dependencies

**`parse_package_json(path: Path) -> tuple[dict, list[Dependency]]`**
- Parse package.json (JSON format)
- Extract dependencies and devDependencies
- Return npm metadata and dependencies

**`parse_cargo_toml(path: Path) -> tuple[dict, list[Dependency]]`**
- Parse Cargo.toml (TOML format)
- Extract [dependencies] and [dev-dependencies]
- Return Rust/Cargo metadata and dependencies

**Data Models**:
```python
@dataclass
class Dependency:
    name: str              # Package name
    version: str | None    # Version specifier (e.g., ">=1.0,<2.0")
    is_dev: bool = False   # Development dependency?
    is_local: bool = False # Local/path dependency?
    extras: list[str] = field(default_factory=list)  # [extras] markers
```

### LanguageDetector — Language Identification & Parser Loading

**Purpose**: Identify programming language and lazy-load language-specific parsers.

**Key Methods**:

**`detect(file_path: Path | str) -> str | None`**
- Map file extension to language name
- Return language string (e.g., "python") or None if unknown

**`get_parser(language: str) -> Any`**
- Lazy-load parser class for language
- Return parser instance (or None if not available)
- Supported: python, javascript, typescript, rust, go
- Fall back gracefully if tree-sitter unavailable

**`_lazy_load_parsers()`**
- Load parser classes on first use
- Prefer tree-sitter for JS/TS when available
- Fall back to regex-based parsers otherwise
- Called automatically by get_parser()

**Constants**:
```python
EXTENSION_MAP = {
    ".py": "python",
    ".pyx": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".rs": "rust",
    ".go": "go",
}

PARSER_CLASSES = {
    "python": PythonLanguageParser,
    "typescript": TypeScriptTreeSitterParser | TypeScriptLanguageParser,
    "javascript": JavaScriptLanguageParser,
    "rust": RustLanguageParser,
    "go": GoLanguageParser,
}
```

## Data Representations

All outputs are **immutable after construction** (dataclasses with frozen=True). All paths are `Path` objects; all timestamps are `datetime` with UTC timezone.

### Core Snapshot

```python
@dataclass(frozen=True)
class RepoMetadata:
    name: str
    url: str
    commit_hash: str | None = None
    commit_message: str | None = None
    timestamp: datetime | None = None
    author: str | None = None
    language: str | None = None
    description: str | None = None

@dataclass(frozen=True)
class FileInfo:
    path: Path
    relative_path: str
    language: str | None
    size_bytes: int
    is_test: bool = False
    checksum: str | None = None

@dataclass(frozen=True)
class Dependency:
    name: str
    version: str | None = None
    is_dev: bool = False
    is_local: bool = False
    extras: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class RepoSnapshot:
    metadata: RepoMetadata
    files: list[FileInfo]
    dependencies: list[Dependency]
    root_path: Path
```

## Common Usage Patterns

### Ingest a Local Repository

```python
from pathlib import Path
from cogant.ingest.repo import RepoIngester

ingester = RepoIngester()
snapshot = ingester.ingest_local(
    Path("/path/to/my/repo"),
    include_test_files=True,
    compute_checksums=False
)

print(f"Repository: {snapshot.metadata.name}")
print(f"Files: {len(snapshot.files)}")
print(f"Dependencies: {len(snapshot.dependencies)}")
print(f"Languages: {set(f.language for f in snapshot.files if f.language)}")
```

### Ingest a Remote Repository

```python
from cogant.ingest.repo import RepoIngester

ingester = RepoIngester(work_dir=Path("/tmp/my_work"))
snapshot = ingester.ingest_remote(
    "https://github.com/user/repo.git",
    include_test_files=True,
    shallow=True  # --depth 1 for faster clone
)

# Snapshot is ready; temporary clone is cleaned up
print(f"Cloned and ingested: {snapshot.metadata.name}")
```

### Filter Files by Language

```python
from cogant.ingest.repo import RepoIngester

snapshot = ingester.ingest_local(Path("."))

python_files = [f for f in snapshot.files if f.language == "python"]
test_files = [f for f in snapshot.files if f.is_test]

print(f"Python files: {len(python_files)}")
print(f"Test files: {len(test_files)}")
```

### Inspect Dependencies

```python
snapshot = ingester.ingest_local(Path("."))

# All dependencies
for dep in snapshot.dependencies:
    print(f"{dep.name} {dep.version or '*'}")

# Only direct (non-dev) dependencies
direct = [d for d in snapshot.dependencies if not d.is_dev]
print(f"Direct dependencies: {len(direct)}")

# Development dependencies
dev = [d for d in snapshot.dependencies if d.is_dev]
print(f"Dev dependencies: {len(dev)}")
```

### Enumerate Files with Filtering

```python
from cogant.ingest.files import FileEnumerator

enumerator = FileEnumerator(
    Path("/path/to/repo"),
    respect_gitignore=True
)

files = enumerator.enumerate(
    include_test_files=True,
    compute_checksums=True
)

for file_info in files:
    print(f"{file_info.relative_path}")
    print(f"  Language: {file_info.language}")
    print(f"  Size: {file_info.size_bytes} bytes")
    print(f"  Checksum: {file_info.checksum}")
    if file_info.is_test:
        print(f"  [TEST FILE]")
```

### Detect Language for a File

```python
from cogant.ingest.language_detect import LanguageDetector

detector = LanguageDetector()
lang = detector.detect("my_script.py")  # Returns "python"
lang = detector.detect("app.tsx")       # Returns "typescript"
lang = detector.detect("data.json")     # Returns None

# Get parser for language
parser = detector.get_parser("python")
if parser:
    ast = parser.parse_file("my_script.py")
```

## Key Concepts & Design Decisions

### .gitignore Respect

The FileEnumerator respects .gitignore patterns to avoid analyzing build artifacts, dependencies, and vendored code:
- Parses .gitignore file into regex patterns
- Checks each file/directory against patterns
- Also checks against hardcoded IGNORE_PATTERNS (node_modules, .venv, etc.)
- Can be disabled with respect_gitignore=False (not recommended)

### Language Detection

Language is detected purely from file extension:
- Supports 11 languages (Python, JS/TS, Rust, Go, Java, C++, C#, Ruby, PHP, etc.)
- One-to-many mapping: .ts and .tsx both map to "typescript"
- Unknown extensions result in language=None
- Language-specific parsers are lazy-loaded on demand

### Test File Detection

Test files are identified by pattern matching on relative path:
- Patterns: "test_", "_test.py", "_spec.py", "tests/", "test/", "spec/"
- Case-sensitive matching
- Can be overridden by language-specific heuristics

### Manifest Format Auto-Detection

ManifestParser tries multiple formats in priority order:
1. pyproject.toml (Python: poetry, setuptools, flit, pdm)
2. setup.py (Python: setuptools)
3. requirements.txt (Python: pip)
4. package.json (JavaScript/TypeScript: npm, yarn)
5. Cargo.toml (Rust: cargo)

First match wins; no attempt to merge multiple formats. If no manifest found, returns empty dependency list.

### Optional Checksum Computation

Checksums (SHA256) are optional because:
- Computation is I/O-intensive on large repos
- Not required for static analysis
- Useful for file integrity checks and deduplication
- Only computed if explicitly requested via compute_checksums=True

### Read-Only Guarantee

Ingest **never modifies the repository**:
- No files created, deleted, or modified
- No git operations other than clone (which is read-only)
- Safe to run against production repos
- Safe to run repeatedly without side effects

## How to Extend

### Add Support for a New Manifest Format

1. Create new `parse_<format>()` method in ManifestParser
2. Parse file and extract (name, version, is_dev) for each dependency
3. Return tuple of (metadata dict, dependencies list)
4. Update `parse_repo()` to include new format in detection order
5. Example for a hypothetical "deps.yaml":
   ```python
   def parse_deps_yaml(self, path: Path) -> tuple[dict, list[Dependency]]:
       """Parse custom deps.yaml format."""
       import yaml

       with open(path) as f:
           data = yaml.safe_load(f) or {}

       metadata = {"name": data.get("name")}
       dependencies = []

       for dep_name, dep_spec in data.get("dependencies", {}).items():
           dependencies.append(Dependency(
               name=dep_name,
               version=dep_spec.get("version"),
               is_dev=dep_spec.get("dev", False),
           ))

       return metadata, dependencies
   ```

### Add Support for a New Language

1. Update LANGUAGE_EXTENSIONS in FileEnumerator:
   ```python
   LANGUAGE_EXTENSIONS["kotlin"] = {".kt", ".kts"}
   ```

2. Update EXTENSION_MAP in LanguageDetector:
   ```python
   EXTENSION_MAP[".kt"] = "kotlin"
   ```

3. Create parser class in parsers/kotlin/ (or use existing parser)
4. Register in LanguageDetector.PARSER_CLASSES:
   ```python
   PARSER_CLASSES["kotlin"] = KotlinLanguageParser
   ```

### Add Custom File Filtering

1. Extend FileEnumerator with custom method:
   ```python
   def enumerate_by_size(self, min_bytes=0, max_bytes=None):
       """Enumerate files within size range."""
       files = self.enumerate()
       filtered = [
           f for f in files
           if f.size_bytes >= min_bytes and (max_bytes is None or f.size_bytes <= max_bytes)
       ]
       return filtered
   ```

### Add Repository Metadata Extraction

1. Extend RepoIngester._extract_metadata() to query additional fields
2. Add new fields to RepoMetadata dataclass
3. Example:
   ```python
   # In _extract_metadata:
   import subprocess
   tags = subprocess.check_output(
       ["git", "tag", "--list"], cwd=repo_path, text=True
   ).strip().split("\n")
   metadata.tags = tags
   ```

## Error Handling & Diagnostics

All methods follow a consistent pattern:

```python
try:
    snapshot = ingester.ingest_local(Path("/repo"))
except FileNotFoundError as e:
    logger.error(f"Repository not found: {e}")
except Exception as e:
    logger.warning(f"Ingest failed: {e}")
    # Return partial snapshot or None
```

**Expected error cases**:
- Repository path doesn't exist → FileNotFoundError
- .gitignore syntax invalid → logged, patterns ignored
- Manifest file malformed → logged, dependencies skipped
- git command fails → logged, metadata fields set to None
- File read permission denied → logged, file skipped

## File Map

| File | Purpose |
|------|---------|
| `repo.py` | RepoIngester, RepoSnapshot, RepoMetadata, repository-level operations |
| `files.py` | FileEnumerator, FileInfo, .gitignore parsing, file filtering |
| `manifest.py` | ManifestParser, Dependency, 5-format manifest parsing |
| `language_detect.py` | LanguageDetector, parser lazy-loading, language identification |
| `incremental.py` | Incremental ingest: git diff-based file selection (optional) |
| `repo_sniff.py` | Repository type detection (Python, Node.js, Rust, etc.) |
| `__init__.py` | Public API exports (RepoIngester, RepoSnapshot, Dependency) |
| `repo.pyi`, `files.pyi`, etc. | Type stubs for each module (mypy) |

## Integration with Downstream Stages

After ingestion, the RepoSnapshot is consumed by:

1. **stage 2: static/** — Uses files to parse AST, extract symbols, compute metrics
2. **stage 3: graph/** — Uses dependencies to build import edges, call graphs
3. **stage 4+: translate, statespace, ...** — Use metadata for logging, filtering, validation

Each downstream consumer independently reads the snapshot; ingest is never re-run.

## Known Limitations & Future Work

### Currently Implemented (v0.5.0)
- Local and remote (git) repository ingestion
- File enumeration with .gitignore respect
- Language detection (11 languages)
- Dependency parsing (5 manifest formats)
- Basic metadata extraction (commit, author, timestamp)

### Planned for v0.6.x
- Incremental ingest (git diff-based file selection)
- Repository type detection (Python, Node.js, Rust, etc.)
- Build system detection (Makefile, Gradle, cargo, npm)
- Container image support (ingest from Docker/OCI images)

### Not Planned
- Repository normalization (reformatting code)
- Automatic dependency resolution (that's package manager's job)
- Source code transformation or optimization

## See Also

- `py/cogant/ingest/README.md` — module-level overview
- `py/cogant/static/` — Consumes RepoSnapshot files for parsing
- `py/cogant/graph/` — Consumes dependencies for import edge building
- `py/cogant/examples/` — Fixture repositories with ingestion examples
- `.gitignore` — Standard gitignore format reference
