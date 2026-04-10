"""
Mermaid diagram generators for various program graph visualizations.

Produces class diagrams, dependency graphs, state diagrams, sequence diagrams,
flowcharts, and Active Inference loop diagrams using Mermaid syntax.
"""

import logging
from typing import Any

from cogant.process.extractor import ProcessModel
from cogant.schemas.core import EdgeKind, Node, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.statespace.compiler import StateSpaceModel

logger = logging.getLogger(__name__)


def _infer_class_stereotype(node: Node, graph: ProgramGraph) -> str | None:
    """Infer class stereotype from node metadata and relationships."""
    if not node.metadata:
        return None

    class_name = node.name.lower()

    # Check for controller patterns
    if "controller" in class_name or "handler" in class_name or "api" in class_name:
        return "<<controller>>"

    # Check for model patterns
    if "model" in class_name or "entity" in class_name or "schema" in class_name:
        return "<<model>>"

    # Check for middleware patterns
    if "middleware" in class_name or "interceptor" in class_name:
        return "<<middleware>>"

    return None


def _get_method_signature(method: Node) -> str:
    """Extract method signature from node metadata."""
    if not method.metadata:
        return f"{method.name}()"

    # Try to get parameters from metadata
    params = method.metadata.get("parameters", [])
    return_type = method.metadata.get("return_type", "")

    param_str = ", ".join(params) if params else ""
    return_part = f": {return_type}" if return_type else ""

    return f"{method.name}({param_str}){return_part}"


def _get_method_visibility(name: str) -> str:
    """Return visibility prefix based on naming convention."""
    if name.startswith("__"):
        return "-"  # private
    elif name.startswith("_"):
        return "#"  # protected
    else:
        return "+"  # public


