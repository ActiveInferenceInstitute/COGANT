#!/usr/bin/env python3
"""Validate and visualize a provisional organization state-space sketch.

This is an R&D review helper, not a public COGANT runtime API. It accepts a
JSON sketch describing typed organization artifacts, dynamic traces, candidate
state/action/observation factors, transitions, and negative controls. The tool
then emits JSON, Markdown, and SVG evidence surfaces that keep the central
claim boundary explicit: an org chart can be a typed prior, but dynamic
evidence and provenance are required before the sketch can be treated as an
optimization-compatible surrogate.
"""

from __future__ import annotations

import argparse
import html
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("/tmp/cogant_org_state_space_audit")
REQUIRED_FACTOR_KINDS = frozenset({"state", "action", "observation"})
REQUIRED_NEGATIVE_CONTROLS = frozenset({"org_chart_only", "trace_only"})


@dataclass(frozen=True)
class Finding:
    """One validation finding for the organization sketch."""

    severity: str
    code: str
    location: str
    message: str


@dataclass(frozen=True)
class AuditSurface:
    """Bounded evidence summary for an organization state-space sketch."""

    model_id: str
    static_artifacts: int
    dynamic_traces: int
    factors: int
    transitions: int
    negative_controls: int
    factor_kinds: tuple[str, ...]
    dynamic_trace_kinds: tuple[str, ...]
    findings: tuple[Finding, ...]

    @property
    def status(self) -> str:
        if any(f.severity == "critical" for f in self.findings):
            return "FAIL"
        if any(f.severity == "warning" for f in self.findings):
            return "REVIEW"
        return "PASS"

    @property
    def ready_for_surrogate(self) -> bool:
        return self.status == "PASS"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status
        data["ready_for_surrogate"] = self.ready_for_surrogate
        data["claim_boundary"] = (
            "This audit checks whether a proposed typed organizational surrogate "
            "has static artifacts, dynamic traces, provenance-bearing factors, "
            "transition evidence, and negative controls. It does not claim that "
            "COGANT models a legal entity or that an organization is literally "
            "differentiable."
        )
        return data


def example_spec() -> dict[str, Any]:
    """Return a minimal positive fixture for docs and tests."""
    return {
        "model_id": "org_state_space_rnd_fixture",
        "static_artifacts": [
            {
                "id": "unit_platform",
                "kind": "organizational_unit",
                "label": "Platform team",
                "provenance": "w3c-org:unit/platform",
            },
            {
                "id": "role_sre",
                "kind": "role",
                "label": "Site reliability role",
                "provenance": "w3c-org:role/sre",
            },
            {
                "id": "process_incident",
                "kind": "process",
                "label": "Incident response process",
                "provenance": "bpmn:incident-response",
            },
            {
                "id": "service_api",
                "kind": "service_ownership",
                "label": "API service ownership",
                "provenance": "service-catalog:api",
            },
        ],
        "dynamic_traces": [
            {
                "id": "ticket_42",
                "kind": "ticket",
                "timestamp": "2026-06-01T10:00:00Z",
                "links": ["process_incident", "service_api"],
                "provenance": "tracker:TICKET-42",
            },
            {
                "id": "incident_7",
                "kind": "incident",
                "timestamp": "2026-06-01T10:07:00Z",
                "links": ["unit_platform", "service_api"],
                "provenance": "incident:INC-7",
            },
            {
                "id": "approval_3",
                "kind": "approval",
                "timestamp": "2026-06-01T10:14:00Z",
                "links": ["role_sre", "process_incident"],
                "provenance": "change:APPROVAL-3",
            },
        ],
        "factors": [
            {
                "id": "state_incident_load",
                "kind": "state",
                "label": "Incident load",
                "evidence": ["unit_platform", "incident_7"],
            },
            {
                "id": "state_service_recovery",
                "kind": "state",
                "label": "Service recovery state",
                "evidence": ["service_api", "ticket_42"],
            },
            {
                "id": "action_assign_oncall",
                "kind": "action",
                "label": "Assign on-call response",
                "evidence": ["role_sre", "approval_3"],
            },
            {
                "id": "observation_handoff",
                "kind": "observation",
                "label": "Observed handoff",
                "evidence": ["process_incident", "ticket_42"],
            },
        ],
        "transitions": [
            {
                "id": "transition_triage_to_recovery",
                "timestamp": "2026-06-01T10:20:00Z",
                "from_state": "state_incident_load",
                "to_state": "state_service_recovery",
                "action": "action_assign_oncall",
                "evidence": ["ticket_42", "incident_7", "approval_3"],
            }
        ],
        "negative_controls": [
            {
                "id": "org_chart_only",
                "expected_failure": "dynamic_evidence_required",
            },
            {
                "id": "trace_only",
                "expected_failure": "typed_artifact_required",
            },
        ],
    }


