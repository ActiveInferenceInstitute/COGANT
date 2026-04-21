"""Tests for render_output_figures discovery helpers and CLI."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

import cogant.tools.render_output_figures as rof

_HAS_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None
_needs_matplotlib = pytest.mark.skipif(
    not _HAS_MATPLOTLIB,
    reason="matplotlib not installed — install cogant[viz] to enable PNG rendering tests",
)


def test_discover_run_dirs_examples_control_positive(tmp_path: Path) -> None:
    suite = tmp_path / "output" / "examples" / "control_positive"
    suite.mkdir(parents=True)
    for name in ("a", "b"):
        d = suite / name
        d.mkdir()
        pg = d / "data"
        pg.mkdir()
        (pg / "program_graph.json").write_text(
            json.dumps({"nodes": {}, "edges": {}}), encoding="utf-8"
        )
    found = rof._discover_run_dirs(tmp_path / "output")
    assert {p.name for p in found} == {"a", "b"}


def test_discover_run_dirs_single_flat(tmp_path: Path) -> None:
    d = tmp_path / "one"
    d.mkdir()
    (d / "program_graph.json").write_text("{}", encoding="utf-8")
    assert rof._discover_run_dirs(d) == [d.resolve()]


def test_discover_run_dirs_multiple_flat_subdirs(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    for name in ("r1", "r2"):
        r = parent / name
        r.mkdir()
        (r / "program_graph.json").write_text('{"nodes":{"a":{}},"edges":{}}', encoding="utf-8")
    found = rof._discover_run_dirs(parent)
    assert len(found) == 2


def test_discover_run_dirs_not_a_dir(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("x", encoding="utf-8")
    assert rof._discover_run_dirs(f) == []


def test_discover_run_dirs_no_graph(tmp_path: Path) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    assert rof._discover_run_dirs(d) == []


def test_has_program_graph(tmp_path: Path) -> None:
    d = tmp_path / "x"
    d.mkdir()
    assert rof._has_program_graph(d) is False
    (d / "program_graph.json").write_text("{}", encoding="utf-8")
    assert rof._has_program_graph(d) is True


def test_has_program_graph_under_data(tmp_path: Path) -> None:
    d = tmp_path / "y"
    (d / "data").mkdir(parents=True)
    (d / "data" / "program_graph.json").write_text("{}", encoding="utf-8")
    assert rof._has_program_graph(d) is True


@_needs_matplotlib
def test_process_run_dir_writes_program_graph_png(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "program_graph.json").write_text(
        json.dumps(
            {
                "nodes": {"n1": {"id": "n1", "name": "m", "kind": "MODULE"}},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    n = rof._process_run_dir(run)
    assert n >= 1
    assert (run / "figures" / "program_graph.png").is_file()


def test_main_missing_path_returns_1(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    assert rof.main([str(missing)]) == 1


def test_main_no_program_graph_returns_1(tmp_path: Path) -> None:
    d = tmp_path / "emptydir"
    d.mkdir()
    assert rof.main([str(d)]) == 1


@_needs_matplotlib
def test_main_success_on_flat_run(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "program_graph.json").write_text(
        json.dumps({"nodes": {"n": {"id": "n", "name": "x", "kind": "MODULE"}}, "edges": {}}),
        encoding="utf-8",
    )
    assert rof.main([str(run)]) == 0
