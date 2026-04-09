"""Semantic section formatters for the GNN markdown export.

This module contains the ``_format_*`` methods that render the
semantic (ontology mapping, Markov blanket) canonical sections of a GNN model to markdown. It is a
mixin for :class:`cogant.gnn.formatter.GNNMarkdownFormatter`; it
does not stand on its own and expects ``self.graph``, ``self.state_space``,
``self.process``, and ``self.mappings`` to be populated by the
concrete formatter.

Families:
  * ``_format_ontology_mapping``
  * ``_format_markov_blanket``

See :class:`cogant.gnn.formatter.base.GNNMarkdownFormatter` for the
main entry point and :mod:`cogant.gnn.formatter` for the package.
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timezone
import logging
import traceback
from collections import defaultdict

from cogant.schemas.graph import ProgramGraph
from cogant.schemas.core import NodeKind, EdgeKind
from cogant.statespace.compiler import StateSpaceModel
from cogant.process.extractor import ProcessModel
from cogant.schemas.semantic import MappingKind

logger = logging.getLogger(__name__)


class _SemanticSectionsMixin:
    def _format_ontology_mapping(self) -> str:
        """Format ontology mapping section."""
        lines = ["## Ontology Mapping"]
        lines.append("")

        if not self.mappings:
            lines.append("No ontology mappings found.")
            lines.append("")
            return "\n".join(lines)

        # Count mappings by kind and node kind
        mapping_by_kind = defaultdict(int)
        node_to_role = defaultdict(list)

        for mapping in self.mappings.values():
            if hasattr(mapping, 'kind'):
                mapping_by_kind[mapping.kind.value] += 1
                # Track which program node kinds map to which roles
                for node_id in mapping.graph_fragment_node_ids:
                    if node_id in self.graph.nodes:
                        node_kind = self.graph.nodes[node_id].kind.value
                        node_to_role[node_kind].append(mapping.kind.value)

        lines.append("### Mapping Counts by Type")
        lines.append("")
        lines.append("| Mapping Kind | Count |")
        lines.append("|----|----|")
        for kind in sorted(mapping_by_kind.keys()):
            lines.append(f"| {kind} | {mapping_by_kind[kind]} |")
        lines.append(f"| **Total** | **{len(self.mappings)}** |")
        lines.append("")

        lines.append("### Program Nodes to Semantic Roles")
        lines.append("")
        lines.append("| Program Node Kind | Semantic Roles |")
        lines.append("|----|----|")
        for node_kind in sorted(node_to_role.keys()):
            roles = node_to_role[node_kind]
            role_counts = defaultdict(int)
            for role in roles:
                role_counts[role] += 1
            role_str = ", ".join([f"{r}({c})" for r, c in sorted(role_counts.items())])
            lines.append(f"| {node_kind} | {role_str} |")
        lines.append("")

        return "\n".join(lines)
    def _format_markov_blanket(self) -> str:
        """
        Format Markov Blanket section.

        Computes an on-the-fly Active-Inference-style Markov blanket by
        partitioning the program graph into internal (μ), sensory (s),
        active (a), and external (η) roles. The seed strategy defaults
        to ``auto``, which picks the module with the best
        cohesion/(cohesion+coupling+1) score; callers can override via
        ``self.state_space.metadata["markov_blanket_strategy"]``.

        The section documents the boundary partition in human-readable
        form and explains the conditional-independence contract:
        ``p(μ | s, a, η) = p(μ | s, a)``.
        """
        lines = ["## Markov Blanket"]
        lines.append("")

        # Lazy import keeps cogant.gnn.formatter importable even if the
        # markov sub-package is being restructured.
        try:
            from cogant.markov import MarkovBlanketExtractor, build_blanket_network
        except Exception as e:  # pragma: no cover - defensive
            lines.append(f"Markov blanket module unavailable: {e}")
            lines.append("")
            return "\n".join(lines)

        # Allow callers to pin a strategy through state-space metadata.
        strategy = "auto"
        module_names = None
        mapping_kinds = None
        if self.state_space.metadata:
            strategy = self.state_space.metadata.get("markov_blanket_strategy", "auto")
            module_names = self.state_space.metadata.get("markov_blanket_modules")
            mapping_kinds = self.state_space.metadata.get("markov_blanket_mapping_kinds")

        try:
            extractor = MarkovBlanketExtractor(self.graph)
            kwargs: Dict[str, Any] = {"strategy": strategy}
            if module_names:
                kwargs["module_names"] = list(module_names)
            if mapping_kinds and self.mappings:
                kwargs["mapping_kinds"] = list(mapping_kinds)
                kwargs["semantic_mappings"] = self.mappings
            blanket = extractor.extract(**kwargs)
            network = build_blanket_network(self.graph, blanket)
        except Exception as e:
            logger.warning(f"Markov blanket extraction failed: {e}")
            lines.append(f"Markov blanket extraction unavailable: {e}")
            lines.append("")
            return "\n".join(lines)

        internal_n = len(blanket.internal_ids)
        sensory_n = len(blanket.sensory_ids)
        active_n = len(blanket.active_ids)
        external_n = len(blanket.external_ids)
        total_n = internal_n + sensory_n + active_n + external_n
        boundary_n = sensory_n + active_n
        system_n = internal_n + sensory_n + active_n
        boundary_ratio = (boundary_n / system_n) if system_n else 0.0

        lines.append(
            "An Active-Inference Markov blanket partitions the program "
            "graph into four disjoint roles:"
        )
        lines.append("")
        lines.append("- **μ internal** — in the system of interest with no external neighbours.")
        lines.append("- **s sensory** — system nodes with incoming edges from outside.")
        lines.append("- **a active** — system nodes with outgoing edges to outside.")
        lines.append("- **η external** — nodes outside the system of interest.")
        lines.append("")
        lines.append(
            "The boundary `B = s ∪ a` renders the interior conditionally "
            "independent of the environment: `p(μ | s, a, η) = p(μ | s, a)`."
        )
        lines.append("")

        lines.append("### Partition Summary")
        lines.append("")
        lines.append(f"- **Seed strategy**: `{strategy}`")
        seeds_count = len(blanket.seeds)
        lines.append(f"- **Seed nodes**: {seeds_count}")
        lines.append(f"- **Total nodes**: {total_n}")
        lines.append(f"- **System (μ+s+a)**: {system_n}")
        lines.append(f"- **Boundary (s+a)**: {boundary_n}")
        lines.append(f"- **Boundary ratio**: {boundary_ratio:.3f}")
        lines.append("")

        lines.append("### Role Counts")
        lines.append("")
        lines.append("| Role | Symbol | Count |")
        lines.append("|----|:----:|----:|")
        lines.append(f"| Internal | μ | {internal_n} |")
        lines.append(f"| Sensory | s | {sensory_n} |")
        lines.append(f"| Active | a | {active_n} |")
        lines.append(f"| External | η | {external_n} |")
        lines.append("")

        # Top members per role (cap for readability).
        def _member_label(node_id: str) -> str:
            node = self.graph.nodes.get(node_id)
            if node is None:
                return node_id
            name = getattr(node, "name", None) or getattr(node, "label", None) or node_id
            kind = getattr(getattr(node, "kind", None), "value", "")
            return f"`{name}`" + (f" ({kind})" if kind else "")

        max_members = 8
        role_sections: List[Tuple[str, str, List[str]]] = [
            ("Internal (μ)", "internal", sorted(blanket.internal_ids)),
            ("Sensory (s)", "sensory", sorted(blanket.sensory_ids)),
            ("Active (a)", "active", sorted(blanket.active_ids)),
            ("External (η)", "external", sorted(blanket.external_ids)),
        ]
        lines.append("### Role Members")
        lines.append("")
        for title, _role_key, members in role_sections:
            total = len(members)
            lines.append(f"#### {title} — {total} node{'s' if total != 1 else ''}")
            lines.append("")
            if not members:
                lines.append("_(none)_")
            else:
                shown = members[:max_members]
                for node_id in shown:
                    lines.append(f"- {_member_label(node_id)}")
                if total > max_members:
                    lines.append(f"- … and {total - max_members} more")
            lines.append("")

        # Aggregate network edges between roles (already counted by network).
        if network.aggregate_edges:
            lines.append("### Aggregate Inter-Role Edges")
            lines.append("")
            lines.append("| Source Role | Target Role | Edge Count |")
            lines.append("|----|----|----:|")
            for (src_role, tgt_role), count in sorted(
                network.aggregate_edges.items(),
                key=lambda kv: (-kv[1], kv[0][0], kv[0][1]),
            ):
                lines.append(f"| {src_role} | {tgt_role} | {count} |")
            lines.append("")

        # Surface any strategy metadata (auto's scoreboard, chosen module).
        meta = dict(blanket.metadata or {})
        chosen = meta.get("chosen_module") or meta.get("module_name")
        if chosen:
            lines.append(f"- **Chosen module**: `{chosen}`")
        score = meta.get("score")
        if score is not None:
            lines.append(f"- **Cohesion score**: {score:.3f}")
        if chosen or score is not None:
            lines.append("")

        return "\n".join(lines)