def _records(spec: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = spec.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_set(records: list[dict[str, Any]], field: str) -> set[str]:
    values: set[str] = set()
    for record in records:
        value = record.get(field)
        if isinstance(value, str) and value:
            values.add(value)
    return values


def _evidence(record: dict[str, Any]) -> list[str]:
    values = record.get("evidence", [])
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if isinstance(value, str) and value]


def _links(record: dict[str, Any]) -> list[str]:
    values = record.get("links", [])
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if isinstance(value, str) and value]


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _check_record_ids(records: list[dict[str, Any]], key: str, findings: list[Finding]) -> None:
    seen: set[str] = set()
    for index, record in enumerate(records):
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            findings.append(
                Finding(
                    "critical",
                    "record_id_required",
                    f"{key}[{index}]",
                    "Record is missing a stable string id.",
                )
            )
            continue
        if record_id in seen:
            findings.append(
                Finding(
                    "critical",
                    "duplicate_record_id",
                    f"{key}.{record_id}",
                    "Record id is duplicated within the section.",
                )
            )
        seen.add(record_id)


def validate_spec(spec: dict[str, Any]) -> AuditSurface:
    """Validate a provisional organization state-space sketch."""
    static = _records(spec, "static_artifacts")
    dynamic = _records(spec, "dynamic_traces")
    factors = _records(spec, "factors")
    transitions = _records(spec, "transitions")
    controls = _records(spec, "negative_controls")
    findings: list[Finding] = []

    for key, records in (
        ("static_artifacts", static),
        ("dynamic_traces", dynamic),
        ("factors", factors),
        ("transitions", transitions),
        ("negative_controls", controls),
    ):
        _check_record_ids(records, key, findings)

    if not static:
        findings.append(
            Finding(
                "critical",
                "typed_artifact_required",
                "static_artifacts",
                "At least one typed organization/process artifact is required.",
            )
        )
    if not dynamic:
        findings.append(
            Finding(
                "critical",
                "dynamic_evidence_required",
                "dynamic_traces",
                "At least one time-indexed dynamic trace is required.",
            )
        )
    if not transitions:
        findings.append(
            Finding(
                "critical",
                "transition_required",
                "transitions",
                "A state-space sketch needs at least one evidence-bearing transition.",
            )
        )

    static_ids = _string_set(static, "id")
    dynamic_ids = _string_set(dynamic, "id")
    factor_ids = _string_set(factors, "id")
    known_evidence = static_ids | dynamic_ids
    dynamic_times: dict[str, datetime] = {}
    factor_kind_by_id = {
        str(factor["id"]): str(factor.get("kind", ""))
        for factor in factors
        if isinstance(factor.get("id"), str)
    }
    factor_kinds = _string_set(factors, "kind")
    missing_factor_kinds = REQUIRED_FACTOR_KINDS - factor_kinds
    if missing_factor_kinds:
        findings.append(
            Finding(
                "critical",
                "required_factor_kind_missing",
                "factors",
                "Missing factor kind(s): " + ", ".join(sorted(missing_factor_kinds)),
            )
        )

    for record in static:
        record_id = str(record.get("id", "unknown"))
        if not record.get("provenance"):
            findings.append(
                Finding(
                    "critical",
                    "static_provenance_required",
                    f"static_artifacts.{record_id}",
                    "Typed artifacts must keep a provenance pointer.",
                )
            )

    for record in dynamic:
        record_id = str(record.get("id", "unknown"))
        timestamp = record.get("timestamp")
        parsed_timestamp = _parse_timestamp(timestamp)
        if not timestamp:
            findings.append(
                Finding(
                    "critical",
                    "dynamic_timestamp_required",
                    f"dynamic_traces.{record_id}",
                    "Dynamic traces must be time indexed.",
                )
            )
        elif parsed_timestamp is None:
            findings.append(
                Finding(
                    "critical",
                    "dynamic_timestamp_invalid",
                    f"dynamic_traces.{record_id}",
                    "Dynamic trace timestamp must be a timezone-aware ISO 8601 value.",
                )
            )
        elif isinstance(record.get("id"), str):
            dynamic_times[record["id"]] = parsed_timestamp
        if not record.get("provenance"):
            findings.append(
                Finding(
                    "critical",
                    "dynamic_provenance_required",
                    f"dynamic_traces.{record_id}",
                    "Dynamic traces must keep a provenance pointer.",
                )
            )
        if not _links(record):
            findings.append(
                Finding(
                    "warning",
                    "dynamic_trace_unlinked",
                    f"dynamic_traces.{record_id}",
                    "Trace is not linked to any typed artifact.",
                )
            )
        for link in _links(record):
            if link not in static_ids:
                findings.append(
                    Finding(
                        "critical",
                        "unknown_dynamic_link",
                        f"dynamic_traces.{record_id}.links",
                        f"Trace link {link!r} does not resolve to a typed artifact.",
                    )
                )

    for factor in factors:
        factor_id = str(factor.get("id", "unknown"))
        evidence = _evidence(factor)
        if not evidence:
            findings.append(
                Finding(
                    "critical",
                    "factor_evidence_required",
                    f"factors.{factor_id}",
                    "Every factor needs explicit evidence references.",
                )
            )
            continue
        unknown = sorted(ref for ref in evidence if ref not in known_evidence)
        if unknown:
            findings.append(
                Finding(
                    "critical",
                    "unknown_factor_evidence",
                    f"factors.{factor_id}.evidence",
                    "Unknown evidence reference(s): " + ", ".join(unknown),
                )
            )
        if factor.get("kind") == "observation" and not (set(evidence) & dynamic_ids):
            findings.append(
                Finding(
                    "critical",
                    "observation_needs_dynamic_trace",
                    f"factors.{factor_id}",
                    "Observation factors need dynamic trace evidence.",
                )
            )
        elif not (set(evidence) & dynamic_ids):
            findings.append(
                Finding(
                    "warning",
                    "factor_without_dynamic_trace",
                    f"factors.{factor_id}",
                    "Factor is static-only; it should not drive transition updates.",
                )
            )

    for transition in transitions:
        transition_id = str(transition.get("id", "unknown"))
        transition_timestamp = transition.get("timestamp")
        parsed_transition_timestamp = _parse_timestamp(transition_timestamp)
        if not transition_timestamp:
            findings.append(
                Finding(
                    "critical",
                    "transition_timestamp_required",
                    f"transitions.{transition_id}",
                    "Transitions need a timestamp so evidence cannot leak backward from the future.",
                )
            )
        elif parsed_transition_timestamp is None:
            findings.append(
                Finding(
                    "critical",
                    "transition_timestamp_invalid",
                    f"transitions.{transition_id}",
                    "Transition timestamp must be a timezone-aware ISO 8601 value.",
                )
            )
        for field_name, expected_kind in (
            ("from_state", "state"),
            ("to_state", "state"),
            ("action", "action"),
        ):
            ref = transition.get(field_name)
            if ref not in factor_ids:
                findings.append(
                    Finding(
                        "critical",
                        "unknown_transition_factor",
                        f"transitions.{transition_id}.{field_name}",
                        f"Transition reference {ref!r} does not resolve to a factor.",
                    )
                )
                continue
            actual_kind = factor_kind_by_id.get(str(ref))
            if actual_kind != expected_kind:
                findings.append(
                    Finding(
                        "critical",
                        "transition_factor_kind_mismatch",
                        f"transitions.{transition_id}.{field_name}",
                        (
                            f"Transition field {field_name!r} references factor "
                            f"{ref!r} with kind {actual_kind!r}; expected "
                            f"{expected_kind!r}."
                        ),
                    )
                )
        evidence = _evidence(transition)
        if not evidence:
            findings.append(
                Finding(
                    "critical",
                    "transition_evidence_required",
                    f"transitions.{transition_id}",
                    "Transitions need dynamic evidence references.",
                )
            )
            continue
        unknown = sorted(ref for ref in evidence if ref not in known_evidence)
        if unknown:
            findings.append(
                Finding(
                    "critical",
                    "unknown_transition_evidence",
                    f"transitions.{transition_id}.evidence",
                    "Unknown evidence reference(s): " + ", ".join(unknown),
                )
            )
        if not (set(evidence) & dynamic_ids):
            findings.append(
                Finding(
                    "critical",
                    "transition_needs_dynamic_trace",
                    f"transitions.{transition_id}",
                    "Transitions cannot be inferred from static artifacts alone.",
                )
            )
        if parsed_transition_timestamp is not None:
            future_refs = sorted(
                ref
                for ref in evidence
                if ref in dynamic_times and dynamic_times[ref] > parsed_transition_timestamp
            )
            if future_refs:
                findings.append(
                    Finding(
                        "critical",
                        "future_transition_evidence",
                        f"transitions.{transition_id}.evidence",
                        "Transition evidence occurs after the transition timestamp: "
                        + ", ".join(future_refs),
                    )
                )

    control_ids = _string_set(controls, "id")
    missing_controls = REQUIRED_NEGATIVE_CONTROLS - control_ids
    if missing_controls:
        findings.append(
            Finding(
                "critical",
                "negative_control_missing",
                "negative_controls",
                "Missing negative control(s): " + ", ".join(sorted(missing_controls)),
            )
        )

    model_id = spec.get("model_id", "organization_state_space_sketch")
    return AuditSurface(
        model_id=str(model_id),
        static_artifacts=len(static),
        dynamic_traces=len(dynamic),
        factors=len(factors),
        transitions=len(transitions),
        negative_controls=len(controls),
        factor_kinds=tuple(sorted(factor_kinds)),
        dynamic_trace_kinds=tuple(sorted(_string_set(dynamic, "kind"))),
        findings=tuple(findings),
    )


