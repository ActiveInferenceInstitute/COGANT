"""CodebaseMetrics: Compute complexity, coupling, cohesion, and coverage metrics."""

import math
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MetricsReport:
    """Container for all codebase metrics."""

    complexity_score: float
    coupling_score: float
    cohesion_score: float
    semantic_coverage: float
    observability_score: float
    controllability_score: float
    node_count: int
    edge_count: int
    state_var_count: int
    observation_count: int
    action_count: int


class CodebaseMetrics:
    """Compute architectural quality metrics for a codebase analysis."""

    def __init__(self, graph: Dict[str, Any], state_space: Dict[str, Any], mappings: Dict[str, Any]):
        """Initialize metrics calculator.

        Args:
            graph: ProgramGraph dict with 'nodes' and 'edges' keys.
            state_space: StateSpaceModel dict with 'states', 'observations', 'actions'.
            mappings: SemanticMappings dict (may be empty).
        """
        self.graph = graph or {}
        self.state_space = state_space or {}
        self.mappings = mappings or {}

        self.nodes = self.graph.get("nodes", [])
        self.edges = self.graph.get("edges", [])
        self.state_vars = self.state_space.get("states", [])
        self.observations = self.state_space.get("observations", [])
        self.actions = self.state_space.get("actions", [])

    def complexity_score(self) -> float:
        """
        Compute cyclomatic-like complexity: accounts for node and edge counts.

        Range: 0-1 (higher = more complex).
        Uses a normalized metric based on graph density and size.
        """
        if not self.nodes:
            return 0.0

        node_count = len(self.nodes)
        edge_count = len(self.edges)

        # Maximum edges in a DAG: n*(n-1)/2
        max_edges = node_count * (node_count - 1) / 2

        if max_edges == 0:
            return 0.0

        # Density: actual edges / max possible edges
        density = edge_count / max_edges

        # Cyclomatic-like: scale node count (higher node count = higher baseline complexity)
        # Use log scale to normalize: log2(n) / log2(max_reasonable_nodes)
        # Assume 1000 is "very large"
        max_nodes = 1000
        size_factor = math.log2(node_count + 1) / math.log2(max_nodes)

        # Combine: weighted sum (density and size)
        complexity = (0.6 * density + 0.4 * min(size_factor, 1.0))
        return min(complexity, 1.0)

    def coupling_score(self) -> float:
        """
        Compute cross-module coupling: edge density between different modules.

        Range: 0-1 (higher = more tightly coupled).
        """
        if not self.edges:
            return 0.0

        # Group nodes by module (assume 'parent_id' or 'attributes.module' indicates module)
        modules: Dict[str, List[str]] = {}
        for node in self.nodes:
            module_id = node.get("parent_id") or node.get("attributes", {}).get("module", "root")
            if module_id not in modules:
                modules[module_id] = []
            modules[module_id].append(node.get("id"))

        if len(modules) <= 1:
            return 0.0

        # Count cross-module edges
        cross_module_edges = 0
        for edge in self.edges:
            src_id = edge.get("source")
            tgt_id = edge.get("target")
            if not src_id or not tgt_id:
                continue

            # Find modules for src and tgt
            src_module = None
            tgt_module = None
            for mod, node_ids in modules.items():
                if src_id in node_ids:
                    src_module = mod
                if tgt_id in node_ids:
                    tgt_module = mod

            if src_module and tgt_module and src_module != tgt_module:
                cross_module_edges += 1

        total_edges = len(self.edges)
        coupling = cross_module_edges / total_edges if total_edges > 0 else 0.0
        return min(coupling, 1.0)

    def cohesion_score(self) -> float:
        """
        Compute intra-module cohesion: edge density within modules.

        Range: 0-1 (higher = more cohesive).
        """
        if not self.edges:
            return 0.0

        # Group nodes by module
        modules: Dict[str, List[str]] = {}
        for node in self.nodes:
            module_id = node.get("parent_id") or node.get("attributes", {}).get("module", "root")
            if module_id not in modules:
                modules[module_id] = []
            modules[module_id].append(node.get("id"))

        if len(modules) == 0:
            return 0.0

        # Count intra-module edges
        intra_module_edges = 0
        for edge in self.edges:
            src_id = edge.get("source")
            tgt_id = edge.get("target")
            if not src_id or not tgt_id:
                continue

            # Find modules for src and tgt
            src_module = None
            tgt_module = None
            for mod, node_ids in modules.items():
                if src_id in node_ids:
                    src_module = mod
                if tgt_id in node_ids:
                    tgt_module = mod

            if src_module and tgt_module and src_module == tgt_module:
                intra_module_edges += 1

        total_edges = len(self.edges)
        cohesion = intra_module_edges / total_edges if total_edges > 0 else 0.0
        return min(cohesion, 1.0)

    def semantic_coverage(self) -> float:
        """
        Fraction of graph nodes with semantic mappings.

        Range: 0-1 (1.0 = all nodes mapped).
        """
        if not self.nodes:
            return 1.0  # Empty graph is "covered"

        mapped_count = 0
        for node in self.nodes:
            node_id = node.get("id")
            if node_id and node_id in self.mappings:
                mapped_count += 1

        coverage = mapped_count / len(self.nodes)
        return min(coverage, 1.0)

    def observability_score(self) -> float:
        """
        Fraction of state variables with observations.

        Range: 0-1 (1.0 = all state fully observable).
        """
        if not self.state_vars:
            return 1.0

        observable_count = 0
        for state_var in self.state_vars:
            # Check if any observation references this state
            for obs in self.observations:
                obs_states = obs.get("observes_state_vars", [])
                if state_var.get("var_id") in obs_states:
                    observable_count += 1
                    break

        observability = observable_count / len(self.state_vars)
        return min(observability, 1.0)

    def controllability_score(self) -> float:
        """
        Fraction of state variables with control actions.

        Range: 0-1 (1.0 = all state fully controllable).
        """
        if not self.state_vars:
            return 1.0

        controllable_count = 0
        for state_var in self.state_vars:
            # Check if any action affects this state
            for action in self.actions:
                affected_states = action.get("affects_state_vars", [])
                if state_var.get("var_id") in affected_states:
                    controllable_count += 1
                    break

        controllability = controllable_count / len(self.state_vars)
        return min(controllability, 1.0)

    def summary(self) -> MetricsReport:
        """Compute all metrics and return summary."""
        return MetricsReport(
            complexity_score=self.complexity_score(),
            coupling_score=self.coupling_score(),
            cohesion_score=self.cohesion_score(),
            semantic_coverage=self.semantic_coverage(),
            observability_score=self.observability_score(),
            controllability_score=self.controllability_score(),
            node_count=len(self.nodes),
            edge_count=len(self.edges),
            state_var_count=len(self.state_vars),
            observation_count=len(self.observations),
            action_count=len(self.actions),
        )

    def format_report(self) -> str:
        """Generate markdown metrics report."""
        m = self.summary()

        lines = [
            "# Codebase Metrics Report",
            "",
            "## Architectural Metrics",
            "",
            f"- **Complexity Score**: {m.complexity_score:.2%}",
            f"  - Measures cyclomatic-like complexity based on graph density and size.",
            f"  - Range: 0% (simple) to 100% (highly complex).",
            "",
            f"- **Coupling Score**: {m.coupling_score:.2%}",
            f"  - Measures cross-module dependencies.",
            f"  - Range: 0% (decoupled) to 100% (tightly coupled).",
            "",
            f"- **Cohesion Score**: {m.cohesion_score:.2%}",
            f"  - Measures intra-module connectivity.",
            f"  - Range: 0% (scattered) to 100% (highly cohesive).",
            "",
            "## Coverage Metrics",
            "",
            f"- **Semantic Coverage**: {m.semantic_coverage:.2%}",
            f"  - Fraction of nodes with semantic mappings.",
            f"  - {int(m.node_count * m.semantic_coverage)}/{m.node_count} nodes mapped.",
            "",
            f"- **Observability Score**: {m.observability_score:.2%}",
            f"  - Fraction of state variables with observations.",
            f"  - {int(m.state_var_count * m.observability_score)}/{m.state_var_count} state variables observable.",
            "",
            f"- **Controllability Score**: {m.controllability_score:.2%}",
            f"  - Fraction of state variables with control actions.",
            f"  - {int(m.state_var_count * m.controllability_score)}/{m.state_var_count} state variables controllable.",
            "",
            "## Graph Structure",
            "",
            f"- **Nodes**: {m.node_count}",
            f"- **Edges**: {m.edge_count}",
            f"- **Density**: {(m.edge_count / (m.node_count * (m.node_count - 1) / 2) if m.node_count > 1 else 0):.4f}",
            "",
            "## State Space Structure",
            "",
            f"- **State Variables**: {m.state_var_count}",
            f"- **Observations**: {m.observation_count}",
            f"- **Actions**: {m.action_count}",
            "",
        ]

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dictionary for JSON serialization."""
        m = self.summary()
        return {
            "complexity_score": m.complexity_score,
            "coupling_score": m.coupling_score,
            "cohesion_score": m.cohesion_score,
            "semantic_coverage": m.semantic_coverage,
            "observability_score": m.observability_score,
            "controllability_score": m.controllability_score,
            "graph_structure": {
                "node_count": m.node_count,
                "edge_count": m.edge_count,
                "density": m.edge_count / (m.node_count * (m.node_count - 1) / 2)
                if m.node_count > 1
                else 0,
            },
            "state_space_structure": {
                "state_variables": m.state_var_count,
                "observations": m.observation_count,
                "actions": m.action_count,
            },
        }
