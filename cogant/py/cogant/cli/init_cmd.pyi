from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

__all__ = [
    "DEFAULT_COGANT_TOML",
    "GITIGNORE_ENTRY",
    "RepoPathError",
    "ScaffoldResult",
    "render_repo_path_error",
    "render_scaffold_summary",
    "scaffold_project",
    "suggest_repo_path",
    "validate_repo_path",
]

DEFAULT_COGANT_TOML: str
GITIGNORE_ENTRY: str

@dataclass
class ScaffoldResult:
    project_dir: Path
    toml_path: Path
    gitignore_path: Path
    toml_created: bool
    gitignore_created: bool
    gitignore_updated: bool
    notes: list[str] = field(default_factory=list)

@dataclass
class RepoPathError:
    path: Path
    reason: str
    hint: Path | None

def suggest_repo_path(path: Path) -> Path | None: ...
def validate_repo_path(path: str | Path) -> RepoPathError | None: ...
def render_repo_path_error(console: Console, error: RepoPathError) -> None: ...
def scaffold_project(project_dir: str | Path) -> ScaffoldResult: ...
def render_scaffold_summary(console: Console, result: ScaffoldResult) -> None: ...
