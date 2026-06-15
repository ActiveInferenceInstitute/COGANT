"""COGANT manuscript formalism numbering helpers.

Pandoc-crossref handles sections, figures, tables, and equations in this
project, but the installed filter does not process theorem-style ``@def:`` or
``@prop:`` references. This module owns COGANT's formal-object counters so
definitions, propositions, invariants, conjectures, algorithms, and theorems
render as formal objects rather than ordinary subsections.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

SKIP_NAMES = frozenset({"AGENTS.md", "README.md", "SYNTAX.md", "preamble.md"})
FORMAL_PREFIXES = ("def", "prop", "inv", "conj", "alg", "thm")

DISPLAY_KIND_TO_PREFIX = {
    "Definition": "def",
    "Proposition": "prop",
    "Implementation invariant": "inv",
    "Empirical invariant": "inv",
    "Conjecture": "conj",
    "Algorithm": "alg",
    "Theorem": "thm",
}

DISPLAY_KIND_TO_COUNTER = {
    "Definition": "def",
    "Proposition": "prop",
    "Implementation invariant": "implementation_invariant",
    "Empirical invariant": "empirical_invariant",
    "Conjecture": "conj",
    "Algorithm": "alg",
    "Theorem": "thm",
}

FORMAL_HEADING_RE = re.compile(
    r"^(?P<level>#{2,6})\s+"
    r"(?P<display_kind>Definition|Proposition|Implementation invariant|"
    r"Empirical invariant|Conjecture|Algorithm|Theorem):\s+"
    r"(?P<title>.*?)\s+\{#(?P<prefix>def|prop|inv|conj|alg|thm):"
    r"(?P<label>[A-Za-z0-9_-]+)\}\s*$"
)

LEGACY_SEC_FORMAL_HEADING_RE = re.compile(
    r"^(?P<level>#{2,6})\s+"
    r"(?P<display_kind>Definition|Proposition|Implementation invariant|"
    r"Empirical invariant|Conjecture|Algorithm|Theorem):.*?"
    r"\{#sec:(?P<label>(?:def|prop|thm|alg|conj|inv)-[A-Za-z0-9_-]+)\}\s*$"
)

HAND_NUMBERED_FORMAL_HEADING_RE = re.compile(
    r"^#{2,6}\s+"
    r"(Definition|Proposition|Implementation invariant|Empirical invariant|"
    r"Conjecture|Algorithm|Theorem)\s+\d+(?:[.:)]|\s+\()"
)

FORMAL_REF_RE = re.compile(r"(?<![\w])@(def|prop|inv|conj|alg|thm):([A-Za-z0-9_-]+)\b")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
LEGACY_SEC_FORMAL_REF_RE = re.compile(
    r"(?<![\w])@sec:((?:def|prop|thm|alg|conj|inv)-[A-Za-z0-9_-]+)\b"
)
GENERATED_FORMAL_RE = re.compile(
    r"^\[\]\{#(?P<prefix>def|prop|inv|conj|alg|thm):(?P<label>[A-Za-z0-9_-]+)\}"
    r"\*\*(?P<reference>[^*]+?)\s+\((?P<title>.*?)\)\.\*\*"
)


@dataclass(frozen=True)
class FormalismRecord:
    """One source formalism and its generated reference label."""

    kind: str
    display_kind: str
    counter_key: str
    label: str
    title: str
    number: int
    source_file: str
    source_line: int
    anchor: str
    rendered_reference: str

    @property
    def generated_heading(self) -> str:
        return f"[]{{#{self.anchor}}}**{self.rendered_reference} ({self.title}).**"


def iter_manuscript_markdown(manuscript_dir: Path) -> list[Path]:
    """Return manuscript Markdown files that participate in body formalism scans."""

    return sorted(path for path in manuscript_dir.glob("*.md") if path.name not in SKIP_NAMES)


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def build_formalism_registry(manuscript_dir: Path, *, root: Path | None = None) -> list[FormalismRecord]:
    """Scan source manuscript fragments and assign formalism counters."""

    root = root or manuscript_dir.parent
    counters: Counter[str] = Counter()
    records: list[FormalismRecord] = []
    for path in iter_manuscript_markdown(manuscript_dir):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = FORMAL_HEADING_RE.match(line)
            if not match:
                continue
            display_kind = match.group("display_kind")
            expected_prefix = DISPLAY_KIND_TO_PREFIX[display_kind]
            actual_prefix = match.group("prefix")
            if actual_prefix != expected_prefix:
                # The audit reports this as an error. The registry skips it so
                # generated output cannot silently bless a mismatched label.
                continue
            counter_key = DISPLAY_KIND_TO_COUNTER[display_kind]
            counters[counter_key] += 1
            number = counters[counter_key]
            label = match.group("label")
            anchor = f"{actual_prefix}:{label}"
            records.append(
                FormalismRecord(
                    kind=actual_prefix,
                    display_kind=display_kind,
                    counter_key=counter_key,
                    label=label,
                    title=match.group("title").strip(),
                    number=number,
                    source_file=_relative(path, root),
                    source_line=line_no,
                    anchor=anchor,
                    rendered_reference=f"{display_kind} {number}",
                )
            )
    return records


def registry_payload(records: list[FormalismRecord]) -> dict[str, object]:
    """Serialize registry records for ``output/data/formalism_registry.json``."""

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "record_count": len(records),
        "records": [asdict(record) for record in records],
    }


def write_formalism_registry(records: list[FormalismRecord], output_path: Path) -> Path:
    """Write a formalism registry JSON file and return its path."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(registry_payload(records), indent=2) + "\n", encoding="utf-8")
    return output_path


