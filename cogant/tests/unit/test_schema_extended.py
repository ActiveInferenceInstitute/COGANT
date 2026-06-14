"""Extended tests for the current-only GNN schema surface."""

from __future__ import annotations

from cogant.schema import (
    CURRENT_GNN_VERSION,
    GNN_V2_REQUIRED_SECTIONS,
    UNSUPPORTED_GNN_VERSION,
    detect_version,
)


def test_detect_version_requires_header_and_marker() -> None:
    assert detect_version("## GNNVersionAndFlags\nGNN v2.0.0\n") == CURRENT_GNN_VERSION
    assert detect_version("GNN v2.0.0\n") == UNSUPPORTED_GNN_VERSION
    assert detect_version("## GNNVersionAndFlags\nstrict_validation=true\n") == UNSUPPORTED_GNN_VERSION


def test_detect_version_handles_whitespace_after_hashes() -> None:
    text = "##   GNNVersionAndFlags\nGNN v2.0.0\n"
    assert detect_version(text) == CURRENT_GNN_VERSION


def test_detect_version_is_case_sensitive_for_section_name() -> None:
    text = "## gnnversionandflags\nGNN v2.0.0\n"
    assert detect_version(text) == UNSUPPORTED_GNN_VERSION


def test_current_required_sections_include_runtime_tail() -> None:
    for section in ("Equations", "ModelParameters", "Footer", "Signature"):
        assert section in GNN_V2_REQUIRED_SECTIONS
