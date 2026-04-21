"""Integration tests for real-world repo fixtures.

Runs the full :class:`RoundtripOrchestrator` pipeline against the three
fixtures under ``examples/real_world/``:

* ``flask_app/``    — hand-written Flask/SQLAlchemy-pattern app
* ``requests_lib/`` — hand-written requests-pattern HTTP library
* ``json_stdlib/``  — snapshot of CPython's ``Lib/json/``

Quality bar:

1. Pipeline completes without raising.
2. ``program_graph.json`` is emitted with a non-empty node set.
3. ``semantic_mappings.json`` is emitted with at least one mapping.
4. ``model.gnn.md`` contains the canonical GNN formatter sections.
5. Auxiliary artifacts (summary, validation report) are generated.

These tests are marked ``integration`` so the fast unit-test suite can
skip them with ``-m "not integration"``.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PY_ROOT = _REPO_ROOT / "py"
_EXAMPLES_DIR = _REPO_ROOT / "examples"

for _p in (_PY_ROOT, _EXAMPLES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from orchestrate_roundtrip import RoundtripOrchestrator  # noqa: E402

REAL_WORLD_REPOS = [
    ("flask_app", _REPO_ROOT / "examples" / "real_world" / "flask_app"),
    ("requests_lib", _REPO_ROOT / "examples" / "real_world" / "requests_lib"),
    ("json_stdlib", _REPO_ROOT / "examples" / "real_world" / "json_stdlib"),
]


@pytest.fixture(scope="module")
def real_world_outputs():
    """Run the orchestrator once per real-world fixture and cache the results.

    Returns a dict keyed on repo name. Each entry contains:

    * ``success`` -- bool returned by ``RoundtripOrchestrator.run()``
    * ``files``   -- dict of relative path -> file contents (str).
                     Binary files appear as the literal string ``"<binary>"``.
    * ``output_dir`` -- path the orchestrator wrote to (before tmpdir cleanup).
    """
    results = {}
    for name, repo_path in REAL_WORLD_REPOS:
        if not repo_path.exists():
            continue
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / name
            output_dir.mkdir()
            orch = RoundtripOrchestrator(repo_path, output_dir)
            success = orch.run()
            files: dict[str, str] = {}
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


# ---------------------------------------------------------------------------
# 1. Pipeline completes
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("repo_name,_", REAL_WORLD_REPOS)
def test_pipeline_completes(real_world_outputs, repo_name, _):
    if repo_name not in real_world_outputs:
        pytest.skip(f"Fixture {repo_name} not available")
    entry = real_world_outputs[repo_name]
    assert entry["success"] is True, f"{repo_name} pipeline did not report success"
    assert entry["files"], f"{repo_name} produced no output files"


# ---------------------------------------------------------------------------
# 2. Program graph is non-empty
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("repo_name,_", REAL_WORLD_REPOS)
def test_program_graph_nonempty(real_world_outputs, repo_name, _):
    if repo_name not in real_world_outputs:
        pytest.skip(f"Fixture {repo_name} not available")
    files = real_world_outputs[repo_name]["files"]
    content = files.get("program_graph.json")
    assert content is not None, f"{repo_name}: program_graph.json missing"
    graph = json.loads(content)
    nodes = graph.get("nodes") or {}
    assert len(nodes) > 0, f"{repo_name}: program graph has no nodes"


@pytest.mark.integration
@pytest.mark.parametrize("repo_name,_", REAL_WORLD_REPOS)
def test_program_graph_has_edges(real_world_outputs, repo_name, _):
    if repo_name not in real_world_outputs:
        pytest.skip(f"Fixture {repo_name} not available")
    files = real_world_outputs[repo_name]["files"]
    graph = json.loads(files["program_graph.json"])
    edges = graph.get("edges") or {}
    assert len(edges) > 0, f"{repo_name}: program graph has no edges"


# ---------------------------------------------------------------------------
# 3. Semantic mappings are non-empty
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("repo_name,_", REAL_WORLD_REPOS)
def test_semantic_mappings_nonempty(real_world_outputs, repo_name, _):
    if repo_name not in real_world_outputs:
        pytest.skip(f"Fixture {repo_name} not available")
    files = real_world_outputs[repo_name]["files"]
    content = files.get("semantic_mappings.json")
    assert content is not None, f"{repo_name}: semantic_mappings.json missing"
    data = json.loads(content)
    total = data.get("total_mappings", 0)
    by_role = data.get("mappings_by_role") or {}
    assert total > 0 or by_role, (
        f"{repo_name}: semantic mappings are empty (total={total}, roles={list(by_role)})"
    )


# ---------------------------------------------------------------------------
# 4. GNN markdown has canonical sections
# ---------------------------------------------------------------------------


CANONICAL_GNN_SECTIONS = [
    "Model Metadata",
    "Repository Metadata",
    "State Space",
    "Observation Modalities",
]


@pytest.mark.integration
@pytest.mark.parametrize("repo_name,_", REAL_WORLD_REPOS)
def test_gnn_markdown_has_canonical_sections(real_world_outputs, repo_name, _):
    if repo_name not in real_world_outputs:
        pytest.skip(f"Fixture {repo_name} not available")
    files = real_world_outputs[repo_name]["files"]
    gnn_md = files.get("model.gnn.md", "")
    assert gnn_md, f"{repo_name}: model.gnn.md missing"
    assert len(gnn_md) > 500, f"{repo_name}: model.gnn.md too short ({len(gnn_md)} chars)"
    for section in CANONICAL_GNN_SECTIONS:
        assert section in gnn_md, f"{repo_name}: model.gnn.md missing canonical section {section!r}"


# ---------------------------------------------------------------------------
# 5. Core support artifacts exist
# ---------------------------------------------------------------------------


_REQUIRED_CORE_FILES = [
    "model.gnn.md",
    "model.gnn.json",
    "program_graph.json",
    "semantic_mappings.json",
    "summary.md",
    "validation_report.json",
]


@pytest.mark.integration
@pytest.mark.parametrize("repo_name,_", REAL_WORLD_REPOS)
def test_core_artifacts_present(real_world_outputs, repo_name, _):
    if repo_name not in real_world_outputs:
        pytest.skip(f"Fixture {repo_name} not available")
    files = real_world_outputs[repo_name]["files"]
    for required in _REQUIRED_CORE_FILES:
        assert required in files, f"{repo_name}: required artifact {required!r} missing"


@pytest.mark.integration
@pytest.mark.parametrize("repo_name,_", REAL_WORLD_REPOS)
def test_model_gnn_json_parses(real_world_outputs, repo_name, _):
    if repo_name not in real_world_outputs:
        pytest.skip(f"Fixture {repo_name} not available")
    files = real_world_outputs[repo_name]["files"]
    data = json.loads(files["model.gnn.json"])
    assert isinstance(data, dict), f"{repo_name}: model.gnn.json not a dict"
