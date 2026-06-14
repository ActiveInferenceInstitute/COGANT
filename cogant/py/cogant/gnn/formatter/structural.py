"""Structural section formatters for the GNN markdown export.

This module contains the ``_format_*`` methods that render the
structural (state space, observations, actions/policies, connections, factors) canonical sections of a GNN model to markdown. It is a
mixin for :class:`cogant.gnn.formatter.GNNMarkdownFormatter`; it
does not stand on its own and expects ``self.graph``, ``self.state_space``,
``self.process``, and ``self.mappings`` to be populated by the
concrete formatter.

Families:
  * ``_format_state_space``
  * ``_format_observation_modalities``
  * ``_format_actions_policies``
  * ``_format_connections``
  * ``_format_factors``

See :class:`cogant.gnn.formatter.base.GNNMarkdownFormatter` for the
main entry point and :mod:`cogant.gnn.formatter` for the package.
"""

import logging
from collections import defaultdict
from typing import Any

from cogant.gnn.matrices import GNNMatrices
from cogant.process.extractor import ProcessModel
from cogant.schemas.core import NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import MappingKind
from cogant.statespace.compiler import StateSpaceModel

logger = logging.getLogger(__name__)


class _StructuralSectionsMixin:
    """Mixin providing the structural-section formatters for GNN export.

    Implements the COGANT-extended "structural" block family of the GNN
    markdown document: the state space (with derived A/B/C/D matrices),
    observation modalities, actions/policies, program-graph connections,
    and factorization. Each ``_format_*`` method returns a newline-joined
    markdown string suitable for concatenation into the document by
    :meth:`cogant.gnn.formatter.base.GNNMarkdownFormatter.format`.

    The mixin is not instantiable on its own. It expects the concrete
    formatter to expose:

    * ``self.graph``       -- :class:`cogant.schemas.graph.ProgramGraph`
    * ``self.state_space`` -- :class:`cogant.statespace.compiler.StateSpaceModel`
    * ``self.process``     -- :class:`cogant.process.extractor.ProcessModel`
    * ``self.mappings``    -- dict of ``SemanticMapping`` keyed by id
    * ``self._action_effects(action)`` helper for action effect extraction
    """

    # Attributes populated by the concrete formatter (see base.py).
    graph: ProgramGraph
    state_space: StateSpaceModel
    process: ProcessModel
    mappings: dict[str, Any]

    def _format_state_space(self) -> str:
        """Format the State Space section of the GNN markdown document.

        Emits the ``## State Space`` heading, a table of state variables
        pulled from ``self.state_space.variables`` (with per-row source
        node, domain, cardinality, factorization, and confidence), and,
        when the program graph exposes enough evidence, an embedded
        ``### Active Inference Matrices (A/B/C/D)`` block produced by
        :class:`cogant.gnn.matrices.GNNMatrices`.

        The matrix block is best-effort: any ``ValueError``,
        ``KeyError``, or ``AttributeError`` raised during derivation is
        logged at warning level and swallowed so the rest of the report
        still renders.

        Returns:
            A newline-joined markdown string for the state space section.
        """
        lines = ["## State Space"]
        lines.append("")

        if self.state_space.variables:
            lines.append("### State Variables")
            lines.append("")
            lines.append(
                "| ID | Name | Type | Domain | Cardinality | Factors | Confidence | Source |"
            )
            lines.append("|----|----|------|--------|------|---------|------|-------|")
            for var_id, var in self.state_space.variables.items():
                card = var.cardinality or "∞"
                # Truncate domain to avoid multi-thousand-element lists that
                # balloon the markdown to hundreds of MB on large repos.
                # Show the first 5 elements and a count suffix when longer.
                raw_domain = var.domain or "unknown"
                if isinstance(raw_domain, list):
                    if len(raw_domain) > 5:
                        domain = str(raw_domain[:5])[:-1] + f", +{len(raw_domain) - 5} more]"
                    else:
                        domain = str(raw_domain)
                else:
                    domain = str(raw_domain)[:120]
                factors = ", ".join(var.factors) if var.factors else "none"
                # Extract source node name if available
                source = ""
                if var.node_id and var.node_id in self.graph.nodes:
                    source = self.graph.nodes[var.node_id].name
                elif var.node_id:
                    source = var.node_id
                lines.append(
                    f"| {var_id[:12]} | {var.name} | {var.var_type} | {domain} | {card} | {factors} | {var.confidence.value} | {source} |"
                )
            lines.append("")
            lines.append(f"**Total Variables**: {len(self.state_space.variables)}")
            lines.append("")
        else:
            lines.append("No state variables detected in this codebase.")
            lines.append("")

        # Emit the A/B/C/D Active Inference matrices derived from the
        # graph and semantic mappings. These are required by the AII
        # upstream GNN validator and are computed by GNNMatrices.
        try:
            matrices = GNNMatrices(
                graph=self.graph,
                mappings=self.mappings,
                state_space=self.state_space,
            )
            block = matrices.to_gnn_markdown_block()
            if block:
                lines.append("### Active Inference Matrices (A/B/C/D)")
                lines.append("")
                lines.append(
                    "The following matrices are derived from the program graph "
                    "and semantic mappings. They conform to the AII GNN matrix "
                    "notation: `A[[rows=n_obs][cols=n_states]]`, "
                    "`B[[rows=n_states][cols=n_states][depth=n_actions]]`, "
                    "`C[[rows=n_obs]]`, `D[[rows=n_states]]`."
                )
                lines.append("")
                lines.append("```gnn-matrices")
                lines.append(block)
                lines.append("```")
                lines.append("")
                dims = matrices.to_dict()["dimensions"]
                lines.append(
                    f"**Matrix dimensions**: n_states={dims['n_states']}, "
                    f"n_obs={dims['n_obs']}, n_actions={dims['n_actions']}"
                )
                lines.append("")
        except (ValueError, KeyError, AttributeError) as exc:
            logger.warning(
                "Failed to derive GNN A/B/C/D matrices: %s: %s",
                type(exc).__name__,
                exc,
            )

        return "\n".join(lines)

    def _format_observation_modalities(self) -> str:
        """Format the Observation Modalities section.

        Emits a ``## Observation Modalities`` heading followed by one
        table sourced from ``self.state_space.observations`` (each row
        describes an :class:`ObservationModality` with its source node
        name resolved from the graph) and, if any
        :class:`MappingKind.OBSERVATION` semantic mappings are present,
        a secondary ``### Observation Mappings from Semantic Analysis``
        subsection capped at 20 rows for readability.

        Returns:
            A newline-joined markdown string. If no observations are
            detected, the section still renders with an explanatory
            placeholder sentence.
        """
        lines = ["## Observation Modalities"]
        lines.append("")

        if self.state_space.observations:
            lines.append(
                "| ID | Name | Modality | Source Node | Channels | Confidence | Description |"
            )
            lines.append("|----|----|------|------|------|------|------|")
            for obs_id, obs in self.state_space.observations.items():
                # Find source node name
                source_name = obs.source_node_id
                if obs.source_node_id in self.graph.nodes:
                    source_name = self.graph.nodes[obs.source_node_id].name
                # ObservationModality cardinality used as channels indicator
                channels_str = f"{obs.cardinality}ch" if obs.cardinality else "default"
                desc = obs.description or ""
                lines.append(
                    f"| {obs_id[:12]} | {obs.name} | {obs.modality_type} | {source_name} | {channels_str} | {obs.confidence.value} | {desc} |"
                )
            lines.append("")
            lines.append(f"**Total Observations**: {len(self.state_space.observations)}")
            lines.append("")
        else:
            lines.append("No observation modalities detected in this codebase.")
            lines.append("")

        # Also list semantic OBSERVATION mappings
        obs_mappings = [
            m
            for m in self.mappings.values()
            if hasattr(m, "kind") and m.kind == MappingKind.OBSERVATION
        ]
        if obs_mappings:
            lines.append("### Observation Mappings from Semantic Analysis")
            lines.append("")
            lines.append("| ID | Label | Nodes | Confidence |")
            lines.append("|----|----|------|------|")
            for mapping in obs_mappings[:20]:  # Limit to 20
                node_ids = mapping.graph_fragment_node_ids[:2]
                node_names = [
                    self.graph.nodes[nid].name if nid in self.graph.nodes else nid
                    for nid in node_ids
                ]
                lines.append(
                    f"| {mapping.id[:12]} | {mapping.semantic_label} | {', '.join(node_names)} | {mapping.confidence_score:.2f} |"
                )
            lines.append("")

        return "\n".join(lines)

    def _format_actions_policies(self) -> str:
        """Format the Actions and Policies section.

        Emits a ``## Actions Policies`` heading followed by:

        1. An ``### Actions`` table built from
           ``self.state_space.actions``. For each
           :class:`cogant.statespace.compiler.Action`, the row records
           its parameters (truncated to 2), effects (computed via
           ``self._action_effects``), first precondition, confidence
           tier, and the resolved controller-node name.
        2. An ``### Action and Policy Mappings`` subsection listing the
           first 30 :class:`MappingKind.ACTION` / :class:`MappingKind.POLICY`
           semantic mappings with their evidence counts.

        Returns:
            A newline-joined markdown string. Emits an explanatory empty-state
            sentence when no actions are detected.
        """
        lines = ["## Actions Policies"]
        lines.append("")

        if self.state_space.actions:
            lines.append("### Actions")
            lines.append("")
            lines.append(
                "| ID | Name | Parameters | Effects | Preconditions | Confidence | Controller |"
            )
            lines.append("|----|----|------|------|------|------|------|")
            for action_id, action in self.state_space.actions.items():
                # Handle parameters - could be dict or list
                if action.parameters:
                    if isinstance(action.parameters, dict):
                        params = ", ".join(list(action.parameters.keys())[:2])
                    elif isinstance(action.parameters, list):
                        params = ", ".join(action.parameters[:2])
                    else:
                        params = str(action.parameters)[:20]
                else:
                    params = "none"
                effects_list = self._action_effects(action)  # type: ignore[attr-defined]
                effects = ", ".join(effects_list[:2]) if effects_list else "none"
                precond = ", ".join(action.preconditions[:1]) if action.preconditions else "none"
                controller = action.controller_id
                if action.controller_id in self.graph.nodes:
                    controller = self.graph.nodes[action.controller_id].name
                lines.append(
                    f"| {action_id[:12]} | {action.name} | {params} | {effects} | {precond} | {action.confidence.value} | {controller} |"
                )
            lines.append("")
            lines.append(f"**Total Actions**: {len(self.state_space.actions)}")
            lines.append("")
        else:
            lines.append("No actions detected in this codebase.")
            lines.append("")

        # List ACTION and POLICY mappings
        action_mappings = [
            m
            for m in self.mappings.values()
            if hasattr(m, "kind") and m.kind in (MappingKind.ACTION, MappingKind.POLICY)
        ]
        if action_mappings:
            lines.append("### Action and Policy Mappings")
            lines.append("")
            lines.append("| ID | Label | Kind | Nodes | Confidence | Decision Points |")
            lines.append("|----|----|------|------|------|------|")
            for mapping in action_mappings[:30]:  # Limit to 30
                node_ids = mapping.graph_fragment_node_ids[:1]
                node_names = [
                    self.graph.nodes[nid].name if nid in self.graph.nodes else nid
                    for nid in node_ids
                ]
                # SemanticMapping doesn't have metadata; estimate decision points from evidence
                dp_str = (
                    str(mapping.evidence_count)
                    if hasattr(mapping, "evidence_count") and mapping.evidence_count
                    else "0"
                )
                lines.append(
                    f"| {mapping.id[:12]} | {mapping.semantic_label} | {mapping.kind.value} | {', '.join(node_names)} | {mapping.confidence_score:.2f} | {dp_str} |"
                )
            lines.append("")

        return "\n".join(lines)

    def _format_connections(self) -> str:
        """Format program-graph connections section (graph edges).

        This COGANT-extended section uses the header ``## Program Graph
        Connections`` (not ``## Connections``) to avoid a duplicate level-2
        header collision with the upstream GNN v2.0.0.x ``## Connections`` section
        that appears earlier in the document.  The upstream type-checker only
        processes the first ``## Connections`` section it encounters; a second
        identically-named section would be parsed as a continuation of the
        upstream connections block and generate spurious parse errors.
        """
        lines = ["## Program Graph Connections"]
        lines.append("")

        # Group edges by kind
        edges_by_kind = defaultdict(list)
        for edge in self.graph.edges.values():
            edges_by_kind[edge.kind.value].append(edge)

        # Show top edge kinds
        for edge_kind in sorted(edges_by_kind.keys())[:15]:  # Top 15 kinds
            edges = edges_by_kind[edge_kind][:50]  # Top 50 edges per kind
            lines.append(f"### {edge_kind.title()}")
            lines.append("")
            lines.append("| Source → Target | Weight | Evidence |")
            lines.append("|----|----|------|")

            for edge in edges:
                source_name = (
                    self.graph.nodes[edge.source_id].name
                    if edge.source_id in self.graph.nodes
                    else edge.source_id
                )
                target_name = (
                    self.graph.nodes[edge.target_id].name
                    if edge.target_id in self.graph.nodes
                    else edge.target_id
                )

                # Extract evidence from edge metadata (file and line information)
                evidence = "none"
                if edge.evidence_sources:
                    evidence = ", ".join(edge.evidence_sources[:2])
                elif edge.metadata:
                    # Try to construct evidence from metadata
                    evidence_parts = []
                    if "source_file" in edge.metadata:
                        evidence_parts.append(f"file:{edge.metadata['source_file']}")
                    if "line_number" in edge.metadata:
                        evidence_parts.append(f"line:{edge.metadata['line_number']}")
                    if "pattern" in edge.metadata:
                        evidence_parts.append(f"pattern:{edge.metadata['pattern']}")
                    if evidence_parts:
                        evidence = ", ".join(evidence_parts[:2])

                lines.append(f"| {source_name} → {target_name} | {edge.weight} | {evidence} |")

            lines.append("")

        # Process model connections if available
        if self.process.connections:
            lines.append("### Process Flow Connections")
            lines.append("")
            lines.append("| Source Stage → Target Stage | Trigger | Condition | Success Rate |")
            lines.append("|----|----|------|------|")
            for conn in list(self.process.connections.values())[:50]:
                trigger = conn.trigger or "none"
                condition = conn.condition or "none"
                success = f"{conn.success_rate:.2%}" if conn.success_rate else "unknown"
                lines.append(
                    f"| {conn.source_stage_id} → {conn.target_stage_id} | {trigger} | {condition} | {success} |"
                )
            lines.append("")

        lines.append("")

        return "\n".join(lines)

    def _format_factors(self) -> str:
        """Format factorization section.

        Derives factors from:
        1. State space variables (if present)
        2. Graph structure: group by class/module (components that don't interact)
        3. Connected components in the call graph
        """
        lines = ["## Factors"]
        lines.append("")

        # Option 1: Use state space variables if present
        if self.state_space.variables:
            vars_by_factor = defaultdict(list)
            for var_id, var in self.state_space.variables.items():
                if var.factors:
                    for factor in var.factors:
                        vars_by_factor[factor].append((var_id, var.name))
                else:
                    vars_by_factor["(uncategorized)"].append((var_id, var.name))

            for factor in sorted(vars_by_factor.keys()):
                vars_list = vars_by_factor[factor]
                lines.append(f"### Factor: {factor}")
                lines.append("")
                lines.append("| Variable ID | Name |")
                lines.append("|----|----|")
                for var_id, var_name in vars_list:
                    lines.append(f"| {var_id[:16]} | {var_name} |")
                lines.append("")

            # Independence structure hint
            if len(vars_by_factor) > 1:
                lines.append(
                    "**Independence Structure**: Variables in different factors are assumed conditionally independent given parent factors."
                )
                lines.append("")

        else:
            # Option 2: Derive factors from graph structure (classes/modules as independent components)
            lines.append("### Factorization by Program Components")
            lines.append("")

            # Group nodes by class/module
            components_by_class: dict[str, list[str]] = defaultdict(list)
            for node in self.graph.nodes.values():
                # Get class name or module as factor
                if node.kind == NodeKind.METHOD:
                    # Methods belong to their containing class
                    class_name = node.path.split("/")[0] if node.path else "root"
                else:
                    class_name = node.name

                components_by_class[class_name].append(node.name)

            if components_by_class:
                lines.append("| Factor (Class/Component) | Members | Independence |")
                lines.append("|----|----|------|")
                for comp_name in sorted(components_by_class.keys()):
                    members = components_by_class[comp_name]
                    member_str = ", ".join(members[:3])
                    if len(members) > 3:
                        member_str += f", +{len(members) - 3} more"
                    independence = (
                        "Assumed independent from other factors"
                        if len(components_by_class) > 1
                        else "Singleton"
                    )
                    lines.append(f"| {comp_name} | {member_str} | {independence} |")
                lines.append("")

                lines.append("**Factorization Notes**:")
                lines.append(f"- Total factors (components): {len(components_by_class)}")
                lines.append(f"- Total nodes: {len(self.graph.nodes)}")
                lines.append(
                    "- Each factor represents a cohesive unit (class/module) with internal dependencies"
                )
                lines.append("- Cross-factor edges represent component coupling")
                lines.append("")

        return "\n".join(lines)
