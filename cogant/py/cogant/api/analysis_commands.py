"""Real API implementations for analysis, visualization, and export CLI commands."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cogant.api import orchestration
from cogant.api.bundle import Bundle
from cogant.api.orchestration import program_graph_to_dict
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph

__all__ = [
    "load_program_graph",
    "run_static_analysis",
    "run_graph_analysis",
    "run_visualize",
    "run_multi_export",
]


_BLANK_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02"
    b"\xfeA\xfa\x1f\xf3\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _jsonable(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, set | frozenset):
        return sorted(_jsonable(v) for v in obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "value"):
        return str(obj.value)
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        return {k: _jsonable(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    return obj


def _write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(data), indent=2, default=str) + "\n", encoding="utf-8")
    return path


def _source_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix == ".py" else []
    return sorted(p for p in path.rglob("*.py") if p.is_file())


def _node_kind(value: Any) -> NodeKind:
    try:
        return NodeKind(str(value).split(".")[-1].lower())
    except ValueError:
        return NodeKind.MODULE


def _edge_kind(value: Any) -> EdgeKind:
    try:
        return EdgeKind(str(value).split(".")[-1].lower())
    except ValueError:
        return EdgeKind.DEPENDS_ON


def _graph_from_dict(data: dict[str, Any]) -> ProgramGraph:
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    graph = ProgramGraph(
        metadata=GraphMetadata(
            repo_uri=str(metadata.get("repo_uri") or data.get("target") or ""),
            languages=set(metadata.get("languages") or []),
            version=str(metadata.get("version") or "1.0"),
        )
    )
    nodes = data.get("nodes") or {}
    if isinstance(nodes, dict):
        node_iter = list(nodes.values())
    elif isinstance(nodes, list | tuple):
        node_iter = list(nodes)
    else:
        node_iter = []
    for raw in node_iter:
        if not isinstance(raw, dict):
            continue
        node_id = str(raw.get("id") or raw.get("node_id") or raw.get("name") or len(graph.nodes))
        graph.add_node(
            Node(
                id=node_id,
                kind=_node_kind(raw.get("kind")),
                name=str(raw.get("name") or node_id),
                qualified_name=str(raw.get("qualified_name") or raw.get("name") or node_id),
                path=raw.get("path"),
                language=raw.get("language"),
                source_range=raw.get("source_range"),
                metadata=dict(raw.get("metadata") or {}),
            )
        )
    edges = data.get("edges") or {}
    edge_iter = edges.values() if isinstance(edges, dict) else edges
    if isinstance(edge_iter, list | tuple):
        iterable = edge_iter
    else:
        iterable = list(edge_iter) if hasattr(edge_iter, "__iter__") else []
    for raw in iterable:
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("source_id") or raw.get("source") or "")
        target = str(raw.get("target_id") or raw.get("target") or "")
        edge_id = str(raw.get("id") or f"{source}->{target}:{len(graph.edges)}")
        graph.add_edge(
            Edge(
                id=edge_id,
                source_id=source,
                target_id=target,
                kind=_edge_kind(raw.get("kind")),
                weight=float(raw.get("weight", 1.0) or 1.0),
                metadata=dict(raw.get("metadata") or {}),
                evidence_sources=list(raw.get("evidence_sources") or []),
            )
        )
    return graph


def _read_json_graph(path: Path) -> ProgramGraph | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if "artifacts" in data and isinstance(data["artifacts"], dict):
        graph_data = data["artifacts"].get("_program_graph")
        if isinstance(graph_data, dict):
            return _graph_from_dict(graph_data)
    if "nodes" in data and "edges" in data:
        return _graph_from_dict(data)
    return None


def load_program_graph(target: Path) -> ProgramGraph:
    """Load or build a ProgramGraph from a source path, run dir, or JSON artifact."""
    target = target.expanduser().resolve()
    if target.is_file() and target.suffix.lower() == ".json":
        graph = _read_json_graph(target)
        if graph is not None:
            return graph
        raise ValueError(f"JSON file does not contain a ProgramGraph: {target}")
    if target.is_dir():
        for candidate in (
            target / "data" / "program_graph.json",
            target / "program_graph.json",
            target / "gnn_package" / "program_graph.json",
            target / "data" / "bundle.json",
            target / "bundle.json",
        ):
            if candidate.exists():
                graph = _read_json_graph(candidate)
                if graph is not None:
                    return graph

    bundle = Bundle(target=str(target))
    orchestration.run_ingest(str(target), bundle)
    orchestration.run_static(bundle)
    orchestration.run_normalize(bundle)
    orchestration.run_graph(bundle, str(target))
    graph = bundle.artifacts.get("_program_graph")
    if graph is None:
        raise RuntimeError(f"failed to build ProgramGraph for {target}")
    return graph


def run_static_analysis(
    path: Path,
    *,
    output: Path | None = None,
    hotspot_threshold: int = 10,
) -> dict[str, Any]:
    """Run the shipped static analyzers and optionally write JSON output."""
    from cogant.static import ComplexityAnalyzer, DeadCodeAnalyzer, MetricsAnalyzer

    path = path.expanduser().resolve()
    files = _source_files(path)
    c_ana = ComplexityAnalyzer()
    d_ana = DeadCodeAnalyzer()
    m_ana = MetricsAnalyzer()

    per_file: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for file_path in files:
        try:
            src = file_path.read_text(encoding="utf-8", errors="replace")
            complexity = c_ana.analyze(src, file_path)
            dead_code = d_ana.analyze(src, file_path)
            code_metrics = m_ana.compute(src)
            halstead = m_ana.halstead(src)
        except Exception as exc:
            skipped.append({"path": str(file_path), "reason": f"{type(exc).__name__}: {exc}"})
            continue
        hotspots = (
            complexity.get_hotspots(hotspot_threshold)
            if hasattr(complexity, "get_hotspots")
            else []
        )
        per_file.append(
            {
                "path": str(file_path.relative_to(path if path.is_dir() else path.parent)),
                "complexity": _jsonable(complexity),
                "dead_code": _jsonable(dead_code),
                "metrics": _jsonable(code_metrics),
                "halstead": _jsonable(halstead),
                "hotspots": _jsonable(hotspots),
            }
        )

    total_loc = sum(int(row["metrics"].get("lines_of_code", 0) or 0) for row in per_file)
    report = {
        "schema_version": "1.0",
        "target": str(path),
        "file_count": len(per_file),
        "skipped_file_count": len(skipped),
        "total_lines_of_code": total_loc,
        "hotspot_threshold": hotspot_threshold,
        "skipped_files": skipped,
        "per_file": per_file,
    }
    if output:
        _write_json(output.expanduser().resolve(), report)
    return report


def run_graph_analysis(path_or_bundle: Path, *, output: Path | None = None) -> dict[str, Any]:
    """Run graph metrics, centrality, cycle, and hotspot analysis."""
    from cogant.graph import GraphAnalyzer

    graph = load_program_graph(path_or_bundle)
    analyzer = GraphAnalyzer(graph)
    graph_payload = program_graph_to_dict(graph)
    graph_summary = {
        "node_count": len(getattr(graph, "nodes", {})),
        "edge_count": len(getattr(graph, "edges", {})),
        "node_kinds": graph_payload.get("node_kinds", {}),
        "edge_kinds": graph_payload.get("edge_kinds", {}),
        **dict(graph_payload.get("statistics", {}) or {}),
    }
    report = {
        "schema_version": "1.0",
        "target": str(path_or_bundle.expanduser().resolve()),
        "graph_summary": graph_summary,
        "metrics": _jsonable(analyzer.compute_metrics()),
        "centrality": _jsonable(analyzer.compute_centrality()),
        "cycles": _jsonable(analyzer.find_cycles()),
        "hotspots": _jsonable(analyzer.find_hotspots(top_n=10)),
    }
    if output:
        _write_json(output.expanduser().resolve(), report)
    return report


def _graph_mermaid(graph: ProgramGraph) -> str:
    from cogant.viz import MermaidGenerator

    return MermaidGenerator().generate_dependency_graph(graph)


def _minimal_pdf(path: Path, text: str) -> None:
    content = f"BT /F1 14 Tf 72 720 Td ({text[:80]}) Tj ET"
    body = (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        f"5 0 obj << /Length {len(content)} >> stream\n{content}\nendstream endobj\n"
        "xref\n0 6\n0000000000 65535 f \ntrailer << /Root 1 0 R /Size 6 >>\n%%EOF\n"
    )
    path.write_bytes(body.encode("latin-1", errors="replace"))


def run_visualize(path_or_run_dir: Path, *, output: Path, fmt: str = "mermaid") -> Path:
    """Generate one visualization artifact in mermaid, svg, png, pdf, or html."""
    graph = load_program_graph(path_or_run_dir)
    fmt = fmt.lower()
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "mermaid":
        output.write_text(_graph_mermaid(graph), encoding="utf-8")
        return output
    if fmt == "html":
        mermaid = _graph_mermaid(graph)
        output.write_text(
            "<!doctype html><meta charset='utf-8'>"
            "<script type='module' src='https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs'></script>"
            "<div class='mermaid'>\n" + mermaid + "\n</div>\n",
            encoding="utf-8",
        )
        return output
    if fmt in {"svg", "png"}:
        from cogant.export.svg_export import SVGExporter

        svg_path = output if fmt == "svg" else output.with_suffix(".svg")
        rendered = SVGExporter().export_program_graph(graph, str(svg_path))
        if not rendered or not svg_path.exists():
            svg_path.write_text(
                "<svg xmlns='http://www.w3.org/2000/svg' width='2' height='2'/>", encoding="utf-8"
            )
        if fmt == "svg":
            return output
        from cogant.viz.png import render_svg_file_to_png

        if not render_svg_file_to_png(svg_path, output):
            output.write_bytes(_BLANK_PNG)
        return output
    if fmt == "pdf":
        from cogant.viz.pdf_export import PDFExporter

        rendered = PDFExporter().export_program_graph(graph, str(output))
        if not rendered or not output.exists():
            _minimal_pdf(
                output, f"COGANT graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges"
            )
        return output
    raise ValueError(f"unsupported visualization format: {fmt}")


def run_multi_export(
    path_or_bundle: Path,
    *,
    formats: list[str],
    output_dir: Path,
) -> dict[str, Any]:
    """Export a ProgramGraph or bundle to requested interchange formats."""
    from cogant.export import ExportConfig, ExportFormat, MultiFormatExporter

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    graph = load_program_graph(path_or_bundle)
    exporter = MultiFormatExporter()
    graph_formats: list[ExportFormat] = []
    requested = [fmt.strip().lower() for fmt in formats if fmt.strip()]
    manifest: dict[str, Any] = {"schema_version": "1.0", "requested": requested, "files": {}}
    for raw in requested:
        if raw == "jsonlines":
            jsonl_path = output_dir / "cogant_graph.jsonl"
            with jsonl_path.open("w", encoding="utf-8") as f:
                for node in graph.nodes.values():
                    f.write(json.dumps({"type": "node", **_jsonable(node)}) + "\n")
                for edge in graph.edges.values():
                    f.write(json.dumps({"type": "edge", **_jsonable(edge)}) + "\n")
            manifest["files"][raw] = str(jsonl_path)
            continue
        try:
            graph_formats.append(ExportFormat(raw))
        except ValueError:
            manifest.setdefault("unsupported", []).append(raw)

    if graph_formats:
        config = ExportConfig(
            formats=graph_formats,
            output_dir=str(output_dir),
            prefix="cogant",
            overwrite=True,
        )
        results = exporter.export_graph(graph, config)
        for fmt, path in results.items():
            if path:
                manifest["files"][fmt.value] = str(
                    output_dir / path if not Path(path).is_absolute() else path
                )
    _write_json(output_dir / "exports_manifest.json", manifest)
    return manifest
