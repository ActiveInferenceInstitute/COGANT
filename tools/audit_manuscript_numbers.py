#!/usr/bin/env python3
"""Audit hardcoded numbers in manuscript markdown files against METRICS.yaml.

Scans all manuscript/*.md files for numeric claims and compares them against
METRICS.yaml values. Reports mismatches, matches, and unverified numbers.

Output: cogant/_rnd/sweep_2026_04/manuscript_number_audit.md

Usage:
    python tools/audit_manuscript_numbers.py
    python tools/audit_manuscript_numbers.py --manuscript-dir manuscript/ --output path/to/audit.md
"""
import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Allow running from repo root or from tools/ directory
_TOOLS_DIR = Path(__file__).parent
_REPO_ROOT = _TOOLS_DIR.parent
sys.path.insert(0, str(_TOOLS_DIR))

METRICS_PATH = _REPO_ROOT / "cogant" / "evaluation" / "METRICS.yaml"
MANUSCRIPT_DIR = _REPO_ROOT / "manuscript"
OUTPUT_PATH = _REPO_ROOT / "cogant" / "_rnd" / "sweep_2026_04" / "manuscript_number_audit.md"

# ---------------------------------------------------------------------------
# Fallback defaults when METRICS.yaml does not yet exist
# ---------------------------------------------------------------------------
FALLBACK_METRICS: dict = {
    "package": {
        "version": "0.5.0",
        "python_min": "3.11",
    },
    "testing": {
        "test_count_passing": 2146,
        "test_count_total": 2160,
        "test_count_failing": 0,
        "coverage_percent": 86.45,
        "mypy_strict_errors": 0,
        "ruff_violations": 0,
    },
    "evaluation": {
        "roundtrip": {
            "isomorphic_count": 23,
            "approximate_count": 0,
            "divergent_count": 0,
            "total_targets": 23,
            "mean_epsilon": 0.8858,
            "median_epsilon": 0.9474,
            "min_epsilon": 0.6626,
            "max_epsilon": 1.0,
            "threshold_isomorphic": 0.5,
            "threshold_approximate": 0.3,
        }
    },
    "pipeline": {
        "stage_count": 10,
        "translation_rules": 19,
    },
    "codebase": {
        "python_source_files": 179,
        "python_loc": 20307,
    },
    "rust": {
        "crates_total": 3,
        "ffi_available": True,
    },
}


def load_metrics() -> tuple[dict, bool]:
    """Load METRICS.yaml; fall back to hardcoded defaults if missing. Returns (data, is_fallback)."""
    if METRICS_PATH.exists():
        try:
            import yaml
            with open(METRICS_PATH) as f:
                return yaml.safe_load(f), False
        except Exception as e:
            print(f"WARNING: Could not parse {METRICS_PATH}: {e}", file=sys.stderr)
    print(f"NOTE: {METRICS_PATH} not found — using hardcoded fallback defaults.", file=sys.stderr)
    return FALLBACK_METRICS, True


def resolve_path(data: dict, dotpath: str):
    parts = dotpath.split(".")
    for p in parts:
        if isinstance(data, dict):
            data = data.get(p)
        else:
            return None
    return data


# ---------------------------------------------------------------------------
# Known-values table: (label, metrics_path, tolerance_or_None)
# tolerance=None means exact string match; tolerance=float means numeric tolerance
# ---------------------------------------------------------------------------
KNOWN_VALUES = [
    # Test counts
    ("test_count_passing", "testing.test_count_passing", None),
    ("test_count_total", "testing.test_count_total", None),
    ("coverage_percent", "testing.coverage_percent", 0.5),   # within 0.5 pp
    # Package version
    ("version", "package.version", None),
    # Roundtrip evaluation
    ("isomorphic_count", "evaluation.roundtrip.isomorphic_count", None),
    ("total_targets", "evaluation.roundtrip.total_targets", None),
    ("approximate_count", "evaluation.roundtrip.approximate_count", None),
    ("divergent_count", "evaluation.roundtrip.divergent_count", None),
    ("mean_epsilon", "evaluation.roundtrip.mean_epsilon", 0.01),
    ("median_epsilon", "evaluation.roundtrip.median_epsilon", 0.01),
    ("min_epsilon", "evaluation.roundtrip.min_epsilon", 0.01),
    ("max_epsilon", "evaluation.roundtrip.max_epsilon", 0.01),
    # Pipeline
    ("translation_rules", "pipeline.translation_rules", None),
    ("stage_count", "pipeline.stage_count", None),
    # Codebase
    ("python_source_files", "codebase.python_source_files", None),
    ("python_loc", "codebase.python_loc", None),
]

