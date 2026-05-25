"""Fast repository sniffing for CLI ergonomics.

Small, dependency-free helpers used by ``cogant init`` and similar
commands to decide whether a directory looks like a parseable repo and
give the user a rough wall-clock estimate for a full pipeline run.

These helpers intentionally avoid the full ``RepositoryIngester`` code
path:

* ``cogant init`` runs on *any* directory the user points at — including
  empty scaffolds and monorepos — so a full ingest would be far too
  heavy for an interactive "is this worth running?" prompt.
* The estimate is displayed in UI strings only and never gates behavior,
  so best-effort precision is fine.

The module deliberately lives under :mod:`cogant.ingest` because it is
shared business logic about what counts as a "source file" and how the
pipeline scales, rather than CLI plumbing. Keeping it out of
``cogant.cli`` means tests and alternative front-ends (IDE plugins,
web dashboards, scripts) can import it without pulling in Typer.
"""

from __future__ import annotations

from dataclasses import dataclass
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


#: File extensions COGANT can currently parse. Kept in sync with the
#: language detectors in :mod:`cogant.ingest.language_detect`; adding a
#: new parser should append to this set so ``cogant init`` starts
#: counting the matching files.
SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
    }
)


#: Directory names to skip during the shallow sniff. These are the
#: usual suspects that contain vendored / generated / virtualenv code
#: that would inflate the file count without any value to the user.
SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
        "target",
    }
)


#: Hard cap on files examined by :func:`count_source_files`. Pathological
#: monorepos with tens of thousands of files would otherwise freeze the
#: CLI for multiple seconds on first run.
DEFAULT_FILE_BUDGET: int = 5000


def count_source_files(
    root: Path,
    *,
    file_budget: int = DEFAULT_FILE_BUDGET,
) -> int:
    """Best-effort count of parseable source files below ``root``.

    Walks the tree recursively with a file budget and skips well-known
    noise directories (``.git``, ``node_modules``, ``.venv``, …) so the
    result stays fast even on large repos. Files whose extension is not
    in :data:`SOURCE_EXTENSIONS` are ignored.

    Args:
        root: Directory to examine. A missing path, a file, or a
            non-directory returns ``0`` rather than raising so the
            caller can use this in user-facing "is this a repo?" flows.
        file_budget: Maximum number of filesystem entries to inspect
            before stopping early. Defaults to
            :data:`DEFAULT_FILE_BUDGET`.

    Returns:
        Number of matched source files. Always non-negative.
    """
    if not root.exists() or not root.is_dir():
        return 0

    count = 0
    budget = file_budget
    for path in root.rglob("*"):
        if budget <= 0:
            break
        budget -= 1
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS:
            count += 1
    return count


def _iter_source_files(
    root: Path,
    *,
    file_budget: int = DEFAULT_FILE_BUDGET,
) -> list[Path]:
    """Return parseable source files below ``root`` within ``file_budget``."""
    if not root.exists() or not root.is_dir():
        return []

    paths: list[Path] = []
    budget = file_budget
    for path in root.rglob("*"):
        if budget <= 0:
            break
        budget -= 1
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS:
            paths.append(path)
    return paths


_LANGUAGE_BY_SUFFIX: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}


@dataclass(frozen=True)
class RepoSniffer:
    """Small object wrapper around the repository sniff helpers.

    The class form is useful for UI and tests that want one reusable object,
    while the module-level functions remain the lightest public API.
    """

    root: Path | str
    file_budget: int = DEFAULT_FILE_BUDGET

    def _root_path(self) -> Path:
        return Path(self.root)

    def detect_languages(self) -> dict[str, int]:
        """Return language counts inferred from parseable source suffixes."""
        counts: dict[str, int] = {}
        for path in _iter_source_files(self._root_path(), file_budget=self.file_budget):
            language = _LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), path.suffix.lower().lstrip("."))
            counts[language] = counts.get(language, 0) + 1
        return counts

    def sniff(self) -> dict[str, object]:
        """Return a compact, JSON-ready repository summary."""
        files = _iter_source_files(self._root_path(), file_budget=self.file_budget)
        source_count = len(files)
        seconds = estimate_pipeline_seconds(source_count)
        return {
            "root": str(self._root_path()),
            "source_file_count": source_count,
            "languages": self.detect_languages(),
            "estimated_seconds": seconds,
            "estimated_duration": format_duration(seconds),
        }


def sniff_repo(root: Path | str, *, file_budget: int = DEFAULT_FILE_BUDGET) -> dict[str, object]:
    """Convenience wrapper returning :meth:`RepoSniffer.sniff` output."""
    return RepoSniffer(root, file_budget=file_budget).sniff()


def estimate_pipeline_seconds(file_count: int) -> float:
    """Rough wall-clock estimate for a full ``cogant translate`` run.

    The 50 ms/file heuristic comes from the v0.1.0 benchmark table on
    the control-positive fixtures. It overestimates for tiny repos
    (where the constant-time overhead dominates) and underestimates for
    very large ones (where IO starts to matter), but is honest enough to
    tell users whether they are waiting seconds or minutes.

    Args:
        file_count: Number of parseable source files.

    Returns:
        Estimated wall-clock seconds as a ``float``. Returns ``0.0``
        when ``file_count <= 0``.
    """
    if file_count <= 0:
        return 0.0
    # 2s constant-time overhead for pipeline setup + 50ms per file.
    return 2.0 + (file_count * 0.05)


def format_duration(seconds: float) -> str:
    """Human-friendly rendering of a wall-clock duration.

    Examples::

        format_duration(0.3) -> "<1s"
        format_duration(4.9) -> "5s"
        format_duration(75.0) -> "1m 15s"
    """
    if seconds < 1.0:
        return "<1s"
    if seconds < 60.0:
        return f"{seconds:.0f}s"
    minutes, rem = divmod(seconds, 60.0)
    return f"{int(minutes)}m {int(rem)}s"
