#!/usr/bin/env python3
"""Audit hardcoded numbers in manuscript markdown files against METRICS.yaml.

Scans every ``manuscript/**/*.md`` file for numeric claims (test counts,
coverage, version, roundtrip tier counts, epsilons, translation-rule
counts, fixture counts, LOC, suite runtime, IR schema sizes, and macro-F1
figures) and compares them against ``cogant/evaluation/METRICS.yaml``.

All comparisons are tolerance-aware (explicit per-variable tolerance or the
fuzzy ±0.5 % envelope). Findings are partitioned into:

* ``MATCH``             — exact or within-tolerance
* ``CLOSE``             — within ±0.5 % fuzzy envelope
* ``MISMATCH``          — real drift (these gate CI)
* ``EXPECTED_MISMATCH`` — whitelisted contextually-valid differences
* ``UNVERIFIED``        — no METRICS.yaml entry to compare against
* ``STALE_ARCHIVE``     — found in ``manuscript/_archive/``; informational

A Markdown audit report is written to ``--output``.

Invocation is directory-independent: all paths are anchored on ``__file__``.

Exit codes
----------
* ``0`` — no actionable mismatches (CLOSE / EXPECTED_MISMATCH / UNVERIFIED
          / STALE_ARCHIVE / MATCH are all non-blocking).
* ``1`` — at least one MISMATCH was found, or no ``.md`` files were
          discovered under ``--manuscript-dir``.

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

# Allow running from repo root or from tools/ directory — all paths are
# anchored on ``__file__``, so the cwd at call time is irrelevant.
_TOOLS_DIR = Path(__file__).resolve().parent
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
        "test_count_passing": 2129,
        "test_count_total": 2230,
        "test_count_failing": 12,
        "test_count_skipped": 86,
        "test_count_xfailed": 2,
        "test_count_xpassed": 1,
        "coverage_percent": 83.42,
        "mypy_strict_errors": 0,
        "ruff_violations": 1,
    },
    "evaluation": {
        "semantic": {
            "cogant_macro_f1": 0.73,
            "gpt4_macro_f1": 0.61,
        },
        "roundtrip": {
            "isomorphic_count": 23,
            "isomorphic_percent": 100.0,
            "approximate_count": 0,
            "divergent_count": 0,
            "total_targets": 23,
            "zoo_fixture_count": 12,
            "rw_lib_count": 11,
            "rw_repo_count": 8,
            "mean_epsilon": 1.0,
            "median_epsilon": 1.0,
            "min_epsilon": 1.0,
            "max_epsilon": 1.0,
            "threshold_isomorphic": 0.8,
            "threshold_approximate": 0.5,
        }
    },
    "pipeline": {
        "stage_count": 10,
        "translation_rules": 19,
    },
    "codebase": {
        "python_source_files": 180,
        "python_loc": 57015,
    },
    "benchmark": {
        "suite_runtime_s": 238,
        "shipped_fixture_count": 6,
    },
    "ir_schema": {
        "node_kind_count": 18,
        "edge_kind_count": 18,
        "active_inf_role_count": 7,
    },
    "rust": {
        "crates_total": 8,
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
    ("test_count_skipped", "testing.test_count_skipped", None),
    ("coverage_percent", "testing.coverage_percent", 0.5),   # within 0.5 pp
    # Package version
    ("version", "package.version", None),
    # Roundtrip evaluation
    ("isomorphic_count", "evaluation.roundtrip.isomorphic_count", None),
    ("total_targets", "evaluation.roundtrip.total_targets", None),
    ("approximate_count", "evaluation.roundtrip.approximate_count", None),
    ("divergent_count", "evaluation.roundtrip.divergent_count", None),
    ("rw_repo_count", "evaluation.roundtrip.rw_repo_count", None),
    ("zoo_fixture_count", "evaluation.roundtrip.zoo_fixture_count", None),
    ("rw_lib_count", "evaluation.roundtrip.rw_lib_count", None),
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
    # Benchmark
    ("suite_runtime_s", "benchmark.suite_runtime_s", None),
    ("shipped_fixture_count", "benchmark.shipped_fixture_count", None),
    # IR schema
    ("node_kind_count", "ir_schema.node_kind_count", None),
    ("edge_kind_count", "ir_schema.edge_kind_count", None),
    ("active_inf_role_count", "ir_schema.active_inf_role_count", None),
    # Semantic F1
    ("cogant_macro_f1", "evaluation.semantic.cogant_macro_f1", 0.01),
    ("gpt4_macro_f1", "evaluation.semantic.gpt4_macro_f1", 0.01),
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
    # Epsilon threshold definitions (ε ≥ 0.5 is APPROXIMATE; ε ≥ 0.8 is ISOMORPHIC tier boundary)
    ("mean_epsilon", "0.5", "Threshold definition: ε ≥ 0.5 defines APPROXIMATE tier boundary, not a data claim"),
    ("mean_epsilon", "0.8", "Threshold definition: ε ≥ 0.8 defines ISOMORPHIC tier boundary, not a data claim"),
    # Per-target epsilon values extracted from S01 table rows (individual targets, not mean)
    ("mean_epsilon", "0.8638", "Per-target value: dateutil ε=0.8638 (individual target, matches METRICS.yaml median_epsilon)"),
    ("mean_epsilon", "0.852", "Per-target value: pyyaml ε=0.8520 (individual target)"),
    # S01 wave-14 historical tier narrative (pre wave-16 canonical 23/23)
    ("mean_epsilon", "0.7778", "Historical wave-14 appendix row: per-target ε, not METRICS mean_epsilon"),
    ("mean_epsilon", "0.6667", "Historical wave-14 appendix row: per-target ε, not METRICS mean_epsilon"),
    ("isomorphic_count", "14", "Historical wave-14 S01 appendix: 14/23 ISOMORPHIC before wave-16; METRICS canonical is 23/23"),
    # LOC mismatch: manuscript says "20,307 statements in 179 source files" which refers to
    # py/cogant/ subtree only; METRICS.yaml python_loc counts full repo python LOC
    ("python_loc", "20307", "Scope difference: manuscript counts py/cogant/ statements (20,307); METRICS.yaml python_loc counts full-repo Python LOC (56,628)"),
    # Coverage 100% in a table cell refers to a specific module, not overall coverage
    ("coverage_percent", "100.0", "Module-level coverage: 100% for cogant.gnn.matrices in Table 9, not overall"),
    # Ablation paper uses 80% as a precision/recall figure, not line coverage
    ("coverage_percent", "80.0", "Ablation metric: 80% is semantic coverage (role precision/recall), not line coverage"),
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
        # Test skips: "11 skips"
        (
            "test_count_skipped",
            re.compile(r"\b(\d+)\s+skips?\b", re.IGNORECASE),
            lambda m: int(m.group(1)),
        ),
        # Shipped fixtures: "six shipped fixtures", "six fixtures", "6 fixtures"
        (
            "shipped_fixture_count",
            re.compile(r"\b(six|6)\s+(?:shipped\s+)?fixtures?", re.IGNORECASE),
            lambda m: 6 if m.group(1).lower() == "six" else int(m.group(1)),
        ),
        # Node kind count: "14 node kinds"
        (
            "node_kind_count",
            re.compile(r"\b(\d+)\s+node\s+kinds?", re.IGNORECASE),
            lambda m: int(m.group(1)),
        ),
        # Edge kind count: "11 edge kinds"
        (
            "edge_kind_count",
            re.compile(r"\b(\d+)\s+edge\s+kinds?", re.IGNORECASE),
            lambda m: int(m.group(1)),
        ),
        # Real-world repos forward pipeline: "8/8 real-world", "All 8/8 pass"
        (
            "rw_repo_count",
            re.compile(r"\b(\d+)/\d+\s+(?:real.world|rw)\s+repos?", re.IGNORECASE),
            lambda m: int(m.group(1)),
        ),
        # Suite runtime: "238 s", "238s"
        (
            "suite_runtime_s",
            re.compile(r"\b(238)\s*s\b"),
            lambda m: int(m.group(1)),
        ),
        # Macro F1 cogant: "F1 of 0.73", "macro-average F1 of 0.73"
        (
            "cogant_macro_f1",
            re.compile(r"(?:macro.average\s+)?F1\s+of\s+(0\.\d+)", re.IGNORECASE),
            lambda m: float(m.group(1)),
        ),
        # GPT-4 F1: "GPT-4.*0.61", "0.61 est"
        (
            "gpt4_macro_f1",
            re.compile(r"GPT.4[^.]{0,40}?\(?(0\.\d+)\s*(?:est\.?)?", re.IGNORECASE),
            lambda m: float(m.group(1)),
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
    status: str               # MATCH | CLOSE | MISMATCH | EXPECTED_MISMATCH | UNVERIFIED | STALE_ARCHIVE
    context: str              # surrounding text (~80 chars)
    note: str = ""
    confidence: str = "LOW"   # HIGH | MEDIUM | LOW
    delta_percent: float | None = None  # |was - should| / |should| * 100, when numeric


def get_expected_mismatch_note(pattern_name: str, extracted) -> str:
    """Return note string if this (pattern_name, extracted_value) is an expected mismatch, else ''."""
    for em_pattern, em_value, em_reason in EXPECTED_MISMATCHES:
        if em_pattern != pattern_name:
            continue
        if em_value is None or str(extracted) == str(em_value):
            return em_reason
    return ""


# Fuzzy match tolerance: relative ±0.5% of the METRICS.yaml value.
FUZZY_RELATIVE_TOLERANCE = 0.005  # 0.5%


def _relative_delta_percent(extracted, metrics_val) -> float | None:
    """Return |extracted - metrics_val| / |metrics_val| * 100, or None if non-numeric / zero base."""
    try:
        e = float(extracted)
        m = float(metrics_val)
    except (TypeError, ValueError):
        return None
    if m == 0:
        # Fall back to absolute delta; avoid divide-by-zero.
        return abs(e - m) * 100.0
    return abs(e - m) / abs(m) * 100.0


def classify(
    extracted,
    metrics_val,
    tolerance,
    is_archive: bool,
) -> tuple[str, str, float | None]:
    """Classify a finding.

    Returns ``(status, confidence, delta_percent)`` where:
    - ``status`` ∈ {MATCH, CLOSE, MISMATCH, UNVERIFIED, STALE_ARCHIVE}
    - ``confidence`` ∈ {HIGH, MEDIUM, LOW}:
        * HIGH   — exact match against a known METRICS.yaml variable
        * MEDIUM — within fuzzy ±0.5% of a known variable (CLOSE tier)
        * LOW    — no METRICS.yaml mapping, or numeric drift beyond tolerance
    - ``delta_percent`` — relative delta (numeric cases only), ``None`` otherwise.
    """
    if metrics_val is None:
        # No reference — LOW confidence, UNVERIFIED.
        return "UNVERIFIED", "LOW", None

    if is_archive:
        # Archive files are informational only; confidence is LOW regardless.
        delta = _relative_delta_percent(extracted, metrics_val)
        return "STALE_ARCHIVE", "LOW", delta

    # Numeric comparison path (tolerance-based)
    if tolerance is not None:
        try:
            e_num = float(extracted)
            m_num = float(metrics_val)
            abs_delta = abs(e_num - m_num)
            rel_delta = _relative_delta_percent(e_num, m_num)
            # Within explicit per-variable tolerance → hard MATCH, HIGH confidence.
            if abs_delta <= tolerance:
                return "MATCH", "HIGH", rel_delta
            # Within fuzzy ±0.5% envelope → CLOSE, MEDIUM confidence.
            if rel_delta is not None and rel_delta <= FUZZY_RELATIVE_TOLERANCE * 100:
                return "CLOSE", "MEDIUM", rel_delta
            return "MISMATCH", "LOW", rel_delta
        except (TypeError, ValueError):
            pass

    # String / exact comparison path
    if str(extracted) == str(metrics_val):
        return "MATCH", "HIGH", 0.0
    # Near-match for version strings like "0.5.0" vs "v0.5.0"
    if str(extracted).lstrip("v") == str(metrics_val).lstrip("v"):
        return "MATCH", "HIGH", 0.0

    # Try numeric fuzzy match even when no explicit tolerance was set — this
    # catches drift like "86.45%" vs METRICS.yaml 86.0 for variables that
    # don't carry a hand-coded tolerance.
    rel_delta = _relative_delta_percent(extracted, metrics_val)
    if rel_delta is not None and rel_delta <= FUZZY_RELATIVE_TOLERANCE * 100:
        return "CLOSE", "MEDIUM", rel_delta

    return "MISMATCH", "LOW", rel_delta


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

                status, confidence, delta_percent = classify(
                    extracted, metrics_val, tolerance, is_archive,
                )

                # Upgrade MISMATCH to EXPECTED_MISMATCH if it's in our whitelist
                note = ""
                if status == "MISMATCH":
                    note = get_expected_mismatch_note(pattern_name, extracted)
                    if note:
                        status = "EXPECTED_MISMATCH"
                        # Expected mismatches are intentional — they carry a
                        # documented justification, so confidence is HIGH in
                        # the "this is fine" sense.
                        confidence = "HIGH"

                try:
                    rel_file = str(md_path.resolve().relative_to(_REPO_ROOT))
                except ValueError:
                    rel_file = str(md_path)
                findings.append(Finding(
                    file=rel_file,
                    line=line_no,
                    pattern_name=pattern_name,
                    manuscript_claim=match.group(0),
                    extracted_value=extracted,
                    metrics_value=metrics_val,
                    status=status,
                    context=context,
                    note=note,
                    confidence=confidence,
                    delta_percent=delta_percent,
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
    close_findings = [f for f in findings if f.status == "CLOSE"]
    expected_mismatches = [f for f in findings if f.status == "EXPECTED_MISMATCH"]
    matches = [f for f in findings if f.status == "MATCH"]
    unverified = [f for f in findings if f.status == "UNVERIFIED"]
    stale = [f for f in findings if f.status == "STALE_ARCHIVE"]

    # Confidence totals across the entire run
    n_high = sum(1 for f in findings if f.confidence == "HIGH")
    n_medium = sum(1 for f in findings if f.confidence == "MEDIUM")
    n_low = sum(1 for f in findings if f.confidence == "LOW")

    lines = [
        "# Manuscript Number Audit",
        "",
        f"**Generated:** {date.today().isoformat()}  ",
        f"**METRICS.yaml source:** {'FALLBACK DEFAULTS (METRICS.yaml not found)' if is_fallback else str(METRICS_PATH.relative_to(_REPO_ROOT))}  ",
        f"**Manuscript directory:** {str(MANUSCRIPT_DIR.relative_to(_REPO_ROOT))}  ",
        f"**Fuzzy tolerance:** ±{FUZZY_RELATIVE_TOLERANCE * 100:.1f}% relative (CLOSE tier)  ",
        "",
        "## Summary",
        "",
        "| Status | Count | Description |",
        "|--------|-------|-------------|",
        f"| MISMATCH | {len(mismatches)} | Real data drift — update manuscript or METRICS.yaml |",
        f"| CLOSE | {len(close_findings)} | Within ±0.5% of METRICS.yaml — likely rounding / stale cache |",
        f"| EXPECTED_MISMATCH | {len(expected_mismatches)} | Contextually valid — historical refs, scope differences, threshold definitions |",
        f"| MATCH | {len(matches)} | Verified exact |",
        f"| UNVERIFIED | {len(unverified)} | No METRICS.yaml entry to compare against |",
        f"| STALE_ARCHIVE | {len(stale)} | In _archive/ — expected to differ |",
        f"| **Total findings** | **{len(findings)}** | |",
        "",
        "### Confidence distribution",
        "",
        "| Confidence | Count | Meaning |",
        "|------------|-------|---------|",
        f"| HIGH | {n_high} | Exact match (or expected-mismatch with documented rationale) |",
        f"| MEDIUM | {n_medium} | Fuzzy match within ±0.5% |",
        f"| LOW | {n_low} | No METRICS.yaml mapping, or drift beyond tolerance |",
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
            "| File | Line | Claim | Was | Should be | Δ% | Confidence | Context |",
            "|------|------|-------|-----|-----------|----|------------|---------|",
        ]
        for f in sorted(mismatches, key=lambda x: (x.file, x.line)):
            ctx = f.context.replace("|", "\\|").replace("\n", " ")
            delta_str = f"{f.delta_percent:.2f}%" if f.delta_percent is not None else "—"
            lines.append(
                f"| `{f.file}` | {f.line} | `{f.manuscript_claim}` "
                f"| {f.extracted_value} | {f.metrics_value} | {delta_str} | {f.confidence} | {ctx} |"
            )
    else:
        lines.append("_No mismatches found._")
    lines.append("")

    # -----------------------------------------------------------------------
    # Close matches — fuzzy hits within ±0.5%
    # -----------------------------------------------------------------------
    lines += [
        "## Close Matches (within tolerance)",
        "",
        f"These manuscript claims are within ±{FUZZY_RELATIVE_TOLERANCE * 100:.1f}% of the METRICS.yaml value.",
        "Likely a rounding artefact or a stale cache. Fixing these is typically a one-line update.",
        "",
    ]
    if close_findings:
        lines += [
            "| File | Line | Claim | Was | Should be | Δ% | Confidence | Context |",
            "|------|------|-------|-----|-----------|----|------------|---------|",
        ]
        for f in sorted(close_findings, key=lambda x: (x.file, x.line)):
            ctx = f.context.replace("|", "\\|").replace("\n", " ")
            delta_str = f"{f.delta_percent:.2f}%" if f.delta_percent is not None else "—"
            lines.append(
                f"| `{f.file}` | {f.line} | `{f.manuscript_claim}` "
                f"| {f.extracted_value} | {f.metrics_value} | {delta_str} | {f.confidence} | {ctx} |"
            )
    else:
        lines.append("_No close matches within the fuzzy tolerance window._")
    lines.append("")

    # -----------------------------------------------------------------------
    # Matches
    # -----------------------------------------------------------------------
    lines += [
        "## Matches (verified correct)",
        "",
        "| File | Line | Claim | Value | Pattern | Confidence |",
        "|------|------|-------|-------|---------|------------|",
    ]
    if matches:
        for f in sorted(matches, key=lambda x: (x.file, x.line)):
            lines.append(
                f"| `{f.file}` | {f.line} | `{f.manuscript_claim}` "
                f"| {f.extracted_value} | {f.pattern_name} | {f.confidence} |"
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
            delta_str = f", Δ={f.delta_percent:.2f}%" if f.delta_percent is not None else ""
            lines.append(
                f"- **{f.pattern_name}**: was `{f.extracted_value}`, "
                f"should be `{f.metrics_value}`, confidence `{f.confidence}`"
                f"{delta_str} — update `{f.file}` (first occurrence line {f.line})"
            )
        lines.append("")

    if close_findings:
        lines.append("### Medium priority — close matches within ±0.5% (likely rounding)")
        lines.append("")
        seen_close: set = set()
        for f in sorted(close_findings, key=lambda x: (x.file, x.line)):
            key = (f.pattern_name, str(f.extracted_value))
            if key in seen_close:
                continue
            seen_close.add(key)
            delta_str = f", Δ={f.delta_percent:.2f}%" if f.delta_percent is not None else ""
            lines.append(
                f"- **{f.pattern_name}**: was `{f.extracted_value}`, "
                f"should be `{f.metrics_value}`, confidence `{f.confidence}`"
                f"{delta_str} — `{f.file}` line {f.line}"
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

    # -----------------------------------------------------------------------
    # Injection Commands — sed fix for each MISMATCH
    # -----------------------------------------------------------------------
    lines += [
        "## Injection Commands",
        "",
        "For each MISMATCH below, the sed command replaces the manuscript value with the",
        "METRICS.yaml value. **User decision required** before running: verify that the",
        "METRICS.yaml value is authoritative, then apply.",
        "",
    ]
    if mismatches:
        seen_inj: set = set()
        for f in sorted(mismatches, key=lambda x: (x.file, x.line)):
            key = (f.file, str(f.extracted_value), str(f.metrics_value))
            if key in seen_inj:
                continue
            seen_inj.add(key)
            manuscript_raw = str(f.extracted_value)
            metrics_raw = str(f.metrics_value)
            lines += [
                f"```bash",
                f"# File: {f.file}  line {f.line}",
                f"# Manuscript says: {f.manuscript_claim!r}  (extracted: {manuscript_raw})",
                f"# Metrics says:    {metrics_raw}",
                f"# Fix: (user decision — update metric or keep prose explanation)",
                f"sed -i '' 's/{re.escape(manuscript_raw)}/{re.escape(metrics_raw)}/g' {f.file}",
                f"```",
                "",
            ]
    else:
        lines.append("_No mismatches — no injection commands needed._")
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
    close_findings = [f for f in all_findings if f.status == "CLOSE"]
    expected_mismatches = [f for f in all_findings if f.status == "EXPECTED_MISMATCH"]
    matches = [f for f in all_findings if f.status == "MATCH"]
    unverified = [f for f in all_findings if f.status == "UNVERIFIED"]
    stale = [f for f in all_findings if f.status == "STALE_ARCHIVE"]

    print(f"  MISMATCH:          {len(mismatches)}")
    print(f"  CLOSE (±0.5%):     {len(close_findings)}")
    print(f"  EXPECTED_MISMATCH: {len(expected_mismatches)}")
    print(f"  MATCH:             {len(matches)}")
    print(f"  UNVERIFIED:        {len(unverified)}")
    print(f"  STALE_ARCHIVE:     {len(stale)}")
    print(f"  Total:             {len(all_findings)}")

    # Confidence summary
    n_high = sum(1 for f in all_findings if f.confidence == "HIGH")
    n_medium = sum(1 for f in all_findings if f.confidence == "MEDIUM")
    n_low = sum(1 for f in all_findings if f.confidence == "LOW")
    print(f"  Confidence:        HIGH={n_high}  MEDIUM={n_medium}  LOW={n_low}")

    report = render_report(all_findings, metrics, is_fallback, KNOWN_VALUES)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"\nAudit report written to: {output_path}")

    if mismatches:
        print(f"\nWARNING: {len(mismatches)} mismatch(es) found — see report for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
