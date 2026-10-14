"""Coverage data annotates the nodes of a pipeline-built ProgramGraph.

The pipeline's graph stage (``run_graph``) stores repo-relative node paths,
while coverage.py records absolute file paths and Cobertura reports paths
relative to a source root. Enrichment must still attribute executed lines
to the right functions and methods, which also requires the graph stage
to record each callable's line span.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.api.bundle import Bundle
from cogant.api.orchestration import run_dynamic, run_graph, run_ingest
from cogant.dynamic.enrichment import enrich_graph
from cogant.schemas.core import Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

coverage = pytest.importorskip("coverage")

_MOD_SOURCE = (
    "def add(a, b):\n"  # 1
    "    return a + b\n"  # 2
    "\n"  # 3
    "\n"  # 4
    "class Calc:\n"  # 5
    "    def mul(self, a, b):\n"  # 6
    "        return a * b\n"  # 7
    "\n"  # 8
    "    def unused(self):\n"  # 9
    "        return 0\n"  # 10
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("")
    (repo / "pkg" / "mod.py").write_text(_MOD_SOURCE)
    return repo


def _graph_bundle(repo: Path) -> Bundle:
    bundle = Bundle(target=str(repo))
    run_ingest(str(repo), bundle)
    run_graph(bundle, str(repo))
    return bundle


def _callables(bundle: Bundle) -> dict[str, object]:
    pg = bundle.artifacts["_program_graph"]
    return {n.name: n for n in pg.nodes.values() if n.kind.value in ("function", "method")}


@pytest.mark.unit
def test_graph_stage_records_callable_line_spans(tmp_path: Path) -> None:
    """Functions and methods carry the parser's start/end lines."""
    nodes = _callables(_graph_bundle(_repo(tmp_path)))

    assert nodes["add"].source_range == {"start_line": 1, "end_line": 2}
    assert nodes["mul"].source_range == {"start_line": 6, "end_line": 7}
    assert nodes["unused"].source_range == {"start_line": 9, "end_line": 10}


@pytest.mark.unit
def test_absolute_coverage_py_paths_enrich_repo_relative_nodes(tmp_path: Path) -> None:
    """A real .coverage database with absolute paths enriches the executed callables."""
    repo = _repo(tmp_path)
    mod = str((repo / "pkg" / "mod.py").resolve())
    data = coverage.CoverageData(basename=str(repo / ".coverage"))
    data.add_lines({mod: [1, 2, 5, 6, 7, 9]})
    data.write()

    bundle = _graph_bundle(repo)
    summary = run_dynamic(bundle, coverage_path=str(repo / ".coverage"))
    nodes = _callables(bundle)

    assert summary["coverage_nodes_enriched"] >= 3
    assert nodes["add"].metadata["coverage_hits"] == 2
    assert nodes["mul"].metadata["coverage_hits"] == 2
    # Only the ``def`` line of ``unused`` executed (at class creation).
    assert nodes["unused"].metadata["coverage_hits"] == 1


@pytest.mark.unit
def test_source_root_relative_cobertura_paths_enrich_nodes(tmp_path: Path) -> None:
    """Cobertura filenames relative to a source root match by path suffix."""
    repo = _repo(tmp_path)
    xml = tmp_path / "coverage.xml"
    xml.write_text(
        '<?xml version="1.0" ?>\n'
        '<coverage line-rate="0.5" branch-rate="0">\n'
        '  <packages><package name="pkg"><classes>\n'
        '    <class name="mod.py" filename="mod.py" line-rate="0.5">\n'
        "      <lines>\n"
        '        <line number="1" hits="1"/>\n'
        '        <line number="2" hits="1"/>\n'
        '        <line number="7" hits="0"/>\n'
        "      </lines>\n"
        "    </class>\n"
        "  </classes></package></packages>\n"
        "</coverage>\n"
    )

    bundle = _graph_bundle(repo)
    run_dynamic(bundle, coverage_path=str(xml))
    nodes = _callables(bundle)

    assert nodes["add"].metadata["coverage_hits"] == 2
    assert "coverage_hits" not in nodes["unused"].metadata


@pytest.mark.unit
def test_exact_path_match_is_not_reused_for_a_suffix_match(tmp_path: Path) -> None:
    """Coverage for root ``mod.py`` never leaks onto ``pkg/mod.py`` by suffix."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri=tmp_path.as_uri()))
    for node_id, path in (("root", "mod.py"), ("nested", "pkg/mod.py")):
        graph.add_node(
            Node(
                id=node_id,
                kind=NodeKind.FUNCTION,
                name=node_id,
                qualified_name=node_id,
                path=path,
                source_range={"start_line": 1, "end_line": 5},
            )
        )
    xml = tmp_path / "coverage.xml"
    xml.write_text(
        '<?xml version="1.0" ?>\n<coverage><packages><package name="."><classes>\n'
        '<class name="mod.py" filename="mod.py"><lines>'
        '<line number="2" hits="1"/></lines></class>\n'
        "</classes></package></packages></coverage>\n"
    )

    summary = enrich_graph(graph, coverage_path=str(xml))

    assert summary["coverage_nodes_enriched"] == 1
    assert graph.nodes["root"].metadata["coverage_hits"] == 1
    assert "coverage_hits" not in graph.nodes["nested"].metadata
