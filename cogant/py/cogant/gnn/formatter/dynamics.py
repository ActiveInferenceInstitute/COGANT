"""Dynamics section formatters for the GNN markdown export.

This module contains the ``_format_*`` methods that render the
dynamical (transitions, likelihoods, preferences, time, parameterization) canonical sections of a GNN model to markdown. It is a
mixin for :class:`cogant.gnn.formatter.GNNMarkdownFormatter`; it
does not stand on its own and expects ``self.graph``, ``self.state_space``,
``self.process``, and ``self.mappings`` to be populated by the
concrete formatter.

Families:
  * ``_format_transition_structure``
  * ``_format_likelihood_structure``
  * ``_format_preferences``
  * ``_format_time_settings``
  * ``_format_parameterization``

See :class:`cogant.gnn.formatter.base.GNNMarkdownFormatter` for the
main entry point and :mod:`cogant.gnn.formatter` for the package.
"""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from cogant.process.extractor import ProcessModel
from cogant.schemas.core import EdgeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import MappingKind
from cogant.statespace.compiler import StateSpaceModel

logger = logging.getLogger(__name__)


class _DynamicsSectionsMixin:
    # Attributes populated by the concrete formatter (see base.py).
    graph: ProgramGraph
    state_space: StateSpaceModel
    process: ProcessModel
    mappings: dict[str, Any]

    # Helper declared on the concrete formatter (base.py). Declared
    # here via ``TYPE_CHECKING`` so type checkers resolve it when the
    # mixin is inspected in isolation without replacing the real
    # implementation at runtime.
    if TYPE_CHECKING:
        @staticmethod
        def _action_effects(action: Any) -> list[str]: ...

    def _format_transition_structure(self) -> str:
        """Format transition structure section.

        Derives state transitions from:
        1. State space transitions (if present)
        2. Graph CALLS + WRITES edges (function calls that modify state)
        3. Process model connections showing workflow progression
        """
        lines = ["## Transition Structure"]
        lines.append("")

        # Option 1: Use state space transitions if present
        if self.state_space.transitions:
            lines.append(f"**Total Transitions**: {len(self.state_space.transitions)}")
            lines.append("")

            # Map variable IDs to names for display
            var_names = {vid: var.name for vid, var in self.state_space.variables.items()}

            # For each state variable, show which actions can modify it
            var_to_actions = defaultdict(list)
            for action_id, action in self.state_space.actions.items():
                for effect_var_id in self._action_effects(action):
                    var_to_actions[effect_var_id].append((action_id, action.name))

            if var_to_actions:
                lines.append("### Action Effects on State Variables")
                lines.append("")
                lines.append("| State Variable | Modifying Actions |")
                lines.append("|----|----|")
                for var_id, actions in sorted(var_to_actions.items()):
                    var_name = var_names.get(var_id, var_id)
                    action_strs = [f"{aname}({aid[:8]})" for aid, aname in actions[:3]]
                    lines.append(f"| {var_name} | {', '.join(action_strs)} |")
                lines.append("")

            # Show sample transitions
            lines.append("### Sample Transitions")
            lines.append("")
            lines.append("| ID | Action | Probability | Confidence |")
            lines.append("|----|----|------|------|")

            # Calculate transition probabilities by counting transitions per action
            action_to_count: dict[str, int] = defaultdict(int)
            for trans in self.state_space.transitions.values():
                action_key = trans.action_id or "spontaneous"
                action_to_count[action_key] += 1

            for trans_id, trans in list(self.state_space.transitions.items())[:20]:
                action_key = trans.action_id or "spontaneous"
                # Extract probability from transition or derive from count
                if trans.probability is not None:
                    prob = f"{trans.probability:.2f}"
                else:
                    # Derive from normalized action count: 1/N where N = transitions from that action
                    action_count = action_to_count.get(action_key, 1)
                    computed_prob = 1.0 / action_count if action_count > 0 else 1.0
                    prob = f"{computed_prob:.3f}"
                lines.append(f"| {trans_id[:12]} | {action_key} | {prob} | {trans.confidence.value} |")
            lines.append("")

        else:
            # Option 2: Derive transitions from graph structure (CALLS + WRITES edges)
            lines.append("### State Transitions Derived from Call Graph")
            lines.append("")

            # Find all CALLS edges that have corresponding WRITES edges from the same source
            defaultdict(list)
            calls_edges = []
            writes_edges = []

            for edge in self.graph.edges.values():
                if edge.kind == EdgeKind.CALLS:
                    calls_edges.append(edge)
                elif edge.kind == EdgeKind.WRITES:
                    writes_edges.append(edge)

            # Build map of nodes that write
            {e.target_id for e in writes_edges}

            # Show top call-to-write patterns
            call_write_patterns = []
            for call_edge in calls_edges:
                for write_edge in writes_edges:
                    if call_edge.source_id == write_edge.source_id:
                        source_node = self.graph.nodes.get(call_edge.source_id)
                        target_node = self.graph.nodes.get(call_edge.target_id)
                        write_node = self.graph.nodes.get(write_edge.target_id)
                        if source_node and target_node and write_node:
                            call_write_patterns.append({
                                'source': source_node.name,
                                'calls': target_node.name,
                                'writes': write_node.name,
                            })

            if call_write_patterns:
                lines.append("| Function | Calls | Modifies State |")
                lines.append("|----|----|------|")
                for pattern in call_write_patterns[:20]:
                    lines.append(f"| {pattern['source']} | {pattern['calls']} | {pattern['writes']} |")
                lines.append("")
            else:
                lines.append("No explicit call-to-write patterns detected.")
                lines.append("")

            # Show process model stage transitions if available
            if self.process.connections and len(self.process.connections) > 0:
                lines.append("### Process Model Stage Transitions")
                lines.append("")
                lines.append("| Stage | Next Stage(s) | Pattern |")
                lines.append("|----|----|------|")

                # Group connections by source stage
                stage_transitions: dict[str, list[Any]] = defaultdict(list)
                for conn in self.process.connections.values():
                    stage_transitions[conn.source_stage_id].append(conn)

                for src_stage in sorted(stage_transitions.keys())[:15]:
                    conns = stage_transitions[src_stage]
                    next_stages = [c.target_stage_id for c in conns]
                    pattern = "sequential" if len(next_stages) == 1 else "fan_out" if len(next_stages) > 1 else "terminal"
                    next_str = ", ".join(next_stages[:2])
                    if len(next_stages) > 2:
                        next_str += f", +{len(next_stages)-2} more"
                    lines.append(f"| {src_stage} | {next_str} | {pattern} |")
                lines.append("")

        return "\n".join(lines)
    def _format_likelihood_structure(self) -> str:
        """Format likelihood structure section."""
        lines = ["## Likelihood Structure"]
        lines.append("")

        if not self.state_space.likelihoods:
            lines.append("No likelihood distributions detected in this codebase.")
            lines.append("")
            return "\n".join(lines)

        # Map variable IDs to names
        var_names = {vid: var.name for vid, var in self.state_space.variables.items()}

        lines.append("### Distributions over State Variables")
        lines.append("")
        lines.append("| Variable | Distribution | Parameters | Confidence |")
        lines.append("|----|----|------|------|")
        for _like_id, like in self.state_space.likelihoods.items():
            var_name = var_names.get(like.variable_id, like.variable_id)
            # Handle parameters - could be dict or list
            if like.parameters:
                if isinstance(like.parameters, dict):
                    params = ", ".join([f"{k}={v:.2f}" for k, v in list(like.parameters.items())[:2]])
                elif isinstance(like.parameters, list):
                    params = ", ".join([str(p)[:20] for p in like.parameters[:2]])
                else:
                    params = str(like.parameters)[:30]
            else:
                params = "none"
            lines.append(f"| {var_name} | {like.distribution_type} | {params} | {like.confidence.value} |")
        lines.append("")

        # Show observation dependencies
        lines.append("### Observation Dependencies")
        lines.append("")
        lines.append("State variables that are observed through modalities:")
        lines.append("")
        lines.append("| Variable | Observations |")
        lines.append("|----|----|")

        # Map observations to their observed variables
        var_to_obs = defaultdict(list)

        # Use source_node_id from ObservationModality to find READS edges to state variables
        for _obs_id, obs in self.state_space.observations.items():
            # Find state variables this observation connects to via READS edges in the graph
            source_node_id = obs.source_node_id

            if source_node_id and source_node_id in self.graph.nodes:
                # Get READS edges from the observation source node
                reads_edges = [e for e in self.graph.edges.values()
                              if e.kind == EdgeKind.READS and e.source_id == source_node_id]

                # Map READS edge targets to state variables
                for edge in reads_edges:
                    # Find which state variable corresponds to this target node
                    target_node = self.graph.nodes.get(edge.target_id)
                    if target_node:
                        # Match state variables by their representation in the graph
                        for var_id, var in self.state_space.variables.items():
                            # Check if this state variable represents the target node
                            if target_node.name.lower() in var.name.lower() or var.name.lower() in target_node.name.lower():
                                var_to_obs[var_id].append(obs.name)
                                break
                        else:
                            # If no perfect match, add to first variable as fallback
                            if self.state_space.variables:
                                first_var_id = next(iter(self.state_space.variables.keys()))
                                var_to_obs[first_var_id].append(obs.name)
            else:
                # Fallback: infer from naming similarity
                for var_id, var in self.state_space.variables.items():
                    if var.name.lower() in obs.name.lower() or obs.name.lower() in var.name.lower():
                        var_to_obs[var_id].append(obs.name)

        if var_to_obs:
            for var_id, obs_list in sorted(var_to_obs.items()):
                var_name = var_names.get(var_id, var_id)
                obs_str = ", ".join(list(dict.fromkeys(obs_list))[:3])  # Remove duplicates, keep first 3
                lines.append(f"| {var_name} | {obs_str} |")
        else:
            lines.append("| (no observed dependencies detected) | |")

        lines.append("")

        return "\n".join(lines)
    def _format_preferences(self) -> str:
        """Format preferences and constraints section."""
        lines = ["## Preferences Constraints"]
        lines.append("")

        # State space preferences
        if self.state_space.preferences:
            lines.append("### Preferences")
            lines.append("")
            lines.append("| ID | Name | Scope Variables | Weight | Expression | Source |")
            lines.append("|----|----|------|------|------|------|")
            for pref_id, pref in list(self.state_space.preferences.items())[:20]:
                scope_str = ", ".join(pref.scope[:2]) if pref.scope else "global"
                source = pref.source or "derived"
                lines.append(f"| {pref_id[:12]} | {pref.name} | {scope_str} | {pref.weight} | {pref.expression[:30]} | {source} |")
            lines.append("")
        else:
            lines.append("No preferences detected in this codebase.")
            lines.append("")

        # Constraint mappings from semantic analysis
        constraint_mappings = [m for m in self.mappings.values() if hasattr(m, 'kind') and m.kind == MappingKind.CONSTRAINT]
        if constraint_mappings:
            lines.append("### Constraint Mappings")
            lines.append("")
            lines.append("| ID | Label | Evidence Count | Confidence | Status |")
            lines.append("|----|----|------|------|------|")
            for mapping in constraint_mappings[:30]:
                lines.append(f"| {mapping.id[:12]} | {mapping.semantic_label} | {mapping.evidence_count} | {mapping.confidence_score:.2f} | {mapping.status} |")
            lines.append("")

        return "\n".join(lines)
    def _format_time_settings(self) -> str:
        """Format time settings section."""
        lines = ["## Time Settings"]
        lines.append("")
        lines.append(f"- **Time Regime**: {self.state_space.time_regime.value}")

        # Extract time settings from metadata
        if self.state_space.metadata:
            # Step unit
            if "step_unit" in self.state_space.metadata:
                lines.append(f"- **Step Unit**: {self.state_space.metadata['step_unit']}")
            else:
                # Default based on time regime
                lines.append(f"- **Step Unit**: {'discrete' if self.state_space.time_regime.value == 'discrete' else 'continuous'}")

            # Synchronization mode
            if "is_async" in self.state_space.metadata:
                async_flag = "asynchronous" if self.state_space.metadata['is_async'] else "synchronous"
            else:
                async_flag = "synchronous"
            lines.append(f"- **Synchronization**: {async_flag}")

            # Max steps
            if "max_steps" in self.state_space.metadata:
                lines.append(f"- **Max Steps**: {self.state_space.metadata['max_steps']}")

            # Temporal analysis results
            if "temporal_patterns" in self.state_space.metadata:
                patterns = self.state_space.metadata['temporal_patterns']
                if patterns:
                    pattern_str = ", ".join(patterns[:3])
                    lines.append(f"- **Temporal Patterns**: {pattern_str}")

            # Clock / event frequency
            if "clock_frequency" in self.state_space.metadata:
                lines.append(f"- **Clock Frequency**: {self.state_space.metadata['clock_frequency']}")

        lines.append("")

        return "\n".join(lines)
    def _format_parameterization(self) -> str:
        """Format parameterization section."""
        lines = ["## Parameterization"]
        lines.append("")

        if not self.mappings:
            lines.append("No parameterization data found.")
            lines.append("")
            return "\n".join(lines)

        # Extract confidence parameters
        lines.append("### Confidence Parameters")
        lines.append("")
        lines.append("| Parameter | Value/Range | Source |")
        lines.append("|----|----|------|")

        confidence_scores = []
        for mapping in self.mappings.values():
            if hasattr(mapping, 'confidence_score'):
                confidence_scores.append(mapping.confidence_score)

        if confidence_scores:
            min_conf = min(confidence_scores)
            max_conf = max(confidence_scores)
            avg_conf = sum(confidence_scores) / len(confidence_scores)
            lines.append(f"| Confidence (Mean) | {avg_conf:.3f} | mappings |")
            lines.append(f"| Confidence (Range) | [{min_conf:.3f}, {max_conf:.3f}] | mappings |")

        # Threshold settings
        if self.state_space.metadata:
            if "confidence_threshold" in self.state_space.metadata:
                lines.append(f"| Confidence Threshold | {self.state_space.metadata['confidence_threshold']} | configuration |")

        lines.append("")

        # Translation rules extracted from mapping provenance
        lines.append("### Translation Rules")
        lines.append("")
        lines.append("| Rule Type | Count | Average Confidence | Status |")
        lines.append("|----|----|------|------|")

        # Count rules by mapping kind
        rule_counts: dict[str, int] = defaultdict(int)
        rule_confidence: dict[str, list[float]] = defaultdict(list)
        rule_status: dict[str, int] = defaultdict(int)

        for mapping in self.mappings.values():
            if hasattr(mapping, 'kind'):
                kind = mapping.kind.value
                rule_counts[kind] += 1
                if hasattr(mapping, 'confidence_score'):
                    rule_confidence[kind].append(mapping.confidence_score)
                if hasattr(mapping, 'status'):
                    rule_status[(kind, mapping.status)] += 1

        for kind in sorted(rule_counts.keys()):
            count = rule_counts[kind]
            avg_conf = sum(rule_confidence[kind]) / len(rule_confidence[kind]) if rule_confidence[kind] else 0.0
            status_list = [s for (k, s), cnt in rule_status.items() if k == kind]
            lines.append(f"| {kind} | {count} | {avg_conf:.3f} | {', '.join(set(status_list))} |")

        lines.append("")

        # Rule weights from preferences
        if self.state_space.preferences:
            lines.append("### Rule Weights")
            lines.append("")
            lines.append("| Rule | Weight | Impact |")
            lines.append("|----|----|------|")
            for _pref_id, pref in list(self.state_space.preferences.items())[:10]:
                impact = "high" if pref.weight > 0.7 else "medium" if pref.weight > 0.3 else "low"
                lines.append(f"| {pref.name} | {pref.weight:.2f} | {impact} |")
            lines.append("")

        return "\n".join(lines)
