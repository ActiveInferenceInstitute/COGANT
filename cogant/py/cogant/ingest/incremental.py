"""Incremental analysis mode.

Detects which files in a repository have changed between two git refs
(or in the working tree) so downstream stages only need to re-analyze
the affected subset. Non-git repositories degrade to an empty result
without raising, which lets callers treat incremental mode as an
optional fast path.

Usage::

    from cogant.ingest.incremental import IncrementalIngester

    ingester = IncrementalIngester(repo_path)
    if ingester.is_git_repo():
        changed = ingester.changed_since("HEAD~1")
        python_changed = ingester.python_files_changed_since("HEAD~1")
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ChangedFile:
    """A single file that changed between two git refs.

    ``change_type`` follows ``git diff --name-status`` conventions:

    * ``A`` — added
    * ``M`` — modified
    * ``D`` — deleted
    * ``R`` — renamed
    * ``C`` — copied
    * ``T`` — type changed (e.g. symlink ↔ file)
    * ``U`` — unmerged
    * ``?`` — untracked (from ``git status``)
    """

    path: Path
    change_type: str


class IncrementalIngester:
    """Detect changed files between git refs for incremental re-analysis."""

    _SOURCE_EXTENSIONS = {
        ".py", ".pyx", ".pyi",
        ".js", ".jsx", ".mjs", ".cjs",
        ".ts", ".tsx",
        ".rs",
        ".go",
    }

    def __init__(self, repo_path: Path, git_timeout: float = 30.0) -> None:
        self.repo_path = Path(repo_path)
        self.git_timeout = float(git_timeout)
        self._git_available = self._check_git()

    # ------------------------------------------------------------------
    # Git plumbing
    # ------------------------------------------------------------------

    def _check_git(self) -> bool:
        """Return True iff ``self.repo_path`` is inside a git repo."""
        if not self.repo_path.exists():
            return False
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return False

    def is_git_repo(self) -> bool:
        """Return True when git plumbing can be used on this repo."""
        return self._git_available

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def changed_since(self, ref: str = "HEAD~1") -> list[ChangedFile]:
        """Return files changed between ``ref`` and ``HEAD``.

        Non-git repos return an empty list (with a warning log).
        Renamed and copied files are reported with the *new* path and
        ``R`` / ``C`` change types; callers that need the old path
        should use a richer git API.
        """
        if not self._git_available:
            logger.warning(
                "Not a git repository, cannot do incremental analysis"
            )
            return []

        try:
            result = subprocess.run(
                ["git", "diff", "--name-status", ref, "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self.git_timeout,
            )
        except subprocess.SubprocessError as exc:
            logger.warning("git diff error: %s", exc)
            return []

        if result.returncode != 0:
            logger.warning("git diff failed: %s", result.stderr.strip())
            return []

        return self._parse_name_status(result.stdout)

    def changed_since_commit(self, commit_hash: str) -> list[ChangedFile]:
        """Return files changed since a specific commit."""
        return self.changed_since(commit_hash)

    def working_tree_changes(self) -> list[ChangedFile]:
        """Return uncommitted (index + worktree) changes.

        Uses ``git status --porcelain`` so both staged and unstaged
        modifications are reported with a single-character ``change_type``
        (the first column of the porcelain status, which covers the
        index state for tracked files and ``?`` for untracked ones).
        """
        if not self._git_available:
            return []

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except subprocess.SubprocessError as exc:
            logger.warning("git status error: %s", exc)
            return []

        if result.returncode != 0:
            logger.warning("git status failed: %s", result.stderr.strip())
            return []

        changed: list[ChangedFile] = []
        for line in result.stdout.splitlines():
            if len(line) < 3:
                continue
            status = line[:2]
            path = line[3:].strip()
            # `git status` separates old → new for renames with " -> "
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            # Pick the first non-space status char to report something
            # meaningful for both staged and unstaged modifications.
            primary = status[0] if status[0] != " " else status[1]
            if primary == " ":
                primary = "M"
            if primary == "?":
                change_type = "?"
            else:
                change_type = primary
            changed.append(
                ChangedFile(
                    path=self.repo_path / path,
                    change_type=change_type,
                )
            )
        return changed

    def python_files_changed_since(self, ref: str = "HEAD~1") -> list[Path]:
        """Return only Python files changed between ``ref`` and ``HEAD``."""
        return self.source_files_changed_since(
            ref, extensions={".py", ".pyx", ".pyi"}
        )

    def source_files_changed_since(
        self,
        ref: str = "HEAD~1",
        extensions: set | None = None,
    ) -> list[Path]:
        """Return source files changed since ``ref``.

        ``extensions`` defaults to the full cross-language set COGANT
        can parse (``.py``, ``.js``, ``.ts``, ``.rs``, ``.go``, …).
        Deletions are excluded because there is nothing to re-parse.
        """
        exts = extensions or self._SOURCE_EXTENSIONS
        changed = self.changed_since(ref)
        return [
            cf.path
            for cf in changed
            if cf.change_type != "D" and cf.path.suffix.lower() in exts
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_name_status(self, stdout: str) -> list[ChangedFile]:
        """Parse ``git diff --name-status`` output into ChangedFile list."""
        changed: list[ChangedFile] = []
        for line in stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            raw_status = parts[0]
            # Rename / copy entries have 3 columns: R100\told\tnew
            if raw_status[0] in {"R", "C"} and len(parts) >= 3:
                path = parts[-1]
            else:
                path = parts[1]
            change_type = raw_status[0]
            changed.append(
                ChangedFile(
                    path=self.repo_path / path.strip(),
                    change_type=change_type,
                )
            )
        return changed
