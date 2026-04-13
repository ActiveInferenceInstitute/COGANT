"""Tests for example output layout (no mocks; temp dirs and real file moves)."""

from __future__ import annotations

from pathlib import Path

from cogant.tools.organize_example_outputs import (
    migrate_output_tree,
    organize_run_dir,
)
from cogant.tools.organize_example_outputs import _rewrite_index_html
from cogant.tools import organize_example_outputs as oeo


def test_organize_run_dir_moves_known_files(tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    (root / "program_graph.json").write_text('{"nodes":{},"edges":{}}', encoding="utf-8")
    (root / "state_space.json").write_text("{}", encoding="utf-8")
    (root / "bundle.json").write_text("{}", encoding="utf-8")
    (root / "class_diagram.mermaid").write_text("classDiagram\n  class A\n", encoding="utf-8")
    (root / "index.html").write_text(
        "<ul><li><a href='program_graph.json'>program_graph.json</a></li></ul>",
        encoding="utf-8",
    )

    organize_run_dir(root, dry_run=False)

    assert (root / "data" / "program_graph.json").is_file()
    assert (root / "data" / "state_space.json").is_file()
    assert (root / "data" / "bundle.json").is_file()
    assert (root / "diagrams" / "class_diagram.mermaid").is_file()
    assert (root / "site" / "index.html").is_file()
    html = (root / "site" / "index.html").read_text(encoding="utf-8")
    assert "../data/program_graph.json" in html


def test_rewrite_index_html_preserves_external_hrefs(tmp_path: Path) -> None:
    p = tmp_path / "index.html"
    p.write_text(
        "<a href='https://example.com/x'>x</a><a href='model.gnn.json'>m</a>",
        encoding="utf-8",
    )
    _rewrite_index_html(p)
    t = p.read_text(encoding="utf-8")
    assert "https://example.com/x" in t
    assert "../data/model.gnn.json" in t


def test_organize_run_dir_dry_run_no_moves(tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    (root / "program_graph.json").write_text("{}", encoding="utf-8")
    organize_run_dir(root, dry_run=True)
    assert (root / "program_graph.json").is_file()
    assert not (root / "data").exists()


def test_organize_run_dir_already_organized_skips(tmp_path: Path) -> None:
    root = tmp_path / "org"
    (root / "data").mkdir(parents=True)
    (root / "site").mkdir(parents=True)
    (root / "data" / "program_graph.json").write_text("{}", encoding="utf-8")
    (root / "site" / "index.html").write_text("<html/>", encoding="utf-8")
    organize_run_dir(root, dry_run=False)
    assert (root / "data" / "program_graph.json").read_text() == "{}"


def test_migrate_output_tree_moves_flat_example(tmp_path: Path) -> None:
    out = tmp_path / "output"
    calc = out / "demo"
    calc.mkdir(parents=True)
    (calc / "program_graph.json").write_text('{"nodes":{},"edges":{}}', encoding="utf-8")

    n = migrate_output_tree(out, suite="control_positive", examples=["demo"], dry_run=False)
    assert n == 1
    assert not calc.exists()
    target = out / "examples" / "control_positive" / "demo"
    assert (target / "data" / "program_graph.json").is_file()


def test_migrate_output_tree_dry_run(tmp_path: Path) -> None:
    out = tmp_path / "o"
    flat = out / "demo"
    flat.mkdir(parents=True)
    (flat / "program_graph.json").write_text("{}", encoding="utf-8")
    migrate_output_tree(out, examples=["demo"], dry_run=True)
    assert (flat / "program_graph.json").is_file()


def test_main_organize_only_exits_zero(tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    (root / "program_graph.json").write_text("{}", encoding="utf-8")
    rc = oeo.main(["--organize-only", str(root)])
    assert rc == 0
    assert (root / "data" / "program_graph.json").is_file()


def test_main_default_migrate_missing_examples(tmp_path: Path) -> None:
    empty = tmp_path / "empty_out"
    empty.mkdir()
    rc = oeo.main([str(empty)])
    assert rc == 0
