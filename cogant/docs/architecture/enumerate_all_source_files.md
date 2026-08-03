## Enumerate all source files

`FileEnumerator` walks a repository tree, respects `.gitignore` and standard ignore
patterns, detects each file's language from its extension, and marks test files. The
example below enumerates all source files without test files and without checksums:

```python
from cogant.ingest import FileEnumerator

enumerator = FileEnumerator(repo_root="path/to/repo")

files = enumerator.enumerate(
    include_test_files=False,
    compute_checksums=True,
)

for file_info in files:
    print(f"{file_info.relative_path} ({file_info.language})")
    print(f"  Size: {file_info.size_bytes} bytes")
    if file_info.checksum:
        print(f"  Checksum: {file_info.checksum}")
```

##### Extension recognition:

`LANGUAGE_EXTENSIONS` in `cogant.ingest.files` maps the following extensions to
language names:

- Python (.py, .pyx, .pyi)
- JavaScript (.js, .jsx, .mjs, .cjs)
- TypeScript (.ts, .tsx)
- Rust (.rs)
- Go (.go)
- Java (.java)
- C/C++ (.c, .cpp, .cc, .cxx, .h, .hpp)
- C# (.cs)
- Ruby (.rb)
- PHP (.php)

Registered **parsers** exist only for Python, JavaScript, TypeScript, Rust, and Go
(see `cogant.parsers`); files in the other recognized languages are enumerated and
classified but not parsed into the program graph.

#### ManifestParser

**Location:** `cogant.ingest.manifest.ManifestParser`

Parses package manifest files to extract dependencies and metadata.

##### Supported Manifest Formats:

- Python: `setup.py`, `pyproject.toml`, `requirements.txt`
- Node.js: `package.json`
- Rust: `Cargo.toml`

##### Usage:

```python
from cogant.ingest import ManifestParser
from pathlib import Path

parser = ManifestParser()
metadata, dependencies = parser.parse_repo(Path("path/to/repo"))
for dep in dependencies:
    print(dep)
```
