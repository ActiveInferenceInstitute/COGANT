## Enumerate all source files
files = enumerator.enumerate(
    include_test_files=False,
    compute_checksums=True
)

for file_info in files:
    print(f"{file_info.relative_path} ({file_info.language})")
    print(f"  Size: {file_info.size_bytes} bytes")
    if file_info.checksum:
        print(f"  Checksum: {file_info.checksum}")
```

##### Supported Languages:
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

