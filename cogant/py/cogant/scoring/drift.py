"""DriftAnalyzer: Compare bundles and compute architectural drift scores."""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Tuple, Set
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class DriftScore:
    """Drift analysis result."""

    total_score: float
    """Overall drift score 0-1 (higher = more drift)."""

    architectural_score: float
    """Architectural changes (0-1)."""

    semantic_churn_score: float
    """Semantic model changes (0-1)."""

    details: Dict[str, Any]
    """Detailed breakdown of changes."""


class DriftAnalyzer:
    """
    Analyze architectural and semantic drift between two bundles.

    Compares:
      - Program graph structure (added/removed/changed nodes and edges)
      - Semantic mappings (new/lost/changed roles)
      - State space modifications (added/removed variables, observations, actions)
      - Process model evolution
      - Validation results
    """

    def __init__(self, bundle_a: Dict[str, Any], bundle_b: Dict[str, Any]):
        """Initialize drift analyzer.

        Args:
            bundle_a: First bundle (baseline). Dict with keys: 'graph', 'state_space', 'mappings'.
            bundle_b: Second bundle (current). Dict with keys: 'graph', 'state_space', 'mappings'.
        """
        self.bundle_a = bundle_a or {}
        self.bundle_b = bundle_b or {}

        # Extract components from bundles
        self.graph_a = self._extract_graph(bundle_a)
        self.graph_b = self._extract_graph(bundle_b)

        self.ss_a = self._extract_statespace(bundle_a)
        self.ss_b = self._extract_statespace(bundle_b)

        self.mappings_a = bundle_a.get("mappings", {}) if isinstance(bundle_a, dict) else {}
        self.mappings_b = bundle_b.get("mappings", {}) if isinstance(bundle_b, dict) else {}

        logger.info(f"DriftAnalyzer initialized: {len(self.graph_a.get('nodes', []))} -> {len(self.graph_b.get('nodes', []))} nodes")

    def _extract_graph(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Extract graph from bundle, handling different nesting levels."""
        if not isinstance(bundle, dict):
            return {}

        # Try direct 'graph' key
        if "graph" in bundle:
            return bundle["graph"]

        # Try 'stage_results.graph' (legacy format)
        if "stage_results" in bundle and isinstance(bundle["stage_results"], dict):
            return bundle["stage_results"].get("graph", {})

        return {}

    def _extract_statespace(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Extract state space from bundle, handling different nesting levels."""
        if not isinstance(bundle, dict):
            return {}

        # Try direct 'state_space' key
        if "state_space" in bundle:
            return bundle["state_space"]

        # Try 'stage_results.statespace' (legacy format)
        if "stage_results" in bundle and isinstance(bundle["stage_results"], dict):
            return bundle["stage_results"].get("statespace", {})

        return {}

    def analyze(self, bundle_a: Dict[str, Any], bundle_b: Dict[str, Any]) -> DriftScore:
        """Legacy analyze method for backward compatibility."""
        # Re-initialize with new bundles
        self.__init__(bundle_a, bundle_b)
        return self._compute_drift_score()

    def _compute_drift_score(self) -> DriftScore:
        """Compute overall drift score."""
        logger.info("Analyzing architectural drift")

        arch_score = self.compute_architectural_drift_score()
        semantic_score = self.compute_semantic_churn_score()

        # Weighted average
        total = (arch_score + semantic_score) / 2

        details = {
            "structural_drift": self.compute_structural_drift(),
            "semantic_drift": self.compute_semantic_drift(),
            "state_space_drift": self.compute_state_space_drift(),
        }

        return DriftScore(
            total_score=total,
            architectural_score=arch_score,
            semantic_churn_score=semantic_score,
            details=details,
        )

    def compute_structural_drift(self) -> Dict[str, Any]:
        """Compare program graphs: added/removed/changed nodes and edges."""
        nodes_a = {n.get("id"): n for n in self.graph_a.get("nodes", [])}
        nodes_b = {n.get("id"): n for n in self.graph_b.get("nodes", [])}

        edges_a = [f"{e.get('source')}→{e.get('target')}" for e in self.graph_a.get("edges", [])]
        edges_b = [f"{e.get('source')}→{e.get('target')}" for e in self.graph_b.get("edges", [])]

        added_nodes = set(nodes_b.keys()) - set(nodes_a.keys())
        removed_nodes = set(nodes_a.keys()) - set(nodes_b.keys())

        # Changed nodes: exist in both but differ
        changed_nodes = []
        for nid in set(nodes_a.keys()) & set(nodes_b.keys()):
            if nodes_a[nid] != nodes_b[nid]:
                changed_nodes.append(nid)

        added_edges = set(edges_b) - set(edges_a)
        removed_edges = set(edges_a) - set(edges_b)

        return {
            "nodes_added": list(added_nodes),
            "nodes_removed": list(removed_nodes),
            "nodes_changed": changed_nodes,
            "nodes_added_count": len(added_nodes),
            "nodes_removed_count": len(removed_nodes),
            "nodes_changed_count": len(changed_nodes),
            "edges_added_count": len(added_edges),
            "edges_removed_count": len(removed_edges),
        }

    def compute_semantic_drift(self) -> Dict[str, Any]:
        """Compare semantic mappings: new/lost/changed roles."""
        mapping_ids_a = set(self.mappings_a.keys()) if isinstance(self.mappings_a, dict) else set()
        mapping_ids_b = set(self.mappings_b.keys()) if isinstance(self.mappings_b, dict) else set()

        new_mappings = mapping_ids_b - mapping_ids_a
        lost_mappings = mapping_ids_a - mapping_ids_b

        # Changed mappings: exist in both but differ
        changed_mappings = []
        for mid in mapping_ids_a & mapping_ids_b:
            if self.mappings_a.get(mid) != self.mappings_b.get(mid):
                changed_mappings.append(mid)

        return {
            "new_mappings": list(new_mappings),
            "lost_mappings": list(lost_mappings),
            "changed_mappings": changed_mappings,
            "new_count": len(new_mappings),
            "lost_count": len(lost_mappings),
            "changed_count": len(changed_mappings),
        }

    def compute_state_space_drift(self) -> Dict[str, Any]:
        """Compare state spaces: added/removed variables, observations, actions."""
        states_a = {s.get("var_id"): s for s in self.ss_a.get("states", [])}
        states_b = {s.get("var_id"): s for s in self.ss_b.get("states", [])}

        obs_a = {o.get("modality_id"): o for o in self.ss_a.get("observations", [])}
        obs_b = {o.get("modality_id"): o for o in self.ss_b.get("observations", [])}

        actions_a = {a.get("action_id"): a for a in self.ss_a.get("actions", [])}
        actions_b = {a.get("action_id"): a for a in self.ss_b.get("actions", [])}

        return {
            "state_vars_added": len(set(states_b.keys()) - set(states_a.keys())),
            "state_vars_removed": len(set(states_a.keys()) - set(states_b.keys())),
            "state_vars_changed": len([s for s in set(states_a.keys()) & set(states_b.keys())
                                       if states_a[s] != states_b[s]]),
            "observations_added": len(set(obs_b.keys()) - set(obs_a.keys())),
            "observations_removed": len(set(obs_a.keys()) - set(obs_b.keys())),
            "actions_added": len(set(actions_b.keys()) - set(actions_a.keys())),
            "actions_removed": len(set(actions_a.keys()) - set(actions_b.keys())),
        }

    def compute_architectural_drift_score(self) -> float:
        """0.0 = identical, 1.0 = completely different."""
        graph_a = self.graph_a.get("nodes", [])
        graph_b = self.graph_b.get("nodes", [])

        nodes_a = len(graph_a)
        nodes_b = len(graph_b)

        edges_a = len(self.graph_a.get("edges", []))
        edges_b = len(self.graph_b.get("edges", []))

        # Compute change ratio
        if nodes_a == 0:
            node_drift = 0.5 if nodes_b > 0 else 0.0
        else:
            node_drift = abs(nodes_b - nodes_a) / max(nodes_a, nodes_b)

        if edges_a == 0:
            edge_drift = 0.5 if edges_b > 0 else 0.0
        else:
            edge_drift = abs(edges_b - edges_a) / max(edges_a, edges_b)

        return (node_drift + edge_drift) / 2

    def compute_semantic_churn_score(self) -> float:
        """Measure how much the semantic interpretation changed."""
        # State space churn
        states_a = len(self.ss_a.get("states", []))
        states_b = len(self.ss_b.get("states", []))

        obs_a = len(self.ss_a.get("observations", []))
        obs_b = len(self.ss_b.get("observations", []))

        actions_a = len(self.ss_a.get("actions", []))
        actions_b = len(self.ss_b.get("actions", []))

        state_drift = self._compute_count_drift(states_a, states_b)
        obs_drift = self._compute_count_drift(obs_a, obs_b)
        action_drift = self._compute_count_drift(actions_a, actions_b)

        # Mapping churn
        mapping_a_count = len(self.mappings_a) if isinstance(self.mappings_a, dict) else 0
        mapping_b_count = len(self.mappings_b) if isinstance(self.mappings_b, dict) else 0
        mapping_drift = self._compute_count_drift(mapping_a_count, mapping_b_count)

        return (state_drift + obs_drift + action_drift + mapping_drift) / 4

    def _compute_count_drift(self, count_a: int, count_b: int) -> float:
        """Compute drift between two counts."""
        if count_a == 0:
            return 0.5 if count_b > 0 else 0.0
        if count_b == 0:
            return 0.5 if count_a > 0 else 0.0

        return abs(count_b - count_a) / max(count_a, count_b)

    def _compute_collection_drift(self, col1: List[Any], col2: List[Any]) -> float:
        """Compute drift between two collections (legacy method)."""
        return self._compute_count_drift(len(col1), len(col2))

    def _count_added_nodes(self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]) -> int:
        """Count added graph nodes."""
        graph1 = self._extract_graph(bundle1)
        graph2 = self._extract_graph(bundle2)

        ids1 = {n.get("id") for n in graph1.get("nodes", [])}
        ids2 = {n.get("id") for n in graph2.get("nodes", [])}

        return len(ids2 - ids1)

    def _count_removed_nodes(self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]) -> int:
        """Count removed graph nodes."""
        graph1 = self._extract_graph(bundle1)
        graph2 = self._extract_graph(bundle2)

        ids1 = {n.get("id") for n in graph1.get("nodes", [])}
        ids2 = {n.get("id") for n in graph2.get("nodes", [])}

        return len(ids1 - ids2)

    def _count_edge_changes(self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]) -> int:
        """Count changed edges."""
        graph1 = self._extract_graph(bundle1)
        graph2 = self._extract_graph(bundle2)

        edges1 = len(graph1.get("edges", []))
        edges2 = len(graph2.get("edges", []))

        return abs(edges2 - edges1)

    def _count_added_states(self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]) -> int:
        """Count added states."""
        ss1 = self._extract_statespace(bundle1)
        ss2 = self._extract_statespace(bundle2)

        states1 = len(ss1.get("states", []))
        states2 = len(ss2.get("states", []))

        return max(0, states2 - states1)

    def _count_removed_states(self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]) -> int:
        """Count removed states."""
        ss1 = self._extract_statespace(bundle1)
        ss2 = self._extract_statespace(bundle2)

        states1 = len(ss1.get("states", []))
        states2 = len(ss2.get("states", []))

        return max(0, states1 - states2)

    def _count_observation_changes(self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]) -> int:
        """Count changed observations."""
        ss1 = self._extract_statespace(bundle1)
        ss2 = self._extract_statespace(bundle2)

        obs1 = len(ss1.get("observations", []))
        obs2 = len(ss2.get("observations", []))

        return abs(obs2 - obs1)

    def _count_action_changes(self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]) -> int:
        """Count changed actions."""
        ss1 = self._extract_statespace(bundle1)
        ss2 = self._extract_statespace(bundle2)

        actions1 = len(ss1.get("actions", []))
        actions2 = len(ss2.get("actions", []))

        return abs(actions2 - actions1)

    def _count_policy_changes(self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]) -> int:
        """Count changed policies."""
        ss1 = self._extract_statespace(bundle1)
        ss2 = self._extract_statespace(bundle2)

        policies1 = len(ss1.get("policies", []))
        policies2 = len(ss2.get("policies", []))

        return abs(policies2 - policies1)

    def generate_diff_report(self) -> str:
        """Full markdown diff report."""
        drift = self._compute_drift_score()

        lines = [
            "# Architectural Drift Report",
            "",
            "## Summary",
            "",
            f"**Overall Drift Score**: {drift.total_score:.1%}",
            f"- Architectural Drift: {drift.architectural_score:.1%}",
            f"- Semantic Churn: {drift.semantic_churn_score:.1%}",
            "",
        ]

        # Structural drift
        struct = drift.details.get("structural_drift", {})
        lines.extend([
            "## Structural Changes",
            "",
            f"**Nodes**:",
            f"- Added: {struct.get('nodes_added_count', 0)}",
            f"- Removed: {struct.get('nodes_removed_count', 0)}",
            f"- Changed: {struct.get('nodes_changed_count', 0)}",
            "",
            f"**Edges**:",
            f"- Added: {struct.get('edges_added_count', 0)}",
            f"- Removed: {struct.get('edges_removed_count', 0)}",
            "",
        ])

        # Semantic drift
        sem = drift.details.get("semantic_drift", {})
        lines.extend([
            "## Semantic Changes",
            "",
            f"**Mappings**:",
            f"- New: {sem.get('new_count', 0)}",
            f"- Lost: {sem.get('lost_count', 0)}",
            f"- Changed: {sem.get('changed_count', 0)}",
            "",
        ])

        # State space drift
        ss = drift.details.get("state_space_drift", {})
        lines.extend([
            "## State Space Changes",
            "",
            f"**State Variables**:",
            f"- Added: {ss.get('state_vars_added', 0)}",
            f"- Removed: {ss.get('state_vars_removed', 0)}",
            f"- Changed: {ss.get('state_vars_changed', 0)}",
            "",
            f"**Observations**:",
            f"- Added: {ss.get('observations_added', 0)}",
            f"- Removed: {ss.get('observations_removed', 0)}",
            "",
            f"**Actions**:",
            f"- Added: {ss.get('actions_added', 0)}",
            f"- Removed: {ss.get('actions_removed', 0)}",
            "",
        ])

        return "\n".join(lines)

    def generate_diff_mermaid(self) -> str:
        """Mermaid diagram showing changes: green=added, red=removed, yellow=changed."""
        struct = self._compute_drift_score().details.get("structural_drift", {})

        lines = [
            "graph TD",
            "  Drift[Architectural Drift Report]",
            "  Drift --> Struct[Structural Changes]",
            "  Struct --> NA[🟢 Added Nodes]",
            f"  NA --> NAL[n={struct.get('nodes_added_count', 0)}]",
            "  Struct --> NR[🔴 Removed Nodes]",
            f"  NR --> NRL[n={struct.get('nodes_removed_count', 0)}]",
            "  Struct --> NC[🟡 Changed Nodes]",
            f"  NC --> NCL[n={struct.get('nodes_changed_count', 0)}]",
            "  Struct --> EA[🟢 Added Edges]",
            f"  EA --> EAL[n={struct.get('edges_added_count', 0)}]",
            "  Struct --> ER[🔴 Removed Edges]",
            f"  ER --> ERL[n={struct.get('edges_removed_count', 0)}]",
            "  style NA fill:#90EE90",
            "  style NR fill:#FFB6C6",
            "  style NC fill:#FFFF99",
            "  style EA fill:#90EE90",
            "  style ER fill:#FFB6C6",
        ]

        return "\n".join(lines)

    def _compute_architectural_drift(
        self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]
    ) -> float:
        """Compute drift in program graph structure."""
        graph1 = bundle1.get("stage_results", {}).get("graph", {})
        graph2 = bundle2.get("stage_results", {}).get("graph", {})

        nodes1 = len(graph1.get("nodes", []))
        nodes2 = len(graph2.get("nodes", []))

        edges1 = len(graph1.get("edges", []))
        edges2 = len(graph2.get("edges", []))

        # Compute change ratio
        if nodes1 == 0:
            node_drift = 0.5 if nodes2 > 0 else 0.0
        else:
            node_drift = abs(nodes2 - nodes1) / max(nodes1, nodes2)

        if edges1 == 0:
            edge_drift = 0.5 if edges2 > 0 else 0.0
        else:
            edge_drift = abs(edges2 - edges1) / max(edges1, edges2)

        return (node_drift + edge_drift) / 2

    def _compute_semantic_churn(
        self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]
    ) -> float:
        """Compute semantic model churn."""
        ss1 = bundle1.get("stage_results", {}).get("statespace", {})
        ss2 = bundle2.get("stage_results", {}).get("statespace", {})

        state_drift = self._compute_collection_drift(
            ss1.get("states", []), ss2.get("states", [])
        )
        obs_drift = self._compute_collection_drift(
            ss1.get("observations", []), ss2.get("observations", [])
        )
        action_drift = self._compute_collection_drift(
            ss1.get("actions", []), ss2.get("actions", [])
        )

        return (state_drift + obs_drift + action_drift) / 3

    def _compute_collection_drift(self, col1: List[Any], col2: List[Any]) -> float:
        """Compute drift between two collections."""
        if len(col1) == 0:
            return 0.5 if len(col2) > 0 else 0.0
        if len(col2) == 0:
            return 0.5 if len(col1) > 0 else 0.0

        # Simple size-based drift
        return abs(len(col2) - len(col1)) / max(len(col1), len(col2))

    def _count_added_nodes(
        self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]
    ) -> int:
        """Count added graph nodes."""
        graph1 = bundle1.get("stage_results", {}).get("graph", {})
        graph2 = bundle2.get("stage_results", {}).get("graph", {})

        ids1 = {n.get("id") for n in graph1.get("nodes", [])}
        ids2 = {n.get("id") for n in graph2.get("nodes", [])}

        return len(ids2 - ids1)

    def _count_removed_nodes(
        self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]
    ) -> int:
        """Count removed graph nodes."""
        graph1 = bundle1.get("stage_results", {}).get("graph", {})
        graph2 = bundle2.get("stage_results", {}).get("graph", {})

        ids1 = {n.get("id") for n in graph1.get("nodes", [])}
        ids2 = {n.get("id") for n in graph2.get("nodes", [])}

        return len(ids1 - ids2)

    def _count_edge_changes(
        self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]
    ) -> int:
        """Count changed edges."""
        graph1 = bundle1.get("stage_results", {}).get("graph", {})
        graph2 = bundle2.get("stage_results", {}).get("graph", {})

        edges1 = len(graph1.get("edges", []))
        edges2 = len(graph2.get("edges", []))

        return abs(edges2 - edges1)

    def _count_added_states(
        self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]
    ) -> int:
        """Count added states."""
        ss1 = bundle1.get("stage_results", {}).get("statespace", {})
        ss2 = bundle2.get("stage_results", {}).get("statespace", {})

        states1 = len(ss1.get("states", []))
        states2 = len(ss2.get("states", []))

        return max(0, states2 - states1)

    def _count_removed_states(
        self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]
    ) -> int:
        """Count removed states."""
        ss1 = bundle1.get("stage_results", {}).get("statespace", {})
        ss2 = bundle2.get("stage_results", {}).get("statespace", {})

        states1 = len(ss1.get("states", []))
        states2 = len(ss2.get("states", []))

        return max(0, states1 - states2)

    def _count_observation_changes(
        self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]
    ) -> int:
        """Count changed observations."""
        ss1 = bundle1.get("stage_results", {}).get("statespace", {})
        ss2 = bundle2.get("stage_results", {}).get("statespace", {})

        obs1 = len(ss1.get("observations", []))
        obs2 = len(ss2.get("observations", []))

        return abs(obs2 - obs1)

    def _count_action_changes(
        self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]
    ) -> int:
        """Count changed actions."""
        ss1 = bundle1.get("stage_results", {}).get("statespace", {})
        ss2 = bundle2.get("stage_results", {}).get("statespace", {})

        actions1 = len(ss1.get("actions", []))
        actions2 = len(ss2.get("actions", []))

        return abs(actions2 - actions1)

    def _count_policy_changes(
        self, bundle1: Dict[str, Any], bundle2: Dict[str, Any]
    ) -> int:
        """Count changed policies."""
        ss1 = bundle1.get("stage_results", {}).get("statespace", {})
        ss2 = bundle2.get("stage_results", {}).get("statespace", {})

        policies1 = len(ss1.get("policies", []))
        policies2 = len(ss2.get("policies", []))

        return abs(policies2 - policies1)

    def report(self, score: DriftScore) -> str:
        """Generate human-readable report (legacy method)."""
        return self.generate_diff_report()

    def to_dict(self) -> Dict[str, Any]:
        """Export drift analysis as dictionary for JSON serialization."""
        drift = self._compute_drift_score()
        return {
            "total_score": drift.total_score,
            "architectural_score": drift.architectural_score,
            "semantic_churn_score": drift.semantic_churn_score,
            "details": drift.details,
        }
