from pathlib import Path

__all__ = [
    "RepoSniffer",
    "SOURCE_EXTENSIONS",
    "SKIP_DIRS",
    "count_source_files",
    "sniff_repo",
    "estimate_pipeline_seconds",
    "format_duration",
]

SOURCE_EXTENSIONS: frozenset[str]
SKIP_DIRS: frozenset[str]

class RepoSniffer:
    root: Path | str
    file_budget: int
    def __init__(self, root: Path | str, file_budget: int = ...) -> None: ...
    def detect_languages(self) -> dict[str, int]: ...
    def sniff(self) -> dict[str, object]: ...

def count_source_files(root: Path, *, file_budget: int = ...) -> int: ...
def sniff_repo(root: Path | str, *, file_budget: int = ...) -> dict[str, object]: ...
def estimate_pipeline_seconds(file_count: int) -> float: ...
def format_duration(seconds: float) -> str: ...
