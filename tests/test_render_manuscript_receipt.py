"""Only successful, nontrivial PDF renders replace the documentation receipt."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def render_workspace(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("render_manuscript", ROOT / "scripts/render_manuscript.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt = tmp_path / "docs/manuscript-render.json"
    receipt.parent.mkdir()
    receipt.write_text("previous successful render\n", encoding="utf-8")
    pdf = tmp_path / "COGANT.pdf"
    pdf.write_bytes(b"previous artifact")
    source = tmp_path / "00_abstract.md"
    source.write_text("# Example\n", encoding="utf-8")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "RECEIPT", receipt)
    return module, receipt, pdf, source


def test_render_receipt_binds_actual_input_and_artifact_bytes(render_workspace, tmp_path):
    module, receipt, pdf, source = render_workspace
    staged = tmp_path / "staged.pdf"
    content = b"%PDF-1.4\n" + b"x" * 10_001
    staged.write_bytes(content)
    inputs = module.input_manifest([source])
    assert module.publish_render(staged, pdf, [source], inputs) == 0
    recorded = json.loads(receipt.read_text(encoding="utf-8"))
    assert pdf.read_bytes() == content
    assert recorded["pdf_sha256"] == hashlib.sha256(content).hexdigest()
    assert recorded["pdf_bytes"] == len(content)
    assert recorded["inputs"] == [
        {
            "path": source.name,
            "sha256": hashlib.sha256(b"# Example\n").hexdigest(),
            "size_bytes": len(b"# Example\n"),
        }
    ]
    assert recorded["artifact_availability"] == {
        "scope": "local-output",
        "observed_at_render": True,
        "retained_in_repository": False,
        "fresh_clone_comparable": False,
    }


@pytest.mark.parametrize("failure", ["missing", "small", "changed-input"])
def test_render_refusal_preserves_prior_receipt_and_pdf(render_workspace, tmp_path, failure):
    module, receipt, pdf, source = render_workspace
    before = module.input_manifest([source])
    staged = tmp_path / "staged.pdf"
    if failure != "missing":
        staged.write_bytes(b"x" * (20 if failure == "small" else 10_001))
    if failure == "changed-input":
        source.write_text("# Concurrent edit\n", encoding="utf-8")
    assert module.publish_render(staged, pdf, [source], before) == 1
    assert receipt.read_text(encoding="utf-8") == "previous successful render\n"
    assert pdf.read_bytes() == b"previous artifact"


def test_published_pdf_stays_readable_until_atomic_replacement(render_workspace, tmp_path, monkeypatch):
    module, receipt, pdf, source = render_workspace
    staged = tmp_path / "staged.pdf"
    staged.write_bytes(b"%PDF-1.4\n" + b"x" * 10_001)
    original_replace = module.os.replace
    observed = []

    def replace(source_path, destination):
        observed.append(pdf.read_bytes())
        return original_replace(source_path, destination)

    monkeypatch.setattr(module.os, "replace", replace)
    assert module.publish_render(staged, pdf, [source], module.input_manifest([source])) == 0
    assert observed[0] == b"previous artifact"
    assert all(observed)


def test_receipt_publication_failure_restores_prior_pdf(render_workspace, tmp_path, monkeypatch):
    module, receipt, pdf, source = render_workspace
    staged = tmp_path / "staged.pdf"
    staged.write_bytes(b"%PDF-1.4\n" + b"x" * 10_001)
    original_replace = module.os.replace

    def replace(source_path, destination):
        if destination == receipt:
            raise OSError("receipt destination refused")
        return original_replace(source_path, destination)

    monkeypatch.setattr(module.os, "replace", replace)
    with pytest.raises(OSError, match="receipt destination refused"):
        module.publish_render(staged, pdf, [source], module.input_manifest([source]))
    assert pdf.read_bytes() == b"previous artifact"
    assert receipt.read_text(encoding="utf-8") == "previous successful render\n"
