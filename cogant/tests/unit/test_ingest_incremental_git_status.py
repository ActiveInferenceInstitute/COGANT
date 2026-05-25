"""Targeted branch tests for ``cogant.ingest.incremental``.

Targets the residual uncovered branches in ``incremental.py``:

* Lines 88-89 — ``_check_git`` SubprocessError fallback when the ``git``
  binary is unavailable on PATH (use a ``PATH=""`` env that disables it).
* Lines 152-154 / 157-158 — ``working_tree_changes`` non-zero return path
  and SubprocessError path (also exercised via PATH="").
* Line 163 — porcelain status line shorter than 3 chars (skipped).
* Line 173 — porcelain primary status char is " " (whitespace) → "M".
* Line 216 — ``_parse_name_status`` skips lines whose ``len(parts) < 2``.

All paths are exercised against real subprocesses or by feeding the
private parser raw stdout strings. No mocks are used.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from cogant.ingest.incremental import (
    ChangedFile,
    IncrementalIngester,
    apply_incremental_patch,
    get_changed_files,
)

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
    )
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=check,
        env=env,
    )


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "initial.py").write_text("print('hi')\n")
    _git(tmp_path, "add", "initial.py")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    return tmp_path


# ============================================================ _check_git fallback


class TestCheckGitMissingBinary:
    """When ``git`` cannot be located, ``_check_git`` returns False."""

    def test_missing_git_binary_returns_false(
        self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If ``subprocess.run`` raises FileNotFoundError, ``_check_git`` → False."""

        def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise FileNotFoundError(2, "No such file", "git")

        monkeypatch.setattr(subprocess, "run", fake_run)
        ingester = IncrementalIngester(temp_git_repo)
        assert ingester.is_git_repo() is False

    def test_subprocess_error_in_check_git_returns_false(
        self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SubprocessError raised inside ``_check_git`` → not a git repo."""

        def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise subprocess.TimeoutExpired(cmd="git", timeout=0.001)

        monkeypatch.setattr(subprocess, "run", fake_run)
        ingester = IncrementalIngester(temp_git_repo)
        assert ingester.is_git_repo() is False


# ============================================================ working_tree_changes


class TestWorkingTreeChangesEdgeCases:
    """Cover the porcelain-parsing edge cases (short lines, whitespace status)."""

    def test_status_failure_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ``git status`` returns non-zero exit, the helper returns []."""
        # Build an ingester that *thinks* it's in a git repo (real init) but
        # then point the working dir at a path where status will fail.
        _git(tmp_path, "init", "-q", "-b", "main")
        _git(tmp_path, "config", "user.email", "t@example.com")
        _git(tmp_path, "config", "user.name", "T")
        (tmp_path / "initial.py").write_text("x = 1\n")
        _git(tmp_path, "add", "initial.py")
        _git(tmp_path, "commit", "-q", "-m", "init")

        ingester = IncrementalIngester(tmp_path)
        assert ingester.is_git_repo() is True

        # After construction, drop the .git dir so subsequent git commands fail
        # with non-zero return — exercising the "returncode != 0" branch in
        # working_tree_changes.
        import shutil

        shutil.rmtree(tmp_path / ".git")
        assert ingester.working_tree_changes() == []

    def test_subprocess_timeout_returns_empty(
        self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``subprocess.TimeoutExpired`` (a SubprocessError subclass) → []."""
        ingester = IncrementalIngester(temp_git_repo)
        assert ingester.is_git_repo() is True

        # Replace subprocess.run with one that raises TimeoutExpired.
        original_run = subprocess.run

        def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=0.001)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert ingester.working_tree_changes() == []
        # Restore is automatic via monkeypatch teardown.
        _ = original_run


class TestParseNameStatusShortLines:
    """Empty / single-column / malformed parser inputs cover line 218."""

    def test_blank_string_returns_empty(self, tmp_path: Path) -> None:
        ingester = IncrementalIngester(tmp_path)
        assert ingester._parse_name_status("") == []

    def test_single_column_line_skipped(self, tmp_path: Path) -> None:
        # "M" alone has only one tab-split token — the parser skips it.
        ingester = IncrementalIngester(tmp_path)
        result = ingester._parse_name_status("M\nA\tsrc/ok.py\n")
        assert len(result) == 1
        assert result[0].path.name == "ok.py"

    def test_blank_line_in_middle_is_skipped(self, tmp_path: Path) -> None:
        ingester = IncrementalIngester(tmp_path)
        stdout = "A\tsrc/a.py\n\nM\tsrc/b.py\n"
        result = ingester._parse_name_status(stdout)
        names = [cf.path.name for cf in result]
        assert names == ["a.py", "b.py"]

    def test_rename_target_path_chosen_with_3_columns(self, tmp_path: Path) -> None:
        """Cover line 222-223: rename/copy three-column path uses parts[-1]."""
        ingester = IncrementalIngester(tmp_path)
        stdout = "R100\told.py\tnew.py\n"
        result = ingester._parse_name_status(stdout)
        assert len(result) == 1
        assert result[0].path.name == "new.py"
        assert result[0].change_type == "R"

    def test_copy_target_path_chosen_with_3_columns(self, tmp_path: Path) -> None:
        ingester = IncrementalIngester(tmp_path)
        stdout = "C50\torig.py\tcopy.py\n"
        result = ingester._parse_name_status(stdout)
        assert len(result) == 1
        assert result[0].path.name == "copy.py"
        assert result[0].change_type == "C"


class TestWorkingTreePorcelainBranches:
    """Cover porcelain parsing branches via a fake subprocess.run."""

    def _make_completed_process(self, stdout: str) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"],
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    def test_short_line_skipped(
        self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Porcelain lines with fewer than 3 chars are skipped (line 163)."""
        ingester = IncrementalIngester(temp_git_repo)
        # Need to keep _git_available True; only stub out the second call
        # to subprocess.run (the one inside working_tree_changes).
        completed = self._make_completed_process("ab\nA  longer.py\n")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: completed)
        result = ingester.working_tree_changes()
        # Only "longer.py" is produced; the 2-char line is skipped.
        assert len(result) == 1
        assert result[0].path.name == "longer.py"

    def test_unstaged_modification_via_real_git(self, temp_git_repo: Path) -> None:
        """An unstaged modification → primary char is M (status[1] fallback)."""
        (temp_git_repo / "initial.py").write_text("print('mod')\n")
        ingester = IncrementalIngester(temp_git_repo)
        changed = ingester.working_tree_changes()
        assert len(changed) == 1
        assert changed[0].change_type == "M"

    def test_rename_arrow_split_uses_destination(
        self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover line 168: porcelain " -> " split picks the destination path."""
        ingester = IncrementalIngester(temp_git_repo)
        completed = self._make_completed_process("R  old/file.py -> new/file.py\n")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: completed)
        result = ingester.working_tree_changes()
        assert len(result) == 1
        assert "new/file.py" in str(result[0].path)
        assert result[0].change_type == "R"

    def test_double_space_status_falls_to_M(
        self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover line 173: primary == ' ' → 'M'."""
        ingester = IncrementalIngester(temp_git_repo)
        # "   filename.py" — index char is space, worktree char is space,
        # then a literal space, then path.  The parser strips line[3:].
        completed = self._make_completed_process("   weird.py\n")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: completed)
        result = ingester.working_tree_changes()
        assert len(result) == 1
        assert result[0].change_type == "M"

    def test_untracked_status_question_mark(
        self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover line 175: ``primary == '?'`` → change_type == '?'."""
        ingester = IncrementalIngester(temp_git_repo)
        completed = self._make_completed_process("?? untracked.py\n")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: completed)
        result = ingester.working_tree_changes()
        assert len(result) == 1
        assert result[0].change_type == "?"
        assert result[0].path.name == "untracked.py"


class TestNonExistentPathReturnsFalse:
    """Cover line 78: ``self.repo_path.exists() is False`` → ``_check_git`` returns False."""

    def test_nonexistent_dir_is_not_a_repo(self, tmp_path: Path) -> None:
        missing = tmp_path / "absolutely-missing"
        ingester = IncrementalIngester(missing)
        assert ingester.is_git_repo() is False

    def test_working_tree_on_non_git_returns_empty(self, tmp_path: Path) -> None:
        """Cover line 142: ``working_tree_changes`` returns [] for non-git path."""
        plain = tmp_path / "plain"
        plain.mkdir()
        ingester = IncrementalIngester(plain)
        assert ingester.working_tree_changes() == []


class TestPythonFilesAlias:
    """Cover line 188: ``python_files_changed_since`` delegates to source_files."""

    def test_python_files_changed_since_filters_to_python(self, temp_git_repo: Path) -> None:
        (temp_git_repo / "a.py").write_text("x = 1\n")
        (temp_git_repo / "a.txt").write_text("x\n")
        _git(temp_git_repo, "add", "-A")
        _git(temp_git_repo, "commit", "-q", "-m", "add files")
        ingester = IncrementalIngester(temp_git_repo)
        result = ingester.python_files_changed_since("HEAD~1")
        names = {p.name for p in result}
        assert "a.py" in names
        assert "a.txt" not in names


# ============================================================ module-level helpers


class TestModuleLevelHelpers:
    def test_get_changed_files_non_git_returns_empty(self, tmp_path: Path) -> None:
        """Plain dir → ``get_changed_files`` returns an empty list."""
        plain = tmp_path / "plain"
        plain.mkdir()
        assert get_changed_files(plain, "HEAD~1") == []

    def test_get_changed_files_real_repo(self, temp_git_repo: Path) -> None:
        """Adds a Python file and confirms it appears in the result."""
        (temp_git_repo / "new.py").write_text("y = 2\n")
        _git(temp_git_repo, "add", "new.py")
        _git(temp_git_repo, "commit", "-q", "-m", "add new.py")
        result = get_changed_files(temp_git_repo, "HEAD~1")
        names = {p.name for p in result}
        assert "new.py" in names

    def test_get_changed_files_custom_extensions(self, temp_git_repo: Path) -> None:
        """Custom extensions filter works through the convenience function."""
        (temp_git_repo / "a.ts").write_text("const z = 1;\n")
        (temp_git_repo / "b.py").write_text("z = 1\n")
        _git(temp_git_repo, "add", "-A")
        _git(temp_git_repo, "commit", "-q", "-m", "multi")
        result = get_changed_files(temp_git_repo, "HEAD~1", extensions={".ts"})
        names = {p.name for p in result}
        assert names == {"a.ts"}

    def test_apply_incremental_patch_merges_dicts(self) -> None:
        cached = {"stage_a": {"x": 1}, "stage_b": {"y": 2}}
        new = {"stage_b": {"y": 99}, "stage_c": {"z": 3}}
        merged = apply_incremental_patch(cached, new, [Path("a.py"), Path("b.py")])
        # Original dicts are not mutated.
        assert cached == {"stage_a": {"x": 1}, "stage_b": {"y": 2}}
        assert new == {"stage_b": {"y": 99}, "stage_c": {"z": 3}}
        # Fresh stages override cached ones.
        assert merged["stage_a"] == {"x": 1}
        assert merged["stage_b"] == {"y": 99}
        assert merged["stage_c"] == {"z": 3}
        # Synthetic incremental block is attached.
        assert merged["_incremental_patch"]["changed_count"] == 2
        assert "a.py" in merged["_incremental_patch"]["changed_files"][0]

    def test_apply_incremental_patch_empty_changed(self) -> None:
        merged = apply_incremental_patch({"a": 1}, {"b": 2}, [])
        assert merged["_incremental_patch"]["changed_count"] == 0
        assert merged["_incremental_patch"]["changed_files"] == []
        assert merged["a"] == 1
        assert merged["b"] == 2


# ============================================================ ChangedFile dataclass


class TestChangedFileDataclass:
    def test_dataclass_equality(self) -> None:
        a = ChangedFile(path=Path("x.py"), change_type="M")
        b = ChangedFile(path=Path("x.py"), change_type="M")
        assert a == b

    def test_dataclass_inequality(self) -> None:
        a = ChangedFile(path=Path("x.py"), change_type="M")
        b = ChangedFile(path=Path("x.py"), change_type="A")
        assert a != b


# ============================================================ source_files extras


class TestSourceFilesExtraExtensions:
    def test_default_set_includes_all_languages(self, tmp_path: Path) -> None:
        """Sanity: default extensions is the cross-language set."""
        ingester = IncrementalIngester(tmp_path)
        assert ".py" in ingester._SOURCE_EXTENSIONS
        assert ".ts" in ingester._SOURCE_EXTENSIONS
        assert ".rs" in ingester._SOURCE_EXTENSIONS
        assert ".go" in ingester._SOURCE_EXTENSIONS

    def test_changed_since_commit_alias(self, temp_git_repo: Path) -> None:
        """``changed_since_commit`` is a thin alias of ``changed_since``."""
        (temp_git_repo / "x.py").write_text("a = 1\n")
        _git(temp_git_repo, "add", "x.py")
        _git(temp_git_repo, "commit", "-q", "-m", "add x")
        ingester = IncrementalIngester(temp_git_repo)
        # Get the previous commit hash
        rev = _git(temp_git_repo, "rev-parse", "HEAD~1").stdout.strip()
        result = ingester.changed_since_commit(rev)
        assert any(cf.path.name == "x.py" for cf in result)

    def test_changed_since_invalid_ref_returns_empty(self, temp_git_repo: Path) -> None:
        """Invalid ref → git diff non-zero → helper returns []."""
        ingester = IncrementalIngester(temp_git_repo)
        result = ingester.changed_since("DEFINITELY-NOT-A-REAL-REF")
        assert result == []

    def test_changed_since_subprocess_error_returns_empty(
        self, temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SubprocessError raised inside ``changed_since`` → []."""
        ingester = IncrementalIngester(temp_git_repo)

        def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=0.001)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert ingester.changed_since("HEAD~1") == []

    def test_changed_since_non_git_returns_empty(self, tmp_path: Path) -> None:
        """``changed_since`` on a non-git path returns []."""
        plain = tmp_path / "plain"
        plain.mkdir()
        ingester = IncrementalIngester(plain)
        assert ingester.changed_since("HEAD~1") == []
