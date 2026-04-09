"""ReviewAPI: Interactive curation and review of analysis results."""

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ReviewableMapping:
    """Single mapping available for review."""

    id: str
    """Unique identifier."""

    source: str
    """Source element (e.g., function name)."""

    target: str
    """Target element (e.g., GNN node)."""

    confidence: float
    """Confidence score 0-1."""

    evidence: str
    """Evidence/justification."""

    status: str = "pending"
    """Review status: pending, accepted, rejected, edited."""

    notes: str = ""
    """Curator notes."""


class ReviewAPI:
    """
    Interactive curation interface for analysis results.

    Workflow:
      1. Load bundle
      2. Present mappings for review
      3. Accept/reject/edit each mapping
      4. Save curated bundle
    """

    def __init__(self):
        """Initialize review API."""
        self.current_bundle: Any | None = None
        self.mappings: list[ReviewableMapping] = []
        self.review_state: dict[str, Any] = {}

    def load_bundle(self, bundle_path: str) -> None:
        """
        Load a bundle for review.

        Args:
            bundle_path: Path to bundle JSON file.

        Raises:
            FileNotFoundError: If bundle does not exist.
            json.JSONDecodeError: If bundle is invalid JSON.
        """
        logger.info(f"Loading bundle from {bundle_path}")

        with open(bundle_path) as f:
            self.current_bundle = json.load(f)

        self._extract_mappings()
        logger.info(f"Loaded {len(self.mappings)} mappings for review")

    def _extract_mappings(self) -> None:
        """Extract reviewable mappings from bundle."""
        self.mappings = []
        # Placeholder: extract from translate stage results
        if self.current_bundle:
            stage_results = self.current_bundle.get("stage_results", {})
            translate = stage_results.get("translate", {})
            # Create sample mappings for demo
            for i, _node_feature in enumerate(translate.get("node_features", [])[:5]):
                self.mappings.append(
                    ReviewableMapping(
                        id=f"mapping_{i}",
                        source=f"function_{i}",
                        target=f"gnn_node_{i}",
                        confidence=0.8 + (i * 0.02),
                        evidence="Static analysis",
                    )
                )

    def present_mapping(self, mapping_id: str) -> ReviewableMapping:
        """
        Present a single mapping for review.

        Args:
            mapping_id: ID of mapping to review.

        Returns:
            Mapping object.

        Raises:
            KeyError: If mapping not found.
        """
        for mapping in self.mappings:
            if mapping.id == mapping_id:
                return mapping
        raise KeyError(f"Mapping not found: {mapping_id}")

    def accept_mapping(self, mapping_id: str, notes: str = "") -> None:
        """
        Accept a mapping as correct.

        Args:
            mapping_id: ID of mapping to accept.
            notes: Optional curator notes.
        """
        for mapping in self.mappings:
            if mapping.id == mapping_id:
                mapping.status = "accepted"
                mapping.notes = notes
                logger.info(f"Accepted mapping: {mapping_id}")
                return
        raise KeyError(f"Mapping not found: {mapping_id}")

    def reject_mapping(self, mapping_id: str, reason: str = "") -> None:
        """
        Reject a mapping as incorrect.

        Args:
            mapping_id: ID of mapping to reject.
            reason: Reason for rejection.
        """
        for mapping in self.mappings:
            if mapping.id == mapping_id:
                mapping.status = "rejected"
                mapping.notes = reason
                logger.info(f"Rejected mapping: {mapping_id}")
                return
        raise KeyError(f"Mapping not found: {mapping_id}")

    def edit_mapping(
        self, mapping_id: str, **changes: Any
    ) -> ReviewableMapping:
        """
        Edit a mapping.

        Args:
            mapping_id: ID of mapping to edit.
            **changes: Fields to update (target, confidence, notes, etc).

        Returns:
            Updated mapping.

        Raises:
            KeyError: If mapping not found.
        """
        for mapping in self.mappings:
            if mapping.id == mapping_id:
                for key, value in changes.items():
                    if hasattr(mapping, key):
                        setattr(mapping, key, value)
                mapping.status = "edited"
                logger.info(f"Edited mapping: {mapping_id}")
                return mapping
        raise KeyError(f"Mapping not found: {mapping_id}")

    def get_review_summary(self) -> dict[str, int]:
        """
        Get summary of review progress.

        Returns:
            Counts of mappings by status.
        """
        summary = {
            "total": len(self.mappings),
            "pending": 0,
            "accepted": 0,
            "rejected": 0,
            "edited": 0,
        }

        for mapping in self.mappings:
            summary[mapping.status] += 1

        return summary

    def save_curated_bundle(self, output_path: str) -> None:
        """
        Save reviewed/curated bundle to disk.

        Includes all review decisions and notes.

        Args:
            output_path: Path to write curated bundle.
        """
        if self.current_bundle is None:
            raise RuntimeError("No bundle loaded")

        logger.info(f"Saving curated bundle to {output_path}")

        # Add review metadata
        curated = self.current_bundle.copy()
        curated["review"] = {
            "mappings": [
                {
                    "id": m.id,
                    "source": m.source,
                    "target": m.target,
                    "confidence": m.confidence,
                    "status": m.status,
                    "notes": m.notes,
                }
                for m in self.mappings
            ],
            "summary": self.get_review_summary(),
        }

        with open(output_path, "w") as f:
            json.dump(curated, f, indent=2)

        logger.info(f"Curated bundle saved to {output_path}")

    def get_pending_mappings(self) -> list[ReviewableMapping]:
        """Get all mappings awaiting review."""
        return [m for m in self.mappings if m.status == "pending"]

    def get_accepted_mappings(self) -> list[ReviewableMapping]:
        """Get all accepted mappings."""
        return [m for m in self.mappings if m.status == "accepted"]

    def get_rejected_mappings(self) -> list[ReviewableMapping]:
        """Get all rejected mappings."""
        return [m for m in self.mappings if m.status == "rejected"]
