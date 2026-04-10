"""Canonical normalization for converting language-specific facts into generic form."""

from dataclasses import dataclass
from typing import Any

from cogant.schemas.core import Node, NodeKind


@dataclass
class LanguageFact:
    """A language-specific fact extracted from static/dynamic analysis."""

    fact_type: str
    """Type of fact (class_definition, function_call, etc.)."""

    language: str
    """Source language."""

    data: dict[str, Any]
    """Raw language-specific data."""


@dataclass
class NormalizedFact:
    """A normalized fact in canonical form."""

    node_kind: NodeKind
    """Canonical node kind."""

    name: str
    """Human-readable name."""

    qualified_name: str
    """Fully qualified name."""

    path: str | None = None
    """File/module path."""

    language: str | None = None
    """Source language."""

    metadata: dict[str, Any] | None = None
    """Normalized metadata."""

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


class CanonicalNormalizer:
    """Normalizes language-specific facts into canonical form for graph construction.

    Handles mapping from Python, JavaScript, Java, etc. constructs to generic
    NodeKind and metadata structures.
    """

    # Mapping of language-specific fact types to canonical node kinds
    _fact_kind_mapping = {
        # Python
        "python:class": NodeKind.CLASS,
        "python:function": NodeKind.FUNCTION,
        "python:method": NodeKind.METHOD,
        "python:module": NodeKind.MODULE,
        "python:variable": NodeKind.VARIABLE,
        "python:parameter": NodeKind.PARAMETER,
        "python:decorator": NodeKind.FUNCTION,
        # JavaScript
        "javascript:class": NodeKind.CLASS,
        "javascript:function": NodeKind.FUNCTION,
        "javascript:async_function": NodeKind.FUNCTION,
        "javascript:arrow_function": NodeKind.FUNCTION,
        "javascript:method": NodeKind.METHOD,
        "javascript:module": NodeKind.MODULE,
        "javascript:variable": NodeKind.VARIABLE,
        # Java
        "java:class": NodeKind.CLASS,
        "java:interface": NodeKind.CLASS,
        "java:method": NodeKind.METHOD,
        "java:package": NodeKind.MODULE,
        "java:field": NodeKind.VARIABLE,
        # Generic
        "generic:class": NodeKind.CLASS,
        "generic:function": NodeKind.FUNCTION,
        "generic:module": NodeKind.MODULE,
    }

    def __init__(self) -> None:
        """Initialize the canonical normalizer."""
        self._normalization_log: list[dict[str, Any]] = []

    def normalize(self, fact: LanguageFact) -> NormalizedFact | None:
        """Normalize a language-specific fact to canonical form.

        Args:
            fact: Language-specific fact to normalize.

        Returns:
            Normalized fact in canonical form, or None if unmappable.
        """
        # Determine the canonical node kind
        fact_key = f"{fact.language}:{fact.fact_type}"
        node_kind = self._fact_kind_mapping.get(fact_key)

        if node_kind is None:
            self._log_normalization(
                "unmapped_fact",
                fact_key,
                fact.language,
                fact.fact_type,
            )
            return None

        # Extract common fields
        name = fact.data.get("name", "")
        qualified_name = fact.data.get("qualified_name", name)
        path = fact.data.get("path")
        metadata = self._normalize_metadata(fact)

        normalized = NormalizedFact(
            node_kind=node_kind,
            name=name,
            qualified_name=qualified_name,
            path=path,
            language=fact.language,
            metadata=metadata,
        )

        self._log_normalization(
            "normalized",
            fact_key,
            fact.language,
            fact.fact_type,
        )

        return normalized

    def _normalize_metadata(self, fact: LanguageFact) -> dict[str, Any]:
        """Extract and normalize metadata from a language-specific fact.

        Args:
            fact: Language-specific fact.

        Returns:
            Normalized metadata dictionary.
        """
        metadata: dict[str, Any] = {}

        # Extract common fields
        if "visibility" in fact.data:
            metadata["visibility"] = fact.data["visibility"]

        if "is_abstract" in fact.data:
            metadata["is_abstract"] = fact.data["is_abstract"]

        if "is_static" in fact.data:
            metadata["is_static"] = fact.data["is_static"]

        if "decorators" in fact.data:
            metadata["decorators"] = fact.data["decorators"]

        if "type_hints" in fact.data:
            metadata["type_hints"] = fact.data["type_hints"]

        # Language-specific fields
        if fact.language == "python":
            self._extract_python_metadata(fact.data, metadata)
        elif fact.language == "javascript":
            self._extract_javascript_metadata(fact.data, metadata)
        elif fact.language == "java":
            self._extract_java_metadata(fact.data, metadata)

        return metadata

    def _extract_python_metadata(
        self,
        fact_data: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        """Extract Python-specific metadata.

        Args:
            fact_data: Raw fact data.
            metadata: Metadata dict to populate.
        """
        if "is_async" in fact_data:
            metadata["is_async"] = fact_data["is_async"]

        if "is_generator" in fact_data:
            metadata["is_generator"] = fact_data["is_generator"]

        if "decorators" in fact_data:
            metadata["decorators"] = fact_data["decorators"]

    def _extract_javascript_metadata(
        self,
        fact_data: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        """Extract JavaScript-specific metadata.

        Args:
            fact_data: Raw fact data.
            metadata: Metadata dict to populate.
        """
        if "is_async" in fact_data:
            metadata["is_async"] = fact_data["is_async"]

        if "is_arrow" in fact_data:
            metadata["is_arrow"] = fact_data["is_arrow"]

        if "export_type" in fact_data:
            metadata["export_type"] = fact_data["export_type"]

    def _extract_java_metadata(
        self,
        fact_data: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        """Extract Java-specific metadata.

        Args:
            fact_data: Raw fact data.
            metadata: Metadata dict to populate.
        """
        if "modifiers" in fact_data:
            metadata["modifiers"] = fact_data["modifiers"]

        if "annotations" in fact_data:
            metadata["annotations"] = fact_data["annotations"]

    def normalize_batch(self, facts: list[LanguageFact]) -> list[NormalizedFact | None]:
        """Normalize a batch of language-specific facts.

        Args:
            facts: List of facts to normalize.

        Returns:
            List of normalized facts (preserving order, with None for unmappable facts).
        """
        return [self.normalize(fact) for fact in facts]

    def to_node(
        self,
        normalized: NormalizedFact,
        node_id: str,
    ) -> Node:
        """Convert a normalized fact to a Node object.

        Args:
            normalized: Normalized fact.
            node_id: Stable ID for the node.

        Returns:
            Node object ready for graph construction.
        """
        return Node(
            id=node_id,
            kind=normalized.node_kind,
            name=normalized.name,
            qualified_name=normalized.qualified_name,
            path=normalized.path,
            language=normalized.language,
            metadata=normalized.metadata,
        )

    def _log_normalization(
        self,
        status: str,
        fact_key: str,
        language: str,
        fact_type: str,
    ) -> None:
        """Log a normalization event.

        Args:
            status: Status of normalization (normalized, unmapped_fact).
            fact_key: Full fact key.
            language: Source language.
            fact_type: Type of fact.
        """
        self._normalization_log.append({
            "status": status,
            "fact_key": fact_key,
            "language": language,
            "fact_type": fact_type,
        })

    def get_normalization_log(self) -> list[dict[str, Any]]:
        """Get the normalization log.

        Returns:
            List of normalization events.
        """
        return self._normalization_log.copy()

    def get_normalization_stats(self) -> dict[str, int]:
        """Get statistics about normalizations.

        Returns:
            Dictionary with normalization statistics.
        """
        stats = {
            "total_normalizations": len(self._normalization_log),
            "normalized": 0,
            "unmapped_facts": 0,
        }

        for entry in self._normalization_log:
            if entry["status"] == "normalized":
                stats["normalized"] += 1
            elif entry["status"] == "unmapped_fact":
                stats["unmapped_facts"] += 1

        return stats
