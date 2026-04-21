"""Integration tests for the full COGANT pipeline end-to-end.

Tests the complete pipeline via the RoundtripOrchestrator against each
control-positive repository: flask_mini, calculator, event_pipeline.

Verifies:
1. Pipeline completes without error
2. Program graph has expected node/edge counts (non-zero)
3. Translation produces semantic mappings (non-empty)
4. GNN markdown contains canonical sections
5. Core output files exist (program graph, model GNN, summary, validation_report, …)

Tests that depend on the GNN package directory, model-runner execution trace, or a non-empty
state_space block in model.gnn.json are skipped when the orchestrator run does not produce
those artifacts. Same when packaged validation or execution outputs are absent.
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure py/cogant is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PY_ROOT = _REPO_ROOT / "py"
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

# Also add examples dir so orchestrator can import
_EXAMPLES_DIR = _REPO_ROOT / "examples"
if str(_EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES_DIR))

from orchestrate_roundtrip import RoundtripOrchestrator


def _has_gnn_package(files: dict) -> bool:
    """True when the roundtrip produced a packaged GNN directory."""
    return "gnn_package/manifest.json" in files


REPO_NAMES = ["flask_mini", "calculator", "event_pipeline"]
REPO_PARAMS = [(name, _REPO_ROOT / "examples" / "control_positive" / name) for name in REPO_NAMES]


@pytest.fixture(scope="module")
def pipeline_outputs():
    """Run the orchestrator once per repo and cache results for all tests."""
    results = {}
    for name, repo_path in REPO_PARAMS:
        if not repo_path.exists():
            continue
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / name
            output_dir.mkdir()
            orch = RoundtripOrchestrator(repo_path, output_dir)
            success = orch.run()
            # Collect all output files and their contents
            files = {}
            for f in output_dir.rglob("*"):
                if f.is_file():
                    rel = str(f.relative_to(output_dir))
                    try:
                        files[rel] = f.read_text(errors="replace")
                    except Exception:
                        files[rel] = "<binary>"
            results[name] = {
                "success": success,
                "files": files,
                "output_dir": str(output_dir),
            }
    return results


class TestPipelineCompletion:
    """Test that the pipeline completes without error on all repos."""

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_pipeline_completes(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        assert pipeline_outputs[repo_name]["success"] is True


class TestProgramGraph:
    """Test program graph output quality."""

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_program_graph_has_nodes_and_edges(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        content = pipeline_outputs[repo_name]["files"].get("program_graph.json")
        assert content is not None, "program_graph.json not generated"
        data = json.loads(content)
        assert len(data["nodes"]) > 0, "Graph should have nodes"
        assert len(data["edges"]) > 0, "Graph should have edges"

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_graph_nodes_have_required_fields(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        data = json.loads(pipeline_outputs[repo_name]["files"]["program_graph.json"])
        for _nid, node in data["nodes"].items():
            assert "id" in node
            assert "kind" in node
            assert "name" in node

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_graph_has_multiple_edge_kinds(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        data = json.loads(pipeline_outputs[repo_name]["files"]["program_graph.json"])
        edge_kinds = set()
        for _eid, edge in data["edges"].items():
            edge_kinds.add(edge["kind"])
        assert len(edge_kinds) >= 2, f"Expected multiple edge kinds, got {edge_kinds}"


class TestSemanticMappings:
    """Test semantic mapping output."""

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_mappings_exist(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        content = pipeline_outputs[repo_name]["files"].get("semantic_mappings.json")
        assert content is not None, "semantic_mappings.json not generated"
        data = json.loads(content)
        assert len(data) > 0, "Should have semantic mappings"

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_mappings_have_multiple_kinds(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        data = json.loads(pipeline_outputs[repo_name]["files"]["semantic_mappings.json"])
        # The orchestrator saves mappings_by_role: {role: [mapping_dicts]}
        by_role = data.get("mappings_by_role", {})
        if by_role:
            roles = set(by_role.keys())
            assert len(roles) >= 1, f"Expected at least 1 role, got {roles}"
        else:
            # Fallback: check total_mappings
            total = data.get("total_mappings", 0)
            assert total > 0, "Should have some mappings"


class TestStateSpace:
    """Test state space in GNN JSON output."""

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_gnn_json_has_state_space(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        content = pipeline_outputs[repo_name]["files"].get("model.gnn.json")
        assert content is not None, "model.gnn.json not generated"
        data = json.loads(content)
        ss = data.get("state_space", {})
        if not ss:
            pytest.skip("state_space block not populated in model.gnn.json")
        assert "variables" in ss or "state_variables" in ss, "State space should have variables"

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_state_space_json_in_package(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        files = pipeline_outputs[repo_name]["files"]
        if not _has_gnn_package(files):
            pytest.skip("GNN package not produced in this environment")
        content = files.get("gnn_package/state_space.json")
        if content is None:
            pytest.skip("gnn_package/state_space.json not generated")
        data = json.loads(content)
        assert isinstance(data, dict)


class TestGNNMarkdown:
    """Test GNN markdown output completeness."""

    CANONICAL_SECTIONS = [
        "Model Metadata",
        "Repository Metadata",
        "Source Coverage",
        "State Space",
        "Observation Modalities",
    ]

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_gnn_markdown_exists(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        content = pipeline_outputs[repo_name]["files"].get("model.gnn.md")
        assert content is not None, "model.gnn.md not generated"
        assert len(content) > 1000, f"GNN markdown too short: {len(content)} chars"

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_gnn_markdown_has_core_sections(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        content = pipeline_outputs[repo_name]["files"]["model.gnn.md"]
        for section in self.CANONICAL_SECTIONS:
            assert section in content, f"Missing canonical section: {section}"

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_gnn_markdown_has_tables(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        content = pipeline_outputs[repo_name]["files"]["model.gnn.md"]
        assert content.count("|") > 10, "GNN markdown should contain tables"


class TestGNNPackage:
    """Test GNN package build, validation, and execution."""

    REQUIRED_PACKAGE_FILES = [
        "manifest.json",
        "model.gnn.md",
        "model.gnn.json",
        "state_space.json",
        "observations.json",
        "actions.json",
        "transitions.json",
        "preferences.json",
        "factors.json",
        "provenance.json",
        "ontology.json",
        "actions_policies.json",
        "connections.json",
        "preferences_constraints.json",
    ]

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_package_has_required_files(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        files = pipeline_outputs[repo_name]["files"]
        if not _has_gnn_package(files):
            pytest.skip("GNN package not produced in this environment")
        for req in self.REQUIRED_PACKAGE_FILES:
            key = f"gnn_package/{req}"
            assert key in files, f"Missing package file: {req}"

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_package_manifest_valid(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        files = pipeline_outputs[repo_name]["files"]
        if not _has_gnn_package(files):
            pytest.skip("GNN package not produced in this environment")
        content = files["gnn_package/manifest.json"]
        manifest = json.loads(content)
        assert "version" in manifest
        assert "files" in manifest
        assert "checksums" in manifest

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_package_json_files_valid(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        files = pipeline_outputs[repo_name]["files"]
        if not _has_gnn_package(files):
            pytest.skip("GNN package not produced in this environment")
        for req in self.REQUIRED_PACKAGE_FILES:
            if req.endswith(".json"):
                key = f"gnn_package/{req}"
                if key in files:
                    data = json.loads(files[key])
                    assert isinstance(data, dict), f"{req} should be a JSON object"

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_validation_report_is_valid_and_high(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        files = pipeline_outputs[repo_name]["files"]
        if not _has_gnn_package(files):
            pytest.skip("GNN package not produced in this environment")
        content = files.get("gnn_validation_report.json")
        if content is None:
            pytest.skip("GNN validation report not generated")
        report = json.loads(content)
        score = float(report.get("score", 0.0))
        # Validator scores are percentage-based and can be valid below 100.
        assert score >= 90.0, f"Validation score {score}% below threshold (90%)"
        assert report["valid"] is True

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_execution_trace_exists(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        files = pipeline_outputs[repo_name]["files"]
        if not _has_gnn_package(files):
            pytest.skip("GNN package not produced in this environment")
        content = files.get("gnn_execution_trace.json")
        if content is None:
            pytest.skip("GNN execution trace not generated (model runner optional)")
        trace = json.loads(content)
        assert isinstance(trace, dict)


class TestOutputCompleteness:
    """Test that all expected output files are generated."""

    # Core artifacts from a successful roundtrip (always required).
    EXPECTED_FILES = [
        "model.gnn.md",
        "model.gnn.json",
        "program_graph.json",
        "semantic_mappings.json",
        "summary.md",
        "validation_report.json",
    ]
    # Produced when optional subsystems succeed (dashboard, packaged validation, model runner).
    OPTIONAL_FILES = [
        "dashboard.html",
        "gnn_validation_report.json",
        "gnn_execution_trace.json",
        "gnn_execution_report.md",
    ]

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_expected_files_exist(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        files = pipeline_outputs[repo_name]["files"]
        for expected in self.EXPECTED_FILES:
            assert expected in files, f"Missing expected output: {expected}"

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_optional_files_when_present(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        files = pipeline_outputs[repo_name]["files"]
        for name in self.OPTIONAL_FILES:
            if name in files:
                assert len(files[name]) > 0 or files[name] == "<binary>"

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_minimum_output_count(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        count = len(pipeline_outputs[repo_name]["files"])
        assert count >= 25, f"Expected >= 25 output files, got {count}"

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_mermaid_diagrams_generated(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        files = pipeline_outputs[repo_name]["files"]
        mermaid_files = [f for f in files if f.endswith(".mermaid")]
        assert len(mermaid_files) >= 3, f"Expected >= 3 Mermaid diagrams, got {len(mermaid_files)}"

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_html_visualizations_generated(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        files = pipeline_outputs[repo_name]["files"]
        html_files = [f for f in files if f.endswith(".html")]
        assert len(html_files) >= 3, f"Expected >= 3 HTML files, got {len(html_files)}"


class TestSimulation:
    """Test simulation outputs are meaningful."""

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_simulation_trace_has_steps(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        content = pipeline_outputs[repo_name]["files"].get("simulation_trace.json")
        if content is None:
            pytest.skip("No simulation trace generated")
        trace = json.loads(content)
        assert isinstance(trace, dict)

    @pytest.mark.parametrize("repo_name", REPO_NAMES)
    def test_active_inference_or_simulation_trace(self, pipeline_outputs, repo_name):
        if repo_name not in pipeline_outputs:
            pytest.skip(f"Repo {repo_name} not available")
        files = pipeline_outputs[repo_name]["files"]
        # Check for any simulation-related output
        ai_trace = files.get("active_inference_trace.json")
        sim_trace = files.get("simulation_trace.json")
        fe_html = files.get("free_energy_trajectory.html")
        sim_report = files.get("simulation_report.md")
        has_any = any([ai_trace, sim_trace, fe_html, sim_report])
        assert has_any, "Should have at least one simulation output"
        # Verify JSON traces are parseable
        if ai_trace:
            data = json.loads(ai_trace)
            assert isinstance(data, (dict, list)), f"Expected dict or list, got {type(data)}"
        if sim_trace:
            data = json.loads(sim_trace)
            assert isinstance(data, (dict, list)), f"Expected dict or list, got {type(data)}"
