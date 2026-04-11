"""Translation engine orchestrating rule application over program graphs."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from cogant.graph.queries import GraphQuery
from cogant.schemas.core import Node
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import ConfidenceTier, MappingKind, SemanticMapping
from cogant.translate.confidence import ConfidenceModel

logger = logging.getLogger(__name__)

__all__ = ["RuleExplanation", "TranslationRule", "TranslationEngine"]
from typing import Annotated
from typing import Callable
from typing import ClassVar

MutantDict = Annotated[dict[str, Callable], "Mutant"] # type: ignore


def _mutmut_trampoline(orig, mutants, call_args, call_kwargs, self_arg = None): # type: ignore
    """Forward call to original or mutated function, depending on the environment"""
    import os # type: ignore
    mutant_under_test = os.environ['MUTANT_UNDER_TEST'] # type: ignore
    if mutant_under_test == 'fail': # type: ignore
        from mutmut.__main__ import MutmutProgrammaticFailException # type: ignore
        raise MutmutProgrammaticFailException('Failed programmatically')       # type: ignore
    elif mutant_under_test == 'stats': # type: ignore
        from mutmut.__main__ import record_trampoline_hit # type: ignore
        record_trampoline_hit(orig.__module__ + '.' + orig.__name__) # type: ignore
        # (for class methods, orig is bound and thus does not need the explicit self argument)
        result = orig(*call_args, **call_kwargs) # type: ignore
        return result # type: ignore
    prefix = orig.__module__ + '.' + orig.__name__ + '__mutmut_' # type: ignore
    if not mutant_under_test.startswith(prefix): # type: ignore
        result = orig(*call_args, **call_kwargs) # type: ignore
        return result # type: ignore
    mutant_name = mutant_under_test.rpartition('.')[-1] # type: ignore
    if self_arg is not None: # type: ignore
        # call to a class method where self is not bound
        result = mutants[mutant_name](self_arg, *call_args, **call_kwargs) # type: ignore
    else:
        result = mutants[mutant_name](*call_args, **call_kwargs) # type: ignore
    return result # type: ignore


@dataclass
class RuleExplanation:
    """Explanation of why a translation rule did or did not fire on a node.

    Produced by :meth:`TranslationRule.explain` during the
    ``cogant explain`` workflow. Each instance records a single
    (rule, node) decision: the rule's name and priority, whether it
    fired, a short human-readable reason, and the list of concrete
    evidence snippets (edge kinds, keyword matches, qualified
    identifiers) that backed the decision.

    The dataclass is deliberately JSON-serialization friendly via
    :meth:`to_dict` so the explain CLI can emit either a rich text
    report or a machine-readable JSON blob without duplicating the
    payload logic.

    Attributes:
        rule_name: Stable rule identifier (``rule.name``).
        priority: Rule priority tier (higher fires first).
        fired: True when the rule actually produced a mapping for this
            node, False when it was considered but skipped.
        reason: One-line explanation of the decision.
        evidence: Concrete evidence strings collected during matching
            (e.g. ``"WRITES self.display"``, ``"keyword match: 'set'"``).
        mapping_kind: Semantic kind the rule would have produced, or
            None when the rule did not fire.
    """

    rule_name: str
    priority: int
    fired: bool
    reason: str
    evidence: list[str] = field(default_factory=list)
    mapping_kind: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain JSON-ready dict."""
        return {
            "rule_name": self.rule_name,
            "priority": self.priority,
            "fired": self.fired,
            "reason": self.reason,
            "evidence": list(self.evidence),
            "mapping_kind": self.mapping_kind,
        }


