#!/usr/bin/env python3
"""Audit COGANT manuscript formalism numbering and references.

COGANT owns formal-object numbering because the local pandoc-crossref filter
does not process theorem-style ``@def:`` / ``@prop:`` references. This audit
therefore checks both source authoring syntax and generated output:

* source formal objects use typed labels such as ``{#def:program-graph}``;
* source references use formal prefixes, not ``@sec:def-*``;
* source does not hand-author formal numbers;
* generated output has contiguous generated numbers and no raw formal refs.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TOOLS_DIR.parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from formalisms import (  # noqa: E402
    DISPLAY_KIND_TO_PREFIX,
    FORMAL_HEADING_RE,
    FORMAL_REF_RE,
    GENERATED_FORMAL_RE,
    HAND_NUMBERED_FORMAL_HEADING_RE,
    LEGACY_SEC_FORMAL_HEADING_RE,
    LEGACY_SEC_FORMAL_REF_RE,
    SKIP_NAMES,
    build_formalism_registry,
    iter_manuscript_markdown,
    load_formalism_registry,
)


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _finding(path: Path, line_no: int | None, message: str) -> str:
    location = _display_path(path)
    if line_no is not None:
        location = f"{location}:{line_no}"
    return f"{location}: {message}"


def _non_fenced_lines(path: Path) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    in_fence = False
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append((line_no, re.sub(r"`[^`]*`", "", line)))
    return out


def _audit_source(manuscript_dir: Path) -> list[str]:
    findings: list[str] = []
    definitions: dict[str, tuple[Path, int]] = {}
    references: list[tuple[str, Path, int]] = []
    for path in iter_manuscript_markdown(manuscript_dir):
        for line_no, line in _non_fenced_lines(path):
            if LEGACY_SEC_FORMAL_HEADING_RE.match(line):
                findings.append(
                    _finding(
                        path,
                        line_no,
                        "formal heading uses section label; use {#def:/#prop:/#inv:/#conj:/#alg:/#thm:}",
                    )
                )
            if HAND_NUMBERED_FORMAL_HEADING_RE.match(line):
                findings.append(
                    _finding(path, line_no, "formal heading appears hand-numbered; numbers are generated")
                )
            heading = FORMAL_HEADING_RE.match(line)
            if heading:
                display_kind = heading.group("display_kind")
                prefix = heading.group("prefix")
                expected = DISPLAY_KIND_TO_PREFIX[display_kind]
                if prefix != expected:
                    findings.append(
                        _finding(
                            path,
                            line_no,
                            f"{display_kind} heading uses {prefix!r}; expected {expected!r}",
                        )
                    )
                anchor = f"{prefix}:{heading.group('label')}"
                if anchor in definitions:
                    first_path, first_line = definitions[anchor]
                    findings.append(
                        _finding(
                            path,
                            line_no,
                            f"duplicate formalism label {anchor!r}; first seen at {_display_path(first_path)}:{first_line}",
                        )
                    )
                definitions[anchor] = (path, line_no)
            for match in LEGACY_SEC_FORMAL_REF_RE.finditer(line):
                findings.append(
                    _finding(
                        path,
                        line_no,
                        f"formal reference {match.group(0)!r} uses section prefix; use typed formal prefix",
                    )
                )
            for match in FORMAL_REF_RE.finditer(line):
                references.append((f"{match.group(1)}:{match.group(2)}", path, line_no))

    for anchor, path, line_no in references:
        if anchor not in definitions:
            findings.append(_finding(path, line_no, f"formal reference {anchor!r} has no definition"))
    return findings


def _audit_registry(registry_path: Path, source_records: int) -> list[str]:
    findings: list[str] = []
    if not registry_path.exists():
        findings.append(f"{_display_path(registry_path)}: missing generated formalism registry")
        return findings
    try:
        records = load_formalism_registry(registry_path)
    except (OSError, ValueError, TypeError) as exc:
        findings.append(f"{_display_path(registry_path)}: invalid formalism registry: {exc}")
        return findings
    if len(records) != source_records:
        findings.append(
            f"{_display_path(registry_path)}: record count {len(records)} does not match source count {source_records}"
        )
    by_counter: dict[str, list[int]] = defaultdict(list)
    seen_anchors: set[str] = set()
    for record in records:
        if record.anchor in seen_anchors:
            findings.append(f"{_display_path(registry_path)}: duplicate anchor {record.anchor!r}")
        seen_anchors.add(record.anchor)
        by_counter[record.counter_key].append(record.number)
        expected_ref = f"{record.display_kind} {record.number}"
        if record.rendered_reference != expected_ref:
            findings.append(
                f"{_display_path(registry_path)}: {record.anchor!r} has rendered_reference "
                f"{record.rendered_reference!r}; expected {expected_ref!r}"
            )
    for counter_key, numbers in sorted(by_counter.items()):
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            findings.append(
                f"{_display_path(registry_path)}: counter {counter_key!r} has non-contiguous numbers {numbers}"
            )
    return findings


def _audit_generated(generated_dir: Path) -> list[str]:
    findings: list[str] = []
    if not generated_dir.exists():
        findings.append(f"{_display_path(generated_dir)}: generated manuscript directory missing")
        return findings
    generated_records: dict[str, list[int]] = defaultdict(list)
    for path in sorted(generated_dir.glob("*.md")):
        if path.name in SKIP_NAMES:
            continue
        for line_no, line in _non_fenced_lines(path):
            if FORMAL_HEADING_RE.match(line):
                findings.append(_finding(path, line_no, "source-style formal heading leaked into generated output"))
            for match in FORMAL_REF_RE.finditer(line):
                findings.append(_finding(path, line_no, f"unresolved generated formal reference {match.group(0)!r}"))
            generated = GENERATED_FORMAL_RE.match(line)
            if generated:
                reference = generated.group("reference")
                number_match = re.search(r"\s(\d+)$", reference)
                if number_match:
                    display_kind = reference[: number_match.start()].strip()
                    generated_records[display_kind].append(int(number_match.group(1)))
                else:
                    findings.append(_finding(path, line_no, f"generated formal heading lacks numeric reference {reference!r}"))
    for display_kind, numbers in sorted(generated_records.items()):
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            findings.append(
                f"{_display_path(generated_dir)}: generated {display_kind!r} numbers are not contiguous: {numbers}"
            )
    return findings


def audit(
    manuscript_dir: Path,
    *,
    registry_path: Path,
    generated_dir: Path | None = None,
    strict: bool = False,
) -> list[str]:
    source_records = build_formalism_registry(manuscript_dir, root=_REPO_ROOT)
    findings = _audit_source(manuscript_dir)
    if strict:
        findings.extend(_audit_registry(registry_path, len(source_records)))
        if generated_dir is not None:
            findings.extend(_audit_generated(generated_dir))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript-dir", type=Path, default=_REPO_ROOT / "manuscript")
    parser.add_argument("--generated-dir", type=Path, default=_REPO_ROOT / "output" / "manuscript")
    parser.add_argument("--registry", type=Path, default=_REPO_ROOT / "output" / "data" / "formalism_registry.json")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    findings = audit(
        args.manuscript_dir,
        registry_path=args.registry,
        generated_dir=args.generated_dir,
        strict=args.strict,
    )
    if findings:
        print("manuscript formalism audit: findings", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1
    mode = "source+generated" if args.strict else "source"
    print(f"manuscript formalism audit: OK ({mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
