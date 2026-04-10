"""``cogant explain`` — justify why a node was assigned an AI role.

This module implements the CLI-facing logic for the ``cogant explain``
subcommand. Given a repository path and a node name, it re-runs the
static pipeline (``ingest`` → ``static`` → ``normalize`` → ``graph`` →
``translate``) to produce a :class:`ProgramGraph` and a set of semantic
mappings, then asks every registered :class:`TranslationRule` whether it
fired on the target node via the rule's :meth:`explain` method.

The public surface is:

* :class:`ExplainResult` — dataclass holding the full explain record
  (node identity, assigned role, fired/considered rule explanations,
  and Markov blanket role).
* :class:`NodeNotFoundError` — raised when the node name cannot be
  resolved against any node in the graph.
* :func:`explain_node` — top-level entry point used by ``cogant explain``
  and by the test suite.
* :func:`format_text` — render an :class:`ExplainResult` to the console
  using Rich.
* :func:`format_json` — render an :class:`ExplainResult` as a JSON
  string.
* :func:`resolve_node` — deterministic exact→case-insensitive→substring
  node resolver used by :func:`explain_node`.

The explain pipeline deliberately skips the ``statespace``, ``process``,
``export``, and ``validate`` stages because none of them affect rule
firing; keeping the pipeline short ensures ``cogant explain`` stays
responsive even on medium-sized repositories.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cogant.api.bundle import ArtifactKey, Bundle
from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.graph.queries import GraphQuery
from cogant.markov import MarkovBlanketExtractor
from cogant.markov.blanket import BlanketRole
from cogant.schemas.core import Node
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import SemanticMapping
from cogant.translate.engine import RuleExplanation, TranslationEngine


class NodeNotFoundError(LookupError):
    """Raised when a node query cannot be resolved.

    The error message always contains the original query and a small
    sample of candidate node names so the caller can retry with a
    better guess. This gives ``cogant explain`` actionable errors rather
    than an opaque ``KeyError``.
    """


@dataclass
class ExplainResult:
    """Result of explaining a single node's AI-role attribution.

    Attributes:
        node_name: Name of the node that was explained.
        node_id: Stable node id in the program graph.
        node_kind: Graph node kind (``function``, ``class``, ...).
        assigned_role: The semantic mapping kind the rule engine
            assigned to this node (e.g. ``"observation"``). ``None``
            when no rule fired.
        rules_fired: :class:`RuleExplanation` records for every rule
            that fired on the node, sorted by priority (descending).
        rules_considered: :class:`RuleExplanation` records for rules
            that ran on the node but did not fire.
        blanket_role: Active Inference Markov blanket role
            (``internal``, ``sensory``, ``active``, ``external``).
        target: Original repository path supplied to the CLI.
    """

    node_name: str
    node_id: str
    node_kind: str
    assigned_role: str | None
    rules_fired: list[RuleExplanation]
    rules_considered: list[RuleExplanation]
    blanket_role: str
    target: str = ""
    mapping_label: str | None = None
    mapping_description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain JSON-ready dict."""
        return {
            "node_name": self.node_name,
            "node_id": self.node_id,
            "node_kind": self.node_kind,
            "assigned_role": self.assigned_role,
            "rules_fired": [r.to_dict() for r in self.rules_fired],
            "rules_considered": [r.to_dict() for r in self.rules_considered],
            "blanket_role": self.blanket_role,
            "target": self.target,
            "mapping_label": self.mapping_label,
            "mapping_description": self.mapping_description,
            "metadata": dict(self.metadata),
        }


def _run_pipeline(repo_path: str) -> Bundle:
    """Run the static pipeline and return the populated bundle.

    Skips ``dynamic``, ``statespace``, ``process``, ``export``, and
    ``validate`` stages because none of them influence rule firing and
    they would otherwise bloat the explain turnaround time.

    Args:
        repo_path: Absolute or relative path to the repository to
            analyze.

    Returns:
        The :class:`Bundle` populated with program-graph and
        semantic-mapping artifacts.

    Raises:
        FileNotFoundError: If ``repo_path`` does not exist.
        RuntimeError: If the pipeline finished without producing a
            program graph.
    """
    path = Path(repo_path)
    if not path.exists():
        raise FileNotFoundError(f"repo path does not exist: {repo_path}")

    runner = PipelineRunner()
    config = PipelineConfig(
        stages=["ingest", "static", "normalize", "graph", "translate"],
        skip_dynamic=True,
    )
    bundle = runner.run(str(path), config)

    if bundle.get_artifact(ArtifactKey.PROGRAM_GRAPH) is None:
        errors = "; ".join(bundle.errors) if bundle.errors else "unknown error"
        raise RuntimeError(
            f"pipeline did not produce a program graph for {repo_path!r}: "
            f"{errors}"
        )
    return bundle


def _graph_from_bundle(bundle: Bundle) -> ProgramGraph:
    """Extract the program graph, raising if it is missing."""
    pg = bundle.get_artifact(ArtifactKey.PROGRAM_GRAPH, required=True)
    return pg


