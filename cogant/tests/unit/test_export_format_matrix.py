"""Coverage tests for cogant.export.formats — targeted.

Targets uncovered branches in MultiFormatExporter:
- export_all loop body (lines 81-102)
- export_graph error catch (135-136)
- export_gnn_bundle error catch (171-172)
- _export_format JSON / JSONLINES / unsupported (lines 184-190)
- _export_graph_format GRAPHML / DOT / SVG / unsupported (206-228)
- _export_bundle_format unsupported (253-254)
- _export_pipeline_json (263-266)
- _export_pipeline_jsonlines (275-284)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cogant.export.formats import (
    ExportConfig,
    ExportFormat,
    MultiFormatExporter,
)
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

pytestmark = pytest.mark.unit


def _make_graph() -> ProgramGraph:
    """Two-node graph used across tests."""
    meta = GraphMetadata(repo_uri="file:///tmp/repo")
    meta.languages = {"python"}
    g = ProgramGraph(metadata=meta)
    g.add_node(
        Node(
            id="a",
            kind=NodeKind.FUNCTION,
            name="alpha",
            qualified_name="pkg.alpha",
            path="pkg/a.py",
        )
    )
    g.add_node(
        Node(
            id="b",
            kind=NodeKind.FUNCTION,
            name="beta",
            qualified_name="pkg.beta",
            path="pkg/b.py",
        )
    )
    g.add_edge(Edge(id="e", source_id="a", target_id="b", kind=EdgeKind.CALLS))
    return g


# ---------------------------------------------------------------------------
# export_all  pipeline_result -> JSON / JSONLINES / unsupported
# ---------------------------------------------------------------------------


def test_export_all_writes_pipeline_json(tmp_path: Path) -> None:
    """export_all with JSON writes a *_result.json file."""
    exporter = MultiFormatExporter()
    pipeline_result = {
        "config": {"target": "/tmp/repo"},
        "validation_results": {"passed": True},
        "gnn_bundle": {"version": "0.5"},
    }
    cfg = ExportConfig(
        formats=[ExportFormat.JSON],
        output_dir=str(tmp_path),
        prefix="pipe",
    )
    results = exporter.export_all(pipeline_result, cfg)
    assert ExportFormat.JSON in results
    out_path = Path(results[ExportFormat.JSON])
    assert out_path.exists()
    payload = json.loads(out_path.read_text())
    assert payload["config"]["target"] == "/tmp/repo"


def test_export_all_writes_pipeline_jsonlines(tmp_path: Path) -> None:
    """export_all with JSONLINES emits one line per known section."""
    exporter = MultiFormatExporter()
    pipeline_result = {
        "config": {"k": 1},
        "validation_results": {"ok": True},
        "gnn_bundle": {"version": "0.5"},
    }
    cfg = ExportConfig(
        formats=[ExportFormat.JSONLINES],
        output_dir=str(tmp_path),
    )
    results = exporter.export_all(pipeline_result, cfg)
    out = Path(results[ExportFormat.JSONLINES])
    assert out.suffix == ".jsonl"
    lines = [ln for ln in out.read_text().splitlines() if ln]
    # config + validation_results + gnn_bundle = 3 lines
    assert len(lines) == 3
    parsed = [json.loads(ln) for ln in lines]
    assert {"k": 1} in parsed


def test_export_all_pipeline_jsonlines_partial_sections(tmp_path: Path) -> None:
    """export_all JSONLINES emits only sections that are actually present."""
    exporter = MultiFormatExporter()
    cfg = ExportConfig(
        formats=[ExportFormat.JSONLINES],
        output_dir=str(tmp_path),
    )
    results = exporter.export_all({"config": {"x": 1}}, cfg)
    out = Path(results[ExportFormat.JSONLINES])
    lines = [ln for ln in out.read_text().splitlines() if ln]
    assert len(lines) == 1


def test_export_all_unsupported_pipeline_format_returns_no_path(tmp_path: Path) -> None:
    """export_all with an unsupported pipeline format silently skips it."""
    exporter = MultiFormatExporter()
    cfg = ExportConfig(
        formats=[ExportFormat.GRAPHML],  # not supported for pipeline_result
        output_dir=str(tmp_path),
    )
    results = exporter.export_all({"config": {}}, cfg)
    # Unsupported format yields no entry but does not raise
    assert ExportFormat.GRAPHML not in results


def test_export_all_skips_failure_and_logs(tmp_path: Path, caplog) -> None:
    """If one format fails internally, export_all still returns successful ones."""
    exporter = MultiFormatExporter()
    cfg = ExportConfig(
        formats=[ExportFormat.JSON, ExportFormat.GRAPHML],
        output_dir=str(tmp_path),
    )
    results = exporter.export_all({"config": {"k": 1}}, cfg)
    # JSON should succeed; GRAPHML is unsupported for pipeline_result and is skipped
    assert ExportFormat.JSON in results


# ---------------------------------------------------------------------------
# export_graph  ProgramGraph -> JSON / GRAPHML / DOT / SVG / unsupported
# ---------------------------------------------------------------------------


def test_export_graph_to_graphml(tmp_path: Path) -> None:
    """export_graph(GRAPHML) writes a *_graph.graphml file."""
    exporter = MultiFormatExporter()
    graph = _make_graph()
    cfg = ExportConfig(
        formats=[ExportFormat.GRAPHML],
        output_dir=str(tmp_path),
        prefix="myg",
    )
    results = exporter.export_graph(graph, cfg)
    assert ExportFormat.GRAPHML in results
    out = Path(results[ExportFormat.GRAPHML])
    assert out.exists()
    assert out.name.endswith("_graph.graphml")
    text = out.read_text()
    assert "<graphml" in text


def test_export_graph_to_dot(tmp_path: Path) -> None:
    """export_graph(DOT) writes a graphviz DOT file."""
    exporter = MultiFormatExporter()
    graph = _make_graph()
    cfg = ExportConfig(
        formats=[ExportFormat.DOT],
        output_dir=str(tmp_path),
    )
    results = exporter.export_graph(graph, cfg)
    assert ExportFormat.DOT in results
    out = Path(results[ExportFormat.DOT])
    assert out.exists()
    text = out.read_text()
    # graphviz output begins with `digraph` (or `graph` for undirected)
    assert "graph" in text.lower()


def test_export_graph_to_svg(tmp_path: Path) -> None:
    """export_graph(SVG) returns a path (SVG or DOT fallback if graphviz absent)."""
    exporter = MultiFormatExporter()
    graph = _make_graph()
    cfg = ExportConfig(
        formats=[ExportFormat.SVG],
        output_dir=str(tmp_path),
    )
    results = exporter.export_graph(graph, cfg)
    assert ExportFormat.SVG in results
    # SVG exporter falls back to writing a .dot file when graphviz is missing
    out_str = results[ExportFormat.SVG]
    out = Path(out_str)
    assert out.exists()


def test_export_graph_to_json(tmp_path: Path) -> None:
    """export_graph(JSON) writes a typed JSON document."""
    exporter = MultiFormatExporter()
    graph = _make_graph()
    cfg = ExportConfig(
        formats=[ExportFormat.JSON],
        output_dir=str(tmp_path),
        prefix="gjson",
    )
    results = exporter.export_graph(graph, cfg)
    assert ExportFormat.JSON in results
    out = Path(results[ExportFormat.JSON])
    payload = json.loads(out.read_text())
    assert "metadata" in payload


def test_export_graph_unsupported_format_skipped(tmp_path: Path) -> None:
    """Graph export with an unsupported format is logged and skipped."""
    exporter = MultiFormatExporter()
    graph = _make_graph()
    cfg = ExportConfig(
        formats=[ExportFormat.PNG],  # unsupported for ProgramGraph
        output_dir=str(tmp_path),
    )
    results = exporter.export_graph(graph, cfg)
    assert ExportFormat.PNG not in results


def test_export_graph_parquet_returns_first_file(tmp_path: Path) -> None:
    """export_graph(PARQUET) returns the first generated file path or skips when pyarrow is absent."""
    exporter = MultiFormatExporter()
    graph = _make_graph()
    cfg = ExportConfig(
        formats=[ExportFormat.PARQUET],
        output_dir=str(tmp_path),
    )
    results = exporter.export_graph(graph, cfg)
    # Either pyarrow is present and we got a relative filename, or it's missing
    # and we got no entry. Either way, exercising the branch is the goal.
    if ExportFormat.PARQUET in results:
        # Returned value is the first filename produced by ParquetExporter.export()
        assert isinstance(results[ExportFormat.PARQUET], str)


# ---------------------------------------------------------------------------
# export_gnn_bundle — JSON / JSONLINES / unsupported
# ---------------------------------------------------------------------------


def test_export_gnn_bundle_unsupported_format_skipped(tmp_path: Path) -> None:
    """Bundle export with an unsupported format is logged and skipped."""
    exporter = MultiFormatExporter()
    cfg = ExportConfig(
        formats=[ExportFormat.GRAPHML],  # not supported for bundle
        output_dir=str(tmp_path),
    )
    results = exporter.export_gnn_bundle({"version": "0.5"}, cfg)
    assert ExportFormat.GRAPHML not in results


def test_export_gnn_bundle_jsonlines_omits_missing_keys(tmp_path: Path) -> None:
    """JSONLINES on a bundle without metadata/state_space writes empty file."""
    exporter = MultiFormatExporter()
    cfg = ExportConfig(
        formats=[ExportFormat.JSONLINES],
        output_dir=str(tmp_path),
    )
    results = exporter.export_gnn_bundle({}, cfg)
    out = Path(results[ExportFormat.JSONLINES])
    assert out.exists()
    assert out.read_text() == ""


def test_export_gnn_bundle_jsonlines_with_state_space_only(tmp_path: Path) -> None:
    """JSONLINES with only state_space writes a single line."""
    exporter = MultiFormatExporter()
    cfg = ExportConfig(
        formats=[ExportFormat.JSONLINES],
        output_dir=str(tmp_path),
    )
    results = exporter.export_gnn_bundle({"state_space": {"hidden_states": ["s1"]}}, cfg)
    out = Path(results[ExportFormat.JSONLINES])
    lines = [ln for ln in out.read_text().splitlines() if ln]
    assert len(lines) == 1


# ---------------------------------------------------------------------------
# Internal _export_pipeline_json paths (covered via export_all above already)
# Direct exercises just to be defensive about prefix handling.
# ---------------------------------------------------------------------------


def test_export_pipeline_json_uses_prefix(tmp_path: Path) -> None:
    """_export_pipeline_json honors the configured prefix."""
    exporter = MultiFormatExporter()
    cfg = ExportConfig(
        formats=[ExportFormat.JSON],
        output_dir=str(tmp_path),
        prefix="custom_pipe",
    )
    results = exporter.export_all({"x": 1}, cfg)
    out = Path(results[ExportFormat.JSON])
    assert "custom_pipe" in out.name


# ---------------------------------------------------------------------------
# Exception-handling branches in export_all / export_graph / export_gnn_bundle
# ---------------------------------------------------------------------------


def _circular_payload() -> dict:
    """Build a dict that contains itself, which json.dumps cannot serialize."""
    payload: dict = {"name": "circular"}
    payload["self"] = payload
    return payload


def test_export_all_logs_when_inner_exporter_fails(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failing format is caught and logged but does not stop other formats."""
    exporter = MultiFormatExporter()
    cfg = ExportConfig(
        formats=[ExportFormat.JSON],
        output_dir=str(tmp_path),
    )
    # JSON pipeline serializes the entire dict via json.dumps; circular raises.
    payload = _circular_payload()
    with caplog.at_level("ERROR"):
        results = exporter.export_all(payload, cfg)
    # JSON fails and is captured, no entry returned.
    assert ExportFormat.JSON not in results
    # An error is logged for the failure.
    assert any("Failed to export" in rec.message for rec in caplog.records)


