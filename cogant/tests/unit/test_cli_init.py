"""Behavioural tests for :mod:`cogant.cli.init_cmd`.

These tests exercise the scaffold helpers through real filesystem
operations under :func:`tmp_path`. They avoid mocking and avoid
spawning the Typer app so they stay independent of the legacy
``cogant init`` command in :mod:`cogant.cli.main`.

Test surface covered:

* ``scaffold_project`` creates ``cogant.toml`` with sensible defaults
* ``scaffold_project`` creates ``.gitignore`` containing the output dir
* Re-running is idempotent (no clobber of user edits)
* ``validate_repo_path`` detects missing paths, files, and returns hints
* ``suggest_repo_path`` uses fuzzy matching on siblings
* ``render_repo_path_error`` emits the canonical ``ERROR`` / ``Hint`` lines
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from rich.console import Console

from cogant.cli.init_cmd import (
    DEFAULT_COGANT_TOML,
    GITIGNORE_ENTRY,
    RepoPathError,
    ScaffoldResult,
    render_repo_path_error,
    render_scaffold_summary,
    scaffold_project,
    suggest_repo_path,
    validate_repo_path,
)

# --------------------------------------------------------------- scaffold --


class TestScaffoldProject:
    def test_creates_cogant_toml_with_defaults(self, tmp_path: Path) -> None:
        """Fresh scaffold writes cogant.toml with the expected sections."""
        proj = tmp_path / "new_proj"
        result = scaffold_project(proj)

        assert isinstance(result, ScaffoldResult)
        assert result.toml_created is True
        assert result.toml_path.exists()
        body = result.toml_path.read_text()
        # Sanity-check the key configuration knobs.
        assert "[project]" in body
        assert "[pipeline]" in body
        assert "skip_dirs" in body
        assert "output_dir" in body
        assert "no_dynamic" in body

    def test_creates_gitignore_with_output_entry(self, tmp_path: Path) -> None:
        """Scaffold writes .gitignore containing cogant_output/."""
        proj = tmp_path / "new_proj"
        result = scaffold_project(proj)

        assert result.gitignore_created is True
        assert result.gitignore_path.exists()
        assert GITIGNORE_ENTRY in result.gitignore_path.read_text()

    def test_creates_missing_project_dir(self, tmp_path: Path) -> None:
        """Nonexistent project directories are created on demand."""
        proj = tmp_path / "nested" / "child" / "proj"
        assert not proj.exists()

        result = scaffold_project(proj)
        assert proj.is_dir()
        assert result.project_dir == proj

    def test_idempotent_does_not_clobber_user_toml(self, tmp_path: Path) -> None:
        """Re-running leaves a user-edited cogant.toml untouched."""
        proj = tmp_path / "proj"
        scaffold_project(proj)

        custom = '# user edits\n[project]\nname = "real-name"\n'
        (proj / "cogant.toml").write_text(custom)

        result = scaffold_project(proj)
        assert result.toml_created is False
        assert (proj / "cogant.toml").read_text() == custom
        assert any("cogant.toml already exists" in n for n in result.notes)

    def test_idempotent_does_not_duplicate_gitignore_entry(self, tmp_path: Path) -> None:
        """Re-running does not append duplicate cogant_output/ lines."""
        proj = tmp_path / "proj"
        scaffold_project(proj)
        scaffold_project(proj)
        scaffold_project(proj)

        body = (proj / ".gitignore").read_text()
        assert body.count(GITIGNORE_ENTRY) == 1

    def test_appends_to_existing_gitignore_without_clobber(self, tmp_path: Path) -> None:
        """Existing gitignore content is preserved; entry is appended."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / ".gitignore").write_text("*.pyc\n__pycache__/\n")

        result = scaffold_project(proj)
        assert result.gitignore_created is False
        assert result.gitignore_updated is True

        body = (proj / ".gitignore").read_text()
        assert "*.pyc" in body  # user content preserved
        assert "__pycache__/" in body
        assert GITIGNORE_ENTRY in body

    def test_raises_on_file_target(self, tmp_path: Path) -> None:
        """Pointing at an existing file should raise NotADirectoryError."""
        target = tmp_path / "file.txt"
        target.write_text("not a dir")
        with pytest.raises(NotADirectoryError):
            scaffold_project(target)

    def test_default_toml_is_non_empty(self) -> None:
        """The TOML template is a non-empty string with a trailing newline."""
        assert DEFAULT_COGANT_TOML
        assert DEFAULT_COGANT_TOML.endswith("\n")


