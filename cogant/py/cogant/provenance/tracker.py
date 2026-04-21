"""
Provenance tracking system.

Creates, stores, and queries provenance records linking evidence to extracted elements.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProvenanceRecord:
    """Record of evidence for an extracted element."""

    id: str
    target_id: str  # Node/edge/variable ID
    target_type: str  # "node", "edge", "variable", "action", etc.
    evidence_type: str  # "code_pattern", "test", "annotation", "inference", "metadata"
    evidence_location: str  # File path + location in source
    confidence: float  # 0-1
    extraction_method: str  # Name of extraction algorithm
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class ProvenanceTracker:
    """
    Manages provenance records linking evidence to extracted elements.
    Enables tracing of how elements were extracted and confidence assessment.
    """

    def __init__(self) -> None:
        """Initialize the tracker."""
        self.records: dict[str, ProvenanceRecord] = {}
        self.target_to_records: dict[str, list[str]] = {}  # target_id -> record IDs

    def add_record(
        self,
        target_id: str,
        target_type: str,
        evidence_type: str,
        evidence_location: str,
        extraction_method: str,
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Add a provenance record.

        Args:
            target_id: ID of the extracted element.
            target_type: Type of element (node, edge, variable, etc.).
            evidence_type: Type of evidence (code_pattern, test, annotation, etc.).
            evidence_location: Location of evidence (file + line).
            extraction_method: Name of extraction algorithm.
            confidence: Confidence in this evidence (0-1).
            metadata: Additional metadata.

        Returns:
            Record ID.
        """
        record_id = f"prov_{target_id}_{len(self.records)}"

        record = ProvenanceRecord(
            id=record_id,
            target_id=target_id,
            target_type=target_type,
            evidence_type=evidence_type,
            evidence_location=evidence_location,
            confidence=max(0.0, min(1.0, confidence)),
            extraction_method=extraction_method,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        self.records[record_id] = record

        # Index by target
        if target_id not in self.target_to_records:
            self.target_to_records[target_id] = []
        self.target_to_records[target_id].append(record_id)

        logger.debug(f"Added provenance record {record_id} for {target_type} {target_id}")
        return record_id

    def get_records_for_target(self, target_id: str) -> list[ProvenanceRecord]:
        """
        Get all provenance records for a target element.

        Args:
            target_id: ID of the element.

        Returns:
            List of ProvenanceRecord objects.
        """
        record_ids = self.target_to_records.get(target_id, [])
        return [self.records[rid] for rid in record_ids if rid in self.records]

    def get_record(self, record_id: str) -> ProvenanceRecord | None:
        """
        Get a specific provenance record.

        Args:
            record_id: ID of the record.

        Returns:
            ProvenanceRecord or None.
        """
        return self.records.get(record_id)

    def compute_target_confidence(self, target_id: str) -> float:
        """
        Compute confidence for a target element based on its provenance records.

        Args:
            target_id: ID of the element.

        Returns:
            Confidence score (0-1).
        """
        records = self.get_records_for_target(target_id)

        if not records:
            return 0.0

        # Average confidence from all evidence
        avg_confidence = sum(r.confidence for r in records) / len(records)

        # Bonus for diversity of evidence sources
        evidence_types = {r.evidence_type for r in records}
        diversity_bonus = min(0.1, len(evidence_types) * 0.02)

        return min(1.0, avg_confidence + diversity_bonus)

    def get_records_by_type(self, target_type: str) -> list[ProvenanceRecord]:
        """
        Get all records for a particular element type.

        Args:
            target_type: Element type (node, edge, variable, etc.).

        Returns:
            List of matching records.
        """
        return [r for r in self.records.values() if r.target_type == target_type]

    def get_records_by_evidence_type(self, evidence_type: str) -> list[ProvenanceRecord]:
        """
        Get all records using a particular evidence type.

        Args:
            evidence_type: Type of evidence.

        Returns:
            List of matching records.
        """
        return [r for r in self.records.values() if r.evidence_type == evidence_type]

    def get_records_by_method(self, method: str) -> list[ProvenanceRecord]:
        """
        Get all records generated by a particular extraction method.

        Args:
            method: Extraction method name.

        Returns:
            List of matching records.
        """
        return [r for r in self.records.values() if r.extraction_method == method]

    def get_coverage_statistics(self) -> dict[str, Any]:
        """
        Get coverage statistics for the tracked provenance.

        Returns:
            Dictionary with coverage stats.
        """
        total_records = len(self.records)
        total_targets = len(self.target_to_records)

        # Count by type
        by_target_type: dict[str, int] = {}
        by_evidence_type: dict[str, int] = {}
        by_method: dict[str, int] = {}

        for record in self.records.values():
            by_target_type[record.target_type] = by_target_type.get(record.target_type, 0) + 1
            by_evidence_type[record.evidence_type] = (
                by_evidence_type.get(record.evidence_type, 0) + 1
            )
            by_method[record.extraction_method] = by_method.get(record.extraction_method, 0) + 1

        # Average confidence
        avg_confidence = (
            sum(r.confidence for r in self.records.values()) / total_records
            if total_records > 0
            else 0.0
        )

        return {
            "total_records": total_records,
            "total_targets": total_targets,
            "avg_confidence": avg_confidence,
            "by_target_type": by_target_type,
            "by_evidence_type": by_evidence_type,
            "by_method": by_method,
        }

    def query_records(
        self,
        target_id: str | None = None,
        target_type: str | None = None,
        evidence_type: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[ProvenanceRecord]:
        """
        Query records with multiple criteria.

        Args:
            target_id: Filter by target ID.
            target_type: Filter by target type.
            evidence_type: Filter by evidence type.
            min_confidence: Minimum confidence threshold.

        Returns:
            Matching records.
        """
        results: list[ProvenanceRecord] = list(self.records.values())

        if target_id:
            results = [r for r in results if r.target_id == target_id]

        if target_type:
            results = [r for r in results if r.target_type == target_type]

        if evidence_type:
            results = [r for r in results if r.evidence_type == evidence_type]

        if min_confidence > 0.0:
            results = [r for r in results if r.confidence >= min_confidence]

        return results

    def merge_tracker(self, other: "ProvenanceTracker") -> None:
        """
        Merge provenance from another tracker.

        Args:
            other: Another ProvenanceTracker to merge.
        """
        for record_id, record in other.records.items():
            if record_id not in self.records:
                self.records[record_id] = record
                target_id = record.target_id
                if target_id not in self.target_to_records:
                    self.target_to_records[target_id] = []
                self.target_to_records[target_id].append(record_id)

    def clear(self) -> None:
        """Clear all provenance records."""
        self.records.clear()
        self.target_to_records.clear()
        logger.info("Provenance tracker cleared")

    def get_record_count(self) -> int:
        """Get total number of records."""
        return len(self.records)

    def get_target_count(self) -> int:
        """Get number of unique targets."""
        return len(self.target_to_records)