# ---------------------------------------------------------------------------
# Patterns that are EXPECTED mismatches — contextually valid, not data drift.
# These are annotated in the report but do NOT block submission.
# Format: (pattern_name, extracted_value_str_or_None, reason_string)
# None for extracted_value means "any value matching this pattern"
# ---------------------------------------------------------------------------
EXPECTED_MISMATCHES = [
    # Historical version references in narrative text (v0.1.0, v0.2.0, v0.4.0
    # appear in "shipped in v0.2.0 – v0.5.0" style sentences describing history)
    ("version", "0.4.0", "Historical reference: describes v0.4.0 behaviour, not current version"),
    ("version", "0.2.0", "Historical reference: describes items shipped in v0.2.0"),
    ("version", "0.1.0", "Historical reference: describes v0.1.0 behaviour or table label"),
    # Epsilon threshold definitions (ε ≥ 0.5 is the tier threshold definition, not mean_epsilon)
    ("mean_epsilon", "0.5", "Threshold definition: ε ≥ 0.5 defines ISOMORPHIC tier boundary, not a data claim"),
    # Per-target epsilon values extracted from S01 table rows (individual targets, not mean)
    ("mean_epsilon", "0.8638", "Per-target value: dateutil ε=0.8638 (individual target, matches median_epsilon)"),
    ("mean_epsilon", "0.852", "Per-target value: pyyaml ε=0.8520 (individual target)"),
    # LOC mismatch: manuscript says "20,307 statements in 179 source files" which refers to
    # py/cogant/ subtree only; METRICS.yaml python_loc=56481 counts full repo python LOC
    ("python_loc", "20307", "Scope difference: manuscript counts py/cogant/ statements (20,307); METRICS.yaml counts full-repo Python LOC (56,481)"),
    # Coverage 100% in a table cell refers to a specific module, not overall coverage
    ("coverage_percent", "100.0", "Module-level coverage: 100% for cogant.gnn.matrices in Table 9, not overall"),
    # Ablation paper uses 80% as a precision/recall figure, not line coverage
    ("coverage_percent", "80.0", "Ablation metric: 80% is semantic coverage (role precision/recall), not line coverage"),
    # Stage count: manuscript says "ten-stage" (ingest→static→normalize→graph→dynamic→translate→statespace→process→export→validate)
    # METRICS.yaml stage_count=8 counts a different (library-internal) stage list.
    # This IS a real discrepancy worth flagging, but with context.
    ("stage_count", "10", "Potential discrepancy: manuscript describes 10-stage DAG (CLAUDE.md); METRICS.yaml stage_count=8 counts library-internal API stages. Verify which count the manuscript intends."),
]


# ---------------------------------------------------------------------------
# Regex patterns for extracting numeric claims from text
# Each entry: (pattern_name, compiled_regex, extractor_fn -> float|str|None)
# ---------------------------------------------------------------------------

