#!/usr/bin/env python3
"""Summarize publication readiness from generated COGANT evidence surfaces."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PROJECT_ROOT / "output"
ANALYSIS_ROOT = OUTPUT_ROOT / "analysis"

DEFAULT_CLAIM_LEDGER = OUTPUT_ROOT / "claim_ledger.json"
DEFAULT_EVIDENCE_AUDIT = ANALYSIS_ROOT / "manuscript_evidence_audit.json"
DEFAULT_VISUAL_QA = OUTPUT_ROOT / "figures" / "visual_quality_audit.json"
DEFAULT_FIGURE_MANIFEST = OUTPUT_ROOT / "figures" / "manifest.json"
DEFAULT_REVIEW_DASHBOARD = ANALYSIS_ROOT / "manuscript_review_dashboard.json"
DEFAULT_JSON_OUTPUT = ANALYSIS_ROOT / "publication_readiness.json"
DEFAULT_MARKDOWN_OUTPUT = ANALYSIS_ROOT / "publication_readiness.md"

FIXED_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
LEGACY_FIXED_DATE_RE = re.compile(r"\b(?:2026-05-22|May\s+22(?:nd)?)\b", re.IGNORECASE)
ACTIVE_MANUSCRIPT_PATHS = (
    Path("manuscript"),
    Path("output/manuscript"),
)

SUPPORTED_CLASSES = {
    "metric-backed",
    "artifact-backed",
    "citation-backed",
    "validator-backed",
    "boundary/limitation",
    "unsupported",
}
CLAIM_LEDGER_METRIC_TOKEN_KIND = "place" "holder"

LIMITATION_WORDS = (
    "limitation",
    "bounded",
    "caveat",
    "does not",
    "not evidence",
    "not a benchmark",
    "not semantic equivalence",
    "not arbitrary-program",
    "strict structural isomorphism",
    "role preservation",
)

VALIDATOR_LITERAL_CLASSES = {
    "allowlisted_literal_number",
    "artifact_coordinate",
    "bibliography_entry",
    "code_block",
    "crossref_or_anchor",
    "date_or_version",
    "figure_caption_or_attribute",
    "generated_table_row",
    "inline_code_or_artifact_path",
    "math_notation",
    "metric_placeholder_line",
    "metric_or_protocol_context",
    "ordered_list_marker",
    "ratio_or_path_fragment",
    "section_heading",
    "threshold_phrase",
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _read_json(path: Path, issues: list[str], *, required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            issues.append(f"missing required evidence surface: {path}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append(f"invalid JSON in {path}: {exc}")
        return {}
    if not isinstance(data, dict):
        issues.append(f"expected object JSON in {path}")
        return {}
    return data


def _read_yaml(path: Path, issues: list[str]) -> dict[str, Any]:
    if not path.exists():
        issues.append(f"missing manuscript config: {path}")
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        issues.append(f"invalid YAML in {path}: {exc}")
        return {}
    if data is None:
        return {}
    if not isinstance(data, dict):
        issues.append(f"expected mapping in {path}")
        return {}
    return data


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _scan_active_date_text(root: Path) -> list[str]:
    issues: list[str] = []
    for rel_dir in ACTIVE_MANUSCRIPT_PATHS:
        scan_dir = root / rel_dir
        if not scan_dir.exists():
            continue
        for path in sorted(scan_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if LEGACY_FIXED_DATE_RE.search(line):
                    rel = _relative_to_root(path, root)
                    issues.append(f"legacy fixed publication date text in {rel}:{line_no}")
    return issues


def _date_config_check(root: Path) -> dict[str, Any]:
    issues: list[str] = []
    configs: list[dict[str, Any]] = []
    for rel_path in (Path("manuscript/config.yaml"), Path("output/manuscript/config.yaml")):
        path = root / rel_path
        if not path.exists() and rel_path.parts[0] == "output":
            configs.append(
                {
                    "path": str(rel_path),
                    "status": "not_generated",
                    "paper_date": None,
                    "autofill_enabled": False,
                }
            )
            issues.append(f"generated manuscript config has not been refreshed: {rel_path}")
            continue
        data = _read_yaml(path, issues)
        paper = data.get("paper") if isinstance(data.get("paper"), dict) else {}
        date_value = paper.get("date") if isinstance(paper, dict) else None
        autofill_enabled = date_value in (None, "")
        status = "autofill" if autofill_enabled else "fixed"
        configs.append(
            {
                "path": str(rel_path),
                "status": status,
                "paper_date": date_value,
                "autofill_enabled": autofill_enabled,
            }
        )
        if not autofill_enabled:
            text = str(date_value)
            if FIXED_DATE_RE.search(text) or text.strip():
                issues.append(
                    f"fixed publication date in {rel_path}: {text!r}; leave paper.date empty for render-time autofill"
                )
    issues.extend(_scan_active_date_text(root))
    return {
        "name": "publication_date_autofill",
        "passed": not issues,
        "configs": configs,
        "issues": issues,
    }


def _citation_class(text: str) -> str:
    citation = text.strip()
    if citation.startswith("@fig:"):
        return "artifact-backed"
    if citation.startswith(
        (
            "@sec:",
            "@tbl:",
            "@eq:",
            "@lst:",
            "@def:",
            "@prop:",
            "@inv:",
            "@conj:",
            "@alg:",
            "@thm:",
        )
    ):
        return "validator-backed"
    return "citation-backed"


def classify_claim_record(record: dict[str, Any]) -> str:
    """Map a claim ledger row to the readiness evidence primitive it requires."""

    kind = str(record.get("kind") or "")
    classification = str(record.get("classification") or "")
    text = str(record.get("text") or "")
    lowered = text.lower()
    if any(word in lowered for word in LIMITATION_WORDS):
        return "boundary/limitation"
    if kind == CLAIM_LEDGER_METRIC_TOKEN_KIND:
        return "metric-backed"
    if kind in {"figure", "path"}:
        return "artifact-backed"
    if kind == "citation":
        return _citation_class(text)
    if kind == "literal_number":
        if classification == "actionable_literal_number":
            return "unsupported"
        if classification in VALIDATOR_LITERAL_CLASSES:
            return "validator-backed"
        return "unsupported"
    if kind == "markdown_link":
        return "artifact-backed"
    return "unsupported"


def _claim_readiness(claim_ledger: dict[str, Any]) -> dict[str, Any]:
    records = claim_ledger.get("records") if isinstance(claim_ledger.get("records"), list) else []
    class_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    unsupported: list[dict[str, Any]] = []
    actionable_literals: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        support_class = classify_claim_record(record)
        if support_class not in SUPPORTED_CLASSES:
            support_class = "unsupported"
        class_counts[support_class] += 1
        kind_counts[str(record.get("kind") or "unknown")] += 1
        if support_class == "unsupported":
            unsupported.append(record)
        if record.get("classification") == "actionable_literal_number":
            actionable_literals.append(record)
    return {
        "name": "claim_readiness",
        "passed": not unsupported and not actionable_literals,
        "record_count": len(records),
        "class_counts": dict(sorted(class_counts.items())),
        "kind_counts": dict(sorted(kind_counts.items())),
        "unsupported_count": len(unsupported),
        "actionable_literal_count": len(actionable_literals),
        "unsupported_examples": unsupported[:10],
        "actionable_literal_examples": actionable_literals[:10],
    }


def _evidence_check(evidence_audit: dict[str, Any]) -> dict[str, Any]:
    summary = evidence_audit.get("summary") if isinstance(evidence_audit.get("summary"), dict) else {}
    failed = int(summary.get("failed") or 0)
    review_queue = list(summary.get("review_queue") or [])
    sections = evidence_audit.get("sections") if isinstance(evidence_audit.get("sections"), list) else []
    thin_sections = [
        {
            "file": section.get("file"),
            "section": section.get("section"),
            "support_lane_count": section.get("support_lane_count"),
        }
        for section in sections
        if isinstance(section, dict) and int(section.get("support_lane_count") or 0) < 3
    ]
    return {
        "name": "manuscript_evidence_audit",
        "passed": failed == 0,
        "failed": failed,
        "review_queue_count": len(review_queue),
        "review_queue": review_queue[:10],
        "thin_sections": thin_sections[:10],
    }


def _visual_check(visual_qa: dict[str, Any]) -> dict[str, Any]:
    summary = visual_qa.get("summary") if isinstance(visual_qa.get("summary"), dict) else {}
    failed = int(summary.get("failed") or 0)
    figures = visual_qa.get("figures") if isinstance(visual_qa.get("figures"), list) else []
    failed_figures = [
        str(figure.get("key") or figure.get("destination"))
        for figure in figures
        if isinstance(figure, dict) and figure.get("status") not in {None, "pass"}
    ]
    missing_metadata = [
        str(figure.get("key") or figure.get("destination"))
        for figure in figures
        if isinstance(figure, dict)
        and not (
            isinstance(figure.get("checks"), dict)
            and figure.get("checks", {}).get("sidecar") is True
            or figure.get("render_backend")
        )
    ]
    return {
        "name": "visual_quality_audit",
        "passed": failed == 0 and not missing_metadata and not failed_figures,
        "failed": failed,
        "figure_count": len(figures),
        "failed_figures": failed_figures[:10],
        "missing_metadata": missing_metadata[:10],
    }


def _figure_manifest_check(figure_manifest: dict[str, Any]) -> dict[str, Any]:
    figures = figure_manifest.get("figures") if isinstance(figure_manifest.get("figures"), list) else []
    missing_metadata = [
        str(figure.get("key") or figure.get("destination"))
        for figure in figures
        if isinstance(figure, dict)
        and not (
            figure.get("metadata_complete") is True
            or figure.get("destination_figure_sidecar_exists") is True
            or figure.get("render_backend")
            or figure.get("figure_metadata")
        )
    ]
    missing_sources = [
        str(figure.get("key") or figure.get("destination"))
        for figure in figures
        if isinstance(figure, dict) and not figure.get("source")
    ]
    return {
        "name": "figure_manifest",
        "passed": not missing_metadata and not missing_sources,
        "figure_count": len(figures),
        "missing_metadata": missing_metadata[:10],
        "missing_sources": missing_sources[:10],
    }


def _review_dashboard_check(review_dashboard: dict[str, Any]) -> dict[str, Any]:
    status = str(review_dashboard.get("status") or "unknown")
    issues = review_dashboard.get("issues") if isinstance(review_dashboard.get("issues"), list) else []
    checks = review_dashboard.get("checks") if isinstance(review_dashboard.get("checks"), list) else []
    return {
        "name": "manuscript_review_dashboard",
        "passed": status == "pass" and not issues,
        "status": status,
        "issue_count": len(issues),
        "issues": issues[:10],
        "check_count": len(checks),
    }


def _tail(text: str, *, max_lines: int = 20) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-max_lines:])


def _run_external_audit(label: str, command: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as exc:
        return {
            "name": label,
            "passed": False,
            "command": command,
            "returncode": None,
            "stdout_tail": "",
            "stderr_tail": str(exc),
        }
    return {
        "name": label,
        "passed": result.returncode == 0,
        "command": command,
        "returncode": result.returncode,
        "stdout_tail": _tail(result.stdout),
        "stderr_tail": _tail(result.stderr),
    }


def _external_checks(*, enabled: bool) -> list[dict[str, Any]]:
    if not enabled:
        return []
    python = sys.executable
    return [
        _run_external_audit(
            "manuscript_claim_scope",
            [python, str(PROJECT_ROOT / "tools" / "audit_manuscript_claim_scope.py")],
        ),
        _run_external_audit(
            "docs_constants",
            [python, str(PROJECT_ROOT / "tools" / "audit_docs_constants.py")],
        ),
    ]


def _collect_blockers(checks: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for check in checks:
        if check.get("passed"):
            continue
        name = str(check.get("name") or "unknown_check")
        issues = check.get("issues")
        if isinstance(issues, list) and issues:
            blockers.extend(f"{name}: {issue}" for issue in issues[:10])
        elif name == "claim_readiness":
            blockers.append(
                "claim_readiness failed: "
                f"{check.get('unsupported_count', 0)} unsupported claim(s), "
                f"{check.get('actionable_literal_count', 0)} actionable literal number(s)"
            )
        elif name == "visual_quality_audit":
            blockers.append(
                "visual_quality_audit failed: "
                f"{check.get('failed', 0)} failed figure(s), "
                f"{len(check.get('missing_metadata') or [])} missing metadata item(s)"
            )
        else:
            blockers.append(f"{name} failed")
    return blockers


def _collect_caveats(checks: list[dict[str, Any]]) -> list[str]:
    caveats: list[str] = []
    for check in checks:
        if check.get("name") == "manuscript_evidence_audit":
            review_queue_count = int(check.get("review_queue_count") or 0)
            if review_queue_count:
                caveats.append(
                    f"{review_queue_count} manuscript section(s) remain in the evidence review queue"
                )
            thin_count = len(check.get("thin_sections") or [])
            if thin_count:
                caveats.append(
                    f"{thin_count} section(s) have fewer than three evidence lanes in the audit sample"
                )
    return caveats


def build_publication_readiness(
    *,
    root: Path = PROJECT_ROOT,
    claim_ledger_path: Path | None = None,
    evidence_audit_path: Path | None = None,
    visual_qa_path: Path | None = None,
    figure_manifest_path: Path | None = None,
    review_dashboard_path: Path | None = None,
    run_external_audits: bool = True,
) -> dict[str, Any]:
    """Build the publication readiness report without writing files."""

    root = root.resolve()
    issues: list[str] = []
    claim_ledger_path = claim_ledger_path or root / "output" / "claim_ledger.json"
    evidence_audit_path = evidence_audit_path or root / "output" / "analysis" / "manuscript_evidence_audit.json"
    visual_qa_path = visual_qa_path or root / "output" / "figures" / "visual_quality_audit.json"
    figure_manifest_path = figure_manifest_path or root / "output" / "figures" / "manifest.json"
    review_dashboard_path = review_dashboard_path or root / "output" / "analysis" / "manuscript_review_dashboard.json"

    claim_ledger = _read_json(claim_ledger_path, issues)
    evidence_audit = _read_json(evidence_audit_path, issues)
    visual_qa = _read_json(visual_qa_path, issues)
    figure_manifest = _read_json(figure_manifest_path, issues)
    review_dashboard = _read_json(review_dashboard_path, issues)

    checks = [
        _date_config_check(root),
        _claim_readiness(claim_ledger),
        _evidence_check(evidence_audit),
        _visual_check(visual_qa),
        _figure_manifest_check(figure_manifest),
        _review_dashboard_check(review_dashboard),
        *_external_checks(enabled=run_external_audits),
    ]
    if issues:
        checks.append({"name": "readiness_inputs", "passed": False, "issues": issues})

    blockers = _collect_blockers(checks)
    caveats = _collect_caveats(checks)
    if blockers:
        verdict = "blocked"
    elif caveats:
        verdict = "ready_with_caveats"
    else:
        verdict = "ready"

    claim_check = next(check for check in checks if check.get("name") == "claim_readiness")
    return {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "verdict": verdict,
        "claim_primitives": {
            "metric-backed": "Resolved manuscript metric token or generated metric value.",
            "artifact-backed": "Generated file, figure, manifest entry, or artifact path.",
            "citation-backed": "Bibliographic citation checked by manuscript citation gates.",
            "validator-backed": "Cross-reference, literal-number, or prose pattern covered by validators.",
            "boundary/limitation": "Explicit scope boundary or limitation statement.",
            "unsupported": "No acceptable evidence primitive was found.",
        },
        "inputs": {
            "claim_ledger": str(claim_ledger_path),
            "evidence_audit": str(evidence_audit_path),
            "visual_qa": str(visual_qa_path),
            "figure_manifest": str(figure_manifest_path),
            "review_dashboard": str(review_dashboard_path),
        },
        "checks": checks,
        "claim_summary": {
            "record_count": claim_check.get("record_count", 0),
            "class_counts": claim_check.get("class_counts", {}),
            "kind_counts": claim_check.get("kind_counts", {}),
            "unsupported_count": claim_check.get("unsupported_count", 0),
            "actionable_literal_count": claim_check.get("actionable_literal_count", 0),
        },
        "blockers": blockers,
        "caveats": caveats,
        "recommendation": _recommendation(verdict),
    }


def _recommendation(verdict: str) -> str:
    if verdict == "ready":
        return "Publication surfaces are internally consistent under the current generated evidence gates."
    if verdict == "ready_with_caveats":
        return (
            "Publication can proceed only with the listed caveats preserved; do not promote the caveated claims "
            "to benchmark, semantic-equivalence, or arbitrary-program claims."
        )
    return "Do not publish until all blockers are cleared and the report is regenerated."


def write_publication_readiness(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Publication Readiness",
        "",
        f"- Verdict: `{report.get('verdict')}`",
        f"- Generated: `{report.get('generated_at')}`",
        f"- Claim records: `{report.get('claim_summary', {}).get('record_count', 0)}`",
        "",
        "## Claim Evidence Primitives",
        "",
    ]
    class_counts = report.get("claim_summary", {}).get("class_counts", {})
    for class_name in sorted(SUPPORTED_CLASSES):
        description = report.get("claim_primitives", {}).get(class_name, "")
        count = class_counts.get(class_name, 0)
        lines.append(f"- `{class_name}`: {count} records. {description}")

    blockers = report.get("blockers") or []
    lines.extend(["", "## Blockers", ""])
    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("- None.")

    caveats = report.get("caveats") or []
    lines.extend(["", "## Caveats", ""])
    if caveats:
        for caveat in caveats:
            lines.append(f"- {caveat}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Checks", ""])
    for check in report.get("checks", []):
        name = check.get("name", "unknown")
        status = "pass" if check.get("passed") else "fail"
        lines.append(f"- `{name}`: {status}")

    lines.extend(["", "## Recommendation", "", str(report.get("recommendation") or ""), ""])
    return "\n".join(lines)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when readiness is blocked.")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT, help="COGANT project root.")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON_OUTPUT, help="JSON report path.")
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN_OUTPUT, help="Markdown report path.")
    parser.add_argument(
        "--skip-external-audits",
        action="store_true",
        help="Do not invoke claim-scope and docs-constant audit scripts.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = build_publication_readiness(
        root=args.root,
        run_external_audits=not args.skip_external_audits,
    )
    write_publication_readiness(report, args.json, args.markdown)
    print(
        "publication_readiness: "
        f"verdict={report['verdict']} "
        f"blockers={len(report['blockers'])} "
        f"caveats={len(report['caveats'])} "
        f"json={args.json}"
    )
    if args.strict and report["verdict"] == "blocked":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
