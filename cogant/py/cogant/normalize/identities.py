"""Identity resolver for generating stable, deterministic IDs for repository elements."""

import hashlib
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class IdentityRecord:
    """Record of a generated identity."""

    id: str
    """The stable ID."""

    entity_type: str
    """Type of entity (repo, module, file, symbol, endpoint, event)."""

    repo_uri: str
    """URI of the repository."""

    path: Optional[str]
    """Path within repository."""

    qualified_name: Optional[str]
    """Qualified name of the entity."""

    hash_inputs: str
    """Concatenated inputs used for hashing."""


class IdentityResolver:
    """Generates and manages stable, deterministic identities for repository elements.

    Uses SHA256 hashing of (repo_uri, path, qualified_name) to ensure consistent,
    collision-resistant IDs across multiple processing runs.
    """

    def __init__(self):
        """Initialize the identity resolver."""
        self._id_cache: Dict[str, IdentityRecord] = {}
        self._reverse_lookup: Dict[str, str] = {}

    def generate_id(
        self,
        entity_type: str,
        repo_uri: str,
        path: Optional[str] = None,
        qualified_name: Optional[str] = None,
    ) -> str:
        """Generate a deterministic ID for an entity.

        Args:
            entity_type: Type of entity (repo, module, file, symbol, endpoint, event).
            repo_uri: URI or identifier of the repository.
            path: File or module path within repository.
            qualified_name: Qualified name in source language (e.g., module.Class.method).

        Returns:
            Stable, deterministic ID as hex string.
        """
        # Create hash input from components
        hash_inputs = self._build_hash_input(repo_uri, path, qualified_name)

        # Generate deterministic ID using SHA256
        hash_obj = hashlib.sha256(hash_inputs.encode("utf-8"))
        identity_id = hash_obj.hexdigest()[:16]  # Use first 16 hex chars

        # Cache the record
        record = IdentityRecord(
            id=identity_id,
            entity_type=entity_type,
            repo_uri=repo_uri,
            path=path,
            qualified_name=qualified_name,
            hash_inputs=hash_inputs,
        )
        self._id_cache[identity_id] = record
        self._reverse_lookup[hash_inputs] = identity_id

        return identity_id

    def _build_hash_input(
        self,
        repo_uri: str,
        path: Optional[str] = None,
        qualified_name: Optional[str] = None,
    ) -> str:
        """Build concatenated string for hashing.

        Args:
            repo_uri: Repository URI.
            path: Optional path.
            qualified_name: Optional qualified name.

        Returns:
            Concatenated string for hashing.
        """
        parts = [repo_uri]
        if path:
            parts.append(path)
        if qualified_name:
            parts.append(qualified_name)
        return "|".join(parts)

    def get_id(
        self,
        entity_type: str,
        repo_uri: str,
        path: Optional[str] = None,
        qualified_name: Optional[str] = None,
    ) -> str:
        """Get or create ID for an entity (idempotent).

        Args:
            entity_type: Type of entity.
            repo_uri: Repository URI.
            path: Optional path.
            qualified_name: Optional qualified name.

        Returns:
            Stable ID for the entity.
        """
        hash_input = self._build_hash_input(repo_uri, path, qualified_name)
        if hash_input in self._reverse_lookup:
            return self._reverse_lookup[hash_input]
        return self.generate_id(entity_type, repo_uri, path, qualified_name)

    def lookup_id(
        self,
        entity_type: str,
        repo_uri: str,
        path: Optional[str] = None,
        qualified_name: Optional[str] = None,
    ) -> Optional[str]:
        """Look up an existing ID without creating one.

        Args:
            entity_type: Type of entity.
            repo_uri: Repository URI.
            path: Optional path.
            qualified_name: Optional qualified name.

        Returns:
            ID if found, None otherwise.
        """
        hash_input = self._build_hash_input(repo_uri, path, qualified_name)
        return self._reverse_lookup.get(hash_input)

    def get_record(self, identity_id: str) -> Optional[IdentityRecord]:
        """Retrieve the record for an identity.

        Args:
            identity_id: The ID to look up.

        Returns:
            IdentityRecord if found, None otherwise.
        """
        return self._id_cache.get(identity_id)

    def deduplicate_ids(self, identity_ids: list) -> list:
        """Remove duplicate IDs, preserving order.

        Args:
            identity_ids: List of IDs to deduplicate.

        Returns:
            Deduplicated list maintaining first occurrence order.
        """
        seen = set()
        result = []
        for iid in identity_ids:
            if iid not in seen:
                seen.add(iid)
                result.append(iid)
        return result

    def generate_edge_id(self, source_id: str, target_id: str, edge_kind: str) -> str:
        """Generate a deterministic ID for an edge.

        Args:
            source_id: ID of source node.
            target_id: ID of target node.
            edge_kind: Kind/type of edge.

        Returns:
            Stable edge ID.
        """
        edge_input = f"{source_id}|{target_id}|{edge_kind}"
        hash_obj = hashlib.sha256(edge_input.encode("utf-8"))
        return hash_obj.hexdigest()[:16]

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about cached identities.

        Returns:
            Dictionary with cache statistics.
        """
        entity_types = {}
        for record in self._id_cache.values():
            entity_types[record.entity_type] = entity_types.get(record.entity_type, 0) + 1

        return {
            "total_identities": len(self._id_cache),
            "unique_hash_inputs": len(self._reverse_lookup),
            **{f"type_{k}": v for k, v in entity_types.items()},
        }

    def clear_cache(self) -> None:
        """Clear all cached identities."""
        self._id_cache.clear()
        self._reverse_lookup.clear()
