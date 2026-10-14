"""Behavior tests for the ``cogant._rust`` PyO3 extension.

Each test pins one observable behavior of the Rust bindings, and where a
pure-Python counterpart exists, checks that the Rust result matches it.
Tests are marked ``requires_rust`` and skip when the extension is not built
(``maturin develop --release`` from ``rust/cogant-ffi``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.rust_backend import RUST_AVAILABLE

pytestmark = pytest.mark.requires_rust

if not RUST_AVAILABLE:
    pytest.skip("Rust bindings not compiled", allow_module_level=True)

from cogant._rust import PyProgramGraph, create_example_graph  # noqa: E402


def _two_function_graph() -> PyProgramGraph:
    graph = PyProgramGraph()
    graph.add_node("function", "main", "pkg.main", "pkg.py", "python", 1, 5)
    graph.add_node("function", "helper", "pkg.helper", "pkg.py", "python", 6, 9)
    assert graph.add_edge("pkg.main", "pkg.helper", "calls")
    return graph


def test_get_callees_and_callers_resolve_the_stable_id_passed_to_add_node() -> None:
    graph = _two_function_graph()

    assert graph.get_callees("pkg.main") == ["helper"]
    assert graph.get_callers("pkg.helper") == ["main"]


def test_get_callees_and_callers_return_empty_for_unknown_ids() -> None:
    graph = _two_function_graph()

    assert graph.get_callees("pkg.missing") == []
    assert graph.get_callers("pkg.missing") == []


def test_example_graph_reports_its_call_edge() -> None:
    graph = create_example_graph()

    assert graph.get_callees("fn_main") == ["helper"]
    assert graph.get_callers("fn_helper") == ["main"]


# --------------------------------------------------------------------------
# connected_components: parity with ProgramGraphBuilder's Python BFS
# --------------------------------------------------------------------------


def _builder_components(
    monkeypatch: pytest.MonkeyPatch, names: list[str], edges: list[tuple[int, int]], backend: str
) -> list[list[str]]:
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    monkeypatch.setenv("COGANT_USE_RUST", backend)
    builder = ProgramGraphBuilder(repo_uri="repo://cc")
    ids = [
        builder.add_node(NodeKind.FUNCTION, name, f"pkg.{name}", "pkg.py", "python").id
        for name in names
    ]
    for src, dst in edges:
        builder.add_edge(ids[src], ids[dst], EdgeKind.CALLS)
    return builder.get_connected_components()


@pytest.mark.parametrize(
    ("names", "edges"),
    [
        pytest.param([], [], id="empty"),
        pytest.param(["solo"], [], id="single-isolated"),
        pytest.param(["a", "b", "c"], [(0, 1), (1, 2), (2, 0)], id="cycle"),
        pytest.param(["a", "b"], [(0, 0), (0, 1)], id="self-loop"),
        pytest.param(["a", "b", "c", "d"], [(3, 2), (0, 1)], id="two-components"),
        pytest.param(["ünï", "名前", "emoji_🙂"], [(1, 2)], id="unicode-ids"),
    ],
)
def test_connected_components_match_python_bfs(
    monkeypatch: pytest.MonkeyPatch, names: list[str], edges: list[tuple[int, int]]
) -> None:
    python = _builder_components(monkeypatch, names, edges, "0")
    rust = _builder_components(monkeypatch, names, edges, "1")

    assert rust == python


def test_connected_components_treat_duplicate_node_ids_as_one_node() -> None:
    from cogant._rust import connected_components

    # The Python backend keys nodes by id (a dict), so a repeated id is one
    # node at its first position; each id must appear exactly once.
    components = connected_components(["a", "b", "a", "c"], [("a", "b")])

    assert components == [["a", "b"], ["c"]]


def test_write_artifact_atomic_leaves_a_sibling_tmp_file_untouched(tmp_path: Path) -> None:
    from cogant._rust import write_artifact_atomic

    sibling = tmp_path / "notes.tmp"
    sibling.write_bytes(b"user data")

    write_artifact_atomic(str(tmp_path / "notes.md"), b"artifact")

    assert (tmp_path / "notes.md").read_bytes() == b"artifact"
    assert sibling.read_bytes() == b"user data"


def test_write_artifact_atomic_keeps_artifacts_sharing_a_stem_apart(tmp_path: Path) -> None:
    from cogant._rust import write_artifact_atomic

    write_artifact_atomic(str(tmp_path / "model.json"), b"{}")
    write_artifact_atomic(str(tmp_path / "model.md"), b"# model")

    assert sorted(p.name for p in tmp_path.iterdir()) == ["model.json", "model.md"]
    assert (tmp_path / "model.json").read_bytes() == b"{}"


def test_write_artifact_atomic_removes_its_temp_file_when_the_rename_fails(
    tmp_path: Path,
) -> None:
    from cogant._rust import write_artifact_atomic

    target = tmp_path / "out.json"
    target.mkdir()  # renaming a file over a directory fails

    with pytest.raises(OSError):
        write_artifact_atomic(str(target), b"{}")

    assert [p.name for p in tmp_path.iterdir()] == ["out.json"]


def test_connected_components_ignore_edges_to_unknown_nodes() -> None:
    from cogant._rust import connected_components

    components = connected_components(["a", "b"], [("a", "ghost"), ("ghost", "b")])

    assert components == [["a"], ["b"]]
