"""Regression tests for COGANT-owned manuscript formalism numbering."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import audit_manuscript_formalisms as formalism_audit  # noqa: E402
from formalisms import (  # noqa: E402
    build_formalism_registry,
    render_formalisms_for_output,
    write_formalism_registry,
)


def _write_source(tmp_path: Path, text: str) -> tuple[Path, Path]:
    manuscript_dir = tmp_path / "manuscript"
    manuscript_dir.mkdir()
    source = manuscript_dir / "01_body.md"
    source.write_text(text, encoding="utf-8")
    return manuscript_dir, source


def _write_generated(tmp_path: Path, manuscript_dir: Path) -> tuple[Path, Path]:
    records = build_formalism_registry(manuscript_dir, root=tmp_path)
    registry_path = tmp_path / "output" / "data" / "formalism_registry.json"
    write_formalism_registry(records, registry_path)
    generated_dir = tmp_path / "output" / "manuscript"
    generated_dir.mkdir(parents=True)
    for path in sorted(manuscript_dir.glob("*.md")):
        rendered = render_formalisms_for_output(path.read_text(encoding="utf-8"), records)
        (generated_dir / path.name).write_text(rendered, encoding="utf-8")
    return generated_dir, registry_path


def test_strict_audit_accepts_generated_formalism_numbering(tmp_path: Path) -> None:
    manuscript_dir, _source = _write_source(
        tmp_path,
        "### Definition: Program graph {#def:program-graph}\n\n"
        "See @def:program-graph.\n\n"
        "### Proposition: Fixpoint termination {#prop:fixpoint-termination}\n\n"
        "The proof sketch uses @def:program-graph.\n",
    )
    generated_dir, registry_path = _write_generated(tmp_path, manuscript_dir)

    findings = formalism_audit.audit(
        manuscript_dir,
        registry_path=registry_path,
        generated_dir=generated_dir,
        strict=True,
    )

    assert findings == []
    rendered = (generated_dir / "01_body.md").read_text(encoding="utf-8")
    assert "[]{#def:program-graph}**Definition 1 (Program graph).**" in rendered
    assert "[Definition 1](#def:program-graph)" in rendered
    assert "[]{#prop:fixpoint-termination}**Proposition 1" in rendered


def test_legacy_section_labeled_formalism_fails_source_audit(tmp_path: Path) -> None:
    manuscript_dir, _source = _write_source(
        tmp_path,
        "### Definition: Foo {#sec:def-foo}\n\n"
        "Legacy prose points at @sec:def-foo.\n",
    )

    findings = formalism_audit.audit(
        manuscript_dir,
        registry_path=tmp_path / "missing.json",
    )

    assert any("formal heading uses section label" in finding for finding in findings)
    assert any("uses section prefix" in finding for finding in findings)


def test_unknown_formal_reference_fails_source_audit(tmp_path: Path) -> None:
    manuscript_dir, _source = _write_source(
        tmp_path,
        "This paragraph cites @def:not-defined.\n",
    )

    findings = formalism_audit.audit(
        manuscript_dir,
        registry_path=tmp_path / "missing.json",
    )

    assert any("has no definition" in finding for finding in findings)


def test_duplicate_and_hand_numbered_formalisms_fail_source_audit(tmp_path: Path) -> None:
    manuscript_dir, _source = _write_source(
        tmp_path,
        "### Definition: Foo {#def:foo}\n\n"
        "### Definition: Foo again {#def:foo}\n\n"
        "### Proposition 1 (Bar) {#prop:bar}\n",
    )

    findings = formalism_audit.audit(
        manuscript_dir,
        registry_path=tmp_path / "missing.json",
    )

    assert any("duplicate formalism label" in finding for finding in findings)
    assert any("appears hand-numbered" in finding for finding in findings)


def test_generated_output_with_raw_formal_reference_fails_strict_audit(
    tmp_path: Path,
) -> None:
    manuscript_dir, _source = _write_source(
        tmp_path,
        "### Definition: Foo {#def:foo}\n\n"
        "See @def:foo.\n",
    )
    _generated_dir, registry_path = _write_generated(tmp_path, manuscript_dir)
    bad_generated_dir = tmp_path / "output" / "bad_manuscript"
    bad_generated_dir.mkdir(parents=True)
    (bad_generated_dir / "01_body.md").write_text(
        "### Definition: Foo {#def:foo}\n\n"
        "Still raw @def:foo.\n",
        encoding="utf-8",
    )

    findings = formalism_audit.audit(
        manuscript_dir,
        registry_path=registry_path,
        generated_dir=bad_generated_dir,
        strict=True,
    )

    assert any("source-style formal heading leaked" in finding for finding in findings)
    assert any("unresolved generated formal reference" in finding for finding in findings)
