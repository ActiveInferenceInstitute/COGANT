"""Compile DSL rules into executable matchers."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass

from cogant.schemas.core import EdgeKind, Node, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.translate.dsl.schema import DSLCondition, DSLRuleSet


@dataclass
class CompiledRule:
    """A DSL rule compiled into a callable matcher.

    Call :meth:`match` with a node and the program graph.  Returns the
    rule's ``confidence`` when **all** conditions are satisfied, or
    ``0.0`` otherwise.
    """

    name: str
    role: str
    confidence: float
    description: str | None
    _conditions: list[DSLCondition]

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def match(self, node: Node, graph: ProgramGraph) -> float:
        """Evaluate the rule against *node* in *graph*.

        Returns:
            ``self.confidence`` if every condition matches, ``0.0`` otherwise.
        """
        for cond in self._conditions:
            if not _evaluate_condition(cond, node, graph):
                return 0.0
        return self.confidence


def compile_ruleset(ruleset: DSLRuleSet) -> list[CompiledRule]:
    """Compile a :class:`DSLRuleSet` into a list of :class:`CompiledRule`.

    An empty ruleset yields an empty list (no error).
    """
    compiled: list[CompiledRule] = []
    for rule in ruleset.rules:
        compiled.append(
            CompiledRule(
                name=rule.name,
                role=rule.role,
                confidence=rule.confidence,
                description=rule.description,
                _conditions=list(rule.conditions),
            )
        )
    return compiled


# ---------------------------------------------------------------------- #
# Condition evaluators
# ---------------------------------------------------------------------- #


def _evaluate_condition(
    cond: DSLCondition,
    node: Node,
    graph: ProgramGraph,
) -> bool:
    """Return True if *node* satisfies *cond* within *graph*."""

    if cond.node_kind is not None:
        expected = cond.node_kind.upper()
        try:
            expected_kind = NodeKind(expected.lower())
        except ValueError:
            return False
        if node.kind != expected_kind:
            return False

    if cond.name_pattern is not None:
        if not fnmatch.fnmatch(node.name, cond.name_pattern):
            return False

    if cond.has_method is not None:
        if not _node_has_method(node, graph, cond.has_method):
            return False

    if cond.edge_type is not None:
        if not _node_has_outgoing_edge(node, graph, cond.edge_type):
            return False

    return True


def _node_has_method(node: Node, graph: ProgramGraph, method_name: str) -> bool:
    """Check if *node* contains a METHOD child named *method_name*."""
    from cogant.schemas.core import EdgeKind as EK

    for edge in graph.get_edges_from(node.id):
        if edge.kind == EK.CONTAINS:
            child = graph.get_node(edge.target_id)
            if child and child.kind == NodeKind.METHOD and child.name == method_name:
                return True
    return False


def _node_has_outgoing_edge(node: Node, graph: ProgramGraph, edge_type: str) -> bool:
    """Check if *node* has at least one outgoing edge of *edge_type*."""
    try:
        expected_kind = EdgeKind(edge_type.lower())
    except ValueError:
        return False
    for edge in graph.get_edges_from(node.id):
        if edge.kind == expected_kind:
            return True
    return False
