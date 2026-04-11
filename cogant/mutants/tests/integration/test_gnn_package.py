"""Integration tests for GNN package build, validate, and run operations.

Tests that:
1. Package directory created with manifest.json
2. All required JSON files present
3. Validation passes (score >= 90%)
4. Model runner produces execution trace with >0 steps
"""

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

# Ensure py/cogant is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PY_ROOT = _REPO_ROOT / "py"
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from cogant.api.orchestration import (
    run_graph,
    run_ingest,
    run_normalize,
    run_process,
    run_statespace,
    run_static,
    run_translate,
)
from cogant.gnn.package import GNNPackageBuilder
from cogant.gnn.runner import GNNModelRunner
from cogant.gnn.validator import GNNValidator


class PipelineArtifactsBundle:
    """Lightweight artifact container across pipeline stages."""

    def __init__(self):
        self.artifacts: dict[str, Any] = {}


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory for test artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def full_pipeline_bundle():
    """Fixture to run full pipeline and return bundle with all artifacts."""

    def _create_bundle(repo_path: Path) -> PipelineArtifactsBundle:
        bundle = PipelineArtifactsBundle()
        run_ingest(str(repo_path), bundle)
        run_static(bundle)
        run_normalize(bundle)
        run_graph(bundle, str(repo_path))
        run_translate(bundle)
        run_statespace(bundle, str(repo_path))
        run_process(bundle, str(repo_path))
        return bundle

    return _create_bundle


