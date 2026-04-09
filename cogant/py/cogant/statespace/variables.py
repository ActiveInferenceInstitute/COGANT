"""
State variable extraction and classification.

Identifies and classifies state variables from hidden_state nodes in the
program graph, computing cardinality, domain, and factorization.
"""

from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from cogant.schemas.core import Node, NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import SemanticMapping, MappingKind

logger = logging.getLogger(__name__)


class StateVariableType(str, Enum):
    """Classification of state variables."""
    BOOLEAN = "boolean"
    DISCRETE = "discrete"
    CONTINUOUS = "continuous"
    CATEGORICAL = "categorical"
    VECTOR = "vector"
    COMPOSITE = "composite"


class ConfidenceLevel(str, Enum):
    """Confidence in extracted information."""
    DEFINITE = "definite"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


@dataclass
class StateVariable:
    """A state variable in the system."""
    id: str
    name: str
    var_type: StateVariableType
    node_id: str  # Reference to graph node marked as hidden_state
    cardinality: Optional[int] = None
    domain: Optional[List[Any]] = None
    factors: Optional[List[str]] = None  # For factorization
    is_discrete: bool = True
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    description: Optional[str] = None
    mutations: List[str] = field(default_factory=list)  # Edge IDs of mutations
    reads: List[str] = field(default_factory=list)  # Edge IDs of reads
    observable: bool = False
    """True when the same underlying node also has an OBSERVATION mapping.

    Used by the state-space compiler and downstream GNN formatter to decide
    whether this hidden-state variable should expose an observation channel
    in the generated A/B/C/D matrices.
    """


@dataclass
class FactorizationInfo:
    """Information about state variable factorization."""
    factors: List[str]
    independence_score: float  # 0-1: how independent are factors
    dependencies: Dict[str, List[str]]  # Factor ID -> list of dependent factors