def render_markdown(surface: AuditSurface) -> str:
    """Render a compact human-readable report."""
    lines = [
        "# Organization State-Space Audit",
        "",
        f"- Model id: `{surface.model_id}`",
        f"- Status: **{surface.status}**",
        f"- Typed static artifacts: {surface.static_artifacts}",
        f"- Dynamic traces: {surface.dynamic_traces}",
        f"- Candidate factors: {surface.factors}",
        f"- Candidate transitions: {surface.transitions}",
        f"- Negative controls: {surface.negative_controls}",
        "",
        "## Claim Boundary",
        "",
        (
            "This audit treats organization charts and process diagrams as typed "
            "priors. It requires dynamic evidence, provenance, temporal "
            "admissibility, role-compatible transitions, and negative controls "
            "before a sketch can be discussed as a surrogate model."
        ),
        "",
    ]
    if surface.findings:
        lines.extend(["## Findings", ""])
        for finding in surface.findings:
            lines.append(
                f"- `{finding.severity}` `{finding.code}` at `{finding.location}`: "
                f"{finding.message}"
            )
        lines.append("")
    else:
        lines.extend(
            [
                "## Findings",
                "",
                "No critical or warning findings. This is still only an R&D evidence "
                "surface, not an operational organization model.",
                "",
            ]
        )
    return "\n".join(lines)


