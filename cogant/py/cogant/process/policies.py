"""
Policy extraction from graph patterns.

Identifies decision points, retry logic, branching policies from graph patterns.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging

from cogant.schemas.core import Node, NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)


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

        Retry patterns are indicated by:
        - Error/exception handling paths that loop back
        - Explicit retry counters
        - Sleep/backoff patterns before re-execution
        """
        for node in self.graph.nodes.values():
            # Check for retry-related metadata
            if node.metadata.get("has_retry") or "retry" in node.name.lower():
                policy_id = f"retry_{node.id}"

                # Infer retry parameters from metadata or defaults
                max_attempts = node.metadata.get("max_retries", 3)
                backoff_strategy = node.metadata.get("backoff_strategy", "exponential")
                backoff_base = node.metadata.get("backoff_base", 1.0)

                policy = RetryPolicy(
                    id=policy_id,
                    stage_id=node.id,
                    max_attempts=max_attempts,
                    backoff_strategy=backoff_strategy,
                    backoff_base=backoff_base,
                )
                self.retry_policies[policy_id] = policy
                logger.debug(f"Extracted retry policy: {policy_id}")

    def _extract_branching_policies(self) -> None:
        """
        Extract branching decision points from the graph.

        Branching patterns occur at:
        - Conditional (if/else) constructs
        - Switch/case statements
        - Try/catch/finally blocks
        """
        for node in self.graph.nodes.values():
            # Check if node is a control flow point
            if "decision" in node.name.lower() or "branch" in node.name.lower():
                policy_id = f"branch_{node.id}"
                branches = self._extract_branches_for_node(node.id)

                policy = BranchingPolicy(
                    id=policy_id,
                    stage_id=node.id,
                    decision_point=node.id,
                    branches=branches,
                )
                self.branching_policies[policy_id] = policy
                logger.debug(f"Extracted branching policy: {policy_id}")

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

        Circuit breakers typically:
        - Monitor for repeated failures
        - Fail fast after threshold
        - Include timeout/reset logic
        """
        for node in self.graph.nodes.values():
            # Check for circuit breaker metadata or patterns
            if node.metadata.get("is_circuit_breaker") or "circuit" in node.name.lower():
                policy_id = f"circuit_{node.id}"

                failure_threshold = node.metadata.get("failure_threshold", 5)
                success_threshold = node.metadata.get("success_threshold", 2)
                timeout = node.metadata.get("timeout", 60.0)

                policy = CircuitBreakerPolicy(
                    id=policy_id,
                    stage_id=node.id,
                    failure_threshold=failure_threshold,
                    success_threshold=success_threshold,
                    timeout=timeout,
                )
                self.circuit_breaker_policies[policy_id] = policy
                logger.debug(f"Extracted circuit breaker policy: {policy_id}")

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
