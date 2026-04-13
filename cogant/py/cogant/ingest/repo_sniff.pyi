from pathlib import Path

__all__ = ['SOURCE_EXTENSIONS', 'SKIP_DIRS', 'count_source_files', 'estimate_pipeline_seconds', 'format_duration']

SOURCE_EXTENSIONS: frozenset[str]
SKIP_DIRS: frozenset[str]

def count_source_files(root: Path, *, file_budget: int = ...) -> int: ...
def estimate_pipeline_seconds(file_count: int) -> float: ...
def format_duration(seconds: float) -> str: ...
