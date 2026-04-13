from typing import Any

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cogant.ingest.files import FileInfo as FileInfo
from cogant.ingest.manifest import Dependency as Dependency

@dataclass
class RepoMetadata:
    name: str
    url: str
    commit_hash: str | None = ...
    commit_message: str | None = ...
    timestamp: datetime | None = ...
    author: str | None = ...
    language: str | None = ...
    description: str | None = ...

@dataclass
class RepoSnapshot:
    metadata: RepoMetadata
    files: list[FileInfo]
    dependencies: list[Dependency]
    root_path: Path

class RepoIngester:
    work_dir: Any
    manifest_parser: Any
    def __init__(self, work_dir: Path | None = None) -> None: ...
    def ingest_local(self, repo_path: Path, include_test_files: bool = True, compute_checksums: bool = False) -> RepoSnapshot: ...
    def ingest_git_remote(self, url: str, branch: str | None = None, include_test_files: bool = True, compute_checksums: bool = False, cleanup: bool = True) -> RepoSnapshot: ...
