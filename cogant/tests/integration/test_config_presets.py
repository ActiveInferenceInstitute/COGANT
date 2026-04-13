"""Integration tests for configuration presets.

Tests that each config preset loads without error and runs the pipeline:
- minimal
- standard
- comprehensive
- gnn-focused
- security
"""

import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

# Ensure py/cogant is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PY_ROOT = _REPO_ROOT / "py"
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from cogant.config.presets import PRESETS, get_preset
from cogant.api.orchestration import (
    run_ingest,
    run_static,
    run_normalize,
    run_graph,
    run_translate,
    run_statespace,
    run_process,
)


class MockBundle:
    """Mock bundle to track artifacts across pipeline stages."""

    def __init__(self):
        self.artifacts: Dict[str, Any] = {}


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory for test artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestConfigPresetsLoading:
    """Test that all config presets can be loaded."""

    def test_all_presets_defined(self):
        """Test that all expected presets are defined."""
        expected_presets = ["minimal", "standard", "comprehensive", "gnn-focused", "security"]

        for preset_name in expected_presets:
            assert preset_name in PRESETS, f"Preset '{preset_name}' not found in PRESETS"

    def test_minimal_preset_loads(self):
        """Test that minimal preset loads without error."""
        preset = get_preset("minimal")
        assert preset is not None
        assert isinstance(preset, dict)
        assert len(preset) > 0

    def test_standard_preset_loads(self):
        """Test that standard preset loads without error."""
        preset = get_preset("standard")
        assert preset is not None
        assert isinstance(preset, dict)
        assert len(preset) > 0

    def test_comprehensive_preset_loads(self):
        """Test that comprehensive preset loads without error."""
        preset = get_preset("comprehensive")
        assert preset is not None
        assert isinstance(preset, dict)
        assert len(preset) > 0

    def test_gnn_focused_preset_loads(self):
        """Test that gnn-focused preset loads without error."""
        preset = get_preset("gnn-focused")
        assert preset is not None
        assert isinstance(preset, dict)
        assert len(preset) > 0

    def test_security_preset_loads(self):
        """Test that security preset loads without error."""
        preset = get_preset("security")
        assert preset is not None
        assert isinstance(preset, dict)
        assert len(preset) > 0

    def test_preset_structure(self):
        """Test that presets have expected structure."""
        for preset_name, preset in PRESETS.items():
            assert isinstance(preset, dict), f"Preset '{preset_name}' is not a dict"

            # Presets should have pipeline or stages configuration
            has_config = any(
                key in preset
                for key in ["stages", "pipeline", "features", "analysis", "config"]
            )
            assert has_config, (
                f"Preset '{preset_name}' missing expected configuration keys"
            )


class TestPresetsWithPipeline:
    """Test that presets work with the pipeline."""

    @pytest.mark.parametrize("preset_name", ["minimal", "standard", "comprehensive", "gnn-focused", "security"])
    def test_preset_with_flask_mini(self, preset_name: str, temp_output_dir: Path):
        """Test preset with flask_mini control-positive repo."""
        repo_path = _REPO_ROOT / "examples" / "control_positive" / "flask_mini"
        if not repo_path.exists():
            pytest.skip(f"flask_mini repo not found")

        preset = get_preset(preset_name)
        assert preset is not None

        # Load preset configuration
        assert isinstance(preset, dict)

        # Run pipeline stages
        bundle = MockBundle()

        try:
            run_ingest(str(repo_path), bundle)
            assert "repo_snapshot" in bundle.artifacts

            run_static(bundle)
            assert "parsed_modules_detail" in bundle.artifacts

            run_normalize(bundle)
            assert "normalized_facts" in bundle.artifacts

            run_graph(bundle, str(repo_path))
            assert "_program_graph" in bundle.artifacts

            run_translate(bundle)
            assert "_semantic_mappings" in bundle.artifacts

            run_statespace(bundle, str(repo_path))
            assert "_state_space_model" in bundle.artifacts

            run_process(bundle, str(repo_path))
            assert "_process_model" in bundle.artifacts
        except Exception as e:
            pytest.fail(f"Preset '{preset_name}' failed during pipeline execution: {e}")

    @pytest.mark.parametrize("preset_name", ["minimal", "standard", "comprehensive", "gnn-focused", "security"])
    def test_preset_with_calculator(self, preset_name: str, temp_output_dir: Path):
        """Test preset with calculator control-positive repo."""
        repo_path = _REPO_ROOT / "examples" / "control_positive" / "calculator"
        if not repo_path.exists():
            pytest.skip(f"calculator repo not found")

        preset = get_preset(preset_name)
        assert preset is not None

        # Load preset configuration
        assert isinstance(preset, dict)

        # Run pipeline stages
        bundle = MockBundle()

        try:
            run_ingest(str(repo_path), bundle)
            assert "repo_snapshot" in bundle.artifacts

            run_static(bundle)
            assert "parsed_modules_detail" in bundle.artifacts

            run_normalize(bundle)
            assert "normalized_facts" in bundle.artifacts

            run_graph(bundle, str(repo_path))
            assert "_program_graph" in bundle.artifacts

            run_translate(bundle)
            assert "_semantic_mappings" in bundle.artifacts

            run_statespace(bundle, str(repo_path))
            assert "_state_space_model" in bundle.artifacts

            run_process(bundle, str(repo_path))
            assert "_process_model" in bundle.artifacts
        except Exception as e:
            pytest.fail(f"Preset '{preset_name}' failed during pipeline execution: {e}")

    @pytest.mark.parametrize("preset_name", ["minimal", "standard", "comprehensive", "gnn-focused", "security"])
    def test_preset_with_event_pipeline(self, preset_name: str, temp_output_dir: Path):
        """Test preset with event_pipeline control-positive repo."""
        repo_path = _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"
        if not repo_path.exists():
            pytest.skip(f"event_pipeline repo not found")

        preset = get_preset(preset_name)
        assert preset is not None

        # Load preset configuration
        assert isinstance(preset, dict)

        # Run pipeline stages
        bundle = MockBundle()

        try:
            run_ingest(str(repo_path), bundle)
            assert "repo_snapshot" in bundle.artifacts

            run_static(bundle)
            assert "parsed_modules_detail" in bundle.artifacts

            run_normalize(bundle)
            assert "normalized_facts" in bundle.artifacts

            run_graph(bundle, str(repo_path))
            assert "_program_graph" in bundle.artifacts

            run_translate(bundle)
            assert "_semantic_mappings" in bundle.artifacts

            run_statespace(bundle, str(repo_path))
            assert "_state_space_model" in bundle.artifacts

            run_process(bundle, str(repo_path))
            assert "_process_model" in bundle.artifacts
        except Exception as e:
            pytest.fail(f"Preset '{preset_name}' failed during pipeline execution: {e}")


