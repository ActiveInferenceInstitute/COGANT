"""Tests for manuscript-body Markdown-file link audit."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "tools" / "audit_manuscript_markdown_links.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_manuscript_markdown_links", AUDIT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_body_markdown_file_link_fails(tmp_path: Path) -> None:
    mod = _load_module()
    manuscript = tmp_path / "manuscript"
    manuscript.mkdir()
    (manuscript / "00_demo.md").write_text(
        "Read [the package docs](../cogant/docs/index.md) for details.\n",
        encoding="utf-8",
    )

    findings = mod.audit_directories([manuscript])

    assert len(findings) == 1
    assert findings[0].target == "../cogant/docs/index.md"


def test_angle_bracket_body_markdown_file_link_fails(tmp_path: Path) -> None:
    mod = _load_module()
    manuscript = tmp_path / "manuscript"
    manuscript.mkdir()
    (manuscript / "00_demo.md").write_text(
        "Read [the package docs](<../cogant/docs/index.md>) for details.\n",
        encoding="utf-8",
    )

    findings = mod.audit_directories([manuscript])

    assert len(findings) == 1
    assert findings[0].target == "../cogant/docs/index.md"


def test_intra_manuscript_refs_and_non_markdown_links_pass(tmp_path: Path) -> None:
    mod = _load_module()
    manuscript = tmp_path / "manuscript"
    manuscript.mkdir()
    (manuscript / "00_demo.md").write_text(
        "See @sec:method and [the GNN repository](https://github.com/example/repo).\n"
        "![Figure](../figures/demo.png){#fig:demo width=98%}\n",
        encoding="utf-8",
    )

    assert mod.audit_directories([manuscript]) == []


def test_helper_docs_are_ignored(tmp_path: Path) -> None:
    mod = _load_module()
    manuscript = tmp_path / "manuscript"
    manuscript.mkdir()
    (manuscript / "README.md").write_text(
        "Contributor docs may link to [syntax](SYNTAX.md).\n",
        encoding="utf-8",
    )
    (manuscript / "SYNTAX.md").write_text(
        "Examples may link to [README](README.md).\n",
        encoding="utf-8",
    )
    (manuscript / "AGENTS.md").write_text(
        "Agents may link to [README](README.md).\n",
        encoding="utf-8",
    )

    assert mod.audit_directories([manuscript]) == []


def test_generated_body_markdown_file_link_fails(tmp_path: Path) -> None:
    mod = _load_module()
    (tmp_path / "manuscript").mkdir()
    generated = tmp_path / "output" / "manuscript"
    generated.mkdir(parents=True)
    (generated / "00_demo.md").write_text(
        "Generated output still links to [source](other.md).\n",
        encoding="utf-8",
    )

    findings = mod.audit(tmp_path, include_generated=True)

    assert len(findings) == 1
    assert findings[0].target == "other.md"