# --------------------------------------------------------- path validation --


class TestValidateRepoPath:
    def test_returns_none_for_valid_dir(self, tmp_path: Path) -> None:
        assert validate_repo_path(tmp_path) is None

    def test_detects_missing_path(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist"
        err = validate_repo_path(missing)
        assert err is not None
        assert isinstance(err, RepoPathError)
        assert "Repo not found" in err.reason

    def test_detects_file_as_not_dir(self, tmp_path: Path) -> None:
        f = tmp_path / "a_file.py"
        f.write_text("x = 1")
        err = validate_repo_path(f)
        assert err is not None
        assert "file" in err.reason.lower()

    def test_suggest_finds_close_sibling(self, tmp_path: Path) -> None:
        (tmp_path / "my_repo").mkdir()
        suggestion = suggest_repo_path(tmp_path / "my_rep0")  # typo
        assert suggestion is not None
        assert suggestion.name == "my_repo"

    def test_suggest_returns_none_when_no_siblings(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty_parent"
        empty.mkdir()
        assert suggest_repo_path(empty / "ghost") is None

    def test_validate_populates_hint_when_available(self, tmp_path: Path) -> None:
        """A missing path next to a near-match should carry a hint."""
        (tmp_path / "alpha").mkdir()
        err = validate_repo_path(tmp_path / "alphaa")  # extra letter
        assert err is not None
        assert err.hint is not None
        assert err.hint.name == "alpha"


# -------------------------------------------------------- console helpers --


def _capture(fn, *args, **kwargs) -> str:
    """Run ``fn(console, *args)`` into an in-memory Rich console."""
    buf = io.StringIO()
    console = Console(file=buf, width=120, force_terminal=False, color_system=None)
    fn(console, *args, **kwargs)
    return buf.getvalue()


class TestConsoleRendering:
    def test_render_error_without_hint(self, tmp_path: Path) -> None:
        err = RepoPathError(
            path=tmp_path / "missing",
            reason="Repo not found: X",
            hint=None,
        )
        output = _capture(render_repo_path_error, err)
        assert "ERROR" in output
        assert "Repo not found" in output
        assert "Hint" not in output

    def test_render_error_with_hint(self, tmp_path: Path) -> None:
        err = RepoPathError(
            path=tmp_path / "mising",
            reason="Repo not found: mising",
            hint=tmp_path / "missing",
        )
        output = _capture(render_repo_path_error, err)
        assert "ERROR" in output
        assert "Hint" in output
        assert "Did you mean" in output
        assert "missing" in output

    def test_render_scaffold_summary_fresh(self, tmp_path: Path) -> None:
        proj = tmp_path / "new"
        result = scaffold_project(proj)
        output = _capture(render_scaffold_summary, result)
        assert "Scaffold complete" in output
        assert "cogant.toml" in output
        assert ".gitignore" in output

    def test_render_scaffold_summary_rerun(self, tmp_path: Path) -> None:
        proj = tmp_path / "new"
        scaffold_project(proj)
        result = scaffold_project(proj)  # second run
        output = _capture(render_scaffold_summary, result)
        assert "Scaffold complete" in output
        # On rerun neither file should report as created.
        assert result.toml_created is False
        assert result.gitignore_created is False
