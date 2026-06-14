"""ReviewAPI: Interactive curation and review of analysis results."""

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


__all__ = ["ReviewableMapping", "ReviewAPI"]


# Statuses on a ``SemanticMapping`` that should surface as ``"pending"``
# in the review API. ``auto_proposed`` is the default emitted by
# ``cogant.translate.engine`` for any rule firing that has not yet been
# touched by a human curator.
_PENDING_BUNDLE_STATUSES: frozenset[str] = frozenset({"", "auto_proposed", "in_review", "pending"})
_REVIEW_STATUSES: frozenset[str] = frozenset({"pending", "accepted", "rejected", "edited"})


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

    def __init__(self) -> None:
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

    @staticmethod
    def _normalise_status(raw: Any) -> str:
        """Map a bundle ``SemanticMapping.status`` onto the review taxonomy.

        ``cogant.translate.engine`` initialises every fired mapping with
        ``status="auto_proposed"``; ``ReviewableMapping.status`` only
        knows ``pending``/``accepted``/``rejected``/``edited``. Treat
        any non-curated status as ``"pending"`` so
        :meth:`get_review_summary` can keep its narrow histogram.
        """
        text = str(raw or "").lower()
        if text in _PENDING_BUNDLE_STATUSES:
            return "pending"
        if text in _REVIEW_STATUSES:
            return text
        return "pending"

    def _extract_mappings(self) -> None:
        """Extract reviewable mappings from the loaded bundle.

        Reads the real ``_semantic_mappings`` artifact emitted by the
        translate stage. Each ``SemanticMapping`` contributes one
        :class:`ReviewableMapping` with:

        * ``id`` — the mapping's stable id (e.g. ``"mapping_func_foo"``).
        * ``source`` — the first ``graph_fragment_node_ids`` entry, i.e.
          the program-graph node the rule fired on.
        * ``target`` — the assigned semantic role (``MappingKind`` value).
        * ``confidence`` — the rule-scored ``confidence_score``.
        * ``evidence`` — the human-readable ``description`` produced by
          the rule, falling back to ``semantic_label`` then ``"Static analysis"``.
        * ``status`` — pre-existing review status (``"accepted"`` etc.)
          when present, otherwise ``"pending"``.

        Falls back to the older ``stage_results['translate']['node_features']``
        shape only when the bundle predates the artifact-style payload.
        """
        self.mappings = []
        if not self.current_bundle:
            return

        artifacts = self.current_bundle.get("artifacts", {}) or {}
        raw_mappings = artifacts.get("_semantic_mappings") or {}
        if isinstance(raw_mappings, dict):
            entries: list[Any] = list(raw_mappings.values())
        elif isinstance(raw_mappings, list):
            entries = list(raw_mappings)
        else:
            entries = []

        for entry in entries:
            data = entry if isinstance(entry, dict) else getattr(entry, "__dict__", {})
            if not isinstance(data, dict) or not data:
                continue
            kind = data.get("kind")
            if hasattr(kind, "value"):
                kind = kind.value
            node_ids = data.get("graph_fragment_node_ids") or []
            source = node_ids[0] if node_ids else data.get("semantic_label", "")
            self.mappings.append(
                ReviewableMapping(
                    id=str(data.get("id", "")),
                    source=str(source),
                    target=str(kind or ""),
                    confidence=float(data.get("confidence_score", 0.0) or 0.0),
                    evidence=str(
                        data.get("description") or data.get("semantic_label") or "Static analysis"
                    ),
                    status=self._normalise_status(data.get("status")),
                )
            )

        if self.mappings:
            return

        # Compatibility fallback: bundles that only carry the translate-stage
        # node_features shape (no _semantic_mappings artifact).
        stage_results = self.current_bundle.get("stage_results", {}) or {}
        translate = stage_results.get("translate", {}) or {}
        for node_feature in translate.get("node_features", []) or []:
            if not isinstance(node_feature, dict):
                continue
            mapping_id = str(node_feature.get("id", ""))
            kind = node_feature.get("kind", "")
            self.mappings.append(
                ReviewableMapping(
                    id=mapping_id,
                    source=mapping_id,
                    target=str(kind),
                    confidence=float(node_feature.get("confidence", 0.0) or 0.0),
                    evidence="translate stage node feature",
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

    def edit_mapping(self, mapping_id: str, **changes: Any) -> ReviewableMapping:
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
