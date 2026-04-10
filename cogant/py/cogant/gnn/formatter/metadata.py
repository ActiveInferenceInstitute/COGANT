"""Metadata section formatters for the GNN markdown export.

This module contains the ``_format_*`` methods that render the
metadata-level (model, repo, source coverage, provenance, confidence, rendering, validation) canonical sections of a GNN model to markdown. It is a
mixin for :class:`cogant.gnn.formatter.GNNMarkdownFormatter`; it
does not stand on its own and expects ``self.graph``, ``self.state_space``,
``self.process``, and ``self.mappings`` to be populated by the
concrete formatter.

Families:
  * ``_format_model_metadata``
  * ``_format_repository_metadata``
  * ``_format_source_coverage``
  * ``_format_provenance``
  * ``_format_confidence``
  * ``_format_rendering_hints``
  * ``_format_validation_notes``

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


class _MetadataSectionsMixin:
    # Attributes populated by the concrete formatter (see base.py).
    # Declared here so that type checkers can resolve references in
    # mixin methods without running into missing-attribute errors.
    graph: ProgramGraph
    state_space: StateSpaceModel
    process: ProcessModel
    mappings: Dict[str, Any]

    def _format_model_metadata(self) -> str:
        """Format model metadata section."""
        lines = ["# GNN Model: " + self.state_space.schema_name]
        lines.append("")
        lines.append("## Model Metadata")
        lines.append("")
        lines.append(f"- **Model ID**: {self.state_space.id}")
        lines.append(f"- **Schema Name**: {self.state_space.schema_name}")
        lines.append(f"- **Generated**: {datetime.now(timezone.utc).isoformat()}")
        lines.append(f"- **COGANT Version**: 0.1.0")

        # Pipeline stages from metadata
        if self.state_space.metadata and "pipeline_stages" in self.state_space.metadata:
            stages = self.state_space.metadata["pipeline_stages"]
            lines.append(f"- **Pipeline Stages**: {', '.join(stages)}")

        # Extraction time
        if self.state_space.metadata and "extraction_time_ms" in self.state_space.metadata:
            lines.append(f"- **Extraction Time**: {self.state_space.metadata['extraction_time_ms']} ms")

        lines.append(f"- **State Variables**: {len(self.state_space.variables)}")
        lines.append(f"- **Observations**: {len(self.state_space.observations)}")
        lines.append(f"- **Actions**: {len(self.state_space.actions)}")
        lines.append("")

        return "\n".join(lines)
    def _format_repository_metadata(self) -> str:
        """Format repository metadata section."""
        lines = ["## Repository Metadata"]
        lines.append("")
        if self.graph.metadata:
            meta = self.graph.metadata
            lines.append(f"- **Repository URI**: {meta.repo_uri}")

            # Count files by language (includes both FILE and MODULE nodes, which may represent files)
            file_count = sum(1 for node in self.graph.nodes.values() if node.kind in (NodeKind.FILE, NodeKind.MODULE))
            lines.append(f"- **File Count**: {file_count}")

            if meta.languages:
                lines.append(f"- **Languages**: {', '.join(sorted(meta.languages))}")
            else:
                lines.append("- **Languages**: Not detected")

            # Calculate total lines of code (from metadata if available)
            if "total_lines" in meta.custom_metadata:
                lines.append(f"- **Total Lines of Code**: {meta.custom_metadata['total_lines']}")

            lines.append(f"- **Schema Version**: {meta.version}")
            lines.append(f"- **Created**: {meta.created_at.isoformat()}")
            lines.append(f"- **Updated**: {meta.updated_at.isoformat()}")

            if meta.evidence_sources:
                lines.append(f"- **Evidence Sources**: {', '.join(meta.evidence_sources)}")
        else:
            lines.append("No repository metadata available.")

        lines.append("")

        return "\n".join(lines)
    def _format_source_coverage(self) -> str:
        """Format source coverage section."""
        lines = ["## Source Coverage"]
        lines.append("")

        # Count nodes by kind
        node_counts: Dict[str, int] = defaultdict(int)
        for node in self.graph.nodes.values():
            node_counts[node.kind.value] += 1

        # Count edges by kind
        edge_counts: Dict[str, int] = defaultdict(int)
        for edge in self.graph.edges.values():
            edge_counts[edge.kind.value] += 1

        # Node breakdown table
        lines.append("### Nodes by Kind")
        lines.append("")
        lines.append("| Kind | Count |")
        lines.append("|------|-------|")
        for kind in sorted(node_counts.keys()):
            lines.append(f"| {kind} | {node_counts[kind]} |")
        lines.append(f"| **Total** | **{len(self.graph.nodes)}** |")
        lines.append("")

        # Edge breakdown table
        lines.append("### Edges by Kind")
        lines.append("")
        lines.append("| Kind | Count |")
        lines.append("|------|-------|")
        for kind in sorted(edge_counts.keys()):
            lines.append(f"| {kind} | {edge_counts[kind]} |")
        lines.append(f"| **Total** | **{len(self.graph.edges)}** |")
        lines.append("")

        # Semantic coverage: count nodes that appear in at least one mapping
        covered_nodes = set()
        for mapping in self.mappings.values():
            if hasattr(mapping, 'graph_fragment_node_ids'):
                covered_nodes.update(mapping.graph_fragment_node_ids)

        if len(self.graph.nodes) > 0:
            coverage = (len(covered_nodes) / len(self.graph.nodes)) * 100
            lines.append(f"- **Semantic Coverage**: {coverage:.1f}% ({len(covered_nodes)}/{len(self.graph.nodes)} nodes appear in semantic mappings)")
        lines.append("")

        return "\n".join(lines)
    def _format_provenance(self) -> str:
        """Format provenance section."""
        lines = ["## Provenance"]
        lines.append("")

        # Files parsed (from graph metadata)
        if self.graph.metadata and self.graph.metadata.evidence_sources:
            lines.append("### Evidence Sources from Repository")
            lines.append("")
            lines.append("| Source | Count |")
            lines.append("|----|----|")
            source_counts: Dict[str, int] = defaultdict(int)
            for source in self.graph.metadata.evidence_sources:
                source_counts[source] += 1
            for source in sorted(source_counts.keys()):
                lines.append(f"| {source} | {source_counts[source]} |")
            lines.append("")

        # Provenance from mappings
        lines.append("### Provenance Chain for Semantic Mappings")
        lines.append("")
        if self.mappings:
            provenance_sources: Dict[str, int] = defaultdict(int)
            provenance_confidence: Dict[str, List[float]] = defaultdict(list)

            for mapping in self.mappings.values():
                if hasattr(mapping, 'provenance') and mapping.provenance:
                    for prov in mapping.provenance:
                        source = prov.source if hasattr(prov, 'source') else 'unknown'
                        provenance_sources[source] += 1
                        confidence = prov.confidence if hasattr(prov, 'confidence') else 0.0
                        provenance_confidence[source].append(confidence)

            if provenance_sources:
                lines.append("| Source Type | Count | Average Confidence |")
                lines.append("|------|-------|-----------|")
                for source in sorted(provenance_sources.keys()):
                    count = provenance_sources[source]
                    avg_conf = sum(provenance_confidence[source]) / len(provenance_confidence[source]) if provenance_confidence[source] else 0.0
                    lines.append(f"| {source} | {count} | {avg_conf:.3f} |")
            else:
                lines.append("No provenance chains found in mappings.")
        lines.append("")

        # Rules and mappings created
        lines.append("### Extraction Methods")
        lines.append("")
        if self.mappings:
            lines.append(f"- **Semantic Mappings Created**: {len(self.mappings)}")
        if self.state_space.variables:
            lines.append(f"- **State Variables Extracted**: {len(self.state_space.variables)}")
        if self.state_space.observations:
            lines.append(f"- **Observations Identified**: {len(self.state_space.observations)}")
        if self.state_space.actions:
            lines.append(f"- **Actions Extracted**: {len(self.state_space.actions)}")
        if self.process.stages:
            lines.append(f"- **Process Stages Identified**: {len(self.process.stages)}")

        lines.append("")

        # Confidence tier distribution
        if self.mappings:
            lines.append("### Confidence Tiers")
            lines.append("")
            lines.append("| Tier | Count |")
            lines.append("|----|----|")
            tier_counts: Dict[str, int] = defaultdict(int)
            for mapping in self.mappings.values():
                if hasattr(mapping, 'confidence_tier'):
                    tier_counts[mapping.confidence_tier.value] += 1
            for tier in sorted(tier_counts.keys()):
                lines.append(f"| {tier} | {tier_counts[tier]} |")
            lines.append("")

        return "\n".join(lines)
    def _format_confidence(self) -> str:
        """Format confidence scores section."""
        lines = ["## Confidence Scores"]
        lines.append("")

        if not self.mappings:
            lines.append("No mappings to analyze for confidence.")
            lines.append("")
            return "\n".join(lines)

        # Calculate confidence statistics by mapping kind
        lines.append("### Confidence by Mapping Kind")
        lines.append("")
        lines.append("| Kind | Mean | Min | Max | Count |")
        lines.append("|----|----|------|------|------|")

        kind_confidences = defaultdict(list)
        for mapping in self.mappings.values():
            if hasattr(mapping, 'kind') and hasattr(mapping, 'confidence_score'):
                kind_confidences[mapping.kind.value].append(mapping.confidence_score)

        for kind in sorted(kind_confidences.keys()):
            scores = kind_confidences[kind]
            mean = sum(scores) / len(scores) if scores else 0
            min_s = min(scores) if scores else 0
            max_s = max(scores) if scores else 0
            lines.append(f"| {kind} | {mean:.3f} | {min_s:.3f} | {max_s:.3f} | {len(scores)} |")

        lines.append("")

        # Overall statistics with distribution
        lines.append("### Overall Statistics")
        lines.append("")
        all_scores = [m.confidence_score for m in self.mappings.values() if hasattr(m, 'confidence_score')]
        if all_scores:
            overall_mean = sum(all_scores) / len(all_scores)
            overall_min = min(all_scores)
            overall_max = max(all_scores)
            lines.append(f"- **Mean Confidence**: {overall_mean:.3f}")
            lines.append(f"- **Min Confidence**: {overall_min:.3f}")
            lines.append(f"- **Max Confidence**: {overall_max:.3f}")
            lines.append(f"- **Total Mappings Analyzed**: {len(all_scores)}")

        lines.append("")

        # Confidence distribution histogram
        lines.append("### Confidence Distribution")
        lines.append("")
        if all_scores:
            high_conf = sum(1 for s in all_scores if s > 0.8)
            medium_conf = sum(1 for s in all_scores if 0.5 <= s <= 0.8)
            low_conf = sum(1 for s in all_scores if s < 0.5)

            lines.append("| Tier | Count | Percentage | Histogram |")
            lines.append("|------|-------|------------|-----------|")

            # Create simple ASCII histogram
            max_count = max(high_conf, medium_conf, low_conf)
            bar_width = 30

            def make_bar(count, max_val, width):
                """Build a fixed-width ASCII bar for a histogram cell."""
                if max_val == 0:
                    return "█" * 0
                filled = int((count / max_val) * width)
                return "█" * filled + "░" * (width - filled)

            high_pct = (high_conf / len(all_scores) * 100) if all_scores else 0
            med_pct = (medium_conf / len(all_scores) * 100) if all_scores else 0
            low_pct = (low_conf / len(all_scores) * 100) if all_scores else 0

            lines.append(f"| High (>0.8) | {high_conf} | {high_pct:.1f}% | {make_bar(high_conf, max_count, bar_width)} |")
            lines.append(f"| Medium (0.5-0.8) | {medium_conf} | {med_pct:.1f}% | {make_bar(medium_conf, max_count, bar_width)} |")
            lines.append(f"| Low (<0.5) | {low_conf} | {low_pct:.1f}% | {make_bar(low_conf, max_count, bar_width)} |")

        lines.append("")

        return "\n".join(lines)
    def _format_rendering_hints(self) -> str:
        """Format rendering hints section."""
        lines = ["## Rendering Hints"]
        lines.append("")

        lines.append("### Suggested Graph Layout")
        lines.append("")

        # Heuristics for layout suggestions
        if len(self.graph.nodes) > 500:
            lines.append("- **Algorithm**: Hierarchical/DAG layout (large graph)")
            lines.append("- **Clustering**: Group by file or module")
        elif len(self.graph.nodes) > 100:
            lines.append("- **Algorithm**: Force-directed (medium graph)")
            lines.append("- **Clustering**: Group by node kind")
        else:
            lines.append("- **Algorithm**: Circular or planar (small graph)")

        lines.append("")
        lines.append("### Key Nodes to Highlight")
        lines.append("")

        # Find high-degree nodes
        node_degrees: Dict[str, int] = defaultdict(int)
        for edge in self.graph.edges.values():
            node_degrees[edge.source_id] += 1
            node_degrees[edge.target_id] += 1

        top_nodes = sorted(node_degrees.items(), key=lambda x: x[1], reverse=True)[:10]
        lines.append("| Node Name | In/Out Degree | Kind |")
        lines.append("|----|----|------|")
        for node_id, degree in top_nodes:
            if node_id in self.graph.nodes:
                node = self.graph.nodes[node_id]
                lines.append(f"| {node.name} | {degree} | {node.kind.value} |")

        lines.append("")
        lines.append("### Recommended Mermaid Diagrams")
        lines.append("")

        # Count specific node and edge types for recommendations
        class_count = sum(1 for n in self.graph.nodes.values() if n.kind == NodeKind.CLASS)
        state_var_count = len(self.state_space.variables)
        call_edges = sum(1 for e in self.graph.edges.values() if e.kind == EdgeKind.CALLS)
        action_mappings = sum(1 for m in self.mappings.values() if hasattr(m, 'kind') and m.kind == MappingKind.ACTION)

        lines.append("Based on detected elements:")
        lines.append("")

        if class_count > 0:
            lines.append(f"- **class_diagram.mermaid**: {class_count} classes detected")
        if state_var_count > 0:
            lines.append(f"- **state_diagram.mermaid**: {state_var_count} state variables ({len(self.state_space.transitions)} transitions)")
        if call_edges > 3:
            lines.append(f"- **sequence_diagram.mermaid**: {call_edges} call edges (ideal for call sequences)")
        if action_mappings > 0:
            lines.append(f"- **flowchart.mermaid**: {action_mappings} semantic action mappings found")

        lines.append("")
        lines.append("### Recommended Views")
        lines.append("")
        lines.append("- **Data Flow Graph**: Show READS/WRITES edges to understand data dependencies")
        lines.append("- **Control Flow Graph**: Show CALLS/TRIGGERS edges to understand execution")
        lines.append("- **Semantic Graph**: Show ACTION/OBSERVATION/CONSTRAINT mappings")
        lines.append("- **State Variable Graph**: Show variable factorization and dependencies")
        lines.append("")

        return "\n".join(lines)
    def _format_validation_notes(self) -> str:
        """Format validation notes section."""
        lines = ["## Validation Notes"]
        lines.append("")

        # Run basic validation checks
        checks = {
            "nodes_exist": len(self.graph.nodes) > 0,
            "edges_exist": len(self.graph.edges) > 0,
            "variables_defined": len(self.state_space.variables) > 0,
            "observations_defined": len(self.state_space.observations) > 0,
            "actions_defined": len(self.state_space.actions) > 0,
            "transitions_defined": len(self.state_space.transitions) > 0,
        }

        lines.append("### Validation Results")
        lines.append("")
        lines.append("| Check | Status |")
        lines.append("|----|----|")

        pass_count = 0
        fail_count = 0

        for check_name, result in checks.items():
            status = "✓ PASS" if result else "✗ FAIL"
            if result:
                pass_count += 1
            else:
                fail_count += 1
            check_label = check_name.replace("_", " ").title()
            lines.append(f"| {check_label} | {status} |")

        lines.append("")
        lines.append(f"**Validation Summary**: {pass_count} passed, {fail_count} failed")
        lines.append("")

        # Semantic mapping coverage statistics
        lines.append("### Semantic Mapping Coverage")
        lines.append("")

        unmapped_nodes = set(self.graph.nodes.keys())
        for mapping in self.mappings.values():
            if hasattr(mapping, 'graph_fragment_node_ids'):
                unmapped_nodes -= set(mapping.graph_fragment_node_ids)

        unmapped_edges = set(self.graph.edges.keys())
        for mapping in self.mappings.values():
            if hasattr(mapping, 'graph_fragment_edge_ids'):
                unmapped_edges -= set(mapping.graph_fragment_edge_ids)

        lines.append(f"- **Nodes with semantic mappings**: {len(self.graph.nodes) - len(unmapped_nodes)}/{len(self.graph.nodes)}")
        lines.append(f"- **Nodes without mappings**: {len(unmapped_nodes)}")
        lines.append(f"- **Edges with semantic mappings**: {len(self.graph.edges) - len(unmapped_edges)}/{len(self.graph.edges)}")
        lines.append(f"- **Edges without mappings**: {len(unmapped_edges)}")
        lines.append("")

        # Consistency warnings
        lines.append("### Issues and Warnings")
        lines.append("")

        warnings = []

        # Check for orphaned nodes
        orphan_list = []
        for node_id in self.graph.nodes:
            in_edges = sum(1 for e in self.graph.edges.values() if e.target_id == node_id)
            out_edges = sum(1 for e in self.graph.edges.values() if e.source_id == node_id)
            if in_edges == 0 and out_edges == 0:
                orphan_list.append(node_id)

        if orphan_list:
            warnings.append(f"- {len(orphan_list)} orphaned nodes (no incoming/outgoing edges)")
            if len(orphan_list) <= 5:
                node_names = [self.graph.nodes[nid].name if nid in self.graph.nodes else nid for nid in orphan_list[:5]]
                warnings.append(f"  Examples: {', '.join(node_names)}")

        # Check for variables without observations
        # Since observations don't link to variables directly in the schema, count unobserved heuristically
        if len(self.state_space.variables) > 0 and len(self.state_space.observations) == 0:
            warnings.append(f"- {len(self.state_space.variables)} state variables have no observation modalities defined")

        # Check for actions with no effects
        actionless = sum(1 for a in self.state_space.actions.values() if not a.effects)
        if actionless > 0:
            warnings.append(f"- {actionless} actions have no effects on state variables")

        # Check for variables with no transitions
        vars_with_transitions: Set[str] = set()
        for trans in self.state_space.transitions.values():
            if hasattr(trans, 'source_state') and trans.source_state:
                src: Any = trans.source_state
                # source_state could be a dict or string
                if isinstance(src, dict):
                    src = str(src.get('id', src.get('var_id', str(src))))
                vars_with_transitions.add(str(src))
            if hasattr(trans, 'target_state') and trans.target_state:
                tgt: Any = trans.target_state
                # target_state could be a dict or string
                if isinstance(tgt, dict):
                    tgt = str(tgt.get('id', tgt.get('var_id', str(tgt))))
                vars_with_transitions.add(str(tgt))

        static_vars = len(self.state_space.variables) - len(vars_with_transitions)
        if static_vars > 0:
            warnings.append(f"- {static_vars} state variables never transition (always static)")

        if warnings:
            for warn in warnings:
                lines.append(warn)
        else:
            lines.append("No significant issues detected.")

        lines.append("")

        return "\n".join(lines)