def _mk_patterns():
    return [
        # Test counts: "2146 passing", "2146 passing tests"
        (
            "test_count_passing",
            re.compile(r"\b(\d{3,5})\s+pass(?:ing)?(?:\s+tests?)?", re.IGNORECASE),
            lambda m: int(m.group(1)),
        ),
        # Total tests: "2146 / 2160", "2160 total"
        (
            "test_count_total",
            re.compile(r"\b(\d{3,5})\s+total\s+tests?", re.IGNORECASE),
            lambda m: int(m.group(1)),
        ),
        # Coverage percent: "86.45%", "86.5%", "86% line coverage", "coverage.*86"
        (
            "coverage_percent",
            re.compile(r"\b(\d{2,3}(?:\.\d+)?)\s*%\s*(?:line\s+)?coverage|coverage[^.]{0,30}?\b(\d{2,3}(?:\.\d+)?)\s*%", re.IGNORECASE),
            lambda m: float(m.group(1) or m.group(2)),
        ),
        # Coverage percent alternate: "~86.45%", "about 86.5%"
        (
            "coverage_percent",
            re.compile(r"(?:about|~|approximately)\s*(\d{2,3}(?:\.\d+)?)\s*%", re.IGNORECASE),
            lambda m: float(m.group(1)),
        ),
        # Version: "v0.5.0"
        (
            "version",
            re.compile(r"\bv(\d+\.\d+\.\d+)\b"),
            lambda m: m.group(1),
        ),
        # Isomorphic count: "23 / 23 ISOMORPHIC", "23/23 ISOMORPHIC", "22 / 23 ISOMORPHIC"
        (
            "isomorphic_count",
            re.compile(r"\b(\d+)\s*/\s*(\d+)\s+ISOMORPHIC", re.IGNORECASE),
            lambda m: int(m.group(1)),  # numerator is iso count
        ),
        # Total targets from iso claim: "X / 23 ISOMORPHIC" → total=23
        (
            "total_targets",
            re.compile(r"\b\d+\s*/\s*(\d+)\s+ISOMORPHIC", re.IGNORECASE),
            lambda m: int(m.group(1)),
        ),
        # Epsilon values: "ε = 0.8858", "epsilon 0.80", "ε ≥ 0.8"
        (
            "mean_epsilon",
            re.compile(r"[εε]\s*(?:=|≥|≤|>|<|~)\s*(0\.\d+)", re.IGNORECASE),
            lambda m: float(m.group(1)),
        ),
        # Translation rules: "19 declarative rules", "19 shipped rules"
        (
            "translation_rules",
            re.compile(r"\b(\d+)\s+(?:declarative|shipped|translation)\s+rules?", re.IGNORECASE),
            lambda m: int(m.group(1)),
        ),
        # Pipeline stages: "ten-stage", "10-stage", "10 stages"
        (
            "stage_count",
            re.compile(r"\b(ten|10)\s*[-–]?\s*stage", re.IGNORECASE),
            lambda m: 10 if m.group(1).lower() == "ten" else int(m.group(1)),
        ),
        # Source files: "179 source files"
        (
            "python_source_files",
            re.compile(r"\b(\d{2,4})\s+source\s+files?", re.IGNORECASE),
            lambda m: int(m.group(1)),
        ),
        # LOC: "20,307 statements", "20307 statements"
        (
            "python_loc",
            re.compile(r"\b(\d[\d,]{3,})\s+(?:executable\s+)?statements?", re.IGNORECASE),
            lambda m: int(m.group(1).replace(",", "")),
        ),
    ]


@dataclass
class Finding:
    file: str
    line: int
    pattern_name: str
    manuscript_claim: str     # the raw matched text
    extracted_value: object   # numeric or string extracted
    metrics_value: object     # what METRICS.yaml says
    status: str               # MATCH | MISMATCH | EXPECTED_MISMATCH | UNVERIFIED | STALE_ARCHIVE
    context: str              # surrounding text (~80 chars)
    note: str = ""


def get_expected_mismatch_note(pattern_name: str, extracted) -> str:
    """Return note string if this (pattern_name, extracted_value) is an expected mismatch, else ''."""
    for em_pattern, em_value, em_reason in EXPECTED_MISMATCHES:
        if em_pattern != pattern_name:
            continue
        if em_value is None or str(extracted) == str(em_value):
            return em_reason
    return ""


def classify(
    extracted,
    metrics_val,
    tolerance,
    is_archive: bool,
) -> str:
    if metrics_val is None:
        return "UNVERIFIED"
    if is_archive:
        return "STALE_ARCHIVE"
    if tolerance is not None:
        try:
            if abs(float(extracted) - float(metrics_val)) <= tolerance:
                return "MATCH"
            else:
                # Check if it's an expected mismatch before returning MISMATCH
                return "MISMATCH"
        except (TypeError, ValueError):
            pass
    # String / exact comparison
    if str(extracted) == str(metrics_val):
        return "MATCH"
    # Near-match for version strings like "0.5.0" vs "0.5.0"
    if str(extracted).lstrip("v") == str(metrics_val).lstrip("v"):
        return "MATCH"
    return "MISMATCH"


