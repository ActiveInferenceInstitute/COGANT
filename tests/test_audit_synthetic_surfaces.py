"""Tests for the synthetic-surface classification gate."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "tools" / "audit_synthetic_surfaces.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_synthetic_surfaces", AUDIT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def _track(root: Path, rel_path: str, text: str) -> Path:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", rel_path], cwd=root, check=True)
    return path


def _write_forward_matrix_registry(root: Path) -> None:
    tools = root / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    (tools / "manuscript_figure_registry.py").write_text(
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class ManuscriptFigure:\n"
        "    key: str\n"
        "    source: str\n"
        "    destination: str\n"
        "MANUSCRIPT_FIGURES = (ManuscriptFigure(\n"
        "    key='forward_abcd_matrices',\n"
        "    source='cogant/output/flask_app/connections_matrix.png',\n"
        "    destination='cogant_forward_abcd_matrices.png',\n"
        "),)\n",
        encoding="utf-8",
    )


def _valid_matrix_sidecar() -> dict[str, object]:
    return {
        "matrix_values_from_artifact": True,
        "matrix_validation_errors": [],
        "fallback_panels": [],
        "degraded_panels": [],
        "matrix_source_artifact": "cogant/output/flask_app/gnn_package/model.gnn.json",
        "source_artifact_digest": "source-digest",
        "source_matrix_shapes": {"A": [1, 1], "B": [1, 1, 1], "C": [1], "D": [1]},
        "matrix_reducers": {"B": {"method": "max_over_actions"}},
        "panel_sources": {"A": "matrix_source_artifact"},
        "dimension_alignment": {
            "hidden_states_match": True,
            "observations_match": True,
            "actions_match": True,
        },
    }


def test_unallowlisted_term_fails_in_tracked_source(tmp_path: Path) -> None:
    mod = _load_module()
    repo = _git_repo(tmp_path)
    _track(repo, "src/bad.py", "def f():\n    return 'fallback value'\n")

    occurrences, findings = mod.audit(repo)

    assert any(o.term.lower() == "fallback" and not o.classified for o in occurrences)
    assert findings
    assert "unclassified synthetic-surface term" in findings[0].message


def test_unallowlisted_term_fails_in_untracked_source_under_strict(tmp_path: Path) -> None:
    mod = _load_module()
    repo = _git_repo(tmp_path)
    path = repo / "src" / "bad.py"
    path.parent.mkdir(parents=True)
    path.write_text("def f():\n    return 'fallback value'\n", encoding="utf-8")

    occurrences, findings = mod.audit(repo, strict=True, stub_runner=lambda root: [])

    assert any(o.term.lower() == "fallback" and not o.classified for o in occurrences)
    assert any("unclassified synthetic-surface term" in f.message for f in findings)


def test_registered_manuscript_variables_pass_source_scan(tmp_path: Path) -> None:
    mod = _load_module()
    repo = _git_repo(tmp_path)
    _track(
        repo,
        "manuscript/00_demo.md",
        "A registered {{VERSION}} placeholder is expected in manuscript sources.\n",
    )

    occurrences, findings = mod.audit(repo)

    assert len(occurrences) == 1
    assert occurrences[0].category == "template_variable"
    assert findings == []


def test_unregistered_manuscript_template_variable_fails_strict_source_check(tmp_path: Path) -> None:
    mod = _load_module()
    repo = _git_repo(tmp_path)
    (repo / "tools").mkdir()
    (repo / "tools" / "manuscript_vars.py").write_text(
        "MANUSCRIPT_VARS = {'{{KNOWN}}': 'metrics.known'}\n",
        encoding="utf-8",
    )
    (repo / "manuscript").mkdir()
    (repo / "manuscript" / "00_demo.md").write_text(
        "Known {{KNOWN}}, unknown {{UNKNOWN}}.\n",
        encoding="utf-8",
    )

    findings = mod.source_template_findings(repo)

    assert any("unregistered manuscript template variable: {{UNKNOWN}}" in f.message for f in findings)


def test_generated_markdown_template_token_fails_strict_artifact_check(tmp_path: Path) -> None:
    mod = _load_module()
    generated = tmp_path / "output" / "manuscript"
    generated.mkdir(parents=True)
    (generated / "00_demo.md").write_text("Rendered text still has {{KNOWN}}.\n", encoding="utf-8")

    findings = mod.registered_template_findings(tmp_path)

    assert any("template variable remained in generated manuscript Markdown: {{KNOWN}}" in f.message for f in findings)


def test_type_stub_occurrence_passes_when_stub_parity_runner_passes(tmp_path: Path) -> None:
    mod = _load_module()
    repo = _git_repo(tmp_path)
    _track(repo, "pkg/api.pyi", "from typing import Any\n\nThing: Any  # type stub surface\n")

    occurrences, findings = mod.audit(repo)

    assert any(o.category == "type_stub" for o in occurrences)
    assert findings == []
    assert mod.stub_parity_findings(repo, runner=lambda root: []) == []


def test_type_stub_occurrence_fails_when_stub_parity_runner_fails(tmp_path: Path) -> None:
    mod = _load_module()
    repo = _git_repo(tmp_path)
    _track(repo, "pkg/api.pyi", "from typing import Any\n\nThing: Any  # type stub surface\n")

    findings = mod.stub_parity_findings(
        repo,
        runner=lambda root: ["synthetic stub parity failure"],
    )

    assert any("synthetic stub parity failure" in finding.message for finding in findings)


def test_matrix_sidecar_rejects_synthetic_public_panels(tmp_path: Path) -> None:
    mod = _load_module()
    _write_forward_matrix_registry(tmp_path)
    copied = tmp_path / "output" / "figures" / "cogant_forward_abcd_matrices.figure.json"
    source = tmp_path / "cogant" / "output" / "flask_app" / "connections_matrix.figure.json"
    for path in (copied, source):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "matrix_values_from_artifact": False,
                    "fallback_panels": ["A"],
                    "matrix_source_artifact": None,
                    "source_matrix_shapes": {"A": [1, 1]},
                    "matrix_reducers": {"B": {"method": "max_over_actions"}},
                    "panel_sources": {"A": "shape_proxy"},
                }
            ),
            encoding="utf-8",
        )

    findings = mod.matrix_provenance_findings(tmp_path)

    messages = "\n".join(f.message for f in findings)
    assert "matrix_values_from_artifact must be true" in messages
    assert "fallback_panels must be empty" in messages
    assert "shape_proxy" in messages


def test_matrix_sidecar_audit_uses_registry_resolved_source(tmp_path: Path) -> None:
    mod = _load_module()
    _write_forward_matrix_registry(tmp_path)
    copied = tmp_path / "output" / "figures" / "cogant_forward_abcd_matrices.figure.json"
    source = tmp_path / "cogant" / "output" / "flask_app" / "connections_matrix.figure.json"
    out_of_sync_calculator = (
        tmp_path / "cogant" / "output" / "calculator" / "connections_matrix.figure.json"
    )
    for path in (copied, source, out_of_sync_calculator):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_valid_matrix_sidecar()), encoding="utf-8")
    source.write_text(
        json.dumps({**_valid_matrix_sidecar(), "matrix_values_from_artifact": False}),
        encoding="utf-8",
    )

    findings = mod.matrix_provenance_findings(tmp_path)

    assert any("matrix_values_from_artifact must be true" in f.message for f in findings)


def test_current_tree_strict_audit_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(AUDIT), "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 finding(s)" in result.stdout
