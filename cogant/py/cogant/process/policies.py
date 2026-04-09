"""
Policy extraction from graph patterns.

Identifies decision points, retry logic, branching policies from graph patterns.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import logging

from cogant.schemas.core import Node, NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)

# Name fragments that strongly indicate retry, branching, or circuit-breaker
# behaviour. Lower-cased on input, matched as substrings.
_RETRY_NAME_HINTS: Set[str] = {"retry", "retries", "backoff", "reattempt"}
_BRANCH_NAME_HINTS: Set[str] = {
    "decision", "branch", "dispatch", "route", "router", "choose", "select",
    "switch", "if_", "when_", "case_", "predicate",
}
_CIRCUIT_NAME_HINTS: Set[str] = {
    "circuit", "breaker", "fuse", "tripped", "open_circuit", "half_open",
}


@dataclass
class RetryPolicy:
    """Retry logic for a stage."""
    id: str
    stage_id: str
    max_attempts: int = 3
    backoff_strategy: str = "exponential"  # "exponential", "linear", "constant"
    backoff_base: float = 1.0  # Seconds
    backoff_multiplier: float = 2.0


@dataclass
class BranchingPolicy:
    """Branching decision point."""
    id: str
    stage_id: str
    decision_point: str  # Node ID making the decision
    branches: Dict[str, str] = field(default_factory=dict)  # Condition -> target_stage_id
    default_branch: Optional[str] = None


@dataclass
class CircuitBreakerPolicy:
    """Circuit breaker pattern for fault tolerance."""
    id: str
    stage_id: str
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 60.0  # Seconds


class PolicyExtractor:
    """
    Identifies decision points, retry logic, branching policies, and other
    control patterns from graph structure.
    """

    def __init__(self, program_graph: ProgramGraph):
        """
        Initialize the extractor.

        Args:
            program_graph: The program graph to analyze.
        """
        self.graph = program_graph
        self.retry_policies: Dict[str, RetryPolicy] = {}
        self.branching_policies: Dict[str, BranchingPolicy] = {}
        self.circuit_breaker_policies: Dict[str, CircuitBreakerPolicy] = {}

    def extract(self) -> Dict[str, object]:
        """
        Extract all policies from the program graph.

        Returns:
            Dictionary containing all extracted policies.
        """
        logger.info("Extracting control policies...")

        self._extract_retry_policies()
        self._extract_branching_policies()
        self._extract_circuit_breaker_policies()

        return {
            "retry_policies": self.retry_policies,
            "branching_policies": self.branching_policies,
            "circuit_breaker_policies": self.circuit_breaker_policies,
        }

    def _extract_retry_policies(self) -> None:
        """
        Extract retry patterns from the graph.

        Retry patterns are indicated by (any of):
        - ``has_retry`` / ``retry_policy`` metadata flag
        - ``max_retries`` metadata (implies retry logic)
        - Node name containing one of ``_RETRY_NAME_HINTS``
        - THROWS self-loop (iteration on failure) combined with CALLS
          edges back to the same node, which is the classic retry
          shape produced by ``while attempts < max: ... try ... except``.
        """
        for node in self.graph.nodes.values():
            metadata = node.metadata or {}
            name_lc = node.name.lower() if node.name else ""

            has_retry_flag = bool(
                metadata.get("has_retry")
                or metadata.get("retry_policy")
                or metadata.get("max_retries") is not None
            )
            name_hit = any(hint in name_lc for hint in _RETRY_NAME_HINTS)
            structural_hit = self._has_retry_structure(node.id)

            if not (has_retry_flag or name_hit or structural_hit):
                continue

            policy_id = f"retry_{node.id}"

            # Infer retry parameters from metadata or defaults
            max_attempts = int(metadata.get("max_retries", metadata.get("max_attempts", 3)))
            backoff_strategy = str(metadata.get("backoff_strategy", "exponential"))
            backoff_base = float(metadata.get("backoff_base", 1.0))
            backoff_mult = float(metadata.get("backoff_multiplier", 2.0))

            policy = RetryPolicy(
                id=policy_id,
                stage_id=node.id,
                max_attempts=max_attempts,
                backoff_strategy=backoff_strategy,
                backoff_base=backoff_base,
                backoff_multiplier=backoff_mult,
            )
            self.retry_policies[policy_id] = policy
            logger.debug(
                "Extracted retry policy %s (name_hit=%s, flag=%s, structural=%s)",
                policy_id, name_hit, has_retry_flag, structural_hit,
            )

    def _has_retry_structure(self, node_id: str) -> bool:
        """
        Detect retry-like structural patterns in the call graph.

        A node has a retry structure when:
        1. It has a CALLS self-loop (calls itself directly), or
        2. It CALLS another node that transitively CALLS it back, AND
           it participates in THROWS/CATCHES edges (indicating error
           handling on the retry path).

        Args:
            node_id: Candidate node id.

        Returns:
            True when a retry-shaped subgraph is detected.
        """
        has_self_call = False
        has_throws = False
        has_catches = False

        for edge in self.graph.get_edges_from(node_id):
            if edge.kind == EdgeKind.CALLS and edge.target_id == node_id:
                has_self_call = True
            if edge.kind == EdgeKind.THROWS:
                has_throws = True
            if edge.kind == EdgeKind.CATCHES:
                has_catches = True

        return has_self_call or (has_throws and has_catches)

    def _extract_branching_policies(self) -> None:
        """
        Extract branching decision points from the graph.

        A node is classified as a decision point when *any* of the
        following holds:

        1. Its name contains a branch hint (decision, branch, route,
           dispatch, switch, etc.).
        2. Its metadata sets ``is_decision`` / ``is_branch`` / contains
           a ``branches`` dictionary.
        3. It has 2+ outgoing CALLS or TRIGGERS edges with distinct
           targets — structurally, a node that fans out to multiple
           downstream handlers acts as a switch.
        """
        for node in self.graph.nodes.values():
            metadata = node.metadata or {}
            name_lc = node.name.lower() if node.name else ""

            name_hit = any(hint in name_lc for hint in _BRANCH_NAME_HINTS)
            metadata_hit = bool(
                metadata.get("is_decision")
                or metadata.get("is_branch")
                or metadata.get("branches")
            )
            structural_hit = self._has_fanout_structure(node.id)

            if not (name_hit or metadata_hit or structural_hit):
                continue

            policy_id = f"branch_{node.id}"
            branches = self._extract_branches_for_node(node.id)

            default_branch = None
            if metadata.get("default_branch"):
                default_branch = str(metadata["default_branch"])

            policy = BranchingPolicy(
                id=policy_id,
                stage_id=node.id,
                decision_point=node.id,
                branches=branches,
                default_branch=default_branch,
            )
            self.branching_policies[policy_id] = policy
            logger.debug(
                "Extracted branching policy %s (name_hit=%s, metadata=%s, structural=%s)",
                policy_id, name_hit, metadata_hit, structural_hit,
            )

    def _has_fanout_structure(self, node_id: str) -> bool:
        """
        Return True when ``node_id`` has 2+ distinct downstream targets
        via CALLS or TRIGGERS edges. Self-loops do not count.
        """
        targets: Set[str] = set()
        for edge in self.graph.get_edges_from(node_id):
            if edge.kind not in (EdgeKind.CALLS, EdgeKind.TRIGGERS):
                continue
            if edge.target_id == node_id:
                continue
            targets.add(edge.target_id)
            if len(targets) >= 2:
                return True
        return False

    def _extract_branches_for_node(self, node_id: str) -> Dict[str, str]:
        """
        Extract branches (outgoing edges) for a decision node.

        Args:
            node_id: The decision node ID.

        Returns:
            Dictionary mapping condition to target node ID.
        """
        branches = {}
        outgoing_edges = self.graph.get_edges_from(node_id)

        for i, edge in enumerate(outgoing_edges):
            # Use edge metadata to infer condition, or default to edge index
            condition = edge.metadata.get("condition", f"branch_{i}")
            branches[condition] = edge.target_id

        return branches

    def _extract_circuit_breaker_policies(self) -> None:
        """
        Extract circuit breaker patterns for fault tolerance.

        A node is flagged as a circuit breaker when any of the following
        holds:

        1. Metadata: ``is_circuit_breaker``, ``circuit_breaker``, or
           explicit ``failure_threshold`` / ``success_threshold`` entries.
        2. Name contains a circuit hint (circuit, breaker, fuse, tripped).
        3. Structural: node has GUARDS/THROWS edges AND metadata suggests
           a threshold-based failure pattern (handled via flags above).
        """
        for node in self.graph.nodes.values():
            metadata = node.metadata or {}
            name_lc = node.name.lower() if node.name else ""

            metadata_hit = bool(
                metadata.get("is_circuit_breaker")
                or metadata.get("circuit_breaker")
                or metadata.get("failure_threshold") is not None
                or metadata.get("success_threshold") is not None
            )
            name_hit = any(hint in name_lc for hint in _CIRCUIT_NAME_HINTS)

            if not (metadata_hit or name_hit):
                continue

            policy_id = f"circuit_{node.id}"

            failure_threshold = int(metadata.get("failure_threshold", 5))
            success_threshold = int(metadata.get("success_threshold", 2))
            timeout = float(metadata.get("timeout", 60.0))

            policy = CircuitBreakerPolicy(
                id=policy_id,
                stage_id=node.id,
                failure_threshold=failure_threshold,
                success_threshold=success_threshold,
                timeout=timeout,
            )
            self.circuit_breaker_policies[policy_id] = policy
            logger.debug(
                "Extracted circuit breaker policy %s (metadata=%s, name=%s)",
                policy_id, metadata_hit, name_hit,
            )

    def get_retry_policy(self, policy_id: str) -> Optional[RetryPolicy]:
        """
        Get a retry policy by ID.

        Args:
            policy_id: The policy ID.

        Returns:
            RetryPolicy or None.
        """
        return self.retry_policies.get(policy_id)

    def get_branching_policy(self, policy_id: str) -> Optional[BranchingPolicy]:
        """
        Get a branching policy by ID.

        Args:
            policy_id: The policy ID.

        Returns:
            BranchingPolicy or None.
        """
        return self.branching_policies.get(policy_id)

    def get_circuit_breaker_policy(self, policy_id: str) -> Optional[CircuitBreakerPolicy]:
        """
        Get a circuit breaker policy by ID.

        Args:
            policy_id: The policy ID.

        Returns:
            CircuitBreakerPolicy or None.
        """
        return self.circuit_breaker_policies.get(policy_id)

    def list_policies_for_stage(self, stage_id: str) -> Dict[str, List[object]]:
        """
        Get all policies affecting a particular stage.

        Args:
            stage_id: The stage ID.

        Returns:
            Dictionary of policy types to policy objects.
        """
        return {
            "retry": [p for p in self.retry_policies.values() if p.stage_id == stage_id],
            "branching": [p for p in self.branching_policies.values() if p.stage_id == stage_id],
            "circuit_breaker": [p for p in self.circuit_breaker_policies.values() if p.stage_id == stage_id],
        }

    def policy_count(self) -> int:
        """
        Return the total number of policies extracted so far.

        Returns:
            Sum of retry, branching, and circuit-breaker policy counts.
        """
        return (
            len(self.retry_policies)
            + len(self.branching_policies)
            + len(self.circuit_breaker_policies)
        )