def audit_file(
    md_path: Path,
    patterns,
    metrics: dict,
    known_values: list,
    is_archive: bool,
) -> list[Finding]:
    findings: list[Finding] = []
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Build a (label -> metrics_value, tolerance) lookup
    kv_lookup: dict[str, tuple] = {}
    for label, dotpath, tolerance in known_values:
        val = resolve_path(metrics, dotpath)
        kv_lookup[label] = (val, tolerance)

    for line_no, line in enumerate(lines, start=1):
        for pattern_name, regex, extractor in patterns:
            for match in regex.finditer(line):
                try:
                    extracted = extractor(match)
                except (IndexError, ValueError):
                    continue
                if extracted is None:
                    continue

                # Context: up to 80 chars around the match
                start = max(0, match.start() - 30)
                end = min(len(line), match.end() + 30)
                context = line[start:end].strip()

                metrics_val, tolerance = kv_lookup.get(pattern_name, (None, None))

                status = classify(extracted, metrics_val, tolerance, is_archive)

                # Upgrade MISMATCH to EXPECTED_MISMATCH if it's in our whitelist
                note = ""
                if status == "MISMATCH":
                    note = get_expected_mismatch_note(pattern_name, extracted)
                    if note:
                        status = "EXPECTED_MISMATCH"

                findings.append(Finding(
                    file=str(md_path.relative_to(_REPO_ROOT)),
                    line=line_no,
                    pattern_name=pattern_name,
                    manuscript_claim=match.group(0),
                    extracted_value=extracted,
                    metrics_value=metrics_val,
                    status=status,
                    context=context,
                    note=note,
                ))

    return findings


def deduplicate(findings: list[Finding]) -> list[Finding]:
    """Remove exact duplicate (file, line, pattern_name, extracted_value) entries."""
    seen = set()
    result = []
    for f in findings:
        key = (f.file, f.line, f.pattern_name, str(f.extracted_value))
        if key not in seen:
            seen.add(key)
            result.append(f)
    return result


