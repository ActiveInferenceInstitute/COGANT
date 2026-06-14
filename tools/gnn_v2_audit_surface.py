#!/usr/bin/env python3
"""Summarize and visualize a COGANT/GNN v2 audit directory.

This is a manuscript and technical-documentation helper, not a runtime API.
It consumes the audit artifacts produced by an exhaustive GNN bridge check and
emits three reviewable files:

* ``gnn_v2_audit_surface.json`` — machine-readable classification.
* ``gnn_v2_audit_surface.md`` — prose summary for technical docs.
* ``gnn_v2_audit_surface.svg`` — compact all-step visualization.

The tool deliberately separates three claims that are easy to conflate:
version/currentness, COGANT-owned GNN method health, and all selected upstream
pipeline steps. In strict mode, selected upstream step failures are fatal even
when ordinary product paths treat them as advisory.
"""

from __future__ import annotations

import argparse
import html
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_AUDIT_DIR = Path("/tmp/cogant_gnn_v2_audit")
EXPECTED_UPSTREAM_COMMIT = "11a89f0615f1e48ddacca58d1bcf3c5092b1b055"


@dataclass(frozen=True)
class StepFinding:
    """One upstream pipeline step classification."""

    step_index: int
    script: str
    status: str
    success: bool
    duration_s: float | None = None
    exit_code: int | None = None
    reason: str = ""


@dataclass(frozen=True)
class SupplyChainFinding:
    """Package-level vulnerability summary from pip-audit."""

    package: str
    version: str
    vulnerability_ids: tuple[str, ...]


@dataclass(frozen=True)
class AuditSurface:
    """Bounded audit surface for manuscript/docs consumption."""

    upstream_commit: str | None
    origin_head: str | None
    tag_v2_0_0: str | None
    distribution_version: str | None
    engine_version: str | None
    raw_import_negative_control: bool
    bridge_import_success: bool
    upstream_commit_expected: bool
    upstream_steps_total: int
    upstream_steps_success: int
    upstream_steps_failed: int
    upstream_failures: tuple[StepFinding, ...]
    supply_chain_findings: tuple[SupplyChainFinding, ...] = field(default_factory=tuple)

    @property
    def version_claim_pass(self) -> bool:
        """True when package evidence matches the pinned v2.0.0 release tag."""
        return (
            self.upstream_commit_expected
            and self.distribution_version == "2.0.0"
            and self.engine_version == "1.6.0"
            and self.bridge_import_success
            and self.raw_import_negative_control
        )

    @property
    def upstream_all_steps_pass(self) -> bool:
        """True only when every selected upstream step succeeds."""
        return self.upstream_steps_total > 0 and self.upstream_steps_failed == 0

    @property
    def supply_chain_pass(self) -> bool:
        """True when no known-vulnerability finding is present."""
        return not self.supply_chain_findings

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["version_claim_pass"] = self.version_claim_pass
        data["upstream_all_steps_pass"] = self.upstream_all_steps_pass
        data["supply_chain_pass"] = self.supply_chain_pass
        data["claim_boundary"] = (
            "COGANT-owned GNN validation/type-check/export/roundtrip/runner paths "
            "can pass while optional upstream executable render/execute steps remain "
            "incompatible for a selected package."
        )
        return data


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def parse_version_probe(path: Path) -> dict[str, str]:
    """Parse key=value lines from the version probe."""
    values: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _reason_for_failure(script: str, audit_dir: Path) -> str:
    """Return a compact, source-backed failure reason when known."""
    if script == "2_tests.py":
        text = _read_text(
            audit_dir
            / "upstream_full_after_A_patch"
            / "2_tests_output"
            / "pytest_reliable_output.txt"
        )
        if "No module named 'scripts'" in text:
            return "upstream installed package tests import missing scripts.check_capability_contracts"
    if script == "11_render.py":
        path = (
            audit_dir
            / "upstream_full_after_A_patch"
            / "11_render_output"
            / "render_processing_summary.json"
        )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "upstream render failed; render summary unavailable"
        failures = data.get("failed_framework_renderings", [])
        if isinstance(failures, list) and failures:
            message = failures[0].get("message") if isinstance(failures[0], dict) else None
            if isinstance(message, str):
                return message
        return "upstream render failed without a detailed framework message"
    if script == "12_execute.py":
        path = (
            audit_dir
            / "upstream_full_after_A_patch"
            / "12_execute_output"
            / "summaries"
            / "execution_summary.json"
        )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "upstream execute failed; execution summary unavailable"
        if data.get("total_scripts_found") == 0:
            return "no executable scripts were produced because render failed"
    return "selected upstream step failed"


