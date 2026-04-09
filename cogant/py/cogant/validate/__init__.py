"""
Validation and integrity checking modules.

Validates IR objects, checks structural integrity, verifies provenance coverage,
and compiles comprehensive validation reports.
"""

from cogant.validate.schema_check import SchemaValidator, ValidationIssue
from cogant.validate.integrity import IntegrityChecker
from cogant.validate.provenance_check import ProvenanceChecker, ProvenanceGap
from cogant.validate.report import ReportGenerator, ValidationReport

__all__ = [
    "SchemaValidator",
    "ValidationIssue",
    "IntegrityChecker",
    "ProvenanceChecker",
    "ProvenanceGap",
    "ReportGenerator",
    "ValidationReport",
]
