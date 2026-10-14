"""Diff CLI command: Compare two output bundles and generate diff reports.

``cogant translate`` / ``cogant analyze`` write their artifacts either flat
in the run directory or, with ``--layout-output``, under ``data/``; the GNN
package always lives in ``gnn_package/``. :func:`load_bundle` looks in all
three places, and :func:`diff_command` normalizes the persisted shapes
(id-keyed graph collections, the compiler's id-keyed state space) into the
list-of-records shape consumed by :class:`cogant.scoring.drift.DriftAnalyzer`
and :class:`cogant.scoring.metrics.CodebaseMetrics`.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Sub-directories that may hold run artifacts, in lookup order: the flat
# layout, the ``--layout-output`` layout, then the GNN package.
_ARTIFACT_SUBDIRS: tuple[str, ...] = ("", "data", "gnn_package")


def _find_artifact(output_dir: Path, name: str) -> Path | None:
    for subdir in _ARTIFACT_SUBDIRS:
        candidate = output_dir / subdir / name if subdir else output_dir / name
        if candidate.is_file():
            return candidate
    return None


def _read_json(path: Path) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Skipping unreadable artifact %s: %s", path, exc)
        return None


def _mapping_index(mappings_data: Any, id_keys: tuple[str, ...]) -> dict[Any, Any]:
    """Key a list of mapping records by the first present id field."""
    if isinstance(mappings_data, dict):
        return mappings_data
    if isinstance(mappings_data, list):
        index: dict[Any, Any] = {}
        for item in mappings_data:
            if not isinstance(item, dict):
                continue
            key = next((item[k] for k in id_keys if item.get(k) is not None), None)
            index[key] = item
        return index
    return {}


def load_bundle(output_dir: Path) -> dict[str, Any]:
    """Load a bundle from an output directory.

    Each artifact is looked up flat in ``output_dir``, then under ``data/``
    (``--layout-output``), then under ``gnn_package/``:

    * ``graph`` from ``program_graph.json``.
    * ``state_space`` from ``state_space.json``, falling back to the
      ``state_space`` section of ``model.gnn.json``.
    * ``mappings`` from ``semantic_mappings.json``, falling back to the
      ``mappings`` section of ``model.gnn.json`` and then to the
      ``mappings`` list of ``rule_evidence_trace.json``.

    Payloads are returned as persisted; :func:`diff_command` normalizes them
    for scoring.

    Args:
        output_dir: Directory containing output artifacts.

    Returns:
        Bundle dict with 'graph', 'state_space', 'mappings' keys (each only
        when a source artifact was found).
    """
    bundle: dict[str, Any] = {}

    graph_path = _find_artifact(output_dir, "program_graph.json")
    if graph_path is not None:
        graph = _read_json(graph_path)
        if isinstance(graph, dict):
            bundle["graph"] = graph
            logger.info("Loaded graph from %s", graph_path)

    gnn_path = _find_artifact(output_dir, "model.gnn.json")
    gnn_data = _read_json(gnn_path) if gnn_path is not None else None
    if not isinstance(gnn_data, dict):
        gnn_data = {}

    state_space_path = _find_artifact(output_dir, "state_space.json")
    state_space = _read_json(state_space_path) if state_space_path is not None else None
    if isinstance(state_space, dict):
        bundle["state_space"] = state_space
        logger.info("Loaded state space from %s", state_space_path)
    elif isinstance(gnn_data.get("state_space"), dict):
        bundle["state_space"] = gnn_data["state_space"]
        logger.info("Loaded state space from %s", gnn_path)

    mappings_path = _find_artifact(output_dir, "semantic_mappings.json")
    mappings_data = _read_json(mappings_path) if mappings_path is not None else None
    if isinstance(mappings_data, (dict, list)):
        bundle["mappings"] = _mapping_index(mappings_data, ("id", "mapping_id"))
        logger.info("Loaded mappings from %s", mappings_path)
    elif isinstance(gnn_data.get("mappings"), dict) and "mappings" in gnn_data["mappings"]:
        bundle["mappings"] = _mapping_index(gnn_data["mappings"]["mappings"], ("id", "mapping_id"))
        logger.info("Loaded mappings from %s", gnn_path)
    else:
        trace_path = _find_artifact(output_dir, "rule_evidence_trace.json")
        trace = _read_json(trace_path) if trace_path is not None else None
        if isinstance(trace, dict) and isinstance(trace.get("mappings"), list):
            bundle["mappings"] = _mapping_index(trace["mappings"], ("mapping_id", "id"))
            logger.info("Loaded mappings from %s", trace_path)

    return bundle


# Per-run wall-clock stamps. They differ between two runs of the same code,
# so they are dropped before records are compared for "changed" drift.
_VOLATILE_KEYS = frozenset({"created_at", "generated_at", "timestamp"})


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_volatile(v) for k, v in value.items() if k not in _VOLATILE_KEYS}
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


def _records(collection: Any, id_key: str) -> list[dict[str, Any]]:
    """Return ``collection`` as a list of dicts that each carry ``id_key``.

    Persisted artifacts key their records by id (``{id: payload}``); the
    scorers expect a list. Payloads keep every original field except
    per-run timestamps, and the record's ``id`` (or its dict key) is copied
    into ``id_key``.
    """
    if isinstance(collection, dict):
        items = [
            {**_strip_volatile(value), "id": value.get("id", key)}
            for key, value in collection.items()
            if isinstance(value, dict)
        ]
    elif isinstance(collection, list):
        items = [_strip_volatile(item) for item in collection if isinstance(item, dict)]
    else:
        return []
    for item in items:
        if item.get(id_key) is None and item.get("id") is not None:
            item[id_key] = item["id"]
    return items


def _scoring_graph(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = _records(graph.get("nodes"), "id")
    edges = _records(graph.get("edges"), "id")
    for edge in edges:
        # ProgramGraph edges persist ``source_id``/``target_id``; the
        # scorers read ``source``/``target``.
        if edge.get("source") is None and edge.get("source_id") is not None:
            edge["source"] = edge["source_id"]
        if edge.get("target") is None and edge.get("target_id") is not None:
            edge["target"] = edge["target_id"]
    return {**graph, "nodes": nodes, "edges": edges}


def _scoring_state_space(state_space: dict[str, Any]) -> dict[str, Any]:
    """Map a persisted state space onto the scorers' list-based shape.

    The compiler's ``state_space.json`` stores ``variables``,
    ``observations`` and ``actions`` as id-keyed dicts. The scorers expect
    ``states`` (``var_id``), ``observations`` (``modality_id``) and
    ``actions`` (``action_id``) lists. An action's ``affects_state_vars``
    is derived from the variables its transitions write when the payload
    does not already list them.
    """
    states_source = state_space.get("states", state_space.get("variables"))
    states = _records(states_source, "var_id")
    observations = _records(state_space.get("observations"), "modality_id")
    actions = _records(state_space.get("actions"), "action_id")

    affected: dict[str, list[str]] = {}
    for transition in _records(state_space.get("transitions"), "id"):
        action_id = transition.get("action_id")
        target_state = transition.get("target_state")
        if action_id is None or not isinstance(target_state, dict):
            continue
        bucket = affected.setdefault(str(action_id), [])
        for var_id in target_state:
            if var_id not in bucket:
                bucket.append(var_id)
    for action in actions:
        if "affects_state_vars" not in action:
            action["affects_state_vars"] = affected.get(str(action.get("action_id")), [])

    return {**state_space, "states": states, "observations": observations, "actions": actions}


def _mapped_node_index(mappings: dict[Any, Any]) -> dict[str, list[Any]]:
    """Index mappings by the graph node ids they cover.

    :meth:`CodebaseMetrics.semantic_coverage` counts a node as covered when
    its id is a key of the mappings dict, while persisted mappings are keyed
    by mapping id and list their node ids separately.
    """
    # Keep the original keys too: older ``semantic_mappings.json`` files were
    # keyed by node id. Mapping ids never collide with node ids.
    index: dict[str, list[Any]] = {str(key): [key] for key in mappings}
    for mapping_id, mapping in mappings.items():
        if not isinstance(mapping, dict):
            continue
        node_ids = (
            mapping.get("graph_fragment_node_ids")
            or mapping.get("matched_node_ids")
            or mapping.get("node_ids")
            or []
        )
        for node_id in node_ids:
            index.setdefault(str(node_id), []).append(mapping_id)
    return index


def diff_command(output_dir_a: str, output_dir_b: str) -> str:
    """Compare two output directories and generate diff report.

    Args:
        output_dir_a: Path to baseline output directory.
        output_dir_b: Path to current output directory.

    Returns:
        Markdown diff report.
    """
    from cogant.scoring.drift import DriftAnalyzer
    from cogant.scoring.metrics import CodebaseMetrics

    # Load bundles
    path_a = Path(output_dir_a).resolve()
    path_b = Path(output_dir_b).resolve()

    logger.info("Loading baseline bundle from %s", path_a)
    bundle_a = load_bundle(path_a)

    logger.info("Loading current bundle from %s", path_b)
    bundle_b = load_bundle(path_b)

    graph_a = _scoring_graph(bundle_a.get("graph", {}))
    ss_a = _scoring_state_space(bundle_a.get("state_space", {}))
    mappings_a = {k: _strip_volatile(v) for k, v in bundle_a.get("mappings", {}).items()}

    graph_b = _scoring_graph(bundle_b.get("graph", {}))
    ss_b = _scoring_state_space(bundle_b.get("state_space", {}))
    mappings_b = {k: _strip_volatile(v) for k, v in bundle_b.get("mappings", {}).items()}

    # Compute drift
    logger.info("Computing drift...")
    analyzer = DriftAnalyzer(
        {"graph": graph_a, "state_space": ss_a, "mappings": mappings_a},
        {"graph": graph_b, "state_space": ss_b, "mappings": mappings_b},
    )
    drift_report = analyzer.generate_diff_report()

    # Compute metrics for each bundle
    logger.info("Computing metrics...")
    metrics_a = CodebaseMetrics(graph_a, ss_a, _mapped_node_index(mappings_a))
    metrics_b = CodebaseMetrics(graph_b, ss_b, _mapped_node_index(mappings_b))

    # Build comprehensive report
    report_lines = [
        "# Codebase Diff Report",
        "",
        f"**Baseline**: {path_a.name}",
        f"**Current**: {path_b.name}",
        "",
        drift_report,
        "",
        "## Metrics Comparison",
        "",
        "### Baseline Metrics",
        "",
        metrics_a.format_report(),
        "",
        "### Current Metrics",
        "",
        metrics_b.format_report(),
        "",
    ]

    return "\n".join(report_lines)
