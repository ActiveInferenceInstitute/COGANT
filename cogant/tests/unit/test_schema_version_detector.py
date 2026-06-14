"""Targeted coverage tests for ``cogant.schema.detector``."""

from cogant.schema.detector import detect_version
from cogant.schema.versions import CURRENT_GNN_VERSION, UNSUPPORTED_GNN_VERSION


class TestDetectVersionCurrentPattern:
    def test_full_current_marker_returns_current(self) -> None:
        text = "## GNNVersionAndFlags\nGNN v2.0.0\n"
        assert detect_version(text) == CURRENT_GNN_VERSION

    def test_marker_with_extra_lines(self) -> None:
        text = "## GNNVersionAndFlags  \n\nGNN v2.0.0 strict_validation=true\n"
        assert detect_version(text) == CURRENT_GNN_VERSION

    def test_marker_in_larger_document(self) -> None:
        text = (
            "# My GNN Model\n"
            "Some prose.\n\n"
            "## GNNVersionAndFlags\n"
            "GNN v2.0.0\n"
            "## ModelName\n"
            "**ModelX**\n"
        )
        assert detect_version(text) == CURRENT_GNN_VERSION


class TestDetectVersionUnsupported:
    def test_empty_string_is_unsupported(self) -> None:
        assert detect_version("") == UNSUPPORTED_GNN_VERSION

    def test_no_markers_is_unsupported(self) -> None:
        assert detect_version("Just some markdown text.") == UNSUPPORTED_GNN_VERSION

    def test_only_section_header_no_current_marker(self) -> None:
        text = "## GNNVersionAndFlags\nstrict_validation=true\n"
        assert detect_version(text) == UNSUPPORTED_GNN_VERSION

    def test_section_header_inline_not_at_start_of_line(self) -> None:
        text = "Inline ## GNNVersionAndFlags then GNN v2.0.0\n"
        assert detect_version(text) == UNSUPPORTED_GNN_VERSION

    def test_returns_string(self) -> None:
        result = detect_version("nothing here")
        assert isinstance(result, str)

    def test_non_string_input_is_unsupported(self) -> None:
        assert detect_version(b"## GNNVersionAndFlags\nGNN v2.0.0\n") == UNSUPPORTED_GNN_VERSION
