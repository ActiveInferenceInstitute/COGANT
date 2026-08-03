## Ingest a remote Git repository
snapshot = ingester.ingest_git_remote(
    "https://github.com/user/repo.git",
    branch="main"
)
```

##### RepoSnapshot Structure:

```python
@dataclass
class RepoSnapshot:
    metadata: RepoMetadata           # Name, URL, commit info, language
    files: List[FileInfo]           # Source files with language info
    dependencies: List[Dependency]  # Extracted from manifests
    root_path: Path                 # Repository root directory
```

#### FileEnumerator

**Location:** `cogant.ingest.files.FileEnumerator`

Walks repository filesystem, detects programming languages, filters files.

##### Features:
- Multi-language file recognition (Python, JavaScript, TypeScript, Rust, Go — the languages with registered parsers; see `cogant.parsers`)
- `.gitignore` pattern respect
- Test file detection
- Checksum computation
- Smart ignore patterns for common directories (node_modules, __pycache__, etc.)

##### Usage:

```python
from cogant.ingest import FileEnumerator

enumerator = FileEnumerator("/path/to/repo", respect_gitignore=True)
