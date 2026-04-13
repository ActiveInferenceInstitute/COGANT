"""
Provenance tracking and management.

Creates, stores, and queries provenance records linking evidence to extracted elements.
"""

from cogant.provenance.tracker import ProvenanceRecord, ProvenanceTracker

__all__ = [
    "ProvenanceTracker",
    "ProvenanceRecord",
]
