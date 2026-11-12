"""The GNN gate must reject drift from its workflow-group pin and pointer."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40
REPOSITORY = "ActiveInferenceInstitute/Generalized_Notation_Notation"


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        (None, None, None),
        ("schema", "wrong", "schema"),
        ("repository", "other/repo", "repository"),
        ("commit", "b" * 40, "commit does not match"),
        ("commit", "short", "full commit"),
        ("tag", "v0.0.0", "tag does not match"),
        ("pointer", "missing", "pointer does not name"),
        ("pin", "invalid JSON", "pin unavailable"),
    ],
)
def test_gnn_pin_drift(tmp_path, monkeypatch, field, value, expected):
    spec = importlib.util.spec_from_file_location("release_integrity", ROOT / "tools/audit_release_integrity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    lock = tmp_path / "uv.lock"
    monkeypatch.setattr(module, "LOCK_PATH", lock)
    lock.write_text(
        '[[package]]\nname = "generalized-notation-notation"\nversion = "5.0.3"\n'
        f'source = {{git = "https://github.com/{REPOSITORY}.git#{COMMIT}"}}\n'
    )
    github = tmp_path / ".github"
    github.mkdir()
    pin = {"schema": "gnn-importer-pin/v1", "repository": REPOSITORY, "commit": COMMIT, "tag": "v5.0.3"}
    if field not in (None, "pointer", "pin"):
        pin[field] = value
    (github / "gnn-pin.json").write_text(value if field == "pin" else json.dumps(pin))
    pointer = f".github/gnn-pin.json {COMMIT} .github/workflows/ci.yml gnn-conformance"
    (github / "GNN.md").write_text(value if field == "pointer" else pointer)
    optional = {"upstream": [f"generalized-notation-notation @ git+https://github.com/{REPOSITORY}.git@{COMMIT}"]}
    _, issues = module._build_sbom({"name": "cogant", "version": "0.0.0"}, optional)
    if expected is None:
        assert issues == []
    else:
        assert any(expected in issue for issue in issues), issues
