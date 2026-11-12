"""Only successful, nontrivial PDF renders replace the documentation receipt."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(("returncode", "size", "success"), [(0, 10001, True), (0, 20, False), (1, 10001, False)])
def test_render_receipt(tmp_path, monkeypatch, returncode, size, success):
    spec = importlib.util.spec_from_file_location("render_manuscript", ROOT / "scripts/render_manuscript.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    injected = tmp_path / "output/manuscript"
    injected.mkdir(parents=True)
    section = injected / "00_abstract.md"
    section.write_text("# Example\n")
    receipt = tmp_path / "docs/manuscript-render.json"
    receipt.parent.mkdir()
    receipt.write_text("previous successful render\n")
    pdf = injected / "COGANT.pdf"
    pdf.write_bytes(b"x" * size)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "INJECTED_DIR", injected)
    monkeypatch.setattr(module, "RECEIPT", receipt)
    monkeypatch.setattr(module, "discover", lambda _: [section])
    monkeypatch.setattr(module, "extract_preamble", lambda _: None)
    monkeypatch.setattr(module, "tool_error", lambda _: 0)
    monkeypatch.setattr(module.shutil, "which", lambda name: name)
    monkeypatch.setattr(module.subprocess, "check_output", lambda *args, **kwargs: "a" * 40 + "\n")
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=returncode))
    status = module.main(["--skip-generate", "--skip-figure-check", "--pdf", str(pdf)])
    assert (status == 0) is success
    if success:
        assert json.loads(receipt.read_text()) == {
            "source_commit": "a" * 40,
            "pdf_artifact": "output/manuscript/COGANT.pdf",
            "pdf_bytes": size,
        }
    else:
        assert receipt.read_text() == "previous successful render\n"