class StateVariableExtractor:
    """
    Identifies and classifies state variables from graph nodes marked as
    hidden_state, computing their cardinality, domain, and factorization.
    """

    def __init__(self, program_graph: ProgramGraph):
        """
        Initialize the extractor.

        Args:
            program_graph: The program graph to analyze.
        """
        self.graph = program_graph
        self.state_variables: Dict[str, StateVariable] = {}
        self.factorization_map: Dict[str, FactorizationInfo] = {}

    def extract(self, semantic_mappings: Dict[str, SemanticMapping]) -> Dict[str, StateVariable]:
        """
        Extract state variables from the program graph.

        Walks every ``HIDDEN_STATE`` mapping and builds a
        :class:`StateVariable` for each referenced graph node, inferring type,
        cardinality and domain from node metadata. Variables whose underlying
        node *also* has an ``OBSERVATION`` mapping are flagged as observable,
        so the compiler can wire the corresponding observation channel later.

        Args:
            semantic_mappings: Semantic mappings identifying hidden state nodes.

        Returns:
            Dictionary mapping variable ID to :class:`StateVariable`.
        """
        # Find all hidden_state mappings
        hidden_state_mappings = {
            mid: m for mid, m in semantic_mappings.items()
            if m.kind == MappingKind.HIDDEN_STATE
        }
        # Pre-compute the set of node IDs that carry an OBSERVATION mapping so
        # we can cheaply mark hidden-state variables as observable.
        observation_node_ids: Set[str] = set()
        for m in semantic_mappings.values():
            if m.kind == MappingKind.OBSERVATION:
                observation_node_ids.update(m.graph_fragment_node_ids)

        logger.info(f"Found {len(hidden_state_mappings)} hidden state mappings")

        for mapping_id, mapping in hidden_state_mappings.items():
            self._extract_from_mapping(mapping_id, mapping)

        # Mark observable flag for any variable whose node also has an
        # OBSERVATION mapping (POMDP observation channel).
        for var in self.state_variables.values():
            if var.node_id in observation_node_ids:
                var.observable = True

        # Analyze factorization
        self._analyze_factorization()

        logger.info(f"Extracted {len(self.state_variables)} state variables")
        return self.state_variables

    def _extract_from_mapping(self, mapping_id: str, mapping: SemanticMapping) -> None:
        """
        Extract state variable from a single hidden_state mapping.

        Args:
            mapping_id: The mapping ID.
            mapping: The semantic mapping.
        """
        for node_id in mapping.graph_fragment_node_ids:
            node = self.graph.get_node(node_id)
            if not node:
                continue

            var_id = f"var_{node_id}"
            var_name = self._infer_var_name(node, mapping)
            var_type = self._infer_var_type(node, mapping)
            is_discrete = var_type != StateVariableType.CONTINUOUS

            # Find mutations and reads
            mutations = [e.id for e in self.graph.get_edges_from(node_id)
                        if e.kind == EdgeKind.WRITES]
            reads = [e.id for e in self.graph.get_edges_to(node_id)
                    if e.kind == EdgeKind.READS]

            # Infer cardinality and domain
            cardinality, domain = self._infer_cardinality_and_domain(node, var_type, mapping)

            state_var = StateVariable(
                id=var_id,
                name=var_name,
                var_type=var_type,
                node_id=node_id,
                cardinality=cardinality,
                domain=domain,
                is_discrete=is_discrete,
                confidence=self._map_confidence(mapping.confidence_score),
                description=mapping.description,
                mutations=mutations,
                reads=reads,
            )

            self.state_variables[var_id] = state_var
            logger.debug(f"Extracted state variable: {var_name} (type={var_type})")

    def _infer_var_name(self, node: Node, mapping: SemanticMapping) -> str:
        """
        Infer variable name from node and mapping.

        Args:
            node: The node.
            mapping: The semantic mapping.

        Returns:
            Inferred variable name.
        """
        if mapping.semantic_label:
            return mapping.semantic_label
        return node.name

    def _infer_var_type(self, node: Node, mapping: SemanticMapping) -> StateVariableType:
        """
        Infer variable type from node metadata and mapping.

        Args:
            node: The node.
            mapping: The semantic mapping.

        Returns:
            Inferred StateVariableType.
        """
        # Check metadata for type hints
        if "type_hint" in node.metadata:
            type_hint = node.metadata["type_hint"]
            if type_hint in ("bool", "boolean"):
                return StateVariableType.BOOLEAN
            elif type_hint in ("int", "integer"):
                return StateVariableType.DISCRETE
            elif type_hint in ("float", "real"):
                return StateVariableType.CONTINUOUS
            elif type_hint in ("str", "string"):
                return StateVariableType.CATEGORICAL
            elif "list" in type_hint or "array" in type_hint:
                return StateVariableType.VECTOR
            elif type_hint in ("dict", "object"):
                return StateVariableType.COMPOSITE

        # Check description for hints
        desc = (mapping.description or "").lower()
        if "flag" in desc or "enabled" in desc or "active" in desc:
            return StateVariableType.BOOLEAN
        elif "count" in desc or "index" in desc or "num" in desc:
            return StateVariableType.DISCRETE
        elif "rate" in desc or "prob" in desc or "value" in desc:
            return StateVariableType.CONTINUOUS

        # Default: assume discrete
        return StateVariableType.DISCRETE

    def _infer_cardinality_and_domain(
        self,
        node: Node,
        var_type: StateVariableType,
        mapping: SemanticMapping
    ) -> tuple[Optional[int], Optional[List[Any]]]:
        """
        Infer cardinality and domain from node metadata, class attributes, and type.

        Args:
            node: The node.
            var_type: The variable type.
            mapping: The semantic mapping.

        Returns:
            Tuple of (cardinality, domain) or (None, None) if not inferrable.
        """
        # Check metadata for explicit cardinality
        if "cardinality" in node.metadata:
            card = node.metadata["cardinality"]
            return card, None

        if "enum_values" in node.metadata:
            values = node.metadata["enum_values"]
            return len(values), values

        # For class nodes, extract attributes from graph to infer cardinality
        if node.kind == NodeKind.CLASS:
            cardinality, domain = self._extract_class_attributes_cardinality(node)
            if cardinality is not None or domain is not None:
                return cardinality, domain

        # Type-based defaults
        if var_type == StateVariableType.BOOLEAN:
            return 2, [False, True]
        elif var_type == StateVariableType.CATEGORICAL:
            # Try to infer from description
            desc = (mapping.description or "").lower()
            if "status" in desc:
                return 3, ["pending", "active", "complete"]
            elif "state" in desc:
                return 4, ["init", "active", "paused", "done"]
            return None, None

        return None, None

    def _extract_class_attributes_cardinality(self, class_node: Node) -> tuple[Optional[int], Optional[List[str]]]:
        """
        Extract cardinality and domain from class attributes in the graph.

        For classes like Request, Response, Middleware, finds contained methods/attributes
        and counts them or infers from known patterns.

        Args:
            class_node: A CLASS node.

        Returns:
            Tuple of (cardinality, domain_list) or (None, None).
        """
        # Find contained methods/attributes
        contained_nodes = []
        for edge in self.graph.edges.values():
            if edge.source_id == class_node.id and edge.kind == EdgeKind.CONTAINS:
                contained_nodes.append(edge.target_id)

        # For methods, cardinality = number of methods
        methods_count = 0
        method_names = []
        for node_id in contained_nodes:
            contained = self.graph.get_node(node_id)
            if contained and contained.kind == NodeKind.METHOD:
                methods_count += 1
                method_names.append(contained.name)

        if methods_count > 0:
            return methods_count, method_names

        # For non-method attributes, try common patterns
        class_name = class_node.name.lower()
        if "middleware" in class_name or "request" in class_name or "response" in class_name:
            # These typically have 3-5 attributes
            return 5, ["headers", "body", "status", "metadata", "config"]

        return None, None

    def _analyze_factorization(self) -> None:
        """
        Analyze factorization of state variables.
        Variables are independent if they don't share mutations or reads.
        """
        var_list = list(self.state_variables.values())

        for i, var in enumerate(var_list):
            var_mutations = set(var.mutations)
            var_reads = set(var.reads)

            # Find dependent variables
            dependencies = []
            for other_var in var_list[i + 1:]:
                other_mutations = set(other_var.mutations)
                other_reads = set(other_var.reads)

                # Check for shared mutations or data dependencies
                if var_mutations & other_mutations or var_reads & other_mutations:
                    dependencies.append(other_var.id)

            if dependencies:
                # independence_score = 0.5 — principled default
                # ("moderately dependent"). Our current dependency
                # check is binary (shared-edge overlap), so we cannot
                # yet produce a graded score; 0.5 is the maximum-
                # entropy placeholder. TODO(calibration): replace
                # with a proper score derived from the fraction of
                # overlapping mutation/read edges, calibrated against
                # a human-labelled factorization gold standard on
                # the 20-repo corpus.
                self.factorization_map[var.id] = FactorizationInfo(
                    factors=[var.id] + dependencies,
                    independence_score=0.5,  # placeholder (see above)
                    dependencies={var.id: dependencies}
                )

    def _map_confidence(self, confidence_score: float) -> ConfidenceLevel:
        """Map numeric confidence score to ConfidenceLevel.

        Thresholds (audit 2026-04-09):
            The 0.95 / 0.80 / 0.60 / 0.40 ladder is a **principled
            default** set to align with the translation-rule
            confidence bands documented in
            :mod:`cogant.translate.rules` (top/high/upper-mid/mid/
            bottom/lowest at 0.90/0.85/0.80/0.75/0.70/0.65). The
            ladder is intentionally coarser than the rule bands so
            that adjacent rule bands map to the same
            ConfidenceLevel label, giving downstream consumers a
            stable categorical view. TODO(calibration): validate the
            mapping against the human-reviewed GNN gold standard
            from the 20-repo corpus; thresholds may be re-centered
            if the resulting LOW/MEDIUM split does not match human
            judgments.

        Args:
            confidence_score: Score from 0.0 to 1.0.

        Returns:
            Corresponding ConfidenceLevel.
        """
        # Principled-default ladder; see docstring for rationale and
        # TODO(calibration) against 20-repo gold standard.
        if confidence_score >= 0.95:        # matches "definite" (near-1)
            return ConfidenceLevel.DEFINITE
        elif confidence_score >= 0.80:      # >= upper-mid rule band
            return ConfidenceLevel.HIGH
        elif confidence_score >= 0.60:      # below lowest rule band
            return ConfidenceLevel.MEDIUM
        elif confidence_score >= 0.40:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNCERTAIN

    def get_state_variables(self) -> Dict[str, StateVariable]:
        """
        Get all extracted state variables.

        Returns:
            Dictionary mapping variable ID to StateVariable.
        """
        return self.state_variables

    def get_factorization(self, var_id: str) -> Optional[FactorizationInfo]:
        """
        Get factorization information for a variable.

        Args:
            var_id: The variable ID.

        Returns:
            FactorizationInfo if available, None otherwise.
        """
        return self.factorization_map.get(var_id)

    def compute_dimensionality(self) -> int:
        """
        Compute the dimensionality of the state space.

        Returns:
            Product of cardinalities of discrete variables (or estimate for continuous).
        """
        cardinality_product = 1
        continuous_count = 0

        for var in self.state_variables.values():
            if var.is_discrete and var.cardinality:
                cardinality_product *= var.cardinality
            elif not var.is_discrete:
                continuous_count += 1

        # Estimate: each continuous variable adds one dimension
        total_dim = cardinality_product * (2 ** continuous_count) if continuous_count else cardinality_product
        return total_dim