def _record_by_anchor(records: list[FormalismRecord]) -> dict[str, FormalismRecord]:
    return {record.anchor: record for record in records}


def _replace_refs_outside_inline_code(
    line: str,
    replace_ref: Callable[[re.Match[str]], str],
) -> str:
    pieces: list[str] = []
    cursor = 0
    for match in INLINE_CODE_RE.finditer(line):
        pieces.append(FORMAL_REF_RE.sub(replace_ref, line[cursor : match.start()]))
        pieces.append(match.group(0))
        cursor = match.end()
    pieces.append(FORMAL_REF_RE.sub(replace_ref, line[cursor:]))
    return "".join(pieces)


def render_formalisms_for_output(text: str, records: list[FormalismRecord]) -> str:
    """Rewrite source formalism headings and references for generated Markdown."""

    by_anchor = _record_by_anchor(records)
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            lines.append(line)
            continue
        if in_fence:
            lines.append(line)
            continue

        heading_match = FORMAL_HEADING_RE.match(line)
        if heading_match:
            anchor = f"{heading_match.group('prefix')}:{heading_match.group('label')}"
            record = by_anchor.get(anchor)
            lines.append(record.generated_heading if record else line)
            continue

        def replace_ref(match: re.Match[str]) -> str:
            anchor = f"{match.group(1)}:{match.group(2)}"
            record = by_anchor.get(anchor)
            if record is None:
                return match.group(0)
            return f"[{record.rendered_reference}](#{record.anchor})"

        lines.append(_replace_refs_outside_inline_code(line, replace_ref))
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + suffix


def load_formalism_registry(path: Path) -> list[FormalismRecord]:
    """Read a generated formalism registry."""

    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("records", [])
    if not isinstance(records, list):
        return []
    out: list[FormalismRecord] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        out.append(
            FormalismRecord(
                kind=str(record.get("kind", "")),
                display_kind=str(record.get("display_kind", "")),
                counter_key=str(record.get("counter_key", "")),
                label=str(record.get("label", "")),
                title=str(record.get("title", "")),
                number=int(record.get("number", 0)),
                source_file=str(record.get("source_file", "")),
                source_line=int(record.get("source_line", 0)),
                anchor=str(record.get("anchor", "")),
                rendered_reference=str(record.get("rendered_reference", "")),
            )
        )
    return out
