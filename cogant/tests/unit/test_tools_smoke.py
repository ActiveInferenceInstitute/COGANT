"""Smoke tests for ``cogant.tools.*``.

These are not the deep integration suite for the figure / output organizer
helpers; they exist so the module is exercised under coverage and so the
public entry points (``organize_run_dir``, ``migrate_output_tree``,
``_discover_run_dirs``) keep their documented behaviour: idempotency,
``dry_run`` no-op safety, and graceful handling of missing inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cogant.tools.organize_example_outputs import (
    migrate_output_tree,
    organize_run_dir,
)
from cogant.tools.render_output_figures import _discover_run_dirs

# ---------------------------------------------------------------------------
# organize_run_dir
# ---------------------------------------------------------------------------


def _seed_flat_run(root: Path) -> Path:
    """Create a flat, pre-organize run directory with a few canonical files."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "program_graph.json").write_text(json.dumps({"nodes": []}))
    (root / "summary.md").write_text("# summary\n")
    (root / "graph.dot").write_text("digraph G {}\n")
    (root / "model.mermaid").write_text("graph TD; A-->B\n")
    (root / "index.html").write_text(
        '<html><body><a href="program_graph.json">graph</a>'
        '<a href="summary.md">md</a></body></html>',
    )
    return root


def test_organize_run_dir_moves_files_into_layout(tmp_path: Path) -> None:
    run = _seed_flat_run(tmp_path / "run1")
    out = organize_run_dir(run)
    assert out == run.resolve()
    assert (run / "data" / "program_graph.json").is_file()
    assert (run / "reports" / "summary.md").is_file()
    assert (run / "diagrams" / "graph.dot").is_file()
    assert (run / "diagrams" / "model.mermaid").is_file()
    assert (run / "site" / "index.html").is_file()
    assert (run / "figures").is_dir()


def test_organize_run_dir_rewrites_index_html_links(tmp_path: Path) -> None:
    run = _seed_flat_run(tmp_path / "run2")
    organize_run_dir(run)
    text = (run / "site" / "index.html").read_text()
    assert 'href="../data/program_graph.json"' in text
    assert 'href="../reports/summary.md"' in text


def test_organize_run_dir_is_idempotent(tmp_path: Path) -> None:
    run = _seed_flat_run(tmp_path / "run3")
    first = organize_run_dir(run)
    second = organize_run_dir(run)
    assert first == second
    assert (run / "data" / "program_graph.json").is_file()


def test_organize_run_dir_dry_run_is_noop(tmp_path: Path) -> None:
    run = _seed_flat_run(tmp_path / "run4")
    organize_run_dir(run, dry_run=True)
    assert (run / "program_graph.json").exists()
    assert not (run / "data").exists()


def test_organize_run_dir_missing_dir_returns_none(tmp_path: Path) -> None:
    assert organize_run_dir(tmp_path / "nope") is None


# ---------------------------------------------------------------------------
# migrate_output_tree
# ---------------------------------------------------------------------------


def test_migrate_output_tree_moves_and_organizes(tmp_path: Path) -> None:
    output = tmp_path / "output"
    _seed_flat_run(output / "calculator")
    n = migrate_output_tree(output, examples=["calculator"], suite="control_positive")
    assert n == 1
    moved = output / "examples" / "control_positive" / "calculator"
    assert (moved / "data" / "program_graph.json").is_file()
    assert not (output / "calculator").exists()


def test_migrate_output_tree_dry_run_skips_move(tmp_path: Path) -> None:
    output = tmp_path / "output"
    _seed_flat_run(output / "calculator")
    n = migrate_output_tree(
        output, examples=["calculator"], suite="control_positive", dry_run=True
    )
    assert n == 1
    assert (output / "calculator" / "program_graph.json").exists()
    assert not (output / "examples").exists()


def test_migrate_output_tree_skips_missing(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    output = tmp_path / "output"
    output.mkdir()
    n = migrate_output_tree(output, examples=["nope"])
    assert n == 0


# ---------------------------------------------------------------------------
# render_output_figures._discover_run_dirs
# ---------------------------------------------------------------------------


def test_discover_run_dirs_single(tmp_path: Path) -> None:
    run = tmp_path / "single"
    run.mkdir()
    (run / "program_graph.json").write_text("{}")
    assert _discover_run_dirs(run) == [run.resolve()]


def test_discover_run_dirs_examples_layout(tmp_path: Path) -> None:
    root = tmp_path / "out"
    suite = root / "examples" / "control_positive"
    (suite / "a").mkdir(parents=True)
    (suite / "b").mkdir()
    (suite / "a" / "program_graph.json").write_text("{}")
    (suite / "b" / "program_graph.json").write_text("{}")
    runs = _discover_run_dirs(root)
    assert {p.name for p in runs} == {"a", "b"}


def test_discover_run_dirs_returns_empty_for_unknown(tmp_path: Path) -> None:
    assert _discover_run_dirs(tmp_path / "missing") == []
    empty = tmp_path / "empty"
    empty.mkdir()
    assert _discover_run_dirs(empty) == []