def resolve_node(graph: ProgramGraph, query: str) -> Node:
    """Resolve a node query string to a concrete :class:`Node`.

    Resolution is deterministic and proceeds in three steps:

    1. Exact match on ``node.name`` or ``node.qualified_name``.
    2. Case-insensitive exact match on ``node.name`` or
       ``node.qualified_name``.
    3. Case-insensitive substring match on ``node.name``, breaking ties
       by shortest name (shorter names are typically less
       ambiguous — ``calc`` prefers ``clear`` over ``calculate_result``
       only when both contain ``calc``, otherwise the shortest
       containing name wins).

    Args:
        graph: The populated program graph.
        query: Raw node name or substring supplied by the user.

    Returns:
        The resolved :class:`Node`.

    Raises:
        NodeNotFoundError: If no node matches the query. The error
            message contains a short sample of candidate names so the
            user can retry.
    """
    if not query:
        raise NodeNotFoundError(
            f"empty node query; provide a non-empty name. "
            f"sample candidates: {_candidate_sample(graph)}"
        )

    # Step 1: exact match on name or qualified_name
    for node in graph.nodes.values():
        if node.name == query or node.qualified_name == query:
            return node

    # Step 2: case-insensitive exact match
    q_lower = query.lower()
    for node in graph.nodes.values():
        if (
            (node.name or "").lower() == q_lower
            or (node.qualified_name or "").lower() == q_lower
        ):
            return node

    # Step 3: case-insensitive substring on name, prefer shortest
    candidates = [
        node for node in graph.nodes.values()
        if q_lower in (node.name or "").lower()
    ]
    if candidates:
        candidates.sort(key=lambda n: (len(n.name or ""), n.name or ""))
        return candidates[0]

    raise NodeNotFoundError(
        f"no node matches query {query!r}. "
        f"sample candidates: {_candidate_sample(graph)}"
    )


def _candidate_sample(graph: ProgramGraph, limit: int = 10) -> list[str]:
    """Return up to ``limit`` candidate node names for error messages."""
    names: list[str] = []
    for node in graph.nodes.values():
        if node.name:
            names.append(node.name)
        if len(names) >= limit:
            break
    return names


def _find_assigned_mapping(
    node_id: str, mappings: dict[str, SemanticMapping]
) -> SemanticMapping | None:
    """Return the highest-confidence mapping whose fragment contains ``node_id``."""
    hits: list[SemanticMapping] = []
    for mapping in mappings.values():
        if node_id in (mapping.graph_fragment_node_ids or []):
            hits.append(mapping)
    if not hits:
        return None
    hits.sort(key=lambda m: m.confidence_score, reverse=True)
    return hits[0]


def _compute_blanket_role(graph: ProgramGraph, node: Node) -> str:
    """Compute the Markov blanket role for ``node``.

    Seeds the :class:`MarkovBlanketExtractor` with the module/file that
    contains the node (``strategy="module"``), falling back to
    ``strategy="auto"`` when the node has no usable path.

    Args:
        graph: Populated program graph.
        node: The target node.

    Returns:
        String role: ``internal``, ``sensory``, ``active``, or
        ``external``. Returns ``"unknown"`` when the extractor cannot
        produce a partition for any reason.
    """
    extractor = MarkovBlanketExtractor(graph)

    module_hint: str | None = None
    if node.path:
        module_hint = Path(node.path).stem

    try:
        if module_hint:
            blanket = extractor.extract(
                strategy="module", module_names=[module_hint]
            )
        else:
            blanket = extractor.extract(strategy="auto")
    except (ValueError, KeyError):
        try:
            blanket = extractor.extract(strategy="auto")
        except (ValueError, KeyError):
            return "unknown"

    role = blanket.roles.get(node.id)
    if role is None:
        return BlanketRole.EXTERNAL.value
    return role.value if hasattr(role, "value") else str(role)


