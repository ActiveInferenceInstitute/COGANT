## Access results
print(snapshot.metadata.name)          # Repository name
print(snapshot.metadata.language)      # Detected language
print([f.relative_path for f in snapshot.files])  # Source files
print([d.name for d in snapshot.dependencies])    # Dependencies
```

#### Pattern 2: Clone and Analyze Remote Repository

```python
# doctest: +SKIP  # example requires runtime context or external resources
from cogant.ingest import RepoIngester

ingester = RepoIngester()
snapshot = ingester.ingest_git_remote(
    "https://github.com/user/repo.git",
    branch="main",
    cleanup=False  # Keep cloned repo
)
```

#### Pattern 3: Extract All Symbols from a File

```python
from cogant.static import SymbolExtractor
from pathlib import Path

extractor = SymbolExtractor(repo_root=Path("."))
table = extractor.extract_from_file(Path("example.py"))

for symbol in table.symbols:
    print(f"{symbol.qualified_name} ({symbol.kind})")
    print(f"  ID: {symbol.id}")
    print(f"  Lines: {symbol.line_start}-{symbol.line_end}")
```

#### Pattern 4: Complete File Analysis

```python
from cogant.static import (
    SymbolExtractor, ImportAnalyzer, CallGraphBuilder,
    TypeInferencer, DataFlowAnalyzer
)
from pathlib import Path

file_path = Path("example.py")
repo_root = Path(".")