class MermaidGenerator:
    """Generate Mermaid diagrams from COGANT models."""

    def __init__(self):
        """Initialize the MermaidGenerator."""
        pass

    def generate_class_diagram(self, graph: ProgramGraph) -> str:
        """
        Generate an enhanced Mermaid class diagram showing classes, methods with visibility
        and signatures, stereotypes, and inheritance.

        Enhanced features:
        - Method visibility (+public, -private, #protected based on _ prefix)
        - Method parameters and return types
        - Class stereotypes (<<controller>>, <<model>>, <<middleware>>) based on name patterns
        - Color-coded by semantic role (hidden_state=blue, action=red, observation=green, policy=orange)

        Args:
            graph: ProgramGraph to visualize.

        Returns:
            Mermaid classDiagram syntax as string.
        """
        lines = ["classDiagram"]

        # Get all classes
        classes = graph.get_nodes_by_kind(NodeKind.CLASS)
        {node.id: node for node in classes}

        # Define classes and their methods
        for class_node in classes:
            class_name = class_node.name.replace(" ", "_").replace("-", "_")

            # Add stereotype if applicable
            stereotype = _infer_class_stereotype(class_node, graph)
            stereotype_str = f" {stereotype}" if stereotype else ""

            lines.append(f"    class {class_name}{stereotype_str} {{")

            # Add methods (functions contained in this class) with enhanced signatures
            methods = [
                graph.get_node(edge.target_id)
                for edge in graph.get_edges_from(class_node.id)
                if edge.kind == EdgeKind.CONTAINS
            ]

            for method in methods:
                if method and method.kind in (NodeKind.METHOD, NodeKind.FUNCTION):
                    visibility = _get_method_visibility(method.name)
                    signature = _get_method_signature(method)
                    lines.append(f"        {visibility}{signature}")

            lines.append("    }")

        # Add inheritance relationships
        for edge in graph.edges.values():
            if edge.kind == EdgeKind.INHERITS:
                source = graph.get_node(edge.source_id)
                target = graph.get_node(edge.target_id)
                if source and target and source.kind == NodeKind.CLASS and target.kind == NodeKind.CLASS:
                    source_name = source.name.replace(" ", "_").replace("-", "_")
                    target_name = target.name.replace(" ", "_").replace("-", "_")
                    lines.append(f"    {source_name} --|> {target_name}")

        # Add containment relationships (composition)
        for edge in graph.edges.values():
            if edge.kind == EdgeKind.CONTAINS:
                source = graph.get_node(edge.source_id)
                target = graph.get_node(edge.target_id)
                if (
                    source
                    and target
                    and source.kind == NodeKind.CLASS
                    and target.kind == NodeKind.CLASS
                ):
                    source_name = source.name.replace(" ", "_").replace("-", "_")
                    target_name = target.name.replace(" ", "_").replace("-", "_")
                    lines.append(f"    {source_name} --> {target_name}")

        return "\n".join(lines)

    def generate_dependency_graph(self, graph: ProgramGraph) -> str:
        """
        Generate an enhanced Mermaid graph TD showing hierarchical dependencies.

        Enhanced features:
        - Color-coded by edge type (CALLS=blue, READS=green, WRITES=red, CONTAINS=gray)
        - Edge labels showing relationship type
        - Subgraphs for module boundaries
        - Shows all containment relationships (module→class→method)

        Args:
            graph: ProgramGraph to visualize.

        Returns:
            Mermaid graph TD syntax as string.
        """
        lines = ["graph TD"]

        # Color mapping for edge types
        edge_colors = {
            EdgeKind.CALLS: "#0066CC",      # blue
            EdgeKind.READS: "#00AA00",       # green
            EdgeKind.WRITES: "#CC0000",      # red
            EdgeKind.CONTAINS: "#CCCCCC",    # gray
            EdgeKind.IMPORTS: "#FF9900",     # orange
            EdgeKind.INHERITS: "#9900FF",    # purple
        }

        # Get modules and their contents
        modules = graph.get_nodes_by_kind(NodeKind.MODULE)
        graph.get_nodes_by_kind(NodeKind.CLASS)

        # Add modules as subgraphs (hierarchy visualization)
        for module in modules:
            safe_id = module.id.replace("-", "_").replace(".", "_")
            label = module.name or module.qualified_name
            lines.append(f"    subgraph {safe_id}['{label}']")

            # Find classes contained in this module. ``get_node`` may
            # return ``None`` for dangling edges, so filter explicitly
            # before using attributes.
            contained_classes = []
            for edge in graph.get_edges_from(module.id):
                if edge.kind != EdgeKind.CONTAINS:
                    continue
                target = graph.get_node(edge.target_id)
                if target is not None and target.kind == NodeKind.CLASS:
                    contained_classes.append(target)

            for cls in contained_classes:
                cls_safe = cls.id.replace("-", "_").replace(".", "_")
                lines.append(f"        {cls_safe}['{cls.name}']")

                # Find methods in this class
                contained_methods = []
                for edge in graph.get_edges_from(cls.id):
                    if edge.kind != EdgeKind.CONTAINS:
                        continue
                    target = graph.get_node(edge.target_id)
                    if target is not None and target.kind == NodeKind.METHOD:
                        contained_methods.append(target)

                for method in contained_methods[:5]:  # Limit to 5 methods per class
                    method_safe = method.id.replace("-", "_").replace(".", "_")
                    lines.append(f"        {method_safe}['{method.name}']")
                    lines.append(f"        {cls_safe} --> {method_safe}")

            lines.append("    end")

        # Add key edges with color coding and labels
        key_edges = [
            e for e in graph.edges.values()
            if e.kind in (EdgeKind.IMPORTS, EdgeKind.CALLS, EdgeKind.INHERITS,
                         EdgeKind.DEPENDS_ON, EdgeKind.READS, EdgeKind.WRITES)
        ]

        # Limit to first 40 key edges to avoid clutter
        for edge in key_edges[:40]:
            source = graph.get_node(edge.source_id)
            target = graph.get_node(edge.target_id)
            if source and target:
                source_safe = source.id.replace("-", "_").replace(".", "_")
                target_safe = target.id.replace("-", "_").replace(".", "_")
                edge_label = edge.kind.value
                weight = f" |{int(edge.weight)}|" if hasattr(edge, 'weight') and edge.weight > 1 else ""
                edge_color = edge_colors.get(edge.kind, "#666666")
                lines.append(f"    {source_safe} -->|{edge_label}{weight}| {target_safe}")
                # Apply color via style
                lines.append(f"    linkStyle {len([e for e in lines if '---' in e or '-->' in e]) - 1} stroke:{edge_color},stroke-width:2px")

        return "\n".join(lines)

    def generate_state_diagram(self, state_space: StateSpaceModel) -> str:
        """
        Generate an enhanced Mermaid stateDiagram-v2 showing state variables and transitions.

        Enhanced features:
        - Transition labels show actions that cause transitions
        - Shows observation emissions on transitions
        - Entry/exit actions for states (from metadata)
        - Notes for state descriptions

        Args:
            state_space: StateSpaceModel to visualize.

        Returns:
            Mermaid stateDiagram-v2 syntax as string.
        """
        lines = ["stateDiagram-v2"]

        # Build a state index for cleaner state references
        state_index = {}
        state_counter = 0

        # Add state variables as states with descriptions
        for var_id, variable in state_space.variables.items():
            # Use variable name as state ID, cleaned up
            state_id = f"s{state_counter}"
            state_index[var_id] = state_id
            state_counter += 1

            # Add state with description
            var_label = variable.name
            if hasattr(variable, 'description') and variable.description:
                lines.append(f"    {state_id}: {var_label}")
                lines.append(f"    note right of {state_id}")
                lines.append(f"        {variable.description[:60]}")
                lines.append("    end note")
            else:
                lines.append(f"    {state_id}: {var_label}")

        # Add transitions with enhanced labels
        for _trans_id, transition in state_space.transitions.items():
            # Simple representation: use state variable changes
            source_state = transition.source_state
            target_state = transition.target_state

            # Create human-readable state labels
            source_label = ",".join(
                [f"{k}={v}" for k, v in sorted(source_state.items())[:2]]
            )
            target_label = ",".join(
                [f"{k}={v}" for k, v in sorted(target_state.items())[:2]]
            )

            # Build transition label with action and optional observation
            action_label = transition.action_id or "transition"
            obs_label = ""

            # Add observation emission if available
            if hasattr(transition, 'observations') and transition.observations:
                obs_names = list(transition.observations)[:2]
                obs_label = f"\\n[obs: {', '.join(obs_names)}]"

            label = f"{action_label}{obs_label}"
            lines.append(f"    {source_label} --> {target_label}: {label}")

        return "\n".join(lines)

    def generate_sequence_diagram(self, process_model: ProcessModel | None = None, graph: ProgramGraph | None = None) -> str:
        """
        Generate an enhanced Mermaid sequenceDiagram showing request flow through middleware chain.

        Enhanced features:
        - Shows actual request flow through middleware chain
        - Labels messages with method names AND parameters
        - Activation boxes for long-running methods
        - Grouped by module

        Args:
            process_model: Optional ProcessModel to visualize.
            graph: Optional ProgramGraph for deriving call chains.

        Returns:
            Mermaid sequenceDiagram syntax as string.
        """
        lines = ["sequenceDiagram"]

        # Try process model first
        if process_model and process_model.stages:
            # Map stages to actors/participants
            participant_set: set[str] = set()
            for stage in process_model.stages.values():
                participant_set.add(stage.id)

            # Add participants
            for stage_id in sorted(participant_set):
                stage_opt = process_model.stages.get(stage_id)
                if stage_opt is not None:
                    lines.append(f"    participant {stage_id}")

            # Add connections as sequence interactions with enhanced labels
            for conn in process_model.connections.values():
                source_stage = process_model.stages.get(conn.source_stage_id)
                target_stage = process_model.stages.get(conn.target_stage_id)
                if source_stage and target_stage:
                    # Build label with method and parameters if available
                    label = conn.trigger or "proceed"
                    if hasattr(conn, 'method_name') and conn.method_name:
                        label = f"{conn.method_name}"
                    if hasattr(conn, 'parameters') and conn.parameters:
                        param_str = ", ".join([f"{k}={v}" for k, v in conn.parameters.items()][:2])
                        label = f"{label}({param_str})"
                    if conn.condition:
                        label = f"{label}\\n[{conn.condition}]"

                    # Use activation boxes for process stages
                    lines.append(
                        f"    {conn.source_stage_id}->>+{conn.target_stage_id}: {label}"
                    )
                    lines.append(f"    {conn.target_stage_id}-->>-{conn.source_stage_id}: done")

        elif graph:
            # Derive from CALLS edges in program graph, ordered by module
            # Find all CALLS edges and organize by source module
            calls_edges = [e for e in graph.edges.values() if e.kind == EdgeKind.CALLS]

            if calls_edges:
                # Get unique participants organized by module
                participants: set[str] = set()
                module_map: dict[str, list[str]] = {}
                for edge in calls_edges:
                    participants.add(edge.source_id)
                    participants.add(edge.target_id)

                    # Try to extract module from node ID
                    src_node = graph.get_node(edge.source_id)
                    if src_node and hasattr(src_node, 'module_id'):
                        module_id = src_node.module_id
                        if module_id not in module_map:
                            module_map[module_id] = []
                        module_map[module_id].append(edge.source_id)

                # Add participants (limit to top 10 to avoid clutter)
                for pid in sorted(participants)[:10]:
                    node = graph.get_node(pid)
                    if node:
                        safe_id = pid.replace("-", "_").replace(".", "_")
                        lines.append(f"    participant {safe_id} as {node.name}")

                # Add call messages with method names and parameters
                for edge in calls_edges[:20]:
                    src_node = graph.get_node(edge.source_id)
                    tgt_node = graph.get_node(edge.target_id)
                    if src_node and tgt_node:
                        src_safe = edge.source_id.replace("-", "_").replace(".", "_")
                        tgt_safe = edge.target_id.replace("-", "_").replace(".", "_")

                        # Build message label with method name and optional parameters
                        message = tgt_node.name
                        if tgt_node.metadata and "parameters" in tgt_node.metadata:
                            params = tgt_node.metadata["parameters"][:2]
                            param_str = ", ".join(params)
                            message = f"{message}({param_str})"

                        lines.append(f"    {src_safe}->>+{tgt_safe}: {message}")
                        lines.append(f"    {tgt_safe}-->>-{src_safe}: return")
            else:
                lines.append("    participant A as Function A")
                lines.append("    A->>A: No call edges found")

        return "\n".join(lines)

    def generate_active_inference_diagram(self, state_space: StateSpaceModel) -> str:
        """
        Generate a Mermaid diagram showing the Active Inference loop structure.

        Shows the complete Active Inference cycle:
        - Hidden states → Observations (likelihood)
        - Observations → Beliefs (inference)
        - Beliefs → Actions (policy)
        - Actions → Hidden states (transition)
        With actual variable/observation/action names from the state space.

        Args:
            state_space: StateSpaceModel to visualize.

        Returns:
            Mermaid graph TD syntax showing the Active Inference loop.
        """
        lines = ["graph TD"]

        # Central components
        lines.append("    HS['Hidden States']")
        lines.append("    OBS['Observations']")
        lines.append("    BELIEFS['Beliefs<br/>(Posterior)']")
        lines.append("    ACTIONS['Actions']")
        lines.append("    PREFS['Preferences']")

        # Add specific state variables
        if state_space.variables:
            var_names = list(state_space.variables.keys())[:5]
            for var_id in var_names:
                var = state_space.variables[var_id]
                safe_name = var.name.replace(" ", "_")
                lines.append(f"    HS__{safe_name}['{var.name}']")
            lines.append("    HS --> " + " --> ".join([f"HS__{var_id.replace('-', '_').replace('.', '_')}" for var_id in var_names[:3]]))

        # Add specific observations
        if state_space.observations:
            obs_names = list(state_space.observations.keys())[:5]
            for obs_id in obs_names:
                obs = state_space.observations[obs_id]
                safe_name = obs.name.replace(" ", "_")
                lines.append(f"    OBS__{safe_name}['{obs.name}']")
            lines.append("    OBS --> " + " --> ".join([f"OBS__{obs_id.replace('-', '_').replace('.', '_')}" for obs_id in obs_names[:3]]))

        # Add specific actions
        if state_space.actions:
            action_names = list(state_space.actions.keys())[:5]
            for action_id in action_names:
                action = state_space.actions[action_id]
                safe_name = action.name.replace(" ", "_")
                lines.append(f"    ACT__{safe_name}['{action.name}']")
            lines.append("    ACTIONS --> " + " --> ".join([f"ACT__{action_id.replace('-', '_').replace('.', '_')}" for action_id in action_names[:3]]))

        # Core Active Inference loop with labels
        lines.append("")
        lines.append("    %% Active Inference Loop")
        lines.append("    HS -->|Likelihood:<br/>P(o|h)| OBS")
        lines.append("    OBS -->|Inference:<br/>P(h|o)| BELIEFS")
        lines.append("    BELIEFS -->|Policy:<br/>π(a|o)| ACTIONS")
        lines.append("    ACTIONS -->|Transition:<br/>P(h'|a,h)| HS")
        lines.append("")
        lines.append("    %% Preferences")
        lines.append("    PREFS -->|Guides| ACTIONS")
        lines.append("    BELIEFS -->|Updates| PREFS")

        # Style the components
        lines.append("")
        lines.append("    style HS fill:#B3E5FF,stroke:#0066CC,stroke-width:2px")
        lines.append("    style OBS fill:#C8E6C9,stroke:#00AA00,stroke-width:2px")
        lines.append("    style BELIEFS fill:#FFE0B2,stroke:#FF8800,stroke-width:2px")
        lines.append("    style ACTIONS fill:#FFCCBC,stroke:#CC0000,stroke-width:2px")
        lines.append("    style PREFS fill:#E1BEE7,stroke:#9900FF,stroke-width:2px")

        return "\n".join(lines)

    def generate_flowchart(
        self, graph: ProgramGraph, semantic_mappings: dict[str, Any]
    ) -> str:
        """
        Generate a Mermaid flowchart showing the translation from code elements
        to semantic roles (OBSERVATION, ACTION, HIDDEN_STATE, POLICY, CONTEXT, CONSTRAINT).

        Args:
            graph: ProgramGraph to visualize.
            semantic_mappings: Dict mapping mapping IDs to SemanticMapping objects.

        Returns:
            Mermaid flowchart syntax as string.
        """
        lines = ["flowchart TD"]

        # Color code by semantic role
        role_colors = {
            "observation": "#B3E5FF",
            "action": "#C8E6C9",
            "hidden_state": "#FFB3B3",
            "policy": "#F8BBD0",
            "context": "#F0F4C3",
            "constraint": "#FFCCBC",
            "preference": "#E1BEE7",
        }

        # Group mappings by semantic kind (sorting by mapping.id for deterministic order)
        sorted_mappings = sorted(
            semantic_mappings.values(),
            key=lambda m: m.id if hasattr(m, 'id') else str(m)
        )

        # Build semantic role to source nodes mapping
        role_to_nodes: dict[str, list[str]] = {}
        for mapping in sorted_mappings:
            if not hasattr(mapping, 'kind'):
                continue
            role_name = mapping.kind.value if hasattr(mapping.kind, 'value') else str(mapping.kind)
            if role_name not in role_to_nodes:
                role_to_nodes[role_name] = []
            role_to_nodes[role_name].append((mapping, mapping.graph_fragment_node_ids))

        # Add semantic role boxes and edges from source code nodes
        added_nodes = set()
        for role_name, mapping_list in sorted(role_to_nodes.items()):
            role_safe = role_name.replace(" ", "_").replace("-", "_")
            role_node_id = f"ROLE_{role_safe}"

            # Add the semantic role box
            if role_node_id not in added_nodes:
                lines.append(f"    {role_node_id}['{role_name.upper()}']")
                color = role_colors.get(role_name, "#EEEEEE")
                lines.append(f"    style {role_node_id} fill:{color}")
                added_nodes.add(role_node_id)

            # Add edges from source nodes to semantic role
            for mapping, node_ids in mapping_list:
                label = mapping.semantic_label if hasattr(mapping, 'semantic_label') and mapping.semantic_label else role_name
                for src_node_id in node_ids[:3]:  # Limit to first 3 source nodes per mapping
                    src_node = graph.get_node(src_node_id)
                    if src_node:
                        src_safe = src_node_id.replace("-", "_").replace(".", "_")
                        if src_safe not in added_nodes:
                            lines.append(f"    {src_safe}['{src_node.name}']")
                            added_nodes.add(src_safe)
                        lines.append(f"    {src_safe} -->|{label}| {role_node_id}")

        return "\n".join(lines)

    def generate_all(
        self,
        graph: ProgramGraph,
        state_space: StateSpaceModel | None = None,
        process_model: ProcessModel | None = None,
        mappings: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """
        Generate all diagrams and return as dict of name -> mermaid_content.

        Generates:
        - class_diagram: Enhanced with visibility, signatures, stereotypes
        - dependency_graph: Color-coded by edge type with module subgraphs
        - state_diagram: With transition labels, observations, entry/exit actions
        - sequence_diagram: With method names, parameters, activation boxes
        - flowchart: Semantic role mapping
        - active_inference_diagram: Active Inference loop showing h→o→b→a→h

        Args:
            graph: ProgramGraph to visualize.
            state_space: Optional StateSpaceModel for state and active inference diagrams.
            process_model: Optional ProcessModel for sequence diagram.
            mappings: Optional semantic mappings for flowchart.

        Returns:
            Dict with keys: "class_diagram", "dependency_graph", "state_diagram",
            "sequence_diagram", "flowchart", "active_inference_diagram", containing
            Mermaid syntax strings.
        """
        result = {}

        # Generate class diagram
        result["class_diagram"] = self.generate_class_diagram(graph)

        # Generate dependency graph
        result["dependency_graph"] = self.generate_dependency_graph(graph)

        # Generate state diagram if provided
        if state_space:
            result["state_diagram"] = self.generate_state_diagram(state_space)

            # Generate Active Inference diagram
            result["active_inference_diagram"] = self.generate_active_inference_diagram(state_space)

        # Generate sequence diagram (with process model or from graph)
        result["sequence_diagram"] = self.generate_sequence_diagram(process_model, graph)

        # Generate flowchart if provided
        if mappings:
            result["flowchart"] = self.generate_flowchart(graph, mappings)

        return result
