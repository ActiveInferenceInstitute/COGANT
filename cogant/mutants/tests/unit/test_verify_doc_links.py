"""Smoke test for ``docs/verify_doc_links.py``."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_verify_module():
    script = _REPO_ROOT / "docs" / "verify_doc_links.py"
    assert script.is_file(), f"missing {script}"
    spec = importlib.util.spec_from_file_location("verify_doc_links", script)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_verify_doc_links_no_errors() -> None:
    mod = _load_verify_module()
    errors = mod.verify_docs()
    assert errors == [], "\n".join(errors)


def test_verify_doc_links_main_exits_zero() -> None:
    mod = _load_verify_module()
    assert mod.main() == 0
