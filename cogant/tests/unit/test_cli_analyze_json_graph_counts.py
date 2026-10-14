"""``cogant analyze --format json`` reports the real graph size.

The graph stage result stores its counts under ``statistics`` and its
``nodes``/``edges`` as id-keyed dicts; the JSON summary must not read
non-existent ``node_count``/``edge_count`` keys and report zero.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cogant.cli.main import app


def test_analyze_json_summary_reports_graph_node_and_edge_counts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "counter.py").write_text(
        "class Counter:\n"
        "    def __init__(self):\n"
        "        self.n = 0\n"
        "    def inc(self):\n"
        "        self.n += 1\n"
        "    def get(self):\n"
        "        return self.n\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"

    result = CliRunner().invoke(
        app, ["analyze", str(repo), "-o", str(out), "--no-dynamic", "--format", "json"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output[result.output.index("{") :])
    graph = json.loads((out / "program_graph.json").read_text(encoding="utf-8"))
    bundle = json.loads((out / "bundle.json").read_text(encoding="utf-8"))
    statistics = bundle["stage_results"]["graph"]["statistics"]

    assert payload["node_count"] == len(graph["nodes"]) == statistics["total_nodes"] > 0
    assert payload["edge_count"] == len(graph["edges"]) == statistics["total_edges"] > 0
    assert payload["mapping_count"] == bundle["stage_results"]["translate"]["mapping_count"] > 0
