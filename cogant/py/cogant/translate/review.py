"""Review manager for semantic mapping validation and curation."""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from cogant.schemas.semantic import SemanticMapping, ConfidenceTier


class ReviewManager:
    """Manages human review of semantic mappings.

    Accepts, rejects, edits, splits, and merges mappings while tracking
    all provenance and changes.
    """

    def __init__(self) -> None:
        """Initialize the review manager."""
        self.mappings: Dict[str, SemanticMapping] = {}
        self.review_history: List[Dict[str, Any]] = []

    def add_mapping(self, mapping: SemanticMapping) -> None:
        """Add a mapping for potential review.

        Args:
            mapping: Mapping to add.
        """
        self.mappings[mapping.id] = mapping

    def accept_mapping(
        self,
        mapping_id: str,
        reviewer: str,
        feedback: Optional[str] = None,
    ) -> bool:
        """Accept a mapping as valid.

        Args:
            mapping_id: ID of mapping to accept.
            reviewer: Name of reviewer.
            feedback: Optional review feedback.

        Returns:
            True if successful, False if mapping not found.
        """
        if mapping_id not in self.mappings:
            return False

        mapping = self.mappings[mapping_id]
        mapping.status = "accepted"
        mapping.reviewed_by = reviewer
        mapping.reviewed_at = datetime.now(timezone.utc)
        mapping.review_feedback = feedback

        # Upgrade confidence tier if human reviewed
        if mapping.confidence_tier != ConfidenceTier.HUMAN_REVIEWED:
            mapping.confidence_tier = ConfidenceTier.HUMAN_REVIEWED
            mapping.confidence_score = min(1.0, mapping.confidence_score + 0.15)

        self._log_review("accept", mapping_id, reviewer, feedback)
        return True

    def reject_mapping(
        self,
        mapping_id: str,
        reviewer: str,
        reason: str,
    ) -> bool:
        """Reject a mapping as invalid.

        Args:
            mapping_id: ID of mapping to reject.
            reviewer: Name of reviewer.
            reason: Reason for rejection.

        Returns:
            True if successful, False if mapping not found.
        """
        if mapping_id not in self.mappings:
            return False

        mapping = self.mappings[mapping_id]
        mapping.status = "rejected"
        mapping.reviewed_by = reviewer
        mapping.reviewed_at = datetime.now(timezone.utc)
        mapping.review_feedback = reason
        mapping.confidence_score = 0.0

        self._log_review("reject", mapping_id, reviewer, reason)
        return True

    def edit_mapping(
        self,
        mapping_id: str,
        reviewer: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Edit a mapping based on review feedback.

        Args:
            mapping_id: ID of mapping to edit.
            reviewer: Name of reviewer.
            updates: Dictionary of fields to update.

        Returns:
            True if successful, False if mapping not found.
        """
        if mapping_id not in self.mappings:
            return False

        mapping = self.mappings[mapping_id]
        old_values = {}

        # Apply updates
        for key, value in updates.items():
            if hasattr(mapping, key):
                old_values[key] = getattr(mapping, key)
                setattr(mapping, key, value)

        mapping.status = "edited"
        mapping.reviewed_by = reviewer
        mapping.reviewed_at = datetime.now(timezone.utc)

        self._log_review("edit", mapping_id, reviewer, {"old_values": old_values, "new_values": updates})
        return True

    def split_mapping(
        self,
        mapping_id: str,
        reviewer: str,
        split_definitions: List[Dict[str, Any]],
    ) -> List[str]:
        """Split a mapping into multiple mappings.

        Args:
            mapping_id: ID of mapping to split.
            reviewer: Name of reviewer.
            split_definitions: List of definitions for new mappings.

        Returns:
            List of IDs of new mappings.
        """
        if mapping_id not in self.mappings:
            return []

        original = self.mappings[mapping_id]
        new_ids = []

        for i, definition in enumerate(split_definitions):
            new_id = f"{mapping_id}_split_{i}"

            new_mapping = SemanticMapping(
                id=new_id,
                kind=definition.get("kind", original.kind),
                graph_fragment_node_ids=definition.get("node_ids", []),
                graph_fragment_edge_ids=definition.get("edge_ids", []),
                semantic_label=definition.get("label", original.semantic_label),
                description=definition.get("description", original.description),
                confidence_tier=ConfidenceTier.HUMAN_REVIEWED,
                status="edited",
                reviewed_by=reviewer,
                reviewed_at=datetime.now(timezone.utc),
            )

            self.mappings[new_id] = new_mapping
            new_ids.append(new_id)

        # Mark original as split
        original.status = "split"
        original.reviewed_by = reviewer
        original.reviewed_at = datetime.now(timezone.utc)

        self._log_review("split", mapping_id, reviewer, {"new_mappings": new_ids})
        return new_ids

    def merge_mappings(
        self,
        mapping_ids: List[str],
        reviewer: str,
        merged_definition: Dict[str, Any],
    ) -> Optional[str]:
        """Merge multiple mappings into one.

        Args:
            mapping_ids: IDs of mappings to merge.
            reviewer: Name of reviewer.
            merged_definition: Definition of merged mapping.

        Returns:
            ID of new merged mapping, or None if invalid.
        """
        # Verify all mappings exist
        for mid in mapping_ids:
            if mid not in self.mappings:
                return None

        # Create merged mapping
        merged_id = f"merged_{'_'.join(m[:8] for m in mapping_ids)}"

        # Collect all node and edge IDs
        all_node_ids = []
        all_edge_ids = []
        for mid in mapping_ids:
            mapping = self.mappings[mid]
            all_node_ids.extend(mapping.graph_fragment_node_ids)
            all_edge_ids.extend(mapping.graph_fragment_edge_ids)

        # Deduplicate
        all_node_ids = list(set(all_node_ids))
        all_edge_ids = list(set(all_edge_ids))

        merged = SemanticMapping(
            id=merged_id,
            kind=merged_definition.get("kind"),  # type: ignore[arg-type]
            graph_fragment_node_ids=all_node_ids,
            graph_fragment_edge_ids=all_edge_ids,
            semantic_label=merged_definition.get("label", "Merged Mapping"),
            description=merged_definition.get("description", ""),
            confidence_tier=ConfidenceTier.HUMAN_REVIEWED,
            status="merged",
            reviewed_by=reviewer,
            reviewed_at=datetime.now(timezone.utc),
        )

        self.mappings[merged_id] = merged

        # Mark originals as merged
        for mid in mapping_ids:
            self.mappings[mid].status = "merged"
            self.mappings[mid].reviewed_by = reviewer
            self.mappings[mid].reviewed_at = datetime.now(timezone.utc)

        self._log_review("merge", ",".join(mapping_ids), reviewer, {"merged_id": merged_id})
        return merged_id

    def get_mapping_for_review(self, mapping_id: str) -> Optional[SemanticMapping]:
        """Get a mapping for review.

        Args:
            mapping_id: ID of mapping.

        Returns:
            Mapping if found, None otherwise.
        """
        return self.mappings.get(mapping_id)

    def get_mappings_by_status(self, status: str) -> List[SemanticMapping]:
        """Get all mappings with a specific status.

        Args:
            status: Status to filter by.

        Returns:
            List of mappings with that status.
        """
        return [m for m in self.mappings.values() if m.status == status]

    def get_unreviewed_mappings(self) -> List[SemanticMapping]:
        """Get all mappings that haven't been reviewed.

        Returns:
            List of unreviewed mappings.
        """
        return [m for m in self.mappings.values() if m.status == "auto_proposed"]

    def get_review_summary(self) -> Dict[str, Any]:
        """Get a summary of review status.

        Returns:
            Dictionary with review statistics.
        """
        statuses: Dict[str, int] = {}
        for mapping in self.mappings.values():
            status = mapping.status
            statuses[status] = statuses.get(status, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "by_status": statuses,
            "unreviewed_count": len(self.get_unreviewed_mappings()),
            "total_review_actions": len(self.review_history),
        }

    def _log_review(self, action: str, mapping_id: str, reviewer: str, detail: Any) -> None:
        """Log a review action.

        Args:
            action: Type of review action.
            mapping_id: ID of affected mapping.
            reviewer: Name of reviewer.
            detail: Action details.
        """
        self.review_history.append({
            "timestamp": datetime.now(timezone.utc),
            "action": action,
            "mapping_id": mapping_id,
            "reviewer": reviewer,
            "detail": detail,
        })

    def get_review_history(self) -> List[Dict[str, Any]]:
        """Get the complete review history.

        Returns:
            List of review events.
        """
        return self.review_history.copy()

    def export_reviewed_mappings(self) -> List[SemanticMapping]:
        """Export all mappings that have been accepted or edited by reviewers.

        Returns:
            List of reviewed and approved mappings.
        """
        return [
            m for m in self.mappings.values()
            if m.status in ("accepted", "edited", "merged")
        ]
