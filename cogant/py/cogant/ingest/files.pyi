from typing import Any

from dataclasses import dataclass
from pathlib import Path

LANGUAGE_EXTENSIONS: Any
TEST_PATTERNS: Any
IGNORE_PATTERNS: Any

@dataclass
class FileInfo:
    path: Path
    relative_path: str
    language: str | None
    size_bytes: int
    is_test: bool = ...
    checksum: str | None = ...

class FileEnumerator:
    repo_root: Any
    respect_gitignore: Any
    def __init__(self, repo_root: Path, respect_gitignore: bool = True) -> None: ...
    def enumerate(self, include_test_files: bool = True, compute_checksums: bool = False) -> list[FileInfo]: ...