def parse_upstream_summary(path: Path, audit_dir: Path) -> tuple[int, int, int, tuple[StepFinding, ...]]:
    """Parse upstream pipeline summary JSON."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: could not read upstream summary {path}: {exc}") from exc
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise SystemExit(f"ERROR: {path} does not contain a steps list")
    total = len(steps)
    success_count = 0
    failures: list[StepFinding] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        success = bool(step.get("success"))
        success_count += int(success)
        if not success:
            script = str(step.get("script", f"step-{index}"))
            findings = StepFinding(
                step_index=int(step.get("step_index", index)),
                script=script,
                status=str(step.get("status", "FAILED")),
                success=False,
                duration_s=(
                    float(step["duration_s"])
                    if isinstance(step.get("duration_s"), (int, float))
                    else None
                ),
                exit_code=(
                    int(step["exit_code"])
                    if isinstance(step.get("exit_code"), int)
                    else None
                ),
                reason=_reason_for_failure(script, audit_dir),
            )
            failures.append(findings)
    return total, success_count, total - success_count, tuple(failures)


def parse_pip_audit(path: Path) -> tuple[SupplyChainFinding, ...]:
    """Parse pip-audit JSON; missing files mean no scan was available."""
    if not path.is_file():
        return ()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    findings: list[SupplyChainFinding] = []
    for dep in data.get("dependencies", []):
        if not isinstance(dep, dict):
            continue
        vulns = dep.get("vulns") or []
        if not isinstance(vulns, list) or not vulns:
            continue
        ids = tuple(str(v.get("id", "unknown")) for v in vulns if isinstance(v, dict))
        findings.append(
            SupplyChainFinding(
                package=str(dep.get("name", "unknown")),
                version=str(dep.get("version", "")),
                vulnerability_ids=ids,
            )
        )
    return tuple(findings)


def build_surface(audit_dir: Path) -> AuditSurface:
    """Build the bounded audit classification from an audit directory."""
    version = parse_version_probe(audit_dir / "version_probe.txt")
    refreshed = parse_version_probe(audit_dir / "version_probe_refreshed.txt")
    version.update(refreshed)

    summary_path = audit_dir / "upstream_full_after_A_patch" / "upstream_pipeline_summary.json"
    if not summary_path.is_file():
        summary_path = audit_dir / "upstream_full" / "upstream_pipeline_summary.json"
    total, succeeded, failed, failures = parse_upstream_summary(summary_path, audit_dir)
    distribution = version.get("dist")
    engine = version.get("bridge_upstream_version") or version.get("src_gnn_version_after_bridge")
    raw_negative = version.get("returncode") == "1" and "ModuleNotFoundError" in version.get(
        "stderr_last",
        "",
    )
    bridge_success = version.get("bridge_available") == "True" and engine == "1.6.0"
    upstream_commit = version.get("HEAD") or version.get("head")
    origin_head = version.get("origin_HEAD") or version.get("origin_head")
    tag = version.get("v2.0.0_tag") or version.get("tag_v2_0_0")
    return AuditSurface(
        upstream_commit=upstream_commit,
        origin_head=origin_head,
        tag_v2_0_0=tag,
        distribution_version=distribution,
        engine_version=engine,
        raw_import_negative_control=raw_negative,
        bridge_import_success=bridge_success,
        upstream_commit_expected=(tag == EXPECTED_UPSTREAM_COMMIT),
        upstream_steps_total=total,
        upstream_steps_success=succeeded,
        upstream_steps_failed=failed,
        upstream_failures=failures,
        supply_chain_findings=parse_pip_audit(audit_dir / "pip_audit_path.json"),
    )


def render_markdown(surface: AuditSurface) -> str:
    """Render a review-ready Markdown summary."""
    lines = [
        "# GNN v2 Audit Surface",
        "",
        "## Claim Boundary",
        "",
        (
            "This report separates version currentness, COGANT-owned GNN method "
            "health, selected upstream pipeline execution, and supply-chain state. "
            "A high COGANT validator score is not an all-25 upstream execution claim."
        ),
        "",
        "## Verdicts",
        "",
        f"- Version and bridge currentness: {'PASS' if surface.version_claim_pass else 'FAIL'}",
        (
            "- Selected upstream steps: "
            f"{surface.upstream_steps_success}/{surface.upstream_steps_total} succeeded"
        ),
        f"- Supply-chain scan: {'PASS' if surface.supply_chain_pass else 'FINDINGS'}",
        "",
    ]
    if surface.upstream_failures:
        lines.extend(["## Upstream Step Failures", ""])
        for failure in surface.upstream_failures:
            lines.append(
                f"- Step {failure.step_index} `{failure.script}`: {failure.reason}"
            )
        lines.append("")
    if surface.supply_chain_findings:
        lines.extend(["## Supply-Chain Findings", ""])
        for finding in surface.supply_chain_findings:
            ids = ", ".join(finding.vulnerability_ids)
            lines.append(f"- `{finding.package}@{finding.version}`: {ids}")
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            (
                "COGANT-owned validation/type-check/export/roundtrip/runner paths can "
                "be green while optional upstream executable render/execute remains "
                "incompatible for a selected package. Manuscript and docs should state "
                "that boundary explicitly."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_svg(surface: AuditSurface) -> str:
    """Render a compact SVG visualization of audit lanes and upstream steps."""
    total = max(surface.upstream_steps_total, 1)
    width = 1040
    margin = 40
    step_gap = 4
    cell_w = (width - (2 * margin) - ((total - 1) * step_gap)) / total
    fail_indices = {f.step_index for f in surface.upstream_failures}
    rects: list[str] = []
    for i in range(total):
        x = margin + i * (cell_w + step_gap)
        color = "#d84c4c" if i in fail_indices else "#2f9e6e"
        label_color = "#fff" if i in fail_indices else "#0f2a1f"
        rects.append(

                f'<rect x="{x:.1f}" y="126" width="{cell_w:.1f}" height="44" '
                f'rx="4" fill="{color}"/>'

        )
        if cell_w >= 22:
            rects.append(

                    f'<text x="{x + cell_w / 2:.1f}" y="153" text-anchor="middle" '
                    f'font-size="12" fill="{label_color}">{i}</text>'

            )
    version_fill = "#2f9e6e" if surface.version_claim_pass else "#d84c4c"
    supply_fill = "#2f9e6e" if surface.supply_chain_pass else "#d49a28"
    upstream_fill = "#2f9e6e" if surface.upstream_all_steps_pass else "#d84c4c"
    title = html.escape("COGANT GNN v2 audit surface")
    subtitle = html.escape(
        f"Version: {surface.distribution_version or '?'} / engine {surface.engine_version or '?'}; "
        f"upstream steps {surface.upstream_steps_success}/{surface.upstream_steps_total}"
    )
    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="260" viewBox="0 0 1040 260" role="img" aria-label="COGANT GNN v2 audit surface">',
            '<rect width="1040" height="260" fill="#f8faf7"/>',
            f'<text x="40" y="38" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#172018">{title}</text>',
            f'<text x="40" y="64" font-family="Arial, sans-serif" font-size="14" fill="#405047">{subtitle}</text>',
            f'<rect x="40" y="84" width="260" height="28" rx="4" fill="{version_fill}"/>',
            '<text x="52" y="103" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#ffffff">Version and bridge boundary</text>',
            f'<rect x="318" y="84" width="260" height="28" rx="4" fill="{upstream_fill}"/>',
            '<text x="330" y="103" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#ffffff">Selected upstream all-step gate</text>',
            f'<rect x="596" y="84" width="260" height="28" rx="4" fill="{supply_fill}"/>',
            '<text x="608" y="103" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#ffffff">Supply-chain scan</text>',
            '<text x="40" y="119" font-family="Arial, sans-serif" font-size="12" fill="#405047">Upstream step index: green = success, red = selected step failure</text>',
            *rects,
            '<line x1="40" x2="1000" y1="192" y2="192" stroke="#ccd6ce" stroke-width="1"/>',
            '<text x="40" y="218" font-family="Arial, sans-serif" font-size="13" fill="#172018">Claim boundary: COGANT-owned method paths can pass while optional upstream executable render/execute remains incompatible.</text>',
            '</svg>',
        ]
    )


def write_outputs(surface: AuditSurface, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "gnn_v2_audit_surface.json").write_text(
        json.dumps(surface.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "gnn_v2_audit_surface.md").write_text(
        render_markdown(surface),
        encoding="utf-8",
    )
    (output_dir / "gnn_v2_audit_surface.svg").write_text(
        render_svg(surface),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT_DIR)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--strict-upstream",
        action="store_true",
        help="Exit non-zero when any selected upstream pipeline step failed.",
    )
    parser.add_argument(
        "--strict-supply-chain",
        action="store_true",
        help="Exit non-zero when pip-audit findings are present.",
    )
    args = parser.parse_args(argv)
    output_dir = args.output_dir or (args.audit_dir / "published_surface")
    surface = build_surface(args.audit_dir)
    write_outputs(surface, output_dir)
    print(output_dir / "gnn_v2_audit_surface.json")
    print(output_dir / "gnn_v2_audit_surface.md")
    print(output_dir / "gnn_v2_audit_surface.svg")
    if args.strict_upstream and not surface.upstream_all_steps_pass:
        return 1
    if args.strict_supply_chain and not surface.supply_chain_pass:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