class TranslationRule(ABC):
    """Base class for translation rules."""

    @abstractmethod
    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
        """Check if rule matches graph patterns.

        Args:
            graph: Program graph to analyze.
            query: Graph query engine.

        Returns:
            List of matched fragments, each with node/edge IDs.
        """
        pass

    @abstractmethod
    def apply(
        self,
        graph: ProgramGraph,
        match: dict[str, Any],
    ) -> SemanticMapping | None:
        """Apply rule to a matched pattern.

        Args:
            graph: Program graph.
            match: Matched pattern from matches().

        Returns:
            SemanticMapping if successful, None otherwise.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this rule."""
        pass

    @property
    @abstractmethod
    def mapping_kind(self) -> MappingKind:
        """Kind of semantic mapping produced."""
        pass

    @property
    def priority(self) -> int:
        """Priority of this rule (higher = applied first). Default 0.

        Rationale for default ``priority=0``:
            Most shipped rules keep the default ``0`` and are applied in
            registration order within a single fixpoint pass.
            :class:`~cogant.translate.rules.structural.MutatingSubsystemRule`
            overrides this property to return ``1`` so class-level hidden-state
            evidence wins ties against overlapping class-scoped mappings from
            aggregate rules at equal confidence. Aside from that exception,
            conflict resolution between overlapping mappings falls through to
            the ``(priority, confidence_score)`` lexicographic comparison in
            :meth:`TranslationEngine._resolve_conflicts`. See
            ``docs/evaluation/CALIBRATION.md`` for the full rule priority audit.
            TODO(calibration): if the empirical conflict-loss rate on
            real-world repos exceeds ~5%, broaden explicit priority tiers.
        """
        return 0

    def explain(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        args = [node, graph, query]# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationRuleǁexplain__mutmut_orig'), object.__getattribute__(self, 'xǁTranslationRuleǁexplain__mutmut_mutants'), args, kwargs, self)

    def xǁTranslationRuleǁexplain__mutmut_orig(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_1(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = None
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_2(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(None, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_3(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, None)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_4(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_5(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, )
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_6(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=None,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_7(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=None,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_8(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=None,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_9(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=None,
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_10(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=None,
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_11(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=None,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_12(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_13(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_14(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_15(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_16(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_17(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_18(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=True,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_19(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(None).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_20(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_21(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get(None) if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_22(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("XXnode_idXX") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_23(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("NODE_ID") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_24(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = None
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_25(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = None
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_26(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(None)
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_27(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) and [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_28(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get(None, []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_29(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", None) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_30(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get([]) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_31(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", ) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_32(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("XXnode_idsXX", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_33(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("NODE_IDS", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_34(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id and node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_35(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id != node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_36(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id not in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_37(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = None
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_38(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(None):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_39(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key not in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_40(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("XXnode_idXX", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_41(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("NODE_ID", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_42(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "XXnode_idsXX"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_43(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "NODE_IDS"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_44(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        break
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_45(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(None)
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_46(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=None,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_47(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=None,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_48(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=None,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_49(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=None,
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_50(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=None,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_51(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=None,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_52(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_53(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_54(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_55(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_56(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_57(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_58(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=False,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_59(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name and node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_60(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=None,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_61(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=None,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_62(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=None,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_63(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=None,
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_64(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=None,
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_65(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=None,
        )

    def xǁTranslationRuleǁexplain__mutmut_66(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_67(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_68(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_69(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_70(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_71(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            )

    def xǁTranslationRuleǁexplain__mutmut_72(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=True,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )

    def xǁTranslationRuleǁexplain__mutmut_73(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name and node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
        )
    
    xǁTranslationRuleǁexplain__mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationRuleǁexplain__mutmut_1': xǁTranslationRuleǁexplain__mutmut_1, 
        'xǁTranslationRuleǁexplain__mutmut_2': xǁTranslationRuleǁexplain__mutmut_2, 
        'xǁTranslationRuleǁexplain__mutmut_3': xǁTranslationRuleǁexplain__mutmut_3, 
        'xǁTranslationRuleǁexplain__mutmut_4': xǁTranslationRuleǁexplain__mutmut_4, 
        'xǁTranslationRuleǁexplain__mutmut_5': xǁTranslationRuleǁexplain__mutmut_5, 
        'xǁTranslationRuleǁexplain__mutmut_6': xǁTranslationRuleǁexplain__mutmut_6, 
        'xǁTranslationRuleǁexplain__mutmut_7': xǁTranslationRuleǁexplain__mutmut_7, 
        'xǁTranslationRuleǁexplain__mutmut_8': xǁTranslationRuleǁexplain__mutmut_8, 
        'xǁTranslationRuleǁexplain__mutmut_9': xǁTranslationRuleǁexplain__mutmut_9, 
        'xǁTranslationRuleǁexplain__mutmut_10': xǁTranslationRuleǁexplain__mutmut_10, 
        'xǁTranslationRuleǁexplain__mutmut_11': xǁTranslationRuleǁexplain__mutmut_11, 
        'xǁTranslationRuleǁexplain__mutmut_12': xǁTranslationRuleǁexplain__mutmut_12, 
        'xǁTranslationRuleǁexplain__mutmut_13': xǁTranslationRuleǁexplain__mutmut_13, 
        'xǁTranslationRuleǁexplain__mutmut_14': xǁTranslationRuleǁexplain__mutmut_14, 
        'xǁTranslationRuleǁexplain__mutmut_15': xǁTranslationRuleǁexplain__mutmut_15, 
        'xǁTranslationRuleǁexplain__mutmut_16': xǁTranslationRuleǁexplain__mutmut_16, 
        'xǁTranslationRuleǁexplain__mutmut_17': xǁTranslationRuleǁexplain__mutmut_17, 
        'xǁTranslationRuleǁexplain__mutmut_18': xǁTranslationRuleǁexplain__mutmut_18, 
        'xǁTranslationRuleǁexplain__mutmut_19': xǁTranslationRuleǁexplain__mutmut_19, 
        'xǁTranslationRuleǁexplain__mutmut_20': xǁTranslationRuleǁexplain__mutmut_20, 
        'xǁTranslationRuleǁexplain__mutmut_21': xǁTranslationRuleǁexplain__mutmut_21, 
        'xǁTranslationRuleǁexplain__mutmut_22': xǁTranslationRuleǁexplain__mutmut_22, 
        'xǁTranslationRuleǁexplain__mutmut_23': xǁTranslationRuleǁexplain__mutmut_23, 
        'xǁTranslationRuleǁexplain__mutmut_24': xǁTranslationRuleǁexplain__mutmut_24, 
        'xǁTranslationRuleǁexplain__mutmut_25': xǁTranslationRuleǁexplain__mutmut_25, 
        'xǁTranslationRuleǁexplain__mutmut_26': xǁTranslationRuleǁexplain__mutmut_26, 
        'xǁTranslationRuleǁexplain__mutmut_27': xǁTranslationRuleǁexplain__mutmut_27, 
        'xǁTranslationRuleǁexplain__mutmut_28': xǁTranslationRuleǁexplain__mutmut_28, 
        'xǁTranslationRuleǁexplain__mutmut_29': xǁTranslationRuleǁexplain__mutmut_29, 
        'xǁTranslationRuleǁexplain__mutmut_30': xǁTranslationRuleǁexplain__mutmut_30, 
        'xǁTranslationRuleǁexplain__mutmut_31': xǁTranslationRuleǁexplain__mutmut_31, 
        'xǁTranslationRuleǁexplain__mutmut_32': xǁTranslationRuleǁexplain__mutmut_32, 
        'xǁTranslationRuleǁexplain__mutmut_33': xǁTranslationRuleǁexplain__mutmut_33, 
        'xǁTranslationRuleǁexplain__mutmut_34': xǁTranslationRuleǁexplain__mutmut_34, 
        'xǁTranslationRuleǁexplain__mutmut_35': xǁTranslationRuleǁexplain__mutmut_35, 
        'xǁTranslationRuleǁexplain__mutmut_36': xǁTranslationRuleǁexplain__mutmut_36, 
        'xǁTranslationRuleǁexplain__mutmut_37': xǁTranslationRuleǁexplain__mutmut_37, 
        'xǁTranslationRuleǁexplain__mutmut_38': xǁTranslationRuleǁexplain__mutmut_38, 
        'xǁTranslationRuleǁexplain__mutmut_39': xǁTranslationRuleǁexplain__mutmut_39, 
        'xǁTranslationRuleǁexplain__mutmut_40': xǁTranslationRuleǁexplain__mutmut_40, 
        'xǁTranslationRuleǁexplain__mutmut_41': xǁTranslationRuleǁexplain__mutmut_41, 
        'xǁTranslationRuleǁexplain__mutmut_42': xǁTranslationRuleǁexplain__mutmut_42, 
        'xǁTranslationRuleǁexplain__mutmut_43': xǁTranslationRuleǁexplain__mutmut_43, 
        'xǁTranslationRuleǁexplain__mutmut_44': xǁTranslationRuleǁexplain__mutmut_44, 
        'xǁTranslationRuleǁexplain__mutmut_45': xǁTranslationRuleǁexplain__mutmut_45, 
        'xǁTranslationRuleǁexplain__mutmut_46': xǁTranslationRuleǁexplain__mutmut_46, 
        'xǁTranslationRuleǁexplain__mutmut_47': xǁTranslationRuleǁexplain__mutmut_47, 
        'xǁTranslationRuleǁexplain__mutmut_48': xǁTranslationRuleǁexplain__mutmut_48, 
        'xǁTranslationRuleǁexplain__mutmut_49': xǁTranslationRuleǁexplain__mutmut_49, 
        'xǁTranslationRuleǁexplain__mutmut_50': xǁTranslationRuleǁexplain__mutmut_50, 
        'xǁTranslationRuleǁexplain__mutmut_51': xǁTranslationRuleǁexplain__mutmut_51, 
        'xǁTranslationRuleǁexplain__mutmut_52': xǁTranslationRuleǁexplain__mutmut_52, 
        'xǁTranslationRuleǁexplain__mutmut_53': xǁTranslationRuleǁexplain__mutmut_53, 
        'xǁTranslationRuleǁexplain__mutmut_54': xǁTranslationRuleǁexplain__mutmut_54, 
        'xǁTranslationRuleǁexplain__mutmut_55': xǁTranslationRuleǁexplain__mutmut_55, 
        'xǁTranslationRuleǁexplain__mutmut_56': xǁTranslationRuleǁexplain__mutmut_56, 
        'xǁTranslationRuleǁexplain__mutmut_57': xǁTranslationRuleǁexplain__mutmut_57, 
        'xǁTranslationRuleǁexplain__mutmut_58': xǁTranslationRuleǁexplain__mutmut_58, 
        'xǁTranslationRuleǁexplain__mutmut_59': xǁTranslationRuleǁexplain__mutmut_59, 
        'xǁTranslationRuleǁexplain__mutmut_60': xǁTranslationRuleǁexplain__mutmut_60, 
        'xǁTranslationRuleǁexplain__mutmut_61': xǁTranslationRuleǁexplain__mutmut_61, 
        'xǁTranslationRuleǁexplain__mutmut_62': xǁTranslationRuleǁexplain__mutmut_62, 
        'xǁTranslationRuleǁexplain__mutmut_63': xǁTranslationRuleǁexplain__mutmut_63, 
        'xǁTranslationRuleǁexplain__mutmut_64': xǁTranslationRuleǁexplain__mutmut_64, 
        'xǁTranslationRuleǁexplain__mutmut_65': xǁTranslationRuleǁexplain__mutmut_65, 
        'xǁTranslationRuleǁexplain__mutmut_66': xǁTranslationRuleǁexplain__mutmut_66, 
        'xǁTranslationRuleǁexplain__mutmut_67': xǁTranslationRuleǁexplain__mutmut_67, 
        'xǁTranslationRuleǁexplain__mutmut_68': xǁTranslationRuleǁexplain__mutmut_68, 
        'xǁTranslationRuleǁexplain__mutmut_69': xǁTranslationRuleǁexplain__mutmut_69, 
        'xǁTranslationRuleǁexplain__mutmut_70': xǁTranslationRuleǁexplain__mutmut_70, 
        'xǁTranslationRuleǁexplain__mutmut_71': xǁTranslationRuleǁexplain__mutmut_71, 
        'xǁTranslationRuleǁexplain__mutmut_72': xǁTranslationRuleǁexplain__mutmut_72, 
        'xǁTranslationRuleǁexplain__mutmut_73': xǁTranslationRuleǁexplain__mutmut_73
    }
    xǁTranslationRuleǁexplain__mutmut_orig.__name__ = 'xǁTranslationRuleǁexplain'


class TranslationEngine:
    """Orchestrates translation of program graphs to semantic concepts.

    Applies a series of translation rules using fixpoint iteration until
    convergence (no new mappings) or max iterations reached. Resolves
    conflicts when multiple mappings target overlapping node sets.
    """

    def __init__(self, max_iterations: int = 10):
        args = [max_iterations]# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationEngineǁ__init____mutmut_orig'), object.__getattribute__(self, 'xǁTranslationEngineǁ__init____mutmut_mutants'), args, kwargs, self)

    def xǁTranslationEngineǁ__init____mutmut_orig(self, max_iterations: int = 10):
        """Initialize the translation engine.

        Args:
            max_iterations: Maximum fixpoint iterations (default 10).

        Rationale for default ``max_iterations=10``:
            Conservative safety bound over the observed convergence
            depth on COGANT's three control-positive fixtures
            (``calculator``, ``event_pipeline``, ``flask_mini``, P3
            qualitative validation, R&D_LOG 2026-04-09). Empirically the
            fixpoint settles in <=5 iterations on all three fixtures and
            on the ``cpython/Lib/json`` real-world corpus (~1.2k LoC),
            so 10 is a ~2x safety margin. The choice is also consistent
            with the Kleene-iteration fixpoint framing of Cousot & Cousot
            (POPL '77, ``docs/evaluation/LITERATURE.md`` §1), which guarantees
            termination on a finite role-assignment lattice — 10
            iterations is an engineering cap rather than a theoretical
            bound. See ``docs/evaluation/CALIBRATION.md`` for the calibration plan.
            TODO(calibration): log observed iteration counts on a larger
            corpus (target: 20+ repos) and revise if the empirical
            maximum exceeds 5.
        """
        self.rules: list[TranslationRule] = []
        self.mappings: dict[str, SemanticMapping] = {}
        self._match_log: list[dict[str, Any]] = []
        self._rule_priority: dict[str, int] = {}
        self.max_iterations = max_iterations

    def xǁTranslationEngineǁ__init____mutmut_1(self, max_iterations: int = 11):
        """Initialize the translation engine.

        Args:
            max_iterations: Maximum fixpoint iterations (default 10).

        Rationale for default ``max_iterations=10``:
            Conservative safety bound over the observed convergence
            depth on COGANT's three control-positive fixtures
            (``calculator``, ``event_pipeline``, ``flask_mini``, P3
            qualitative validation, R&D_LOG 2026-04-09). Empirically the
            fixpoint settles in <=5 iterations on all three fixtures and
            on the ``cpython/Lib/json`` real-world corpus (~1.2k LoC),
            so 10 is a ~2x safety margin. The choice is also consistent
            with the Kleene-iteration fixpoint framing of Cousot & Cousot
            (POPL '77, ``docs/evaluation/LITERATURE.md`` §1), which guarantees
            termination on a finite role-assignment lattice — 10
            iterations is an engineering cap rather than a theoretical
            bound. See ``docs/evaluation/CALIBRATION.md`` for the calibration plan.
            TODO(calibration): log observed iteration counts on a larger
            corpus (target: 20+ repos) and revise if the empirical
            maximum exceeds 5.
        """
        self.rules: list[TranslationRule] = []
        self.mappings: dict[str, SemanticMapping] = {}
        self._match_log: list[dict[str, Any]] = []
        self._rule_priority: dict[str, int] = {}
        self.max_iterations = max_iterations

    def xǁTranslationEngineǁ__init____mutmut_2(self, max_iterations: int = 10):
        """Initialize the translation engine.

        Args:
            max_iterations: Maximum fixpoint iterations (default 10).

        Rationale for default ``max_iterations=10``:
            Conservative safety bound over the observed convergence
            depth on COGANT's three control-positive fixtures
            (``calculator``, ``event_pipeline``, ``flask_mini``, P3
            qualitative validation, R&D_LOG 2026-04-09). Empirically the
            fixpoint settles in <=5 iterations on all three fixtures and
            on the ``cpython/Lib/json`` real-world corpus (~1.2k LoC),
            so 10 is a ~2x safety margin. The choice is also consistent
            with the Kleene-iteration fixpoint framing of Cousot & Cousot
            (POPL '77, ``docs/evaluation/LITERATURE.md`` §1), which guarantees
            termination on a finite role-assignment lattice — 10
            iterations is an engineering cap rather than a theoretical
            bound. See ``docs/evaluation/CALIBRATION.md`` for the calibration plan.
            TODO(calibration): log observed iteration counts on a larger
            corpus (target: 20+ repos) and revise if the empirical
            maximum exceeds 5.
        """
        self.rules: list[TranslationRule] = None
        self.mappings: dict[str, SemanticMapping] = {}
        self._match_log: list[dict[str, Any]] = []
        self._rule_priority: dict[str, int] = {}
        self.max_iterations = max_iterations

    def xǁTranslationEngineǁ__init____mutmut_3(self, max_iterations: int = 10):
        """Initialize the translation engine.

        Args:
            max_iterations: Maximum fixpoint iterations (default 10).

        Rationale for default ``max_iterations=10``:
            Conservative safety bound over the observed convergence
            depth on COGANT's three control-positive fixtures
            (``calculator``, ``event_pipeline``, ``flask_mini``, P3
            qualitative validation, R&D_LOG 2026-04-09). Empirically the
            fixpoint settles in <=5 iterations on all three fixtures and
            on the ``cpython/Lib/json`` real-world corpus (~1.2k LoC),
            so 10 is a ~2x safety margin. The choice is also consistent
            with the Kleene-iteration fixpoint framing of Cousot & Cousot
            (POPL '77, ``docs/evaluation/LITERATURE.md`` §1), which guarantees
            termination on a finite role-assignment lattice — 10
            iterations is an engineering cap rather than a theoretical
            bound. See ``docs/evaluation/CALIBRATION.md`` for the calibration plan.
            TODO(calibration): log observed iteration counts on a larger
            corpus (target: 20+ repos) and revise if the empirical
            maximum exceeds 5.
        """
        self.rules: list[TranslationRule] = []
        self.mappings: dict[str, SemanticMapping] = None
        self._match_log: list[dict[str, Any]] = []
        self._rule_priority: dict[str, int] = {}
        self.max_iterations = max_iterations

    def xǁTranslationEngineǁ__init____mutmut_4(self, max_iterations: int = 10):
        """Initialize the translation engine.

        Args:
            max_iterations: Maximum fixpoint iterations (default 10).

        Rationale for default ``max_iterations=10``:
            Conservative safety bound over the observed convergence
            depth on COGANT's three control-positive fixtures
            (``calculator``, ``event_pipeline``, ``flask_mini``, P3
            qualitative validation, R&D_LOG 2026-04-09). Empirically the
            fixpoint settles in <=5 iterations on all three fixtures and
            on the ``cpython/Lib/json`` real-world corpus (~1.2k LoC),
            so 10 is a ~2x safety margin. The choice is also consistent
            with the Kleene-iteration fixpoint framing of Cousot & Cousot
            (POPL '77, ``docs/evaluation/LITERATURE.md`` §1), which guarantees
            termination on a finite role-assignment lattice — 10
            iterations is an engineering cap rather than a theoretical
            bound. See ``docs/evaluation/CALIBRATION.md`` for the calibration plan.
            TODO(calibration): log observed iteration counts on a larger
            corpus (target: 20+ repos) and revise if the empirical
            maximum exceeds 5.
        """
        self.rules: list[TranslationRule] = []
        self.mappings: dict[str, SemanticMapping] = {}
        self._match_log: list[dict[str, Any]] = None
        self._rule_priority: dict[str, int] = {}
        self.max_iterations = max_iterations

    def xǁTranslationEngineǁ__init____mutmut_5(self, max_iterations: int = 10):
        """Initialize the translation engine.

        Args:
            max_iterations: Maximum fixpoint iterations (default 10).

        Rationale for default ``max_iterations=10``:
            Conservative safety bound over the observed convergence
            depth on COGANT's three control-positive fixtures
            (``calculator``, ``event_pipeline``, ``flask_mini``, P3
            qualitative validation, R&D_LOG 2026-04-09). Empirically the
            fixpoint settles in <=5 iterations on all three fixtures and
            on the ``cpython/Lib/json`` real-world corpus (~1.2k LoC),
            so 10 is a ~2x safety margin. The choice is also consistent
            with the Kleene-iteration fixpoint framing of Cousot & Cousot
            (POPL '77, ``docs/evaluation/LITERATURE.md`` §1), which guarantees
            termination on a finite role-assignment lattice — 10
            iterations is an engineering cap rather than a theoretical
            bound. See ``docs/evaluation/CALIBRATION.md`` for the calibration plan.
            TODO(calibration): log observed iteration counts on a larger
            corpus (target: 20+ repos) and revise if the empirical
            maximum exceeds 5.
        """
        self.rules: list[TranslationRule] = []
        self.mappings: dict[str, SemanticMapping] = {}
        self._match_log: list[dict[str, Any]] = []
        self._rule_priority: dict[str, int] = None
        self.max_iterations = max_iterations

    def xǁTranslationEngineǁ__init____mutmut_6(self, max_iterations: int = 10):
        """Initialize the translation engine.

        Args:
            max_iterations: Maximum fixpoint iterations (default 10).

        Rationale for default ``max_iterations=10``:
            Conservative safety bound over the observed convergence
            depth on COGANT's three control-positive fixtures
            (``calculator``, ``event_pipeline``, ``flask_mini``, P3
            qualitative validation, R&D_LOG 2026-04-09). Empirically the
            fixpoint settles in <=5 iterations on all three fixtures and
            on the ``cpython/Lib/json`` real-world corpus (~1.2k LoC),
            so 10 is a ~2x safety margin. The choice is also consistent
            with the Kleene-iteration fixpoint framing of Cousot & Cousot
            (POPL '77, ``docs/evaluation/LITERATURE.md`` §1), which guarantees
            termination on a finite role-assignment lattice — 10
            iterations is an engineering cap rather than a theoretical
            bound. See ``docs/evaluation/CALIBRATION.md`` for the calibration plan.
            TODO(calibration): log observed iteration counts on a larger
            corpus (target: 20+ repos) and revise if the empirical
            maximum exceeds 5.
        """
        self.rules: list[TranslationRule] = []
        self.mappings: dict[str, SemanticMapping] = {}
        self._match_log: list[dict[str, Any]] = []
        self._rule_priority: dict[str, int] = {}
        self.max_iterations = None
    
    xǁTranslationEngineǁ__init____mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationEngineǁ__init____mutmut_1': xǁTranslationEngineǁ__init____mutmut_1, 
        'xǁTranslationEngineǁ__init____mutmut_2': xǁTranslationEngineǁ__init____mutmut_2, 
        'xǁTranslationEngineǁ__init____mutmut_3': xǁTranslationEngineǁ__init____mutmut_3, 
        'xǁTranslationEngineǁ__init____mutmut_4': xǁTranslationEngineǁ__init____mutmut_4, 
        'xǁTranslationEngineǁ__init____mutmut_5': xǁTranslationEngineǁ__init____mutmut_5, 
        'xǁTranslationEngineǁ__init____mutmut_6': xǁTranslationEngineǁ__init____mutmut_6
    }
    xǁTranslationEngineǁ__init____mutmut_orig.__name__ = 'xǁTranslationEngineǁ__init__'

    def register_rule(self, rule: TranslationRule) -> None:
        args = [rule]# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationEngineǁregister_rule__mutmut_orig'), object.__getattribute__(self, 'xǁTranslationEngineǁregister_rule__mutmut_mutants'), args, kwargs, self)

    def xǁTranslationEngineǁregister_rule__mutmut_orig(self, rule: TranslationRule) -> None:
        """Register a translation rule.

        Args:
            rule: Rule to register.
        """
        self.rules.append(rule)

    def xǁTranslationEngineǁregister_rule__mutmut_1(self, rule: TranslationRule) -> None:
        """Register a translation rule.

        Args:
            rule: Rule to register.
        """
        self.rules.append(None)
    
    xǁTranslationEngineǁregister_rule__mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationEngineǁregister_rule__mutmut_1': xǁTranslationEngineǁregister_rule__mutmut_1
    }
    xǁTranslationEngineǁregister_rule__mutmut_orig.__name__ = 'xǁTranslationEngineǁregister_rule'

    def translate(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        args = [graph, rule_filter]# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationEngineǁtranslate__mutmut_orig'), object.__getattribute__(self, 'xǁTranslationEngineǁtranslate__mutmut_mutants'), args, kwargs, self)

    def xǁTranslationEngineǁtranslate__mutmut_orig(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_1(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = None

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_2(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(None)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_3(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(None, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_4(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, None):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_5(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_6(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, ):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_7(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(2, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_8(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations - 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_9(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 2):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_10(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug(None,
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_11(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         None, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_12(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, None)

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_13(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug(iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_14(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_15(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, )

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_16(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("XXFixpoint iteration %d starting (%d existing mappings)XX",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_17(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_18(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("FIXPOINT ITERATION %D STARTING (%D EXISTING MAPPINGS)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_19(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = None

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_20(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                None, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_21(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, None, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_22(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=None, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_23(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=None
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_24(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_25(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_26(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_27(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_28(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                None,
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_29(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                None,
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_30(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                None,
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_31(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_32(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_33(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_34(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "XXiteration_completeXX",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_35(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "ITERATION_COMPLETE",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_36(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "XXengineXX",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_37(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "ENGINE",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_38(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info(None,
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_39(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        None, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_40(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, None)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_41(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info(iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_42(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_43(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, )

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_44(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("XXFixpoint iteration %d: %d new mappingsXX",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_45(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_46(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("FIXPOINT ITERATION %D: %D NEW MAPPINGS",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_47(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass != 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_48(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 1:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_49(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info(None, iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_50(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", None)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_51(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info(iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_52(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", )
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_53(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("XXFixpoint reached after %d iteration(s)XX", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_54(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_55(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("FIXPOINT REACHED AFTER %D ITERATION(S)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_56(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                return
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_57(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                None, self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_58(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", None
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_59(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_60(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_61(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "XXMax iterations (%d) reached without convergenceXX", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_62(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_63(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "MAX ITERATIONS (%D) REACHED WITHOUT CONVERGENCE", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate__mutmut_64(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(None)
    
    xǁTranslationEngineǁtranslate__mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationEngineǁtranslate__mutmut_1': xǁTranslationEngineǁtranslate__mutmut_1, 
        'xǁTranslationEngineǁtranslate__mutmut_2': xǁTranslationEngineǁtranslate__mutmut_2, 
        'xǁTranslationEngineǁtranslate__mutmut_3': xǁTranslationEngineǁtranslate__mutmut_3, 
        'xǁTranslationEngineǁtranslate__mutmut_4': xǁTranslationEngineǁtranslate__mutmut_4, 
        'xǁTranslationEngineǁtranslate__mutmut_5': xǁTranslationEngineǁtranslate__mutmut_5, 
        'xǁTranslationEngineǁtranslate__mutmut_6': xǁTranslationEngineǁtranslate__mutmut_6, 
        'xǁTranslationEngineǁtranslate__mutmut_7': xǁTranslationEngineǁtranslate__mutmut_7, 
        'xǁTranslationEngineǁtranslate__mutmut_8': xǁTranslationEngineǁtranslate__mutmut_8, 
        'xǁTranslationEngineǁtranslate__mutmut_9': xǁTranslationEngineǁtranslate__mutmut_9, 
        'xǁTranslationEngineǁtranslate__mutmut_10': xǁTranslationEngineǁtranslate__mutmut_10, 
        'xǁTranslationEngineǁtranslate__mutmut_11': xǁTranslationEngineǁtranslate__mutmut_11, 
        'xǁTranslationEngineǁtranslate__mutmut_12': xǁTranslationEngineǁtranslate__mutmut_12, 
        'xǁTranslationEngineǁtranslate__mutmut_13': xǁTranslationEngineǁtranslate__mutmut_13, 
        'xǁTranslationEngineǁtranslate__mutmut_14': xǁTranslationEngineǁtranslate__mutmut_14, 
        'xǁTranslationEngineǁtranslate__mutmut_15': xǁTranslationEngineǁtranslate__mutmut_15, 
        'xǁTranslationEngineǁtranslate__mutmut_16': xǁTranslationEngineǁtranslate__mutmut_16, 
        'xǁTranslationEngineǁtranslate__mutmut_17': xǁTranslationEngineǁtranslate__mutmut_17, 
        'xǁTranslationEngineǁtranslate__mutmut_18': xǁTranslationEngineǁtranslate__mutmut_18, 
        'xǁTranslationEngineǁtranslate__mutmut_19': xǁTranslationEngineǁtranslate__mutmut_19, 
        'xǁTranslationEngineǁtranslate__mutmut_20': xǁTranslationEngineǁtranslate__mutmut_20, 
        'xǁTranslationEngineǁtranslate__mutmut_21': xǁTranslationEngineǁtranslate__mutmut_21, 
        'xǁTranslationEngineǁtranslate__mutmut_22': xǁTranslationEngineǁtranslate__mutmut_22, 
        'xǁTranslationEngineǁtranslate__mutmut_23': xǁTranslationEngineǁtranslate__mutmut_23, 
        'xǁTranslationEngineǁtranslate__mutmut_24': xǁTranslationEngineǁtranslate__mutmut_24, 
        'xǁTranslationEngineǁtranslate__mutmut_25': xǁTranslationEngineǁtranslate__mutmut_25, 
        'xǁTranslationEngineǁtranslate__mutmut_26': xǁTranslationEngineǁtranslate__mutmut_26, 
        'xǁTranslationEngineǁtranslate__mutmut_27': xǁTranslationEngineǁtranslate__mutmut_27, 
        'xǁTranslationEngineǁtranslate__mutmut_28': xǁTranslationEngineǁtranslate__mutmut_28, 
        'xǁTranslationEngineǁtranslate__mutmut_29': xǁTranslationEngineǁtranslate__mutmut_29, 
        'xǁTranslationEngineǁtranslate__mutmut_30': xǁTranslationEngineǁtranslate__mutmut_30, 
        'xǁTranslationEngineǁtranslate__mutmut_31': xǁTranslationEngineǁtranslate__mutmut_31, 
        'xǁTranslationEngineǁtranslate__mutmut_32': xǁTranslationEngineǁtranslate__mutmut_32, 
        'xǁTranslationEngineǁtranslate__mutmut_33': xǁTranslationEngineǁtranslate__mutmut_33, 
        'xǁTranslationEngineǁtranslate__mutmut_34': xǁTranslationEngineǁtranslate__mutmut_34, 
        'xǁTranslationEngineǁtranslate__mutmut_35': xǁTranslationEngineǁtranslate__mutmut_35, 
        'xǁTranslationEngineǁtranslate__mutmut_36': xǁTranslationEngineǁtranslate__mutmut_36, 
        'xǁTranslationEngineǁtranslate__mutmut_37': xǁTranslationEngineǁtranslate__mutmut_37, 
        'xǁTranslationEngineǁtranslate__mutmut_38': xǁTranslationEngineǁtranslate__mutmut_38, 
        'xǁTranslationEngineǁtranslate__mutmut_39': xǁTranslationEngineǁtranslate__mutmut_39, 
        'xǁTranslationEngineǁtranslate__mutmut_40': xǁTranslationEngineǁtranslate__mutmut_40, 
        'xǁTranslationEngineǁtranslate__mutmut_41': xǁTranslationEngineǁtranslate__mutmut_41, 
        'xǁTranslationEngineǁtranslate__mutmut_42': xǁTranslationEngineǁtranslate__mutmut_42, 
        'xǁTranslationEngineǁtranslate__mutmut_43': xǁTranslationEngineǁtranslate__mutmut_43, 
        'xǁTranslationEngineǁtranslate__mutmut_44': xǁTranslationEngineǁtranslate__mutmut_44, 
        'xǁTranslationEngineǁtranslate__mutmut_45': xǁTranslationEngineǁtranslate__mutmut_45, 
        'xǁTranslationEngineǁtranslate__mutmut_46': xǁTranslationEngineǁtranslate__mutmut_46, 
        'xǁTranslationEngineǁtranslate__mutmut_47': xǁTranslationEngineǁtranslate__mutmut_47, 
        'xǁTranslationEngineǁtranslate__mutmut_48': xǁTranslationEngineǁtranslate__mutmut_48, 
        'xǁTranslationEngineǁtranslate__mutmut_49': xǁTranslationEngineǁtranslate__mutmut_49, 
        'xǁTranslationEngineǁtranslate__mutmut_50': xǁTranslationEngineǁtranslate__mutmut_50, 
        'xǁTranslationEngineǁtranslate__mutmut_51': xǁTranslationEngineǁtranslate__mutmut_51, 
        'xǁTranslationEngineǁtranslate__mutmut_52': xǁTranslationEngineǁtranslate__mutmut_52, 
        'xǁTranslationEngineǁtranslate__mutmut_53': xǁTranslationEngineǁtranslate__mutmut_53, 
        'xǁTranslationEngineǁtranslate__mutmut_54': xǁTranslationEngineǁtranslate__mutmut_54, 
        'xǁTranslationEngineǁtranslate__mutmut_55': xǁTranslationEngineǁtranslate__mutmut_55, 
        'xǁTranslationEngineǁtranslate__mutmut_56': xǁTranslationEngineǁtranslate__mutmut_56, 
        'xǁTranslationEngineǁtranslate__mutmut_57': xǁTranslationEngineǁtranslate__mutmut_57, 
        'xǁTranslationEngineǁtranslate__mutmut_58': xǁTranslationEngineǁtranslate__mutmut_58, 
        'xǁTranslationEngineǁtranslate__mutmut_59': xǁTranslationEngineǁtranslate__mutmut_59, 
        'xǁTranslationEngineǁtranslate__mutmut_60': xǁTranslationEngineǁtranslate__mutmut_60, 
        'xǁTranslationEngineǁtranslate__mutmut_61': xǁTranslationEngineǁtranslate__mutmut_61, 
        'xǁTranslationEngineǁtranslate__mutmut_62': xǁTranslationEngineǁtranslate__mutmut_62, 
        'xǁTranslationEngineǁtranslate__mutmut_63': xǁTranslationEngineǁtranslate__mutmut_63, 
        'xǁTranslationEngineǁtranslate__mutmut_64': xǁTranslationEngineǁtranslate__mutmut_64
    }
    xǁTranslationEngineǁtranslate__mutmut_orig.__name__ = 'xǁTranslationEngineǁtranslate'

    def _apply_single_pass(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        args = [graph, query, rule_filter, iteration]# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationEngineǁ_apply_single_pass__mutmut_orig'), object.__getattribute__(self, 'xǁTranslationEngineǁ_apply_single_pass__mutmut_mutants'), args, kwargs, self)

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_orig(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_1(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 1,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_2(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = None
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_3(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 1
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_4(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = None

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_5(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(None, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_6(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=None, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_7(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=None)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_8(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_9(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_10(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, )

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_11(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: None, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_12(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=False)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_13(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter or rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_14(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_15(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                break

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_16(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = None
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_17(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(None, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_18(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, None)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_19(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_20(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, )
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_21(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    None,
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_22(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    None, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_23(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, None, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_24(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, None,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_25(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_26(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_27(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_28(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_29(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "XXRule %r failed during matching (iteration=%d): %sXX",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_30(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_31(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "RULE %R FAILED DURING MATCHING (ITERATION=%D): %S",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_32(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    None,
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_33(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    None,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_34(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    None,
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_35(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_36(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_37(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_38(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "XXrule_errorXX",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_39(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "RULE_ERROR",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_40(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                break

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_41(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = None
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_42(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(None, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_43(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, None)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_44(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_45(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, )
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_46(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping or mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_47(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_48(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = None
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_49(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = None
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_50(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match(None, rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_51(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", None, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_52(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, None)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_53(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match(rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_54(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_55(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, )
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_56(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("XXmapping_createdXX", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_57(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("MAPPING_CREATED", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_58(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings = 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_59(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings -= 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_60(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 2
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_61(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        None,
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_62(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        None, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_63(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, None, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_64(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, None, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_65(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, None,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_66(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_67(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_68(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_69(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_70(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_71(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "XXRule %r failed during apply (iteration=%d, match=%r): %sXX",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_72(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_73(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "RULE %R FAILED DURING APPLY (ITERATION=%D, MATCH=%R): %S",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_74(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        None,
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_75(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        None,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_76(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        None,
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_77(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_78(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_79(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_80(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "XXapply_errorXX",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings

    def xǁTranslationEngineǁ_apply_single_pass__mutmut_81(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "APPLY_ERROR",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )

        return new_mappings
    
    xǁTranslationEngineǁ_apply_single_pass__mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationEngineǁ_apply_single_pass__mutmut_1': xǁTranslationEngineǁ_apply_single_pass__mutmut_1, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_2': xǁTranslationEngineǁ_apply_single_pass__mutmut_2, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_3': xǁTranslationEngineǁ_apply_single_pass__mutmut_3, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_4': xǁTranslationEngineǁ_apply_single_pass__mutmut_4, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_5': xǁTranslationEngineǁ_apply_single_pass__mutmut_5, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_6': xǁTranslationEngineǁ_apply_single_pass__mutmut_6, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_7': xǁTranslationEngineǁ_apply_single_pass__mutmut_7, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_8': xǁTranslationEngineǁ_apply_single_pass__mutmut_8, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_9': xǁTranslationEngineǁ_apply_single_pass__mutmut_9, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_10': xǁTranslationEngineǁ_apply_single_pass__mutmut_10, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_11': xǁTranslationEngineǁ_apply_single_pass__mutmut_11, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_12': xǁTranslationEngineǁ_apply_single_pass__mutmut_12, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_13': xǁTranslationEngineǁ_apply_single_pass__mutmut_13, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_14': xǁTranslationEngineǁ_apply_single_pass__mutmut_14, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_15': xǁTranslationEngineǁ_apply_single_pass__mutmut_15, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_16': xǁTranslationEngineǁ_apply_single_pass__mutmut_16, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_17': xǁTranslationEngineǁ_apply_single_pass__mutmut_17, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_18': xǁTranslationEngineǁ_apply_single_pass__mutmut_18, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_19': xǁTranslationEngineǁ_apply_single_pass__mutmut_19, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_20': xǁTranslationEngineǁ_apply_single_pass__mutmut_20, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_21': xǁTranslationEngineǁ_apply_single_pass__mutmut_21, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_22': xǁTranslationEngineǁ_apply_single_pass__mutmut_22, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_23': xǁTranslationEngineǁ_apply_single_pass__mutmut_23, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_24': xǁTranslationEngineǁ_apply_single_pass__mutmut_24, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_25': xǁTranslationEngineǁ_apply_single_pass__mutmut_25, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_26': xǁTranslationEngineǁ_apply_single_pass__mutmut_26, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_27': xǁTranslationEngineǁ_apply_single_pass__mutmut_27, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_28': xǁTranslationEngineǁ_apply_single_pass__mutmut_28, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_29': xǁTranslationEngineǁ_apply_single_pass__mutmut_29, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_30': xǁTranslationEngineǁ_apply_single_pass__mutmut_30, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_31': xǁTranslationEngineǁ_apply_single_pass__mutmut_31, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_32': xǁTranslationEngineǁ_apply_single_pass__mutmut_32, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_33': xǁTranslationEngineǁ_apply_single_pass__mutmut_33, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_34': xǁTranslationEngineǁ_apply_single_pass__mutmut_34, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_35': xǁTranslationEngineǁ_apply_single_pass__mutmut_35, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_36': xǁTranslationEngineǁ_apply_single_pass__mutmut_36, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_37': xǁTranslationEngineǁ_apply_single_pass__mutmut_37, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_38': xǁTranslationEngineǁ_apply_single_pass__mutmut_38, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_39': xǁTranslationEngineǁ_apply_single_pass__mutmut_39, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_40': xǁTranslationEngineǁ_apply_single_pass__mutmut_40, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_41': xǁTranslationEngineǁ_apply_single_pass__mutmut_41, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_42': xǁTranslationEngineǁ_apply_single_pass__mutmut_42, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_43': xǁTranslationEngineǁ_apply_single_pass__mutmut_43, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_44': xǁTranslationEngineǁ_apply_single_pass__mutmut_44, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_45': xǁTranslationEngineǁ_apply_single_pass__mutmut_45, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_46': xǁTranslationEngineǁ_apply_single_pass__mutmut_46, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_47': xǁTranslationEngineǁ_apply_single_pass__mutmut_47, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_48': xǁTranslationEngineǁ_apply_single_pass__mutmut_48, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_49': xǁTranslationEngineǁ_apply_single_pass__mutmut_49, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_50': xǁTranslationEngineǁ_apply_single_pass__mutmut_50, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_51': xǁTranslationEngineǁ_apply_single_pass__mutmut_51, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_52': xǁTranslationEngineǁ_apply_single_pass__mutmut_52, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_53': xǁTranslationEngineǁ_apply_single_pass__mutmut_53, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_54': xǁTranslationEngineǁ_apply_single_pass__mutmut_54, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_55': xǁTranslationEngineǁ_apply_single_pass__mutmut_55, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_56': xǁTranslationEngineǁ_apply_single_pass__mutmut_56, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_57': xǁTranslationEngineǁ_apply_single_pass__mutmut_57, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_58': xǁTranslationEngineǁ_apply_single_pass__mutmut_58, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_59': xǁTranslationEngineǁ_apply_single_pass__mutmut_59, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_60': xǁTranslationEngineǁ_apply_single_pass__mutmut_60, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_61': xǁTranslationEngineǁ_apply_single_pass__mutmut_61, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_62': xǁTranslationEngineǁ_apply_single_pass__mutmut_62, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_63': xǁTranslationEngineǁ_apply_single_pass__mutmut_63, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_64': xǁTranslationEngineǁ_apply_single_pass__mutmut_64, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_65': xǁTranslationEngineǁ_apply_single_pass__mutmut_65, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_66': xǁTranslationEngineǁ_apply_single_pass__mutmut_66, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_67': xǁTranslationEngineǁ_apply_single_pass__mutmut_67, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_68': xǁTranslationEngineǁ_apply_single_pass__mutmut_68, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_69': xǁTranslationEngineǁ_apply_single_pass__mutmut_69, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_70': xǁTranslationEngineǁ_apply_single_pass__mutmut_70, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_71': xǁTranslationEngineǁ_apply_single_pass__mutmut_71, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_72': xǁTranslationEngineǁ_apply_single_pass__mutmut_72, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_73': xǁTranslationEngineǁ_apply_single_pass__mutmut_73, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_74': xǁTranslationEngineǁ_apply_single_pass__mutmut_74, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_75': xǁTranslationEngineǁ_apply_single_pass__mutmut_75, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_76': xǁTranslationEngineǁ_apply_single_pass__mutmut_76, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_77': xǁTranslationEngineǁ_apply_single_pass__mutmut_77, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_78': xǁTranslationEngineǁ_apply_single_pass__mutmut_78, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_79': xǁTranslationEngineǁ_apply_single_pass__mutmut_79, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_80': xǁTranslationEngineǁ_apply_single_pass__mutmut_80, 
        'xǁTranslationEngineǁ_apply_single_pass__mutmut_81': xǁTranslationEngineǁ_apply_single_pass__mutmut_81
    }
    xǁTranslationEngineǁ_apply_single_pass__mutmut_orig.__name__ = 'xǁTranslationEngineǁ_apply_single_pass'

    def translate_with_confidence(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        args = [graph, rule_filter]# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationEngineǁtranslate_with_confidence__mutmut_orig'), object.__getattribute__(self, 'xǁTranslationEngineǁtranslate_with_confidence__mutmut_mutants'), args, kwargs, self)

    def xǁTranslationEngineǁtranslate_with_confidence__mutmut_orig(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate and rescore all mappings using the ConfidenceModel.

        Runs the standard fixpoint translation, then applies the
        ConfidenceModel to update confidence scores, tiers, and
        conflict penalties on every resulting mapping.

        Args:
            graph: Program graph to translate.
            rule_filter: Optional list of rule names to apply (None = all).

        Returns:
            List of semantic mappings with updated confidence scores.
        """
        mappings = self.translate(graph, rule_filter=rule_filter)

        model = ConfidenceModel()
        model.score_batch(mappings)

        # Re-resolve conflicts now that scores are updated
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate_with_confidence__mutmut_1(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate and rescore all mappings using the ConfidenceModel.

        Runs the standard fixpoint translation, then applies the
        ConfidenceModel to update confidence scores, tiers, and
        conflict penalties on every resulting mapping.

        Args:
            graph: Program graph to translate.
            rule_filter: Optional list of rule names to apply (None = all).

        Returns:
            List of semantic mappings with updated confidence scores.
        """
        mappings = None

        model = ConfidenceModel()
        model.score_batch(mappings)

        # Re-resolve conflicts now that scores are updated
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate_with_confidence__mutmut_2(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate and rescore all mappings using the ConfidenceModel.

        Runs the standard fixpoint translation, then applies the
        ConfidenceModel to update confidence scores, tiers, and
        conflict penalties on every resulting mapping.

        Args:
            graph: Program graph to translate.
            rule_filter: Optional list of rule names to apply (None = all).

        Returns:
            List of semantic mappings with updated confidence scores.
        """
        mappings = self.translate(None, rule_filter=rule_filter)

        model = ConfidenceModel()
        model.score_batch(mappings)

        # Re-resolve conflicts now that scores are updated
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate_with_confidence__mutmut_3(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate and rescore all mappings using the ConfidenceModel.

        Runs the standard fixpoint translation, then applies the
        ConfidenceModel to update confidence scores, tiers, and
        conflict penalties on every resulting mapping.

        Args:
            graph: Program graph to translate.
            rule_filter: Optional list of rule names to apply (None = all).

        Returns:
            List of semantic mappings with updated confidence scores.
        """
        mappings = self.translate(graph, rule_filter=None)

        model = ConfidenceModel()
        model.score_batch(mappings)

        # Re-resolve conflicts now that scores are updated
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate_with_confidence__mutmut_4(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate and rescore all mappings using the ConfidenceModel.

        Runs the standard fixpoint translation, then applies the
        ConfidenceModel to update confidence scores, tiers, and
        conflict penalties on every resulting mapping.

        Args:
            graph: Program graph to translate.
            rule_filter: Optional list of rule names to apply (None = all).

        Returns:
            List of semantic mappings with updated confidence scores.
        """
        mappings = self.translate(rule_filter=rule_filter)

        model = ConfidenceModel()
        model.score_batch(mappings)

        # Re-resolve conflicts now that scores are updated
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate_with_confidence__mutmut_5(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate and rescore all mappings using the ConfidenceModel.

        Runs the standard fixpoint translation, then applies the
        ConfidenceModel to update confidence scores, tiers, and
        conflict penalties on every resulting mapping.

        Args:
            graph: Program graph to translate.
            rule_filter: Optional list of rule names to apply (None = all).

        Returns:
            List of semantic mappings with updated confidence scores.
        """
        mappings = self.translate(graph, )

        model = ConfidenceModel()
        model.score_batch(mappings)

        # Re-resolve conflicts now that scores are updated
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate_with_confidence__mutmut_6(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate and rescore all mappings using the ConfidenceModel.

        Runs the standard fixpoint translation, then applies the
        ConfidenceModel to update confidence scores, tiers, and
        conflict penalties on every resulting mapping.

        Args:
            graph: Program graph to translate.
            rule_filter: Optional list of rule names to apply (None = all).

        Returns:
            List of semantic mappings with updated confidence scores.
        """
        mappings = self.translate(graph, rule_filter=rule_filter)

        model = None
        model.score_batch(mappings)

        # Re-resolve conflicts now that scores are updated
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate_with_confidence__mutmut_7(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate and rescore all mappings using the ConfidenceModel.

        Runs the standard fixpoint translation, then applies the
        ConfidenceModel to update confidence scores, tiers, and
        conflict penalties on every resulting mapping.

        Args:
            graph: Program graph to translate.
            rule_filter: Optional list of rule names to apply (None = all).

        Returns:
            List of semantic mappings with updated confidence scores.
        """
        mappings = self.translate(graph, rule_filter=rule_filter)

        model = ConfidenceModel()
        model.score_batch(None)

        # Re-resolve conflicts now that scores are updated
        self._resolve_conflicts()

        return list(self.mappings.values())

    def xǁTranslationEngineǁtranslate_with_confidence__mutmut_8(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate and rescore all mappings using the ConfidenceModel.

        Runs the standard fixpoint translation, then applies the
        ConfidenceModel to update confidence scores, tiers, and
        conflict penalties on every resulting mapping.

        Args:
            graph: Program graph to translate.
            rule_filter: Optional list of rule names to apply (None = all).

        Returns:
            List of semantic mappings with updated confidence scores.
        """
        mappings = self.translate(graph, rule_filter=rule_filter)

        model = ConfidenceModel()
        model.score_batch(mappings)

        # Re-resolve conflicts now that scores are updated
        self._resolve_conflicts()

        return list(None)
    
    xǁTranslationEngineǁtranslate_with_confidence__mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationEngineǁtranslate_with_confidence__mutmut_1': xǁTranslationEngineǁtranslate_with_confidence__mutmut_1, 
        'xǁTranslationEngineǁtranslate_with_confidence__mutmut_2': xǁTranslationEngineǁtranslate_with_confidence__mutmut_2, 
        'xǁTranslationEngineǁtranslate_with_confidence__mutmut_3': xǁTranslationEngineǁtranslate_with_confidence__mutmut_3, 
        'xǁTranslationEngineǁtranslate_with_confidence__mutmut_4': xǁTranslationEngineǁtranslate_with_confidence__mutmut_4, 
        'xǁTranslationEngineǁtranslate_with_confidence__mutmut_5': xǁTranslationEngineǁtranslate_with_confidence__mutmut_5, 
        'xǁTranslationEngineǁtranslate_with_confidence__mutmut_6': xǁTranslationEngineǁtranslate_with_confidence__mutmut_6, 
        'xǁTranslationEngineǁtranslate_with_confidence__mutmut_7': xǁTranslationEngineǁtranslate_with_confidence__mutmut_7, 
        'xǁTranslationEngineǁtranslate_with_confidence__mutmut_8': xǁTranslationEngineǁtranslate_with_confidence__mutmut_8
    }
    xǁTranslationEngineǁtranslate_with_confidence__mutmut_orig.__name__ = 'xǁTranslationEngineǁtranslate_with_confidence'

    def _resolve_conflicts(self) -> None:
        args = []# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationEngineǁ_resolve_conflicts__mutmut_orig'), object.__getattribute__(self, 'xǁTranslationEngineǁ_resolve_conflicts__mutmut_mutants'), args, kwargs, self)

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_orig(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_1(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = None
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_2(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(None)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_3(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(None, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_4(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, None).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_5(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault([]).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_6(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, ).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_7(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = None
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_8(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) <= 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_9(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 3:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_10(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                break
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_11(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(None):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_12(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(None, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_13(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, None):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_14(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_15(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, ):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_16(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i - 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_17(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 2, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_18(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = None
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_19(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add(None)

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_20(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a <= b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_21(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = None
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_22(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove and b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_23(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id not in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_24(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id not in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_25(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                break
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_26(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = None
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_27(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(None)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_28(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = None
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_29(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(None)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_30(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None and mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_31(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is not None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_32(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is not None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_33(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                break
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_34(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = None
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_35(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(None, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_36(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, None)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_37(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_38(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, )
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_39(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 1)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_40(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = None
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_41(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(None, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_42(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, None)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_43(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_44(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, )
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_45(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 1)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_46(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = None
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_47(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = None
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_48(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a > key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_49(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = None
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_50(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = None
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_51(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(None)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_52(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = None
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_53(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids) | set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_54(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(None)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_55(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(None)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_56(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                None,
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_57(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                None,
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_58(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                None,
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_59(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_60(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_61(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_62(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "XXconflict_resolvedXX",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_63(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "CONFLICT_RESOLVED",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_64(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "XXengineXX",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def xǁTranslationEngineǁ_resolve_conflicts__mutmut_65(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "ENGINE",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]
    
    xǁTranslationEngineǁ_resolve_conflicts__mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationEngineǁ_resolve_conflicts__mutmut_1': xǁTranslationEngineǁ_resolve_conflicts__mutmut_1, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_2': xǁTranslationEngineǁ_resolve_conflicts__mutmut_2, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_3': xǁTranslationEngineǁ_resolve_conflicts__mutmut_3, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_4': xǁTranslationEngineǁ_resolve_conflicts__mutmut_4, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_5': xǁTranslationEngineǁ_resolve_conflicts__mutmut_5, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_6': xǁTranslationEngineǁ_resolve_conflicts__mutmut_6, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_7': xǁTranslationEngineǁ_resolve_conflicts__mutmut_7, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_8': xǁTranslationEngineǁ_resolve_conflicts__mutmut_8, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_9': xǁTranslationEngineǁ_resolve_conflicts__mutmut_9, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_10': xǁTranslationEngineǁ_resolve_conflicts__mutmut_10, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_11': xǁTranslationEngineǁ_resolve_conflicts__mutmut_11, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_12': xǁTranslationEngineǁ_resolve_conflicts__mutmut_12, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_13': xǁTranslationEngineǁ_resolve_conflicts__mutmut_13, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_14': xǁTranslationEngineǁ_resolve_conflicts__mutmut_14, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_15': xǁTranslationEngineǁ_resolve_conflicts__mutmut_15, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_16': xǁTranslationEngineǁ_resolve_conflicts__mutmut_16, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_17': xǁTranslationEngineǁ_resolve_conflicts__mutmut_17, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_18': xǁTranslationEngineǁ_resolve_conflicts__mutmut_18, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_19': xǁTranslationEngineǁ_resolve_conflicts__mutmut_19, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_20': xǁTranslationEngineǁ_resolve_conflicts__mutmut_20, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_21': xǁTranslationEngineǁ_resolve_conflicts__mutmut_21, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_22': xǁTranslationEngineǁ_resolve_conflicts__mutmut_22, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_23': xǁTranslationEngineǁ_resolve_conflicts__mutmut_23, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_24': xǁTranslationEngineǁ_resolve_conflicts__mutmut_24, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_25': xǁTranslationEngineǁ_resolve_conflicts__mutmut_25, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_26': xǁTranslationEngineǁ_resolve_conflicts__mutmut_26, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_27': xǁTranslationEngineǁ_resolve_conflicts__mutmut_27, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_28': xǁTranslationEngineǁ_resolve_conflicts__mutmut_28, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_29': xǁTranslationEngineǁ_resolve_conflicts__mutmut_29, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_30': xǁTranslationEngineǁ_resolve_conflicts__mutmut_30, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_31': xǁTranslationEngineǁ_resolve_conflicts__mutmut_31, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_32': xǁTranslationEngineǁ_resolve_conflicts__mutmut_32, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_33': xǁTranslationEngineǁ_resolve_conflicts__mutmut_33, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_34': xǁTranslationEngineǁ_resolve_conflicts__mutmut_34, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_35': xǁTranslationEngineǁ_resolve_conflicts__mutmut_35, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_36': xǁTranslationEngineǁ_resolve_conflicts__mutmut_36, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_37': xǁTranslationEngineǁ_resolve_conflicts__mutmut_37, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_38': xǁTranslationEngineǁ_resolve_conflicts__mutmut_38, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_39': xǁTranslationEngineǁ_resolve_conflicts__mutmut_39, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_40': xǁTranslationEngineǁ_resolve_conflicts__mutmut_40, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_41': xǁTranslationEngineǁ_resolve_conflicts__mutmut_41, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_42': xǁTranslationEngineǁ_resolve_conflicts__mutmut_42, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_43': xǁTranslationEngineǁ_resolve_conflicts__mutmut_43, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_44': xǁTranslationEngineǁ_resolve_conflicts__mutmut_44, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_45': xǁTranslationEngineǁ_resolve_conflicts__mutmut_45, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_46': xǁTranslationEngineǁ_resolve_conflicts__mutmut_46, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_47': xǁTranslationEngineǁ_resolve_conflicts__mutmut_47, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_48': xǁTranslationEngineǁ_resolve_conflicts__mutmut_48, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_49': xǁTranslationEngineǁ_resolve_conflicts__mutmut_49, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_50': xǁTranslationEngineǁ_resolve_conflicts__mutmut_50, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_51': xǁTranslationEngineǁ_resolve_conflicts__mutmut_51, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_52': xǁTranslationEngineǁ_resolve_conflicts__mutmut_52, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_53': xǁTranslationEngineǁ_resolve_conflicts__mutmut_53, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_54': xǁTranslationEngineǁ_resolve_conflicts__mutmut_54, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_55': xǁTranslationEngineǁ_resolve_conflicts__mutmut_55, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_56': xǁTranslationEngineǁ_resolve_conflicts__mutmut_56, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_57': xǁTranslationEngineǁ_resolve_conflicts__mutmut_57, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_58': xǁTranslationEngineǁ_resolve_conflicts__mutmut_58, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_59': xǁTranslationEngineǁ_resolve_conflicts__mutmut_59, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_60': xǁTranslationEngineǁ_resolve_conflicts__mutmut_60, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_61': xǁTranslationEngineǁ_resolve_conflicts__mutmut_61, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_62': xǁTranslationEngineǁ_resolve_conflicts__mutmut_62, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_63': xǁTranslationEngineǁ_resolve_conflicts__mutmut_63, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_64': xǁTranslationEngineǁ_resolve_conflicts__mutmut_64, 
        'xǁTranslationEngineǁ_resolve_conflicts__mutmut_65': xǁTranslationEngineǁ_resolve_conflicts__mutmut_65
    }
    xǁTranslationEngineǁ_resolve_conflicts__mutmut_orig.__name__ = 'xǁTranslationEngineǁ_resolve_conflicts'

    def get_coverage_report(self, graph: ProgramGraph) -> dict[str, Any]:
        args = [graph]# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationEngineǁget_coverage_report__mutmut_orig'), object.__getattribute__(self, 'xǁTranslationEngineǁget_coverage_report__mutmut_mutants'), args, kwargs, self)

    def xǁTranslationEngineǁget_coverage_report__mutmut_orig(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_1(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = None
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_2(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(None)
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_3(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = None

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_4(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(None)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_5(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids = all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_6(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids |= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_7(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = None

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_8(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids + covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_9(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = None
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_10(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = None

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_11(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total / 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_12(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) * total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_13(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 101.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_14(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total >= 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_15(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 1 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_16(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 1.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_17(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "XXtotal_nodesXX": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_18(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "TOTAL_NODES": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_19(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "XXcovered_nodesXX": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_20(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "COVERED_NODES": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_21(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "XXuncovered_nodesXX": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_22(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "UNCOVERED_NODES": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_23(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "XXcoverage_percentXX": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_24(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "COVERAGE_PERCENT": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_25(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(None, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_26(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, None),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_27(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_28(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, ),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_29(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 3),
            "uncovered_node_ids": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_30(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "XXuncovered_node_idsXX": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_31(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "UNCOVERED_NODE_IDS": sorted(uncovered),
        }

    def xǁTranslationEngineǁget_coverage_report__mutmut_32(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(None),
        }
    
    xǁTranslationEngineǁget_coverage_report__mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationEngineǁget_coverage_report__mutmut_1': xǁTranslationEngineǁget_coverage_report__mutmut_1, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_2': xǁTranslationEngineǁget_coverage_report__mutmut_2, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_3': xǁTranslationEngineǁget_coverage_report__mutmut_3, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_4': xǁTranslationEngineǁget_coverage_report__mutmut_4, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_5': xǁTranslationEngineǁget_coverage_report__mutmut_5, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_6': xǁTranslationEngineǁget_coverage_report__mutmut_6, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_7': xǁTranslationEngineǁget_coverage_report__mutmut_7, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_8': xǁTranslationEngineǁget_coverage_report__mutmut_8, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_9': xǁTranslationEngineǁget_coverage_report__mutmut_9, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_10': xǁTranslationEngineǁget_coverage_report__mutmut_10, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_11': xǁTranslationEngineǁget_coverage_report__mutmut_11, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_12': xǁTranslationEngineǁget_coverage_report__mutmut_12, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_13': xǁTranslationEngineǁget_coverage_report__mutmut_13, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_14': xǁTranslationEngineǁget_coverage_report__mutmut_14, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_15': xǁTranslationEngineǁget_coverage_report__mutmut_15, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_16': xǁTranslationEngineǁget_coverage_report__mutmut_16, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_17': xǁTranslationEngineǁget_coverage_report__mutmut_17, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_18': xǁTranslationEngineǁget_coverage_report__mutmut_18, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_19': xǁTranslationEngineǁget_coverage_report__mutmut_19, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_20': xǁTranslationEngineǁget_coverage_report__mutmut_20, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_21': xǁTranslationEngineǁget_coverage_report__mutmut_21, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_22': xǁTranslationEngineǁget_coverage_report__mutmut_22, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_23': xǁTranslationEngineǁget_coverage_report__mutmut_23, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_24': xǁTranslationEngineǁget_coverage_report__mutmut_24, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_25': xǁTranslationEngineǁget_coverage_report__mutmut_25, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_26': xǁTranslationEngineǁget_coverage_report__mutmut_26, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_27': xǁTranslationEngineǁget_coverage_report__mutmut_27, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_28': xǁTranslationEngineǁget_coverage_report__mutmut_28, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_29': xǁTranslationEngineǁget_coverage_report__mutmut_29, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_30': xǁTranslationEngineǁget_coverage_report__mutmut_30, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_31': xǁTranslationEngineǁget_coverage_report__mutmut_31, 
        'xǁTranslationEngineǁget_coverage_report__mutmut_32': xǁTranslationEngineǁget_coverage_report__mutmut_32
    }
    xǁTranslationEngineǁget_coverage_report__mutmut_orig.__name__ = 'xǁTranslationEngineǁget_coverage_report'

    def get_mappings_by_kind(self, kind: MappingKind) -> list[SemanticMapping]:
        args = [kind]# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationEngineǁget_mappings_by_kind__mutmut_orig'), object.__getattribute__(self, 'xǁTranslationEngineǁget_mappings_by_kind__mutmut_mutants'), args, kwargs, self)

    def xǁTranslationEngineǁget_mappings_by_kind__mutmut_orig(self, kind: MappingKind) -> list[SemanticMapping]:
        """Get all mappings of a specific kind.

        Args:
            kind: Kind of mapping to retrieve.

        Returns:
            List of matching mappings.
        """
        return [m for m in self.mappings.values() if m.kind == kind]

    def xǁTranslationEngineǁget_mappings_by_kind__mutmut_1(self, kind: MappingKind) -> list[SemanticMapping]:
        """Get all mappings of a specific kind.

        Args:
            kind: Kind of mapping to retrieve.

        Returns:
            List of matching mappings.
        """
        return [m for m in self.mappings.values() if m.kind != kind]
    
    xǁTranslationEngineǁget_mappings_by_kind__mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationEngineǁget_mappings_by_kind__mutmut_1': xǁTranslationEngineǁget_mappings_by_kind__mutmut_1
    }
    xǁTranslationEngineǁget_mappings_by_kind__mutmut_orig.__name__ = 'xǁTranslationEngineǁget_mappings_by_kind'

    def get_mappings_by_confidence(
        self,
        tier: ConfidenceTier,
    ) -> list[SemanticMapping]:
        args = [tier]# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationEngineǁget_mappings_by_confidence__mutmut_orig'), object.__getattribute__(self, 'xǁTranslationEngineǁget_mappings_by_confidence__mutmut_mutants'), args, kwargs, self)

    def xǁTranslationEngineǁget_mappings_by_confidence__mutmut_orig(
        self,
        tier: ConfidenceTier,
    ) -> list[SemanticMapping]:
        """Get all mappings with a specific confidence tier.

        Args:
            tier: Confidence tier to filter by.

        Returns:
            List of mappings at that tier.
        """
        return [m for m in self.mappings.values() if m.confidence_tier == tier]

    def xǁTranslationEngineǁget_mappings_by_confidence__mutmut_1(
        self,
        tier: ConfidenceTier,
    ) -> list[SemanticMapping]:
        """Get all mappings with a specific confidence tier.

        Args:
            tier: Confidence tier to filter by.

        Returns:
            List of mappings at that tier.
        """
        return [m for m in self.mappings.values() if m.confidence_tier != tier]
    
    xǁTranslationEngineǁget_mappings_by_confidence__mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationEngineǁget_mappings_by_confidence__mutmut_1': xǁTranslationEngineǁget_mappings_by_confidence__mutmut_1
    }
    xǁTranslationEngineǁget_mappings_by_confidence__mutmut_orig.__name__ = 'xǁTranslationEngineǁget_mappings_by_confidence'

    def get_mapping(self, mapping_id: str) -> SemanticMapping | None:
        args = [mapping_id]# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationEngineǁget_mapping__mutmut_orig'), object.__getattribute__(self, 'xǁTranslationEngineǁget_mapping__mutmut_mutants'), args, kwargs, self)

    def xǁTranslationEngineǁget_mapping__mutmut_orig(self, mapping_id: str) -> SemanticMapping | None:
        """Get a mapping by ID.

        Args:
            mapping_id: ID of mapping.

        Returns:
            SemanticMapping if found, None otherwise.
        """
        return self.mappings.get(mapping_id)

    def xǁTranslationEngineǁget_mapping__mutmut_1(self, mapping_id: str) -> SemanticMapping | None:
        """Get a mapping by ID.

        Args:
            mapping_id: ID of mapping.

        Returns:
            SemanticMapping if found, None otherwise.
        """
        return self.mappings.get(None)
    
    xǁTranslationEngineǁget_mapping__mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationEngineǁget_mapping__mutmut_1': xǁTranslationEngineǁget_mapping__mutmut_1
    }
    xǁTranslationEngineǁget_mapping__mutmut_orig.__name__ = 'xǁTranslationEngineǁget_mapping'

    def _log_match(self, event_type: str, rule_name: str, detail: str) -> None:
        args = [event_type, rule_name, detail]# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationEngineǁ_log_match__mutmut_orig'), object.__getattribute__(self, 'xǁTranslationEngineǁ_log_match__mutmut_mutants'), args, kwargs, self)

    def xǁTranslationEngineǁ_log_match__mutmut_orig(self, event_type: str, rule_name: str, detail: str) -> None:
        """Log a match event.

        Args:
            event_type: Type of event.
            rule_name: Name of rule.
            detail: Event details.
        """
        self._match_log.append({
            "event_type": event_type,
            "rule_name": rule_name,
            "detail": detail,
        })

    def xǁTranslationEngineǁ_log_match__mutmut_1(self, event_type: str, rule_name: str, detail: str) -> None:
        """Log a match event.

        Args:
            event_type: Type of event.
            rule_name: Name of rule.
            detail: Event details.
        """
        self._match_log.append(None)

    def xǁTranslationEngineǁ_log_match__mutmut_2(self, event_type: str, rule_name: str, detail: str) -> None:
        """Log a match event.

        Args:
            event_type: Type of event.
            rule_name: Name of rule.
            detail: Event details.
        """
        self._match_log.append({
            "XXevent_typeXX": event_type,
            "rule_name": rule_name,
            "detail": detail,
        })

    def xǁTranslationEngineǁ_log_match__mutmut_3(self, event_type: str, rule_name: str, detail: str) -> None:
        """Log a match event.

        Args:
            event_type: Type of event.
            rule_name: Name of rule.
            detail: Event details.
        """
        self._match_log.append({
            "EVENT_TYPE": event_type,
            "rule_name": rule_name,
            "detail": detail,
        })

    def xǁTranslationEngineǁ_log_match__mutmut_4(self, event_type: str, rule_name: str, detail: str) -> None:
        """Log a match event.

        Args:
            event_type: Type of event.
            rule_name: Name of rule.
            detail: Event details.
        """
        self._match_log.append({
            "event_type": event_type,
            "XXrule_nameXX": rule_name,
            "detail": detail,
        })

    def xǁTranslationEngineǁ_log_match__mutmut_5(self, event_type: str, rule_name: str, detail: str) -> None:
        """Log a match event.

        Args:
            event_type: Type of event.
            rule_name: Name of rule.
            detail: Event details.
        """
        self._match_log.append({
            "event_type": event_type,
            "RULE_NAME": rule_name,
            "detail": detail,
        })

    def xǁTranslationEngineǁ_log_match__mutmut_6(self, event_type: str, rule_name: str, detail: str) -> None:
        """Log a match event.

        Args:
            event_type: Type of event.
            rule_name: Name of rule.
            detail: Event details.
        """
        self._match_log.append({
            "event_type": event_type,
            "rule_name": rule_name,
            "XXdetailXX": detail,
        })

    def xǁTranslationEngineǁ_log_match__mutmut_7(self, event_type: str, rule_name: str, detail: str) -> None:
        """Log a match event.

        Args:
            event_type: Type of event.
            rule_name: Name of rule.
            detail: Event details.
        """
        self._match_log.append({
            "event_type": event_type,
            "rule_name": rule_name,
            "DETAIL": detail,
        })
    
    xǁTranslationEngineǁ_log_match__mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationEngineǁ_log_match__mutmut_1': xǁTranslationEngineǁ_log_match__mutmut_1, 
        'xǁTranslationEngineǁ_log_match__mutmut_2': xǁTranslationEngineǁ_log_match__mutmut_2, 
        'xǁTranslationEngineǁ_log_match__mutmut_3': xǁTranslationEngineǁ_log_match__mutmut_3, 
        'xǁTranslationEngineǁ_log_match__mutmut_4': xǁTranslationEngineǁ_log_match__mutmut_4, 
        'xǁTranslationEngineǁ_log_match__mutmut_5': xǁTranslationEngineǁ_log_match__mutmut_5, 
        'xǁTranslationEngineǁ_log_match__mutmut_6': xǁTranslationEngineǁ_log_match__mutmut_6, 
        'xǁTranslationEngineǁ_log_match__mutmut_7': xǁTranslationEngineǁ_log_match__mutmut_7
    }
    xǁTranslationEngineǁ_log_match__mutmut_orig.__name__ = 'xǁTranslationEngineǁ_log_match'

    def get_match_log(self) -> list[dict[str, Any]]:
        """Get the match log.

        Returns:
            List of match events.
        """
        return self._match_log.copy()

    def get_statistics(self) -> dict[str, Any]:
        args = []# type: ignore
        kwargs = {}# type: ignore
        return _mutmut_trampoline(object.__getattribute__(self, 'xǁTranslationEngineǁget_statistics__mutmut_orig'), object.__getattribute__(self, 'xǁTranslationEngineǁget_statistics__mutmut_mutants'), args, kwargs, self)

    def xǁTranslationEngineǁget_statistics__mutmut_orig(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_1(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = None
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_2(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = None
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_3(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = None

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_4(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) - 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_5(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(None, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_6(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, None) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_7(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_8(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, ) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_9(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 1) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_10(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 2

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_11(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = None
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_12(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = None
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_13(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = None

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_14(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) - 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_15(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(None, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_16(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, None) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_17(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_18(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, ) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_19(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 1) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_20(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 2

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_21(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "XXtotal_mappingsXX": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_22(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "TOTAL_MAPPINGS": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_23(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "XXmappings_by_kindXX": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_24(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "MAPPINGS_BY_KIND": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_25(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "XXmappings_by_confidence_tierXX": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_26(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "MAPPINGS_BY_CONFIDENCE_TIER": by_tier,
            "rules_registered": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_27(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "XXrules_registeredXX": len(self.rules),
        }

    def xǁTranslationEngineǁget_statistics__mutmut_28(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "RULES_REGISTERED": len(self.rules),
        }
    
    xǁTranslationEngineǁget_statistics__mutmut_mutants : ClassVar[MutantDict] = { # type: ignore
    'xǁTranslationEngineǁget_statistics__mutmut_1': xǁTranslationEngineǁget_statistics__mutmut_1, 
        'xǁTranslationEngineǁget_statistics__mutmut_2': xǁTranslationEngineǁget_statistics__mutmut_2, 
        'xǁTranslationEngineǁget_statistics__mutmut_3': xǁTranslationEngineǁget_statistics__mutmut_3, 
        'xǁTranslationEngineǁget_statistics__mutmut_4': xǁTranslationEngineǁget_statistics__mutmut_4, 
        'xǁTranslationEngineǁget_statistics__mutmut_5': xǁTranslationEngineǁget_statistics__mutmut_5, 
        'xǁTranslationEngineǁget_statistics__mutmut_6': xǁTranslationEngineǁget_statistics__mutmut_6, 
        'xǁTranslationEngineǁget_statistics__mutmut_7': xǁTranslationEngineǁget_statistics__mutmut_7, 
        'xǁTranslationEngineǁget_statistics__mutmut_8': xǁTranslationEngineǁget_statistics__mutmut_8, 
        'xǁTranslationEngineǁget_statistics__mutmut_9': xǁTranslationEngineǁget_statistics__mutmut_9, 
        'xǁTranslationEngineǁget_statistics__mutmut_10': xǁTranslationEngineǁget_statistics__mutmut_10, 
        'xǁTranslationEngineǁget_statistics__mutmut_11': xǁTranslationEngineǁget_statistics__mutmut_11, 
        'xǁTranslationEngineǁget_statistics__mutmut_12': xǁTranslationEngineǁget_statistics__mutmut_12, 
        'xǁTranslationEngineǁget_statistics__mutmut_13': xǁTranslationEngineǁget_statistics__mutmut_13, 
        'xǁTranslationEngineǁget_statistics__mutmut_14': xǁTranslationEngineǁget_statistics__mutmut_14, 
        'xǁTranslationEngineǁget_statistics__mutmut_15': xǁTranslationEngineǁget_statistics__mutmut_15, 
        'xǁTranslationEngineǁget_statistics__mutmut_16': xǁTranslationEngineǁget_statistics__mutmut_16, 
        'xǁTranslationEngineǁget_statistics__mutmut_17': xǁTranslationEngineǁget_statistics__mutmut_17, 
        'xǁTranslationEngineǁget_statistics__mutmut_18': xǁTranslationEngineǁget_statistics__mutmut_18, 
        'xǁTranslationEngineǁget_statistics__mutmut_19': xǁTranslationEngineǁget_statistics__mutmut_19, 
        'xǁTranslationEngineǁget_statistics__mutmut_20': xǁTranslationEngineǁget_statistics__mutmut_20, 
        'xǁTranslationEngineǁget_statistics__mutmut_21': xǁTranslationEngineǁget_statistics__mutmut_21, 
        'xǁTranslationEngineǁget_statistics__mutmut_22': xǁTranslationEngineǁget_statistics__mutmut_22, 
        'xǁTranslationEngineǁget_statistics__mutmut_23': xǁTranslationEngineǁget_statistics__mutmut_23, 
        'xǁTranslationEngineǁget_statistics__mutmut_24': xǁTranslationEngineǁget_statistics__mutmut_24, 
        'xǁTranslationEngineǁget_statistics__mutmut_25': xǁTranslationEngineǁget_statistics__mutmut_25, 
        'xǁTranslationEngineǁget_statistics__mutmut_26': xǁTranslationEngineǁget_statistics__mutmut_26, 
        'xǁTranslationEngineǁget_statistics__mutmut_27': xǁTranslationEngineǁget_statistics__mutmut_27, 
        'xǁTranslationEngineǁget_statistics__mutmut_28': xǁTranslationEngineǁget_statistics__mutmut_28
    }
    xǁTranslationEngineǁget_statistics__mutmut_orig.__name__ = 'xǁTranslationEngineǁget_statistics'