def _lane(label: str, ok: bool, y: int) -> str:
    fill = "#2f9e6e" if ok else "#d84c4c"
    escaped = html.escape(label)
    return (
        f'<rect x="40" y="{y}" width="284" height="30" rx="4" fill="{fill}"/>'
        f'<text x="54" y="{y + 20}" font-family="Arial, sans-serif" '
        f'font-size="13" font-weight="700" fill="#ffffff">{escaped}</text>'
    )


def render_svg(surface: AuditSurface) -> str:
    """Render a small SVG evidence-lane visualization."""
    critical_codes = {finding.code for finding in surface.findings if finding.severity == "critical"}
    warning_codes = {finding.code for finding in surface.findings if finding.severity == "warning"}
    transition_blockers = {
        "future_transition_evidence",
        "transition_factor_kind_mismatch",
        "transition_evidence_required",
        "transition_needs_dynamic_trace",
        "transition_timestamp_invalid",
        "transition_timestamp_required",
        "unknown_transition_evidence",
        "unknown_transition_factor",
    }
    lanes = [
        _lane("Typed artifacts present", surface.static_artifacts > 0, 84),
        _lane("Dynamic evidence present", surface.dynamic_traces > 0, 122),
        _lane(
            "State/action/observation factors",
            "required_factor_kind_missing" not in critical_codes,
            160,
        ),
        _lane("Transitions are temporally admissible", not (critical_codes & transition_blockers), 198),
        _lane("Negative controls present", "negative_control_missing" not in critical_codes, 236),
    ]
    title = html.escape("Organization state-space audit")
    subtitle = html.escape(
        f"{surface.status}: {surface.static_artifacts} static artifacts, "
        f"{surface.dynamic_traces} dynamic traces, {surface.factors} factors"
    )
    warning_note = ""
    if warning_codes:
        warning_note = (
            '<text x="370" y="216" font-family="Arial, sans-serif" '
            'font-size="13" fill="#8a5c00">Warnings: '
            + html.escape(", ".join(sorted(warning_codes)))
            + "</text>"
        )
    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="320" viewBox="0 0 900 320" role="img" aria-label="Organization state-space audit">',
            '<rect width="900" height="320" fill="#f8faf7"/>',
            f'<text x="40" y="38" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#172018">{title}</text>',
            f'<text x="40" y="64" font-family="Arial, sans-serif" font-size="14" fill="#405047">{subtitle}</text>',
            *lanes,
            '<text x="370" y="104" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#172018">Review boundary</text>',
            '<text x="370" y="130" font-family="Arial, sans-serif" font-size="13" fill="#405047">Green lanes mean the sketch has the minimum evidence shape.</text>',
            '<text x="370" y="154" font-family="Arial, sans-serif" font-size="13" fill="#405047">They do not mean an organization has been modeled or optimized.</text>',
            '<text x="370" y="178" font-family="Arial, sans-serif" font-size="13" fill="#405047">Red lanes block surrogate-model language until repaired.</text>',
            '<text x="370" y="202" font-family="Arial, sans-serif" font-size="13" fill="#405047">Temporal checks reject future evidence for earlier transitions.</text>',
            warning_note,
            '<text x="40" y="296" font-family="Arial, sans-serif" font-size="12" fill="#405047">Negative controls: org-chart-only should fail for missing dynamic evidence; trace-only should fail for missing typed artifacts.</text>',
            "</svg>",
        ]
    )