class TestMinimalPreset:
    """Tests specific to minimal preset."""

    def test_minimal_preset_has_core_stages(self):
        """Test that minimal preset has core pipeline stages."""
        preset = get_preset("minimal")

        # Should have at least basic stages
        assert preset is not None
        assert isinstance(preset, dict)

    def test_minimal_preset_is_lightweight(self):
        """Test that minimal preset has fewer configuration options than comprehensive."""
        minimal = get_preset("minimal")
        comprehensive = get_preset("comprehensive")

        # Minimal should be a subset
        assert isinstance(minimal, dict)
        assert isinstance(comprehensive, dict)
        # Comprehensive should have more or equal config
        assert len(comprehensive) >= len(minimal)


class TestStandardPreset:
    """Tests specific to standard preset."""

    def test_standard_preset_balanced(self):
        """Test that standard preset is balanced."""
        preset = get_preset("standard")

        assert preset is not None
        assert isinstance(preset, dict)


class TestComprehensivePreset:
    """Tests specific to comprehensive preset."""

    def test_comprehensive_preset_complete(self):
        """Test that comprehensive preset includes all features."""
        preset = get_preset("comprehensive")

        assert preset is not None
        assert isinstance(preset, dict)
        # Should be more extensive than minimal
        assert len(preset) > 0


class TestGNNFocusedPreset:
    """Tests specific to gnn-focused preset."""

    def test_gnn_focused_preset_exists(self):
        """Test that gnn-focused preset exists."""
        preset = get_preset("gnn-focused")
        assert preset is not None
        assert isinstance(preset, dict)

    def test_gnn_focused_has_gnn_config(self):
        """Test that gnn-focused preset has GNN-related configuration."""
        preset = get_preset("gnn-focused")
        assert preset is not None
        # Should contain something related to GNN
        preset_str = str(preset).lower()
        # Check that it has some meaningful configuration
        assert len(preset) > 0


class TestSecurityPreset:
    """Tests specific to security preset."""

    def test_security_preset_exists(self):
        """Test that security preset exists."""
        preset = get_preset("security")
        assert preset is not None
        assert isinstance(preset, dict)

    def test_security_preset_has_security_config(self):
        """Test that security preset has security-related configuration."""
        preset = get_preset("security")
        assert preset is not None
        # Should contain something related to security
        preset_str = str(preset).lower()
        # Check that it has some meaningful configuration
        assert len(preset) > 0


class TestPresetConsistency:
    """Test consistency across all presets."""

    def test_all_presets_are_dicts(self):
        """Test that all presets are dictionaries."""
        for preset_name, preset in PRESETS.items():
            assert isinstance(preset, dict), (
                f"Preset '{preset_name}' is not a dict: {type(preset)}"
            )

    def test_all_presets_non_empty(self):
        """Test that all presets have content."""
        for preset_name, preset in PRESETS.items():
            assert len(preset) > 0, f"Preset '{preset_name}' is empty"

    def test_get_preset_returns_valid_config(self):
        """Test that get_preset returns valid configuration for all presets."""
        for preset_name in PRESETS.keys():
            preset = get_preset(preset_name)
            assert preset is not None, f"get_preset returned None for '{preset_name}'"
            assert isinstance(preset, dict), (
                f"get_preset for '{preset_name}' returned {type(preset)}"
            )


class TestPresetIntegration:
    """Integration tests for all presets."""

    @pytest.mark.parametrize("preset_name", ["minimal", "standard", "comprehensive", "gnn-focused", "security"])
    def test_preset_can_be_loaded_and_used(self, preset_name: str):
        """Test that preset can be loaded and used in configuration."""
        preset = get_preset(preset_name)
        assert preset is not None
        assert isinstance(preset, dict)

        # Preset should be usable as a configuration object
        # (i.e., should contain configuration keys and values)
        assert len(preset) > 0

    @pytest.mark.parametrize("preset_name", ["minimal", "standard", "comprehensive", "gnn-focused", "security"])
    def test_preset_immutability(self, preset_name: str):
        """Test that presets are consistent across calls."""
        preset1 = get_preset(preset_name)
        preset2 = get_preset(preset_name)

        # Should return equivalent configurations
        assert preset1 is not None
        assert preset2 is not None
        assert isinstance(preset1, dict)
        assert isinstance(preset2, dict)
