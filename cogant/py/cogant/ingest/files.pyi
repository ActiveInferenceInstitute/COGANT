from dataclasses import dataclass
from pathlib import Path

from _typeshed import Incomplete as Incomplete

logger: Incomplete
LANGUAGE_EXTENSIONS: Incomplete
TEST_PATTERNS: Incomplete
IGNORE_PATTERNS: Incomplete

@dataclass
class FileInfo:
    path: Path
    relative_path: str
    language: str | None
    size_bytes: int
    is_test: bool = ...
    checksum: str | None = ...

class FileEnumerator:
    repo_root: Incomplete
    respect_gitignore: Incomplete
    def __init__(self, repo_root: Path, respect_gitignore: bool = True) -> None: ...
    def enumerate(self, include_test_files: bool = True, compute_checksums: bool = False) -> list[FileInfo]: ...
