"""Targeted coverage tests for ``cogant.schema.detector``.

The detector is a pure-text classifier that returns either V1_0 or V1_1.
These tests cover both branches plus the never-raise behaviour by passing
inputs that would otherwise trip the regex search (very long strings,
multibyte characters, edge cases around the GNNVersionAndFlags marker).
"""

from cogant.schema.detector import detect_version
from cogant.schema.versions import SchemaVersion


class TestDetectVersionV1Pattern:
    def test_full_v1_marker_returns_v1_1(self):
        text = "## GNNVersionAndFlags\nGNN v1\n"
        assert detect_version(text) == SchemaVersion.V1_1

    def test_marker_with_extra_whitespace(self):
        text = "## GNNVersionAndFlags  \n\nGNN v1 strict_validation=true\n"
        assert detect_version(text) == SchemaVersion.V1_1

    def test_marker_in_larger_document(self):
        text = (
            "# My GNN Model\n"
            "Some prose.\n\n"
            "## GNNVersionAndFlags\n"
            "GNN v1\n"
            "## ModelName\n"
            "**ModelX**\n"
        )
        assert detect_version(text) == SchemaVersion.V1_1


class TestDetectVersionFallback:
    def test_empty_string_falls_back_to_v1_0(self):
        assert detect_version("") == SchemaVersion.V1_0

    def test_no_markers_falls_back_to_v1_0(self):
        assert detect_version("Just some markdown text.") == SchemaVersion.V1_0

    def test_only_section_header_no_v1_marker(self):
        # Has the GNNVersionAndFlags header but lacks "GNN v1" marker
        text = "## GNNVersionAndFlags\nstrict_validation=true\n"
        assert detect_version(text) == SchemaVersion.V1_0

    def test_only_v1_marker_no_section_header(self):
        # Has "GNN v1" but no "## GNNVersionAndFlags" section
        text = "Some prose mentioning GNN v1 in passing.\n"
        assert detect_version(text) == SchemaVersion.V1_0

    def test_section_header_inline_not_at_start_of_line(self):
        # The marker requires anchoring at start of line.
        text = "Inline ## GNNVersionAndFlags then GNN v1\n"
        assert detect_version(text) == SchemaVersion.V1_0

    def test_v2_text_falls_back_to_v1_0(self):
        text = "## GNNVersionAndFlags\nGNN v2\n"
        assert detect_version(text) == SchemaVersion.V1_0

    def test_multibyte_unicode_input(self):
        text = "## GNNVersionAndFlags\né — GNN v1\n"
        assert detect_version(text) == SchemaVersion.V1_1


class TestDetectVersionResilience:
    """Detector must never raise — even on degenerate inputs."""

    def test_large_input(self):
        text = "filler\n" * 10000 + "## GNNVersionAndFlags\nGNN v1\n"
        assert detect_version(text) == SchemaVersion.V1_1

    def test_only_whitespace(self):
        assert detect_version("   \n\n\t\n") == SchemaVersion.V1_0

    def test_returns_string(self):
        result = detect_version("nothing here")
        assert isinstance(result, str)

    def test_non_string_input_returns_v1_0(self):
        # Bytes will trip ``re.search``'s str-pattern check and the
        # detector should swallow the TypeError and fall back to v1.0.
        assert detect_version(b"## GNNVersionAndFlags\nGNN v1\n") == SchemaVersion.V1_0

    def test_none_input_returns_v1_0(self):
        # ``None`` raises TypeError inside re.search -> fallback path.
        assert detect_version(None) == SchemaVersion.V1_0  # type: ignore[arg-type]