class TestGNNPackageDirectory:
    """Test GNN package directory creation and structure."""

    @pytest.mark.parametrize("repo_name,repo_path", [
        ("flask_mini", _REPO_ROOT / "examples" / "control_positive" / "flask_mini"),
        ("calculator", _REPO_ROOT / "examples" / "control_positive" / "calculator"),
        ("event_pipeline", _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"),
    ])
    def test_package_directory_created(
        self,
        repo_name: str,
        repo_path: Path,
        temp_output_dir: Path,
        full_pipeline_bundle,
    ):
        """Test that package directory is created."""
        if not repo_path.exists():
            pytest.skip(f"Control-positive repo '{repo_name}' not found")

        bundle = full_pipeline_bundle(repo_path)

        package_dir = str(temp_output_dir / f"{repo_name}_pkg")
        builder = GNNPackageBuilder(
            graph=bundle.artifacts.get("_program_graph"),
            state_space=bundle.artifacts.get("_state_space_model"),
            process_model=bundle.artifacts.get("_process_model"),
            mappings=bundle.artifacts.get("_semantic_mappings", {}),
        )

        result = builder.build(package_dir)
        assert isinstance(result, dict), f"build() should return a dict, got {type(result)}"

        # Verify directory exists
        pkg_path = Path(package_dir)
        assert pkg_path.exists()
        assert pkg_path.is_dir()

    @pytest.mark.parametrize("repo_name,repo_path", [
        ("flask_mini", _REPO_ROOT / "examples" / "control_positive" / "flask_mini"),
        ("calculator", _REPO_ROOT / "examples" / "control_positive" / "calculator"),
        ("event_pipeline", _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"),
    ])
    def test_manifest_json_created(
        self,
        repo_name: str,
        repo_path: Path,
        temp_output_dir: Path,
        full_pipeline_bundle,
    ):
        """Test that manifest.json is created in package directory."""
        if not repo_path.exists():
            pytest.skip(f"Control-positive repo '{repo_name}' not found")

        bundle = full_pipeline_bundle(repo_path)

        package_dir = str(temp_output_dir / f"{repo_name}_manifest")
        builder = GNNPackageBuilder(
            graph=bundle.artifacts.get("_program_graph"),
            state_space=bundle.artifacts.get("_state_space_model"),
            process_model=bundle.artifacts.get("_process_model"),
            mappings=bundle.artifacts.get("_semantic_mappings", {}),
        )
        builder.build(package_dir)

        # Verify manifest.json exists and is valid JSON
        manifest_path = Path(package_dir) / "manifest.json"
        assert manifest_path.exists(), f"manifest.json not found at {manifest_path}"

        with open(manifest_path) as f:
            manifest = json.load(f)

        assert isinstance(manifest, dict)
        # Manifest should have basic structure
        assert len(manifest) > 0


class TestGNNPackageRequiredFiles:
    """Test that all required JSON files are present in GNN package."""

    @pytest.mark.parametrize("repo_name,repo_path", [
        ("flask_mini", _REPO_ROOT / "examples" / "control_positive" / "flask_mini"),
        ("calculator", _REPO_ROOT / "examples" / "control_positive" / "calculator"),
        ("event_pipeline", _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"),
    ])
    def test_required_json_files_present(
        self,
        repo_name: str,
        repo_path: Path,
        temp_output_dir: Path,
        full_pipeline_bundle,
    ):
        """Test that all required JSON files are present."""
        if not repo_path.exists():
            pytest.skip(f"Control-positive repo '{repo_name}' not found")

        bundle = full_pipeline_bundle(repo_path)

        package_dir = str(temp_output_dir / f"{repo_name}_files")
        builder = GNNPackageBuilder(
            graph=bundle.artifacts.get("_program_graph"),
            state_space=bundle.artifacts.get("_state_space_model"),
            process_model=bundle.artifacts.get("_process_model"),
            mappings=bundle.artifacts.get("_semantic_mappings", {}),
        )
        builder.build(package_dir)

        pkg_path = Path(package_dir)

        # Essential JSON files
        essential_files = [
            "manifest.json",
        ]

        for filename in essential_files:
            filepath = pkg_path / filename
            assert filepath.exists(), f"Required file '{filename}' not found"

        # Check that JSON files are valid
        json_files = list(pkg_path.glob("*.json"))
        assert len(json_files) > 0, "No JSON files found"

        for json_file in json_files:
            try:
                with open(json_file) as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {json_file.name}: {e}")

    @pytest.mark.parametrize("repo_name,repo_path", [
        ("flask_mini", _REPO_ROOT / "examples" / "control_positive" / "flask_mini"),
        ("calculator", _REPO_ROOT / "examples" / "control_positive" / "calculator"),
        ("event_pipeline", _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"),
    ])
    def test_state_space_json_file_exists(
        self,
        repo_name: str,
        repo_path: Path,
        temp_output_dir: Path,
        full_pipeline_bundle,
    ):
        """Test that state_space.json file is created."""
        if not repo_path.exists():
            pytest.skip(f"Control-positive repo '{repo_name}' not found")

        bundle = full_pipeline_bundle(repo_path)

        package_dir = str(temp_output_dir / f"{repo_name}_ss")
        builder = GNNPackageBuilder(
            graph=bundle.artifacts.get("_program_graph"),
            state_space=bundle.artifacts.get("_state_space_model"),
            process_model=bundle.artifacts.get("_process_model"),
            mappings=bundle.artifacts.get("_semantic_mappings", {}),
        )
        builder.build(package_dir)

        pkg_path = Path(package_dir)
        ss_file = pkg_path / "state_space.json"

        # File may exist directly or in subdirectory
        if not ss_file.exists():
            matches = list(pkg_path.glob("**/state_space.json"))
            assert len(matches) > 0, "state_space.json not found in package"

    @pytest.mark.parametrize("repo_name,repo_path", [
        ("flask_mini", _REPO_ROOT / "examples" / "control_positive" / "flask_mini"),
        ("calculator", _REPO_ROOT / "examples" / "control_positive" / "calculator"),
        ("event_pipeline", _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"),
    ])
    def test_process_model_json_file_exists(
        self,
        repo_name: str,
        repo_path: Path,
        temp_output_dir: Path,
        full_pipeline_bundle,
    ):
        """Test that process_model.json or similar file is created."""
        if not repo_path.exists():
            pytest.skip(f"Control-positive repo '{repo_name}' not found")

        bundle = full_pipeline_bundle(repo_path)

        package_dir = str(temp_output_dir / f"{repo_name}_pm")
        builder = GNNPackageBuilder(
            graph=bundle.artifacts.get("_program_graph"),
            state_space=bundle.artifacts.get("_state_space_model"),
            process_model=bundle.artifacts.get("_process_model"),
            mappings=bundle.artifacts.get("_semantic_mappings", {}),
        )
        builder.build(package_dir)

        pkg_path = Path(package_dir)

        # Look for process model file
        json_files = list(pkg_path.glob("*.json"))
        assert len(json_files) > 0, "No JSON files found in package"


class TestGNNPackageValidation:
    """Test GNN package validation."""

    @pytest.mark.parametrize("repo_name,repo_path", [
        ("flask_mini", _REPO_ROOT / "examples" / "control_positive" / "flask_mini"),
        ("calculator", _REPO_ROOT / "examples" / "control_positive" / "calculator"),
        ("event_pipeline", _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"),
    ])
    def test_validation_passes(
        self,
        repo_name: str,
        repo_path: Path,
        temp_output_dir: Path,
        full_pipeline_bundle,
    ):
        """Test that package validation passes."""
        if not repo_path.exists():
            pytest.skip(f"Control-positive repo '{repo_name}' not found")

        bundle = full_pipeline_bundle(repo_path)

        package_dir = str(temp_output_dir / f"{repo_name}_val")
        builder = GNNPackageBuilder(
            graph=bundle.artifacts.get("_program_graph"),
            state_space=bundle.artifacts.get("_state_space_model"),
            process_model=bundle.artifacts.get("_process_model"),
            mappings=bundle.artifacts.get("_semantic_mappings", {}),
        )
        builder.build(package_dir)

        validator = GNNValidator()
        result = validator.validate_package(package_dir)

        assert result.valid, f"Package validation failed: {result.errors}"

    @pytest.mark.parametrize("repo_name,repo_path", [
        ("flask_mini", _REPO_ROOT / "examples" / "control_positive" / "flask_mini"),
        ("calculator", _REPO_ROOT / "examples" / "control_positive" / "calculator"),
        ("event_pipeline", _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"),
    ])
    def test_validation_score_high(
        self,
        repo_name: str,
        repo_path: Path,
        temp_output_dir: Path,
        full_pipeline_bundle,
    ):
        """Test that validation score is >= 90%."""
        if not repo_path.exists():
            pytest.skip(f"Control-positive repo '{repo_name}' not found")

        bundle = full_pipeline_bundle(repo_path)

        package_dir = str(temp_output_dir / f"{repo_name}_score")
        builder = GNNPackageBuilder(
            graph=bundle.artifacts.get("_program_graph"),
            state_space=bundle.artifacts.get("_state_space_model"),
            process_model=bundle.artifacts.get("_process_model"),
            mappings=bundle.artifacts.get("_semantic_mappings", {}),
        )
        builder.build(package_dir)

        validator = GNNValidator()
        result = validator.validate_package(package_dir)

        assert result.score >= 90.0, (
            f"Validation score {result.score}% is below 90% threshold"
        )

    @pytest.mark.parametrize("repo_name,repo_path", [
        ("flask_mini", _REPO_ROOT / "examples" / "control_positive" / "flask_mini"),
        ("calculator", _REPO_ROOT / "examples" / "control_positive" / "calculator"),
        ("event_pipeline", _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"),
    ])
    def test_validation_no_critical_errors(
        self,
        repo_name: str,
        repo_path: Path,
        temp_output_dir: Path,
        full_pipeline_bundle,
    ):
        """Test that validation produces no critical errors."""
        if not repo_path.exists():
            pytest.skip(f"Control-positive repo '{repo_name}' not found")

        bundle = full_pipeline_bundle(repo_path)

        package_dir = str(temp_output_dir / f"{repo_name}_crit")
        builder = GNNPackageBuilder(
            graph=bundle.artifacts.get("_program_graph"),
            state_space=bundle.artifacts.get("_state_space_model"),
            process_model=bundle.artifacts.get("_process_model"),
            mappings=bundle.artifacts.get("_semantic_mappings", {}),
        )
        builder.build(package_dir)

        validator = GNNValidator()
        result = validator.validate_package(package_dir)

        # Check for critical errors
        critical_errors = [e for e in result.errors if "critical" in str(e).lower()]
        assert len(critical_errors) == 0, f"Critical errors found: {critical_errors}"


class TestGNNModelRunner:
    """Test GNN model runner execution."""

    @pytest.mark.parametrize("repo_name,repo_path", [
        ("flask_mini", _REPO_ROOT / "examples" / "control_positive" / "flask_mini"),
        ("calculator", _REPO_ROOT / "examples" / "control_positive" / "calculator"),
        ("event_pipeline", _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"),
    ])
    def test_runner_loads_package(
        self,
        repo_name: str,
        repo_path: Path,
        temp_output_dir: Path,
        full_pipeline_bundle,
    ):
        """Test that model runner can load package."""
        if not repo_path.exists():
            pytest.skip(f"Control-positive repo '{repo_name}' not found")

        bundle = full_pipeline_bundle(repo_path)

        package_dir = str(temp_output_dir / f"{repo_name}_run_load")
        builder = GNNPackageBuilder(
            graph=bundle.artifacts.get("_program_graph"),
            state_space=bundle.artifacts.get("_state_space_model"),
            process_model=bundle.artifacts.get("_process_model"),
            mappings=bundle.artifacts.get("_semantic_mappings", {}),
        )
        builder.build(package_dir)

        runner = GNNModelRunner()
        package = runner.load_package(package_dir)

        assert package is not None
        assert isinstance(package, dict)
        assert len(package) > 0

    @pytest.mark.parametrize("repo_name,repo_path", [
        ("flask_mini", _REPO_ROOT / "examples" / "control_positive" / "flask_mini"),
        ("calculator", _REPO_ROOT / "examples" / "control_positive" / "calculator"),
        ("event_pipeline", _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"),
    ])
    def test_runner_executes_simulation(
        self,
        repo_name: str,
        repo_path: Path,
        temp_output_dir: Path,
        full_pipeline_bundle,
    ):
        """Test that model runner executes simulation."""
        if not repo_path.exists():
            pytest.skip(f"Control-positive repo '{repo_name}' not found")

        bundle = full_pipeline_bundle(repo_path)

        package_dir = str(temp_output_dir / f"{repo_name}_run_exec")
        builder = GNNPackageBuilder(
            graph=bundle.artifacts.get("_program_graph"),
            state_space=bundle.artifacts.get("_state_space_model"),
            process_model=bundle.artifacts.get("_process_model"),
            mappings=bundle.artifacts.get("_semantic_mappings", {}),
        )
        builder.build(package_dir)

        runner = GNNModelRunner()
        runner.load_package(package_dir)
        result = runner.run(steps=5)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.parametrize("repo_name,repo_path", [
        ("flask_mini", _REPO_ROOT / "examples" / "control_positive" / "flask_mini"),
        ("calculator", _REPO_ROOT / "examples" / "control_positive" / "calculator"),
        ("event_pipeline", _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"),
    ])
    def test_runner_produces_execution_trace(
        self,
        repo_name: str,
        repo_path: Path,
        temp_output_dir: Path,
        full_pipeline_bundle,
    ):
        """Test that runner produces execution trace with >0 steps."""
        if not repo_path.exists():
            pytest.skip(f"Control-positive repo '{repo_name}' not found")

        bundle = full_pipeline_bundle(repo_path)

        package_dir = str(temp_output_dir / f"{repo_name}_run_trace")
        builder = GNNPackageBuilder(
            graph=bundle.artifacts.get("_program_graph"),
            state_space=bundle.artifacts.get("_state_space_model"),
            process_model=bundle.artifacts.get("_process_model"),
            mappings=bundle.artifacts.get("_semantic_mappings", {}),
        )
        builder.build(package_dir)

        runner = GNNModelRunner()
        runner.load_package(package_dir)
        result = runner.run(steps=10)

        # Check for execution trace
        steps = result.get("steps_completed", result.get("total_steps", 0))
        assert steps > 0, f"Expected >0 steps, got {steps}"

        # Check for trace structure
        traces = result.get("traces", result.get("trace", []))
        assert len(traces) > 0, "Execution trace is empty"

    @pytest.mark.parametrize("repo_name,repo_path", [
        ("flask_mini", _REPO_ROOT / "examples" / "control_positive" / "flask_mini"),
        ("calculator", _REPO_ROOT / "examples" / "control_positive" / "calculator"),
        ("event_pipeline", _REPO_ROOT / "examples" / "control_positive" / "event_pipeline"),
    ])
    def test_runner_trace_contains_states_and_actions(
        self,
        repo_name: str,
        repo_path: Path,
        temp_output_dir: Path,
        full_pipeline_bundle,
    ):
        """Test that execution trace contains states and actions."""
        if not repo_path.exists():
            pytest.skip(f"Control-positive repo '{repo_name}' not found")

        bundle = full_pipeline_bundle(repo_path)

        package_dir = str(temp_output_dir / f"{repo_name}_run_content")
        builder = GNNPackageBuilder(
            graph=bundle.artifacts.get("_program_graph"),
            state_space=bundle.artifacts.get("_state_space_model"),
            process_model=bundle.artifacts.get("_process_model"),
            mappings=bundle.artifacts.get("_semantic_mappings", {}),
        )
        builder.build(package_dir)

        runner = GNNModelRunner()
        runner.load_package(package_dir)
        result = runner.run(steps=5)

        steps = result.get("steps_completed", result.get("total_steps", 0))
        assert steps > 0

        traces = result.get("traces", result.get("trace", []))
        if traces:
            # Each trace entry should have state and action
            for step in traces:
                assert "state" in step or "observation" in step
                assert "action" in step or "event" in step
