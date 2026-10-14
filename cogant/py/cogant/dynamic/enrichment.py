"""Enrich a ProgramGraph with runtime coverage and trace data.

This module wires CoverageIngester and TraceIngester into the COGANT
pipeline, mapping dynamic observations onto existing graph nodes and
adding dynamic CALLS edges derived from trace call-graphs.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import url2pathname

from cogant.dynamic.coverage import CoverageIngester
from cogant.dynamic.traces import TraceIngester
from cogant.schemas.core import Edge, EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)

# Node kinds that represent callable entities.
_CALLABLE_KINDS = frozenset(
    {
        NodeKind.FUNCTION,
        NodeKind.METHOD,
    }
)


def _normalize_path(raw: str) -> str:
    """Return a canonical path string for matching.

    Strips leading ``./`` and converts backslashes to forward slashes so
    that coverage paths and graph node paths can be compared. Case is
    preserved.
    """
    p = raw.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def _graph_repo_root(graph: ProgramGraph) -> str | None:
    """Return the normalised local repository root of *graph*, if known.

    The pipeline stamps ``metadata.repo_uri`` with a ``file://`` URI for
    local targets; any other scheme yields ``None``.
    """
    repo_uri = getattr(getattr(graph, "metadata", None), "repo_uri", None)
    if not isinstance(repo_uri, str):
        return None
    parsed = urlparse(repo_uri)
    if parsed.scheme != "file" or not parsed.path:
        return None
    return _normalize_path(url2pathname(parsed.path)).rstrip("/")


def _match_key(raw: str, repo_root: str | None) -> str:
    """Normalise *raw* and make it repo-relative when it lies under *repo_root*.

    coverage.py records absolute file paths while graph nodes carry
    repo-relative ones; stripping the root lets both meet on one key.
    """
    p = _normalize_path(raw)
    if repo_root and p.startswith(repo_root + "/"):
        return p[len(repo_root) + 1 :]
    return p


def _is_path_suffix(longer: str, shorter: str) -> bool:
    """Return True if *shorter* equals the trailing path components of *longer*."""
    return longer.endswith("/" + shorter)


def _resolve_coverage_files(node_keys: set[str], coverage_keys: set[str]) -> dict[str, str]:
    """Map graph node path keys to coverage file keys.

    Exact matches win. Remaining node paths fall back to a whole-component
    suffix match in either direction (Cobertura reports paths relative to
    a source root, which may sit above or below the repository root). A
    suffix match is used only when it is unambiguous on both sides and the
    coverage file is not already claimed by an exact match.
    """
    resolved = {key: key for key in node_keys if key in coverage_keys}
    claimed = set(resolved.values())
    open_coverage = [ck for ck in coverage_keys if ck not in claimed]

    suffix_owners: dict[str, list[str]] = {}
    for node_key in node_keys - resolved.keys():
        candidates = [
            ck
            for ck in open_coverage
            if _is_path_suffix(ck, node_key) or _is_path_suffix(node_key, ck)
        ]
        if len(candidates) == 1:
            suffix_owners.setdefault(candidates[0], []).append(node_key)
    for coverage_key, owners in suffix_owners.items():
        if len(owners) == 1:
            resolved[owners[0]] = coverage_key
    return resolved


def _node_spans_line(node: Any, line: int) -> bool:
    """Return True if *node* covers *line* according to its source_range."""
    sr = node.source_range
    if not sr:
        return False
    start = sr.get("start_line") or sr.get("start", {}).get("line")
    end = sr.get("end_line") or sr.get("end", {}).get("line")
    if start is None or end is None:
        return False
    return int(start) <= line <= int(end)


def _stable_edge_id(source_id: str, target_id: str, kind: str) -> str:
    """Generate a deterministic edge ID."""
    raw = f"{source_id}|{target_id}|{kind}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ------------------------------------------------------------------
# Coverage enrichment
# ------------------------------------------------------------------


def _enrich_with_coverage(
    graph: ProgramGraph,
    coverage_path: str,
) -> int:
    """Parse coverage data and annotate matching graph nodes.

    For each file in the coverage report, nodes whose ``path`` matches
    the coverage filename *and* whose ``source_range`` overlaps a
    covered line receive:

    * ``coverage_hits``   -- number of covered lines inside the node
    * ``branch_coverage`` -- branch coverage rate (0.0-1.0) when the
      coverage format provides branch data, else ``None``

    Args:
        graph: The ProgramGraph to enrich (mutated in place).
        coverage_path: Filesystem path to a ``.coverage`` SQLite DB or
            a Cobertura ``coverage.xml``.

    Returns:
        Number of nodes that were enriched.
    """
    ingester = CoverageIngester()

    path_obj = Path(coverage_path)
    suffix = path_obj.suffix.lower()

    if suffix == ".xml":
        ingester.ingest_coverage_xml(coverage_path)
    else:
        # Default: treat as coverage.py SQLite database
        ingester.ingest_coverage_py(coverage_path)

    spans = ingester.map_coverage_to_spans()
    if not spans:
        logger.info("No coverage spans found; skipping coverage enrichment")
        return 0

    # Group spans by normalised, repo-relative file path for fast lookup.
    repo_root = _graph_repo_root(graph)
    file_spans: dict[str, list[dict[str, Any]]] = {}
    for span in spans:
        key = _match_key(str(span["file"] or ""), repo_root)
        file_spans.setdefault(key, []).append(span)

    node_keys = {_match_key(node.path, repo_root) for node in graph.nodes.values() if node.path}
    coverage_file_for = _resolve_coverage_files(node_keys, set(file_spans))

    enriched_count = 0

    for node in graph.nodes.values():
        node_path = node.path
        if not node_path:
            continue

        coverage_key = coverage_file_for.get(_match_key(node_path, repo_root))
        if coverage_key is None:
            continue
        matched_spans = file_spans[coverage_key]

        hits = 0
        branch_total = 0
        branch_covered = 0

        for span in matched_spans:
            line = span["start_line"]
            if not _node_spans_line(node, line):
                continue

            if span.get("covered"):
                hits += 1

            if span.get("is_branch"):
                branch_total += 1
                if span.get("branch_hits", 0) > 0:
                    branch_covered += 1

        if hits > 0 or branch_total > 0:
            node.metadata["coverage_hits"] = hits
            if branch_total > 0:
                node.metadata["branch_coverage"] = branch_covered / branch_total
            else:
                node.metadata["branch_coverage"] = None
            enriched_count += 1

    if not coverage_file_for:
        logger.warning(
            "Coverage data for %d file(s) matched no graph node path; "
            "no node was annotated with coverage",
            len(file_spans),
        )
    elif enriched_count == 0:
        logger.warning(
            "Coverage files matched %d graph path(s) but no node line span "
            "contained a measured line; nodes need source_range line numbers",
            len(coverage_file_for),
        )
    logger.info("Coverage enrichment annotated %d nodes", enriched_count)
    return enriched_count


# ------------------------------------------------------------------
# Trace enrichment
# ------------------------------------------------------------------


def _build_function_index(graph: ProgramGraph) -> dict[str, list[str]]:
    """Map unqualified and qualified function names to node IDs.

    Returns a dict where each key is a name (or qualified_name) and the
    value is a list of node IDs that match.  This allows trace event
    names -- which are typically unqualified -- to be resolved to graph
    nodes.
    """
    index: dict[str, list[str]] = {}
    for node in graph.nodes.values():
        if node.kind not in _CALLABLE_KINDS:
            continue
        index.setdefault(node.name, []).append(node.id)
        if node.qualified_name and node.qualified_name != node.name:
            index.setdefault(node.qualified_name, []).append(node.id)
    return index


def _enrich_with_traces(
    graph: ProgramGraph,
    trace_path: str,
) -> int:
    """Parse trace data and annotate matching graph nodes and edges.

    For each function observed in the trace:

    * Matching nodes receive ``call_count``, ``avg_duration_ms``, and
      ``is_hot_path`` metadata.
    * For each caller -> callee pair in the extracted call-graph, a
      dynamic ``CALLS`` edge is added (or its weight updated) with
      ``evidence_sources=["dynamic_trace"]``.

    Args:
        graph: The ProgramGraph to enrich (mutated in place).
        trace_path: Filesystem path to a Chrome DevTools trace JSON.

    Returns:
        Number of nodes that were enriched.
    """
    ingester = TraceIngester()
    ingester.ingest_chrome_trace(trace_path)

    # -- timing metadata -------------------------------------------
    timing = ingester.extract_timing()  # name -> {min, max, mean, count}
    func_index = _build_function_index(graph)

    # Determine hot-path threshold: top 10% by total time (count * mean).
    # A function is "hot" if its total time >= threshold.
    hot_threshold = 0.0
    if timing:
        totals = sorted(
            (stats["mean"] * stats["count"] for stats in timing.values()),
            reverse=True,
        )
        if totals:
            # Index of the last entry in the top 10% (inclusive).
            cutoff_idx = min(len(totals) - 1, max(0, len(totals) // 10 - 1))
            hot_threshold = totals[cutoff_idx]

    enriched_ids: set[str] = set()

    for func_name, stats in timing.items():
        node_ids = func_index.get(func_name, [])
        if not node_ids:
            continue

        call_count = int(stats["count"])
        avg_duration = stats["mean"]
        total_time = avg_duration * call_count
        is_hot = total_time >= hot_threshold

        for nid in node_ids:
            node = graph.get_node(nid)
            if node is None:
                continue
            node.metadata["call_count"] = call_count
            node.metadata["avg_duration_ms"] = round(avg_duration, 4)
            node.metadata["is_hot_path"] = is_hot
            enriched_ids.add(nid)

    # -- dynamic CALLS edges ---------------------------------------
    call_graph = ingester.extract_call_graph()  # caller -> [callee, ...]
    edges_added = 0

    # Build a call-count map from timing for edge weights.
    call_counts: dict[str, int] = {}
    for name, stats in timing.items():
        call_counts[name] = int(stats["count"])

    for caller_name, callees in call_graph.items():
        caller_ids = func_index.get(caller_name, [])
        if not caller_ids:
            continue

        for callee_name in callees:
            callee_ids = func_index.get(callee_name, [])
            if not callee_ids:
                continue

            weight = float(call_counts.get(callee_name, 1))

            for src_id in caller_ids:
                for tgt_id in callee_ids:
                    edge_id = _stable_edge_id(src_id, tgt_id, EdgeKind.CALLS.value)
                    existing = graph.edges.get(edge_id)
                    if existing:
                        existing.weight = max(existing.weight, weight)
                        if "dynamic_trace" not in existing.evidence_sources:
                            existing.evidence_sources.append("dynamic_trace")
                    else:
                        edge = Edge(
                            id=edge_id,
                            source_id=src_id,
                            target_id=tgt_id,
                            kind=EdgeKind.CALLS,
                            weight=weight,
                            metadata={"source": "dynamic_trace"},
                            evidence_sources=["dynamic_trace"],
                        )
                        graph.add_edge(edge)
                        edges_added += 1

    logger.info(
        "Trace enrichment annotated %d nodes, added %d dynamic edges",
        len(enriched_ids),
        edges_added,
    )
    return len(enriched_ids)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def enrich_graph(
    graph: ProgramGraph,
    coverage_path: str | None = None,
    trace_path: str | None = None,
) -> dict[str, Any]:
    """Enrich a ProgramGraph with runtime coverage and trace data.

    This is the main entry point for dynamic analysis integration.
    Either or both data sources may be provided; when a path is
    ``None`` the corresponding enrichment step is skipped.

    Args:
        graph: The ProgramGraph to enrich (mutated in place).
        coverage_path: Optional path to a ``.coverage`` SQLite DB or
            Cobertura ``coverage.xml``.
        trace_path: Optional path to a Chrome DevTools trace JSON file.

    Returns:
        Summary dict with keys ``coverage_nodes_enriched``,
        ``trace_nodes_enriched``, ``evidence_sources`` (list of
        evidence markers added to the graph metadata), and
        ``graph`` (the same ``ProgramGraph`` instance, returned for
        functional-style composition even though mutation is in-place).
    """
    summary: dict[str, Any] = {
        "coverage_nodes_enriched": 0,
        "trace_nodes_enriched": 0,
        "evidence_sources": [],
        "graph": graph,
    }

    if coverage_path is not None:
        logger.info("Enriching graph with coverage data from %s", coverage_path)
        summary["coverage_nodes_enriched"] = _enrich_with_coverage(
            graph,
            coverage_path,
        )

    if trace_path is not None:
        logger.info("Enriching graph with trace data from %s", trace_path)
        summary["trace_nodes_enriched"] = _enrich_with_traces(
            graph,
            trace_path,
        )

    # Record evidence sources on the graph metadata.
    if coverage_path is not None and "dynamic_coverage" not in graph.metadata.evidence_sources:
        graph.metadata.evidence_sources.append("dynamic_coverage")
        summary["evidence_sources"].append("dynamic_coverage")
    if trace_path is not None and "dynamic_trace" not in graph.metadata.evidence_sources:
        graph.metadata.evidence_sources.append("dynamic_trace")
        summary["evidence_sources"].append("dynamic_trace")

    return summary