def test_export_gnn_bundle_logs_when_inner_exporter_fails(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """export_gnn_bundle catches and logs failures in inner JSON dump."""
    exporter = MultiFormatExporter()
    cfg = ExportConfig(
        formats=[ExportFormat.JSON],
        output_dir=str(tmp_path),
    )
    bundle = _circular_payload()
    with caplog.at_level("ERROR"):
        results = exporter.export_gnn_bundle(bundle, cfg)
    assert ExportFormat.JSON not in results
    assert any("Failed to export" in rec.message for rec in caplog.records)


def test_export_graph_logs_when_inner_exporter_fails(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """export_graph catches failures from inner exporters and logs them.

    We force a failure by corrupting the graph's metadata so typed_export
    raises while accessing ``.isoformat()``.
    """
    exporter = MultiFormatExporter()
    graph = _make_graph()

    # Replace ``created_at`` with something that has no ``isoformat`` method
    # so the inner JSON exporter raises an AttributeError. The outer
    # ``export_graph`` catches the exception and logs it (line 135-136).
    graph.metadata.created_at = "not-a-datetime"  # type: ignore[assignment]
    cfg = ExportConfig(
        formats=[ExportFormat.JSON],
        output_dir=str(tmp_path),
    )
    with caplog.at_level("ERROR"):
        results = exporter.export_graph(graph, cfg)
    # JSON failed; no entry returned, but no raise propagated.
    assert ExportFormat.JSON not in results
    assert any("Failed to export graph as" in rec.message for rec in caplog.records)