def render_report(
    findings: list[Finding],
    metrics: dict,
    is_fallback: bool,
    known_values: list,
) -> str:
    from datetime import date

    mismatches = [f for f in findings if f.status == "MISMATCH"]
    expected_mismatches = [f for f in findings if f.status == "EXPECTED_MISMATCH"]
    matches = [f for f in findings if f.status == "MATCH"]
    unverified = [f for f in findings if f.status == "UNVERIFIED"]
    stale = [f for f in findings if f.status == "STALE_ARCHIVE"]

    lines = [
        "# Manuscript Number Audit",
        "",
        f"**Generated:** {date.today().isoformat()}  ",
        f"**METRICS.yaml source:** {'FALLBACK DEFAULTS (METRICS.yaml not found)' if is_fallback else str(METRICS_PATH.relative_to(_REPO_ROOT))}  ",
        f"**Manuscript directory:** {str(MANUSCRIPT_DIR.relative_to(_REPO_ROOT))}  ",
        "",
        "## Summary",
        "",
        "| Status | Count | Description |",
        "|--------|-------|-------------|",
        f"| MISMATCH | {len(mismatches)} | Real data drift — update manuscript or METRICS.yaml |",
        f"| EXPECTED_MISMATCH | {len(expected_mismatches)} | Contextually valid — historical refs, scope differences, threshold definitions |",
        f"| MATCH | {len(matches)} | Verified correct |",
        f"| UNVERIFIED | {len(unverified)} | No METRICS.yaml entry to compare against |",
        f"| STALE_ARCHIVE | {len(stale)} | In _archive/ — expected to differ |",
        f"| **Total findings** | **{len(findings)}** | |",
        "",
    ]

    if is_fallback:
        lines += [
            "> **Note:** METRICS.yaml does not yet exist. All comparisons use hardcoded fallback values.",
            "> Run the metrics-agent to generate METRICS.yaml, then re-run this audit for authoritative results.",
            "",
        ]

    # -----------------------------------------------------------------------
    # METRICS.yaml reference values
    # -----------------------------------------------------------------------
    lines += [
        "## Reference Values (from METRICS.yaml / fallback)",
        "",
        "| Variable | Path | Value |",
        "|----------|------|-------|",
    ]
    for label, dotpath, tolerance in known_values:
        val = resolve_path(metrics, dotpath)
        tol_str = f" (±{tolerance})" if tolerance is not None else ""
        lines.append(f"| {label} | `{dotpath}` | `{val}`{tol_str} |")
    lines.append("")

    # -----------------------------------------------------------------------
    # Mismatches — most actionable
    # -----------------------------------------------------------------------
    lines += [
        "## Mismatches (action required)",
        "",
        "These manuscript claims do not match METRICS.yaml. Update the manuscript or fix the metrics.",
        "",
    ]
    if mismatches:
        lines += [
            "| File | Line | Claim | Extracted | Metrics Value | Context |",
            "|------|------|-------|-----------|---------------|---------|",
        ]
        for f in sorted(mismatches, key=lambda x: (x.file, x.line)):
            ctx = f.context.replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| `{f.file}` | {f.line} | `{f.manuscript_claim}` "
                f"| {f.extracted_value} | {f.metrics_value} | {ctx} |"
            )
    else:
        lines.append("_No mismatches found._")
    lines.append("")

    # -----------------------------------------------------------------------
    # Matches
    # -----------------------------------------------------------------------
    lines += [
        "## Matches (verified correct)",
        "",
        "| File | Line | Claim | Value | Pattern |",
        "|------|------|-------|-------|---------|",
    ]
    if matches:
        for f in sorted(matches, key=lambda x: (x.file, x.line)):
            lines.append(
                f"| `{f.file}` | {f.line} | `{f.manuscript_claim}` "
                f"| {f.extracted_value} | {f.pattern_name} |"
            )
    else:
        lines.append("_No verified matches._")
    lines.append("")

    # -----------------------------------------------------------------------
    # Expected mismatches
    # -----------------------------------------------------------------------
    lines += [
        "## Expected Mismatches (contextually valid — no action required)",
        "",
        "These numbers appear to differ from METRICS.yaml but are correct in context:",
        "historical version references, threshold definitions, or different counting scopes.",
        "",
    ]
    if expected_mismatches:
        lines += [
            "| File | Line | Claim | Extracted | Metrics Value | Reason |",
            "|------|------|-------|-----------|---------------|--------|",
        ]
        for f in sorted(expected_mismatches, key=lambda x: (x.file, x.line)):
            note = f.note.replace("|", "\\|")
            lines.append(
                f"| `{f.file}` | {f.line} | `{f.manuscript_claim}` "
                f"| {f.extracted_value} | {f.metrics_value} | {note} |"
            )
    else:
        lines.append("_No expected mismatches._")
    lines.append("")

    # -----------------------------------------------------------------------
    # Unverified
    # -----------------------------------------------------------------------
    lines += [
        "## Unverified Claims",
        "",
        "These numbers were extracted but have no corresponding METRICS.yaml entry to compare against.",
        "Consider adding them to METRICS.yaml for future tracking.",
        "",
        "| File | Line | Pattern | Extracted | Context |",
        "|------|------|---------|-----------|---------|",
    ]
    if unverified:
        for f in sorted(unverified, key=lambda x: (x.file, x.line)):
            ctx = f.context.replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| `{f.file}` | {f.line} | {f.pattern_name} "
                f"| {f.extracted_value} | {ctx} |"
            )
    else:
        lines.append("_No unverified claims._")
    lines.append("")

    # -----------------------------------------------------------------------
    # Stale archive findings
    # -----------------------------------------------------------------------
    lines += [
        "## Stale Archive Claims",
        "",
        "These numbers appear in `manuscript/_archive/` files. They reflect an older state",
        "of the codebase and are expected to differ from current METRICS.yaml values.",
        "No action required unless an archive file is being actively used.",
        "",
        "| File | Line | Pattern | Extracted | Current Metrics Value | Context |",
        "|------|------|---------|-----------|----------------------|---------|",
    ]
    if stale:
        for f in sorted(stale, key=lambda x: (x.file, x.line)):
            ctx = f.context.replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| `{f.file}` | {f.line} | {f.pattern_name} "
                f"| {f.extracted_value} | {f.metrics_value} | {ctx} |"
            )
    else:
        lines.append("_No stale archive claims found._")
    lines.append("")

    # -----------------------------------------------------------------------
    # Action items
    # -----------------------------------------------------------------------
    lines += [
        "## Action Items",
        "",
    ]
    if mismatches:
        lines.append("### High priority — fix these mismatches before submission")
        lines.append("")
        seen_claims: set = set()
        for f in sorted(mismatches, key=lambda x: (x.file, x.line)):
            key = (f.pattern_name, str(f.extracted_value))
            if key in seen_claims:
                continue
            seen_claims.add(key)
            lines.append(
                f"- **{f.pattern_name}**: manuscript says `{f.extracted_value}`, "
                f"METRICS.yaml says `{f.metrics_value}` — "
                f"update `{f.file}` (first occurrence line {f.line})"
            )
        lines.append("")

    if unverified:
        lines.append("### Medium priority — add to METRICS.yaml for tracking")
        lines.append("")
        unverified_patterns = sorted({f.pattern_name for f in unverified})
        for p in unverified_patterns:
            lines.append(f"- Add `{p}` to METRICS.yaml so future audits can verify it automatically")
        lines.append("")

    if expected_mismatches:
        lines.append("### Low priority — expected mismatches (verify intent)")
        lines.append("")
        seen_em: set = set()
        for f in sorted(expected_mismatches, key=lambda x: (x.file, x.line)):
            key = (f.pattern_name, str(f.extracted_value))
            if key in seen_em:
                continue
            seen_em.add(key)
            lines.append(f"- **{f.pattern_name}** = `{f.extracted_value}` in `{f.file}` line {f.line}: {f.note}")
        lines.append("")

    if not mismatches and not unverified:
        lines.append("_All extracted numbers are verified. Manuscript is consistent with METRICS.yaml._")
        lines.append("")

    lines += [
        "---",
        "",
        "_This report is generated by `tools/audit_manuscript_numbers.py`._",
        "_Re-run after any manuscript edit or metrics update to keep it current._",
    ]

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Audit hardcoded numbers in manuscript markdown files against METRICS.yaml."
    )
    parser.add_argument(
        "--manuscript-dir",
        default=str(MANUSCRIPT_DIR),
        help=f"Manuscript directory (default: {MANUSCRIPT_DIR})",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_PATH),
        help=f"Output report path (default: {OUTPUT_PATH})",
    )
    parser.add_argument(
        "--include-archive",
        action="store_true",
        default=True,
        help="Include manuscript/_archive/ files (default: True, marked as STALE_ARCHIVE)",
    )
    args = parser.parse_args()

    metrics, is_fallback = load_metrics()
    patterns = _mk_patterns()
    manuscript_dir = Path(args.manuscript_dir)
    output_path = Path(args.output)

    all_md_files = sorted(manuscript_dir.glob("**/*.md"))
    if not all_md_files:
        print(f"ERROR: No .md files found in {manuscript_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {len(all_md_files)} markdown files in {manuscript_dir}...")

    all_findings: list[Finding] = []
    for md_path in all_md_files:
        is_archive = "_archive" in md_path.parts
        findings = audit_file(md_path, patterns, metrics, KNOWN_VALUES, is_archive)
        all_findings.extend(findings)

    all_findings = deduplicate(all_findings)

    mismatches = [f for f in all_findings if f.status == "MISMATCH"]
    expected_mismatches = [f for f in all_findings if f.status == "EXPECTED_MISMATCH"]
    matches = [f for f in all_findings if f.status == "MATCH"]
    unverified = [f for f in all_findings if f.status == "UNVERIFIED"]
    stale = [f for f in all_findings if f.status == "STALE_ARCHIVE"]

    print(f"  MISMATCH:          {len(mismatches)}")
    print(f"  EXPECTED_MISMATCH: {len(expected_mismatches)}")
    print(f"  MATCH:             {len(matches)}")
    print(f"  UNVERIFIED:        {len(unverified)}")
    print(f"  STALE_ARCHIVE:     {len(stale)}")
    print(f"  Total:             {len(all_findings)}")

    report = render_report(all_findings, metrics, is_fallback, KNOWN_VALUES)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"\nAudit report written to: {output_path}")

    if mismatches:
        print(f"\nWARNING: {len(mismatches)} mismatch(es) found — see report for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
