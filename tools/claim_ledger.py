#!/usr/bin/env python3
"""Build a claims-first manuscript ledger for COGANT.

The ledger is deliberately conservative: it records numeric placeholders,
literal numeric prose, citations, figure references, and code/doc artifact
paths by source file and line. It does not decide truth by itself; it creates
the review surface that lets manuscript claims trace back to METRICS.yaml,
generated figures/JSON, tests, docs, or primary citations. The scanned file
set mirrors rendered manuscript body files: helper docs such as AGENTS,
README, and SYNTAX are excluded, while supplementary markdown is included.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
OUTPUT_DIR = ROOT / "output"


@dataclass
class ClaimRecord:
    file: str
    line: int
    kind: str
    text: str
    evidence_hint: str
    classification: str = ""


PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
CITATION_RE = re.compile(r"@\w[\w:-]+")
FIGURE_RE = re.compile(r"@fig:[\w:-]+|!\[[^\]]*\]\(([^)]+)\)")
NUMBER_RE = re.compile(r"(?<![\w])-?(?:\d+(?:\.\d+)?%?|\d+/\d+)(?![\w])")
PATH_RE = re.compile(r"`(\.\./[^`]+|cogant/[^`]+|tools/[^`]+|scripts/[^`]+)`")
INLINE_CODE_RE = re.compile(r"`[^`]+`")
CROSSREF_RE = re.compile(r"@(?:sec|tbl|fig|eq|lst|def|prop|inv|conj|alg|thm):[\w:-]+")
ANCHOR_RE = re.compile(r"\{#[\w:-]+\}")
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
VERSION_RE = re.compile(r"\bv?\d+(?:\.\d+)+(?:[a-z])?\b", re.IGNORECASE)
MATH_RE = re.compile(r"\$[^$]+\$")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\([^)]+\)")
FENCE_RE = re.compile(r"^\s*```")
ORDERED_LIST_RE = re.compile(r"^\s*\d+[.)]\s+")
BIBLIOGRAPHY_ENTRY_RE = re.compile(r"^\s*\[\d+\]")
NUMERIC_CONTEXT_RE = re.compile(
    r"\b("
    r"axis|benchmark|byte|cardinalit|count|coverage|dimension|edge|elapsed|epsilon|"
    r"fixture|function|line|loc|matrix|metric|module|node|observation|policy|rank|"
    r"role|roundtrip|row|runtime|score|section|shape|stage|state|suite|target|test|"
    r"threshold|transition|validation|warning|wave|mutant|sample|baseline"
    r")\w*\b",
    re.IGNORECASE,
)
UNIT_CONTEXT_RE = re.compile(r"\b(ms|s|min|hr|mb|gb|k|m|%|sha-256|ffi|http|json|yaml)\b", re.IGNORECASE)


def _kind_hint(kind: str, token: str, classification: str = "") -> str:
    if kind == "placeholder":
        return "METRICS.yaml via tools/manuscript_vars.py"
    if kind == "citation":
        if CROSSREF_RE.fullmatch(token):
            return "validator-backed manuscript cross-reference"
        return "references.bib primary/source citation"
    if kind == "figure":
        return "generated/copied figure manifest"
    if kind == "path":
        return "local package/documentation artifact"
    if classification and classification != "actionable_literal_number":
        return f"allowlisted literal number ({classification})"
    if "%" in token or any(ch.isdigit() for ch in token):
        return "METRICS.yaml, generated JSON, or explicit source line"
    return "manual review"


def _relative_file(path: Path, manuscript_dir: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.relative_to(manuscript_dir).as_posix()


def _spans(regex: re.Pattern[str], line: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in regex.finditer(line)]


def _inside_span(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(span_start <= start and end <= span_end for span_start, span_end in spans)


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    separator_chars = set("|:- ")
    return any(ch not in separator_chars for ch in stripped)


def classify_literal_number(
    line: str,
    match: re.Match[str],
    *,
    in_code_block: bool = False,
    file: str = "",
) -> str:
    """Classify literal numbers so strict mode reports reviewable prose claims."""
    start, end = match.span()
    token = match.group(0)
    if file.endswith("S05_appendix_extended_related_work.md"):
        return "bibliography_entry"
    if in_code_block:
        return "code_block"
    if PLACEHOLDER_RE.search(line):
        return "metric_placeholder_line"
    if _inside_span(start, end, _spans(CROSSREF_RE, line) + _spans(ANCHOR_RE, line)):
        return "crossref_or_anchor"
    if "§" in line:
        return "crossref_or_anchor"
    if _inside_span(start, end, _spans(INLINE_CODE_RE, line) + _spans(MARKDOWN_LINK_RE, line)):
        return "inline_code_or_artifact_path"
    if _inside_span(start, end, _spans(MATH_RE, line)):
        return "math_notation"
    if line.count("$") == 1 and "$$" not in line:
        return "math_notation"
    if "zoo/" in line:
        return "artifact_coordinate"
    if PATH_RE.search(line) and re.search(r"\b(rank|row|field|key|line|id|orig_n_|synth_n_)\b", line):
        return "artifact_coordinate"
    if _inside_span(start, end, _spans(DATE_RE, line) + _spans(VERSION_RE, line)):
        return "date_or_version"
    if line.lstrip().startswith("![") or "width=" in line:
        return "figure_caption_or_attribute"
    if line.lstrip().startswith("#"):
        return "section_heading"
    if BIBLIOGRAPHY_ENTRY_RE.match(line):
        return "bibliography_entry"
    if _is_table_row(line):
        return "generated_table_row"
    if ORDERED_LIST_RE.match(line) and match.start() < ORDERED_LIST_RE.match(line).end():
        return "ordered_list_marker"
    if "/" in token:
        return "ratio_or_path_fragment"
    if re.search(r"\b(fewer than|more than|at least|at most|under|over)\b", line, re.IGNORECASE):
        return "threshold_phrase"
    if NUMERIC_CONTEXT_RE.search(line) or UNIT_CONTEXT_RE.search(line):
        return "metric_or_protocol_context"
    return "actionable_literal_number"


def actionable_literal_numbers(records: list[ClaimRecord]) -> list[ClaimRecord]:
    return [
        record
        for record in records
        if record.kind == "literal_number" and record.classification == "actionable_literal_number"
    ]


def build_claim_ledger(manuscript_dir: Path = MANUSCRIPT_DIR) -> list[ClaimRecord]:
    records: list[ClaimRecord] = []
    for path in sorted(manuscript_dir.glob("*.md")):
        if path.name in {"AGENTS.md", "README.md", "SYNTAX.md"}:
            continue
        rel = _relative_file(path, manuscript_dir)
        in_code_block = False
        in_math_block = False
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if FENCE_RE.match(line):
                in_code_block = not in_code_block
                continue
            if line.lstrip().startswith("$$"):
                in_math_block = not in_math_block
                continue
            if in_math_block:
                for match in NUMBER_RE.finditer(line):
                    records.append(
                        ClaimRecord(
                            file=rel,
                            line=line_no,
                            kind="literal_number",
                            text=match.group(0),
                            evidence_hint=_kind_hint(
                                "literal_number",
                                match.group(0),
                                "math_notation",
                            ),
                            classification="math_notation",
                        )
                    )
                continue
            if in_code_block:
                for match in NUMBER_RE.finditer(line):
                    classification = classify_literal_number(
                        line,
                        match,
                        in_code_block=True,
                        file=rel,
                    )
                    records.append(
                        ClaimRecord(
                            file=rel,
                            line=line_no,
                            kind="literal_number",
                            text=match.group(0),
                            evidence_hint=_kind_hint("literal_number", match.group(0), classification),
                            classification=classification,
                        )
                    )
                continue
            for regex, kind in (
                (PLACEHOLDER_RE, "placeholder"),
                (CITATION_RE, "citation"),
                (FIGURE_RE, "figure"),
                (PATH_RE, "path"),
                (NUMBER_RE, "literal_number"),
            ):
                for match in regex.finditer(line):
                    token = match.group(0)
                    if kind == "literal_number" and PLACEHOLDER_RE.search(line):
                        classification = classify_literal_number(line, match, file=rel)
                    else:
                        classification = (
                            classify_literal_number(line, match, file=rel)
                            if kind == "literal_number"
                            else kind
                        )
                    records.append(
                        ClaimRecord(
                            file=rel,
                            line=line_no,
                            kind=kind,
                            text=token,
                            evidence_hint=_kind_hint(kind, token, classification),
                            classification=classification,
                        )
                    )
    return records


def write_ledger(records: list[ClaimRecord], output_dir: Path = OUTPUT_DIR) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "record_count": len(records),
        "records": [asdict(record) for record in records],
    }
    json_path = output_dir / "claim_ledger.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    template_seed_path = write_template_evidence_claim_ledger(records, output_dir)
    md_path = output_dir / "claim_ledger.md"
    lines = [
        "# COGANT Claim Ledger",
        "",
        f"Generated records: {len(records)}",
        "",
        "| File | Line | Kind | Claim Token | Classification | Evidence Hint |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for record in records:
        token = record.text.replace("|", "\\|")
        lines.append(
            f"| `{record.file}` | {record.line} | {record.kind} | `{token}` | "
            f"{record.classification} | {record.evidence_hint} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": md_path, "template_evidence": template_seed_path}


def write_template_evidence_claim_ledger(
    records: list[ClaimRecord],
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    """Write a compatibility claim ledger for the parent template validator.

    The template evidence registry already consumes ``*claim*ledger*.json`` files
    under ``output/data``. COGANT's richer ledger lives at ``output/`` and uses a
    different row shape, so this derived seed exposes the same claims as simple
    ``{claim_id, kind, value}`` facts without changing template infrastructure.
    """

    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    claims: list[dict[str, object]] = []
    for index, record in enumerate(records, start=1):
        kind, value = _template_evidence_kind_value(record)
        if kind is None or value is None:
            continue
        claims.append(
            {
                "claim_id": f"{record.file}:{record.line}:{index}",
                "kind": kind,
                "value": value,
                "source": "COGANT claim ledger",
                "source_path": record.file,
                "source_tier": "claim_ledger",
                "freshness": "active",
            }
        )
    path = data_dir / "template_evidence_claim_ledger.json"
    payload = {
        "schema_version": "template-evidence-claim-ledger-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "claims": claims,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _template_evidence_kind_value(record: ClaimRecord) -> tuple[str | None, str | None]:
    if record.kind == "literal_number":
        return "number", record.text
    if record.kind == "citation":
        return "citation", record.text.removeprefix("@")
    if record.kind == "figure" and record.text.startswith("@fig:"):
        return "figure", record.text.removeprefix("@")
    return None, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript-dir", type=Path, default=MANUSCRIPT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--fail-on-literal-numbers",
        action="store_true",
        help=(
            "Fail if any literal numeric claims remain outside registered "
            "METRICS.yaml placeholders. This is intentionally strict and is "
            "best used after curating an allowlist or converting claims to tokens."
        ),
    )
    args = parser.parse_args(argv)

    records = build_claim_ledger(args.manuscript_dir)
    written = write_ledger(records, args.output_dir)
    if not args.quiet:
        print(f"wrote {len(records)} records")
        for path in written.values():
            print(path)
    if args.fail_on_literal_numbers:
        literal_numbers = actionable_literal_numbers(records)
        if literal_numbers:
            print(
                f"claim_ledger: {len(literal_numbers)} actionable literal numeric claim(s) require review",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