def write_outputs(surface: AuditSurface, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "organization_state_space_audit.json").write_text(
        json.dumps(surface.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "organization_state_space_audit.md").write_text(
        render_markdown(surface) + "\n",
        encoding="utf-8",
    )
    (output_dir / "organization_state_space_audit.svg").write_text(
        render_svg(surface) + "\n",
        encoding="utf-8",
    )


def load_spec(path: Path | None) -> dict[str, Any]:
    if path is None:
        return example_spec()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: could not read organization sketch {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {path} must contain a JSON object")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, help="Organization state-space sketch JSON")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when the sketch is not PASS.",
    )
    parser.add_argument(
        "--write-example",
        type=Path,
        help="Write the built-in example spec to this path and exit.",
    )
    args = parser.parse_args(argv)
    if args.write_example:
        args.write_example.parent.mkdir(parents=True, exist_ok=True)
        args.write_example.write_text(
            json.dumps(example_spec(), indent=2) + "\n",
            encoding="utf-8",
        )
        print(args.write_example)
        return 0
    surface = validate_spec(load_spec(args.spec))
    write_outputs(surface, args.output_dir)
    print(args.output_dir / "organization_state_space_audit.json")
    print(args.output_dir / "organization_state_space_audit.md")
    print(args.output_dir / "organization_state_space_audit.svg")
    if args.strict and surface.status != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