def explain_node(repo_path: str, node_query: str) -> ExplainResult:
    """Produce a full :class:`ExplainResult` for ``(repo_path, node_query)``.

    This is the top-level entry point for ``cogant explain``. It runs
    the static pipeline, resolves the query to a concrete node, asks
    every rule to explain its decision, partitions fired vs considered,
    and computes the Markov blanket role.

    Args:
        repo_path: Path to the repository to analyze.
        node_query: Node name or substring to explain.

    Returns:
        A populated :class:`ExplainResult`.

    Raises:
        FileNotFoundError: If ``repo_path`` does not exist.
        RuntimeError: If the pipeline failed to build a program graph.
        NodeNotFoundError: If ``node_query`` cannot be resolved.
    """
    bundle = _run_pipeline(repo_path)
    graph: ProgramGraph = _graph_from_bundle(bundle)

    node = resolve_node(graph, node_query)

    engine: TranslationEngine | None = bundle.get_artifact(
        ArtifactKey.TRANSLATION_ENGINE
    )
    if engine is None:
        raise RuntimeError(
            "translate stage did not register a translation engine; "
            "cannot explain rule decisions"
        )

    mappings: dict[str, SemanticMapping] = (
        bundle.get_artifact(ArtifactKey.SEMANTIC_MAPPINGS) or {}
    )
    query = GraphQuery(graph)

    rules_fired: list[RuleExplanation] = []
    rules_considered: list[RuleExplanation] = []
    for rule in engine.rules:
        try:
            rx = rule.explain(node, graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            rx = RuleExplanation(
                rule_name=getattr(rule, "name", repr(rule)),
                priority=getattr(rule, "priority", 0),
                fired=False,
                reason=f"explain() raised: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=(
                    rule.mapping_kind.value
                    if hasattr(rule, "mapping_kind")
                    else None
                ),
            )
        if rx.fired:
            rules_fired.append(rx)
        else:
            rules_considered.append(rx)

    rules_fired.sort(key=lambda r: (-r.priority, r.rule_name))
    rules_considered.sort(key=lambda r: (-r.priority, r.rule_name))

    assigned_mapping = _find_assigned_mapping(node.id, mappings)
    assigned_role = (
        assigned_mapping.kind.value if assigned_mapping is not None else None
    )
    mapping_label = (
        assigned_mapping.semantic_label if assigned_mapping is not None else None
    )
    mapping_description = (
        assigned_mapping.description if assigned_mapping is not None else None
    )

    blanket_role = _compute_blanket_role(graph, node)

    return ExplainResult(
        node_name=node.name,
        node_id=node.id,
        node_kind=node.kind.value,
        assigned_role=assigned_role,
        rules_fired=rules_fired,
        rules_considered=rules_considered,
        blanket_role=blanket_role,
        target=repo_path,
        mapping_label=mapping_label,
        mapping_description=mapping_description,
        metadata={
            "qualified_name": node.qualified_name,
            "path": node.path,
            "language": node.language,
            "total_rules": len(engine.rules),
            "fired_count": len(rules_fired),
            "considered_count": len(rules_considered),
        },
    )


def format_text(result: ExplainResult, console: Console | None = None) -> None:
    """Render ``result`` as a human-readable report on ``console``.

    Uses Rich panels and tables to make the output scannable. The
    rendered report contains four sections:

    1. Header panel with the node name, kind, assigned role, and
       Markov blanket role.
    2. "Rules fired" table listing each fired rule's name, priority,
       reason, and evidence.
    3. "Rules considered" table listing rules that did not fire.
    4. Footer line with summary counts.

    Args:
        result: The :class:`ExplainResult` to render.
        console: Optional pre-built :class:`rich.console.Console`. When
            omitted, a fresh console is created.
    """
    if console is None:
        console = Console()

    role_str = result.assigned_role or "[dim]unassigned[/dim]"
    header = (
        f"[bold]{result.node_name}[/bold] ({result.node_kind})\n"
        f"[cyan]Assigned role:[/cyan] [bold]{role_str}[/bold]\n"
        f"[cyan]Markov blanket:[/cyan] [bold]{result.blanket_role}[/bold]"
    )
    if result.mapping_label:
        header += f"\n[cyan]Label:[/cyan] {result.mapping_label}"
    if result.mapping_description:
        header += f"\n[dim]{result.mapping_description}[/dim]"
    console.print(Panel(header, title="cogant explain", border_style="blue"))

    if result.rules_fired:
        fired_table = Table(
            title=f"Rules fired ({len(result.rules_fired)})",
            show_lines=False,
            border_style="green",
        )
        fired_table.add_column("Rule", style="bold green")
        fired_table.add_column("Priority", justify="right")
        fired_table.add_column("Mapping Kind")
        fired_table.add_column("Reason")
        fired_table.add_column("Evidence")
        for rx in result.rules_fired:
            fired_table.add_row(
                rx.rule_name,
                str(rx.priority),
                rx.mapping_kind or "",
                rx.reason,
                "\n".join(rx.evidence) if rx.evidence else "",
            )
        console.print(fired_table)
    else:
        console.print("[yellow]No rules fired on this node.[/yellow]")

    if result.rules_considered:
        considered_table = Table(
            title=f"Rules considered ({len(result.rules_considered)})",
            show_lines=False,
            border_style="dim",
        )
        considered_table.add_column("Rule", style="dim")
        considered_table.add_column("Priority", justify="right")
        considered_table.add_column("Reason")
        for rx in result.rules_considered:
            considered_table.add_row(rx.rule_name, str(rx.priority), rx.reason)
        console.print(considered_table)

    console.print(
        f"[dim]Explained {result.node_name!r} "
        f"({len(result.rules_fired)} fired / "
        f"{len(result.rules_considered)} considered).[/dim]"
    )


def format_json(result: ExplainResult) -> str:
    """Render ``result`` as a JSON string.

    The output contains the full contract keys used by programmatic
    consumers: ``node_name``, ``node_id``, ``node_kind``,
    ``assigned_role``, ``rules_fired``, ``rules_considered``,
    ``blanket_role``, ``target``, ``mapping_label``,
    ``mapping_description``, and ``metadata``.

    Args:
        result: The explain result to serialize.

    Returns:
        JSON string with 2-space indentation.
    """
    return json.dumps(result.to_dict(), indent=2, sort_keys=True)
