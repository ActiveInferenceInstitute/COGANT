#!/usr/bin/env python3
"""Collect, summarize, and visualize a COGANT / upstream GNN audit directory.

This is a manuscript and technical-documentation helper, not a runtime API.
It works against whatever upstream ``generalized-notation-notation`` release
the repository pins: the expected commit comes from the optional ``upstream``
extra in ``cogant/pyproject.toml`` and the expected version from the matching
``generalized-notation-notation`` entry in ``cogant/uv.lock``. Nothing about a
specific upstream release is hard-coded here.

Two modes:

* ``--collect`` builds the audit directory reproducibly from the running
  interpreter (which must import ``cogant``; install the ``upstream`` extra to
  exercise the bridge): a version probe, a fresh COGANT translation of a
  control-positive example, single-file upstream validation, the upstream
  pipeline with the bridge's default step selection, and an optional
  ``pip-audit`` scan.
* Without ``--collect`` the tool only reads an existing audit directory.

Either way it emits three reviewable files:

* ``gnn_upstream_audit_surface.json`` — machine-readable classification.
* ``gnn_upstream_audit_surface.md`` — prose summary for technical docs.
* ``gnn_upstream_audit_surface.svg`` — compact all-step visualization.

The tool deliberately separates claims that are easy to conflate:
version/currentness, COGANT-owned GNN method health, the selected upstream
pipeline steps, and supply-chain state. In strict mode, selected upstream step
failures are fatal even when ordinary product paths treat them as advisory.

Audit directory layout (as written by ``--collect``)::

    <audit-dir>/
      version_probe.txt            key=value probe (dist, engine, commits, controls)
      collect_manifest.json        what --collect ran, with timings
      gnn_package/                 COGANT translation of the control-positive example
      single_file_validation.json  COGANT validator + upstream validate_gnn_syntax
      upstream_full/               upstream pipeline output root
        upstream_pipeline_summary.json   bridge summary (per-step records)
        upstream_pipeline.log            upstream console log
        00_pipeline_summary/             upstream run summary
      pip_audit_path.json          pip-audit JSON over the interpreter's site-packages
      pip_audit.log                pip-audit stderr
      published_surface/           default --output-dir

Upstream GNN 4.x resolves hard step prerequisites itself and maps
``--skip-llm`` to skipping step 13, so the steps upstream runs can differ from
the bridge selection; the surface reconciles the two from upstream's own run
summary instead of trusting the selection alone.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INNER = ROOT / "cogant"
PYPROJECT_PATH = INNER / "pyproject.toml"
LOCK_PATH = INNER / "uv.lock"
DEFAULT_EXAMPLE = INNER / "examples" / "control_positive" / "calculator"
DEFAULT_AUDIT_DIR = ROOT / "output" / "gnn_upstream_audit"

UPSTREAM_DISTRIBUTION = "generalized-notation-notation"
UPSTREAM_IMPORT_NAME = "gnn"
NEGATIVE_CONTROL_MODULE = "src.gnn"
"""Import surface the upstream wheel no longer ships; a clean import must fail."""

SURFACE_STEM = "gnn_upstream_audit_surface"
PIPELINE_SUMMARY_NAME = "upstream_pipeline_summary.json"
UPSTREAM_RUN_SUMMARY = Path("00_pipeline_summary") / "pipeline_execution_summary.json"
UPSTREAM_SUCCESS_STATUSES = frozenset({"SUCCESS", "SUCCESS_WITH_WARNINGS", "SKIPPED"})
"""Mirrors ``cogant.gnn.upstream_bridge.pipeline.SUCCESS_STATUSES``."""
SUMMARY_DIRNAMES: tuple[str, ...] = ("upstream_full", "upstream_full_after_A_patch")
"""Upstream output roots searched in order; the second is an earlier hand-made layout."""

VALIDATION_LEVELS: tuple[str, ...] = ("standard", "strict")

_PIN_RE = re.compile(r"@\s*git\+(?P<url>[^@\s]+)@(?P<rev>[0-9a-f]{40})\b")
_COMMIT_RE = re.compile(r"\b[0-9a-f]{40}\b")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UpstreamExpectation:
    """Upstream release the repository pins (derived, never hard-coded)."""

    requirement: str | None
    repository_url: str | None
    pinned_commit: str | None
    locked_version: str | None
    locked_commit: str | None

    @property
    def lock_matches_pin(self) -> bool:
        return bool(self.pinned_commit) and self.pinned_commit == self.locked_commit

    @property
    def release_tag(self) -> str | None:
        """Conventional upstream release tag for the locked version (``v<version>``)."""
        return f"v{self.locked_version}" if self.locked_version else None


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
class ValidationFinding:
    """One single-file validation verdict on the translated ``model.gnn.md``."""

    validator: str
    level: str
    ok: bool
    available: bool = True
    error_count: int = 0
    first_error: str = ""
    detail: str = ""


@dataclass(frozen=True)
class UpstreamRun:
    """Parsed bridge summary for one upstream pipeline invocation."""

    summary_dir: Path
    steps: tuple[StepFinding, ...]
    skipped: tuple[int, ...] = ()
    upstream_status: str | None = None
    run_id: str | None = None
    bridge_error: str | None = None
    available: bool = True
    planned: tuple[int, ...] = ()
    """Steps upstream itself planned (from its own run summary), when recorded."""
    auto_included: tuple[StepFinding, ...] = ()
    """Steps upstream ran outside the bridge selection (e.g. hard prerequisites)."""
    unplanned: tuple[int, ...] = ()
    """Selected steps upstream never planned (e.g. ``--skip-llm`` drops step 13)."""

    @property
    def total(self) -> int:
        return len(self.steps)

    @property
    def succeeded(self) -> int:
        return sum(1 for step in self.steps if step.success)

    @property
    def failures(self) -> tuple[StepFinding, ...]:
        return tuple(step for step in self.steps if not step.success)


@dataclass(frozen=True)
class AuditSurface:
    """Bounded audit surface for manuscript/docs consumption."""

    upstream_commit: str | None
    expected_commit: str | None
    locked_commit: str | None
    locked_version: str | None
    origin_head: str | None
    release_tag: str | None
    release_tag_commit: str | None
    distribution_version: str | None
    engine_version: str | None
    raw_import_negative_control: bool
    bridge_import_success: bool
    upstream_commit_expected: bool
    lock_matches_pin: bool
    upstream_steps_total: int
    upstream_steps_success: int
    upstream_steps_failed: int
    upstream_failures: tuple[StepFinding, ...]
    upstream_steps: tuple[StepFinding, ...] = field(default_factory=tuple)
    upstream_steps_skipped: tuple[int, ...] = field(default_factory=tuple)
    upstream_status: str | None = None
    upstream_bridge_error: str | None = None
    upstream_summary_dir: str | None = None
    upstream_planned_steps: tuple[int, ...] = field(default_factory=tuple)
    upstream_auto_included: tuple[StepFinding, ...] = field(default_factory=tuple)
    upstream_unplanned_steps: tuple[int, ...] = field(default_factory=tuple)
    single_file_validation: tuple[ValidationFinding, ...] = field(default_factory=tuple)
    supply_chain_scanned: bool = False
    supply_chain_findings: tuple[SupplyChainFinding, ...] = field(default_factory=tuple)

    @property
    def version_claim_pass(self) -> bool:
        """True when installed upstream evidence matches the repository pin and lock."""
        return (
            self.upstream_commit_expected
            and self.lock_matches_pin
            and self.locked_version is not None
            and self.distribution_version == self.locked_version
            and self.engine_version == self.locked_version
            and self.bridge_import_success
            and self.raw_import_negative_control
        )

    @property
    def upstream_all_steps_pass(self) -> bool:
        """True only when every selected upstream step succeeds."""
        return self.upstream_steps_total > 0 and self.upstream_steps_failed == 0

    @property
    def supply_chain_pass(self) -> bool:
        """True when a completed scan contains no known-vulnerability findings."""
        return self.supply_chain_scanned and not self.supply_chain_findings

    @property
    def single_file_validation_pass(self) -> bool:
        """True when every recorded single-file validation verdict is ok."""
        return bool(self.single_file_validation) and all(
            finding.ok and finding.available for finding in self.single_file_validation
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["version_claim_pass"] = self.version_claim_pass
        data["upstream_all_steps_pass"] = self.upstream_all_steps_pass
        data["supply_chain_pass"] = self.supply_chain_pass
        data["single_file_validation_pass"] = self.single_file_validation_pass
        data["claim_boundary"] = (
            "COGANT-owned GNN validation/type-check/export/roundtrip/runner paths "
            "can pass while selected optional upstream pipeline steps fail. Steps "
            "outside the bridge selection are not part of the all-step gate, even "
            "when upstream ran them as prerequisites of selected steps."
        )
        return data


# ---------------------------------------------------------------------------
# Expectations from the repository
# ---------------------------------------------------------------------------


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _lock_commit(source: Any) -> str | None:
    """Return the resolved commit from a ``uv.lock`` git source entry."""
    if not isinstance(source, dict) or "git" not in source:
        return None
    url = str(source["git"])
    if "#" in url:
        fragment = url.rsplit("#", 1)[1]
        if _COMMIT_RE.fullmatch(fragment):
            return fragment
    match = _COMMIT_RE.search(url)
    return match.group(0) if match else None


def load_upstream_expectation(
    pyproject_path: Path | None = None,
    lock_path: Path | None = None,
) -> UpstreamExpectation:
    """Derive the expected upstream commit and version from pyproject + uv.lock.

    The commit is the 40-hex git revision pinned by the ``upstream`` optional
    extra. The version is taken from the ``uv.lock`` package entry whose git
    source resolves to that commit; when no entry matches, the first entry for
    the distribution is reported and :attr:`UpstreamExpectation.lock_matches_pin`
    is ``False``.
    """
    pyproject = _load_toml(pyproject_path or PYPROJECT_PATH)
    optional = pyproject.get("project", {}).get("optional-dependencies", {})
    specs = optional.get("upstream", []) if isinstance(optional, dict) else []
    requirement = next(
        (str(spec) for spec in specs if UPSTREAM_DISTRIBUTION in str(spec).lower()),
        None,
    )
    pin = _PIN_RE.search(requirement or "")
    pinned_commit = pin.group("rev") if pin else None
    repository_url = pin.group("url") if pin else None

    lock = _load_toml(lock_path or LOCK_PATH)
    entries = [
        package
        for package in lock.get("package", [])
        if isinstance(package, dict)
        and str(package.get("name", "")).lower().replace("_", "-") == UPSTREAM_DISTRIBUTION
    ]
    matching = next(
        (
            entry
            for entry in entries
            if pinned_commit and _lock_commit(entry.get("source")) == pinned_commit
        ),
        None,
    )
    chosen = matching or (entries[0] if entries else None)
    return UpstreamExpectation(
        requirement=requirement,
        repository_url=repository_url,
        pinned_commit=pinned_commit,
        locked_version=str(chosen["version"]) if chosen and chosen.get("version") else None,
        locked_commit=_lock_commit(chosen.get("source")) if chosen else None,
    )


# ---------------------------------------------------------------------------
# Reading an audit directory
# ---------------------------------------------------------------------------


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def parse_version_probe(path: Path) -> dict[str, str]:
    """Parse key=value lines from the version probe."""
    values: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def resolve_summary_dir(audit_dir: Path) -> Path:
    """Return the upstream output root that holds the bridge summary."""
    for name in SUMMARY_DIRNAMES:
        candidate = audit_dir / name
        if (candidate / PIPELINE_SUMMARY_NAME).is_file():
            return candidate
    return audit_dir / SUMMARY_DIRNAMES[0]


def _step_output_dir(step: dict[str, Any], summary_dir: Path) -> Path:
    """Locate a step's output directory, preferring the summary dir actually read.

    The bridge records absolute paths; an audit directory that was moved or
    copied still resolves through ``<summary_dir>/<script stem>_output``.
    """
    script = str(step.get("script", ""))
    local = summary_dir / f"{script.removesuffix('.py')}_output"
    if local.is_dir():
        return local
    recorded = step.get("output_dir")
    if isinstance(recorded, str) and recorded and Path(recorded).is_dir():
        return Path(recorded)
    return local


@dataclass(frozen=True)
class UpstreamPlan:
    """What upstream itself planned and recorded for the invocation."""

    planned: tuple[int, ...]
    records: dict[int, dict[str, Any]]
    skip_steps: str = ""
    skip_llm: bool | None = None


def _step_number(script: str) -> int | None:
    head = script.split("_", 1)[0]
    return int(head) if head.isdigit() else None


def read_upstream_plan(summary_dir: Path) -> UpstreamPlan | None:
    """Read upstream's own ``00_pipeline_summary/pipeline_execution_summary.json``.

    GNN 4.x resolves hard step prerequisites itself (and maps ``--skip-llm`` to
    skipping step 13), so the steps upstream ran can differ from the bridge's
    selection; this record is what upstream actually planned and executed.
    """
    data = _read_json(summary_dir / UPSTREAM_RUN_SUMMARY)
    if not isinstance(data, dict):
        return None
    planned_raw = data.get("planned_steps")
    records: dict[int, dict[str, Any]] = {}
    for raw in data.get("steps") or []:
        if isinstance(raw, dict):
            number = _step_number(str(raw.get("script_name", "")))
            if number is not None:
                records[number] = raw
    if isinstance(planned_raw, list):
        planned = tuple(
            sorted(n for n in (_step_number(str(s)) for s in planned_raw) if n is not None)
        )
    else:
        planned = tuple(sorted(records))
    arguments = data.get("arguments") if isinstance(data.get("arguments"), dict) else {}
    skip_llm = arguments.get("skip_llm")
    return UpstreamPlan(
        planned=planned,
        records=records,
        skip_steps=str(arguments.get("skip_steps") or ""),
        skip_llm=skip_llm if isinstance(skip_llm, bool) else None,
    )


def _upstream_record_error(raw: dict[str, Any]) -> str:
    """Last error-looking line of an upstream step record."""
    for key in ("stderr", "stdout"):
        text = str(raw.get(key) or "")
        for line in reversed(text.splitlines()):
            stripped = line.strip()
            if stripped and (key == "stderr" or " - ERROR - " in stripped or "FAILED" in stripped):
                return stripped[:500]
    return ""


def _reason_for_failure(
    step: dict[str, Any],
    summary_dir: Path,
    plan: UpstreamPlan | None = None,
) -> str:
    """Return a compact, source-backed failure reason when known.

    Step-specific upstream artifacts give the most precise reason; otherwise
    the bridge's per-step ``error`` field (the last upstream error line) is
    used, then upstream's own plan, then a status-based default.
    """
    script = str(step.get("script", ""))
    status = str(step.get("status", "FAILED"))
    error = step.get("error")
    error_text = error.strip() if isinstance(error, str) else ""
    step_dir = _step_output_dir(step, summary_dir)
    step_index = _optional_int(step.get("step_index"))

    if script == "2_tests.py":
        text = _read_text(step_dir / "pytest_reliable_output.txt")
        if "No module named 'scripts'" in text:
            return (
                "upstream installed package tests import missing scripts.check_capability_contracts"
            )
    if script == "11_render.py":
        data = _read_json(step_dir / "render_processing_summary.json")
        if isinstance(data, dict):
            failures = data.get("failed_framework_renderings", [])
            if isinstance(failures, list) and failures and isinstance(failures[0], dict):
                message = failures[0].get("message")
                if isinstance(message, str) and message:
                    return message
    if script == "12_execute.py":
        data = _read_json(step_dir / "summaries" / "execution_summary.json")
        if isinstance(data, dict) and data.get("total_scripts_found") == 0:
            return "no executable scripts were produced because render failed"

    if status == "NOT_RUN" and plan is not None and step_index is not None:
        if step_index not in plan.planned:
            detail = ", ".join(
                part
                for part in (
                    f"upstream skip_steps={plan.skip_steps}" if plan.skip_steps else "",
                    f"skip_llm={plan.skip_llm}" if plan.skip_llm is not None else "",
                )
                if part
            )
            return "selected but never planned by upstream" + (f" ({detail})" if detail else "")
    if error_text:
        return error_text
    if status == "NOT_RUN":
        return "step absent from the upstream pipeline summary"
    if status == "TIMEOUT":
        return "upstream invocation exceeded the bridge timeout"
    if script == "11_render.py":
        return "upstream render failed; render summary unavailable"
    if script == "12_execute.py":
        return "upstream execute failed; execution summary unavailable"
    return "selected upstream step failed"


def _optional_float(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _optional_int(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def parse_upstream_summary(path: Path, summary_dir: Path | None = None) -> UpstreamRun:
    """Parse the bridge's ``upstream_pipeline_summary.json``.

    When upstream's own run summary sits next to it, the result also records
    which steps upstream planned, which it ran outside the bridge selection,
    and which selected steps it never planned.
    """
    summary_dir = summary_dir or path.parent
    plan = read_upstream_plan(summary_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: could not read upstream summary {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {path} is not a JSON object")
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise SystemExit(f"ERROR: {path} does not contain a steps list")
    findings: list[StepFinding] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        success = bool(step.get("success"))
        step_index = _optional_int(step.get("step_index"))
        findings.append(
            StepFinding(
                step_index=index if step_index is None else step_index,
                script=str(step.get("script", f"step-{index}")),
                status=str(step.get("status", "SUCCESS" if success else "FAILED")),
                success=success,
                duration_s=_optional_float(step.get("duration_s")),
                exit_code=_optional_int(step.get("exit_code")),
                reason="" if success else _reason_for_failure(step, summary_dir, plan),
            )
        )
    skipped = _int_tuple(data.get("skipped"))
    executed = _int_tuple(data.get("executed")) or tuple(sorted(f.step_index for f in findings))
    auto_included: list[StepFinding] = []
    unplanned: tuple[int, ...] = ()
    if plan is not None:
        for number in plan.planned:
            if number in executed:
                continue
            raw = plan.records.get(number, {})
            status = str(raw.get("status", "NOT_RUN"))
            ok = status in UPSTREAM_SUCCESS_STATUSES
            auto_included.append(
                StepFinding(
                    step_index=number,
                    script=str(raw.get("script_name", f"step-{number}")),
                    status=status,
                    success=ok,
                    duration_s=_optional_float(raw.get("duration_seconds")),
                    exit_code=_optional_int(raw.get("exit_code")),
                    reason="" if ok else _upstream_record_error(raw),
                )
            )
        unplanned = tuple(number for number in executed if number not in plan.planned)
    error = data.get("error")
    upstream_status = data.get("upstream_status")
    run_id = data.get("run_id")
    return UpstreamRun(
        summary_dir=summary_dir,
        steps=tuple(findings),
        skipped=skipped,
        upstream_status=str(upstream_status) if upstream_status else None,
        run_id=str(run_id) if run_id else None,
        bridge_error=str(error) if error else None,
        available=bool(data.get("available", True)),
        planned=plan.planned if plan is not None else (),
        auto_included=tuple(auto_included),
        unplanned=unplanned,
    )


def _int_tuple(raw: Any) -> tuple[int, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(sorted(int(i) for i in raw if isinstance(i, int) and not isinstance(i, bool)))


def parse_pip_audit(path: Path) -> tuple[SupplyChainFinding, ...]:
    """Parse pip-audit JSON; missing files mean no scan was available."""
    if not path.is_file():
        return ()
    data = _read_json(path)
    if not isinstance(data, dict):
        return ()
    findings: list[SupplyChainFinding] = []
    for dep in data.get("dependencies", []):
        if not isinstance(dep, dict):
            continue
        vulns = dep.get("vulns") or []
        if not isinstance(vulns, list) or not vulns:
            continue
        ids = tuple(
            dict.fromkeys(str(v.get("id", "unknown")) for v in vulns if isinstance(v, dict))
        )
        findings.append(
            SupplyChainFinding(
                package=str(dep.get("name", "unknown")),
                version=str(dep.get("version", "")),
                vulnerability_ids=ids,
            )
        )
    return tuple(findings)


def _pip_audit_scanned(path: Path) -> bool:
    data = _read_json(path)
    return isinstance(data, dict) and isinstance(data.get("dependencies"), list)


def parse_single_file_validation(path: Path) -> tuple[ValidationFinding, ...]:
    """Parse ``single_file_validation.json`` written by ``--collect``."""
    data = _read_json(path)
    if not isinstance(data, dict):
        return ()
    findings: list[ValidationFinding] = []
    for entry in data.get("results", []):
        if not isinstance(entry, dict):
            continue
        errors = entry.get("errors") or []
        errors = errors if isinstance(errors, list) else [str(errors)]
        findings.append(
            ValidationFinding(
                validator=str(entry.get("validator", "unknown")),
                level=str(entry.get("level", "")),
                ok=bool(entry.get("ok")),
                available=bool(entry.get("available", True)),
                error_count=len(errors),
                first_error=str(errors[0])[:300] if errors else "",
                detail=str(entry.get("detail") or ""),
            )
        )
    return tuple(findings)


def build_surface(
    audit_dir: Path,
    expectation: UpstreamExpectation | None = None,
) -> AuditSurface:
    """Build the bounded audit classification from an audit directory.

    Args:
        audit_dir: Directory produced by ``--collect`` (or an equivalent
            hand-made layout with ``version_probe.txt`` and an upstream
            output root).
        expectation: Expected upstream release; defaults to the pin in
            ``cogant/pyproject.toml`` and the matching ``cogant/uv.lock`` entry.
    """
    expectation = expectation or load_upstream_expectation()
    version = parse_version_probe(audit_dir / "version_probe.txt")

    summary_dir = resolve_summary_dir(audit_dir)
    run = parse_upstream_summary(summary_dir / PIPELINE_SUMMARY_NAME, summary_dir)

    distribution = version.get("dist") or None
    engine = version.get("engine") or version.get("bridge_upstream_version") or None
    bridge_version = version.get("bridge_upstream_version") or None
    bridge_success = (
        version.get("bridge_available") == "True"
        and engine is not None
        and bridge_version == engine
    )
    raw_negative = version.get("returncode") == "1" and "ModuleNotFoundError" in version.get(
        "stderr_last",
        "",
    )
    upstream_commit = (
        version.get("installed_commit") or version.get("HEAD") or version.get("head") or None
    )
    origin_head = version.get("origin_HEAD") or version.get("origin_head") or None
    release_tag = expectation.release_tag
    release_tag_commit = version.get("release_tag_commit") or (
        version.get(f"{release_tag}_tag") if release_tag else None
    )
    pip_audit_path = audit_dir / "pip_audit_path.json"
    scanned = _pip_audit_scanned(pip_audit_path)
    manifest_path = audit_dir / "collect_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            scan = manifest["phases"]["pip_audit"]
            scanned = (
                scanned
                and bool(manifest.get("finished_at"))
                and scan.get("ran") is True
                and scan.get("returncode") in (0, 1)
            )
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            scanned = False
    return AuditSurface(
        upstream_commit=upstream_commit,
        expected_commit=expectation.pinned_commit,
        locked_commit=expectation.locked_commit,
        locked_version=expectation.locked_version,
        origin_head=origin_head,
        release_tag=release_tag,
        release_tag_commit=release_tag_commit or None,
        distribution_version=distribution,
        engine_version=engine,
        raw_import_negative_control=raw_negative,
        bridge_import_success=bridge_success,
        upstream_commit_expected=(
            expectation.pinned_commit is not None and upstream_commit == expectation.pinned_commit
        ),
        lock_matches_pin=expectation.lock_matches_pin,
        upstream_steps_total=run.total,
        upstream_steps_success=run.succeeded,
        upstream_steps_failed=run.total - run.succeeded,
        upstream_failures=run.failures,
        upstream_steps=run.steps,
        upstream_steps_skipped=run.skipped,
        upstream_status=run.upstream_status,
        upstream_bridge_error=run.bridge_error,
        upstream_summary_dir=summary_dir.name,
        upstream_planned_steps=run.planned,
        upstream_auto_included=run.auto_included,
        upstream_unplanned_steps=run.unplanned,
        single_file_validation=parse_single_file_validation(
            audit_dir / "single_file_validation.json"
        ),
        supply_chain_scanned=scanned,
        supply_chain_findings=parse_pip_audit(pip_audit_path),
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _short(commit: str | None) -> str:
    return commit[:8] if commit else "?"


def _release_label(surface: AuditSurface) -> str:
    return f"{UPSTREAM_DISTRIBUTION} {surface.locked_version or '?'}"


def _md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(surface: AuditSurface) -> str:
    """Render a review-ready Markdown summary."""
    supply = (
        "NOT SCANNED"
        if not surface.supply_chain_scanned
        else "PASS"
        if surface.supply_chain_pass
        else "FINDINGS"
    )
    lines = [
        f"# GNN Upstream Audit Surface ({_release_label(surface)})",
        "",
        "## Claim Boundary",
        "",
        (
            "This report separates version currentness, COGANT-owned GNN method "
            "health, selected upstream pipeline execution, and supply-chain state. "
            "A high COGANT validator score is not an all-25 upstream execution claim."
        ),
        "",
        "## Release Evidence",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Pinned commit (`cogant/pyproject.toml`) | `{surface.expected_commit or '?'}` |",
        f"| Locked version / commit (`cogant/uv.lock`) | `{surface.locked_version or '?'}` / `{surface.locked_commit or '?'}` |",
        f"| Installed commit | `{surface.upstream_commit or '?'}` |",
        f"| Distribution version | `{surface.distribution_version or '?'}` |",
        f"| Engine version (`gnn.__version__`) | `{surface.engine_version or '?'}` |",
        f"| Release tag commit (informational) | `{surface.release_tag or '?'}` -> `{surface.release_tag_commit or 'not probed'}` |",
        f"| Upstream default-branch HEAD (informational) | `{surface.origin_head or 'not probed'}` |",
        f"| Bridge import (`cogant.gnn.upstream_bridge`) | {'PASS' if surface.bridge_import_success else 'FAIL'} |",
        f"| Negative control (clean `import {NEGATIVE_CONTROL_MODULE}` fails) | {'PASS' if surface.raw_import_negative_control else 'FAIL'} |",
        "",
        "## Verdicts",
        "",
        f"- Version and bridge currentness: {'PASS' if surface.version_claim_pass else 'FAIL'}",
    ]
    if surface.single_file_validation:
        lines.append(
            "- Single-file validation of the translated model: "
            f"{'PASS' if surface.single_file_validation_pass else 'FAIL'}"
        )
    lines.extend(
        [
            (
                "- Selected upstream steps: "
                f"{surface.upstream_steps_success}/{surface.upstream_steps_total} succeeded"
                + (
                    f" (upstream overall status `{surface.upstream_status}`)"
                    if surface.upstream_status
                    else ""
                )
            ),
            f"- Supply-chain scan: {supply}",
            "",
        ]
    )
    if surface.single_file_validation:
        lines.extend(
            [
                "## Single-File Validation",
                "",
                "| Validator | Level | Verdict | Detail | Errors |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for finding in surface.single_file_validation:
            verdict = "UNAVAILABLE" if not finding.available else "PASS" if finding.ok else "FAIL"
            errors = str(finding.error_count)
            if finding.first_error:
                errors += f" (first: {_md_cell(finding.first_error)})"
            lines.append(
                f"| {finding.validator} | {finding.level} | {verdict} | "
                f"{_md_cell(finding.detail) or '-'} | {errors} |"
            )
        lines.append("")
    if surface.upstream_steps:
        lines.extend(
            [
                "## Selected Upstream Steps",
                "",
                "| Step | Script | Status | Duration (s) | Reason |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for step in surface.upstream_steps:
            duration = f"{step.duration_s:.1f}" if step.duration_s is not None else "-"
            reason = _md_cell(step.reason) if step.reason else ""
            lines.append(
                f"| {step.step_index} | `{step.script}` | {step.status} | {duration} | {reason} |"
            )
        lines.append("")
    if surface.upstream_steps_skipped:
        skipped = ", ".join(str(i) for i in surface.upstream_steps_skipped)
        lines.extend([f"Steps outside the bridge selection: {skipped}.", ""])
    if surface.upstream_auto_included or surface.upstream_unplanned_steps:
        lines.extend(["## Upstream Selection Reconciliation", ""])
        planned = ", ".join(str(i) for i in surface.upstream_planned_steps)
        lines.extend(
            [
                (
                    f"Upstream planned {len(surface.upstream_planned_steps)} steps "
                    f"({planned}); this differs from the bridge selection."
                ),
                "",
            ]
        )
        if surface.upstream_auto_included:
            lines.extend(
                [
                    "Run by upstream outside the bridge selection (hard prerequisites of "
                    "selected steps; not part of the all-step gate):",
                    "",
                    "| Step | Script | Upstream status | Duration (s) |",
                    "| --- | --- | --- | --- |",
                ]
            )
            for step in surface.upstream_auto_included:
                duration = f"{step.duration_s:.1f}" if step.duration_s is not None else "-"
                lines.append(
                    f"| {step.step_index} | `{step.script}` | {step.status} | {duration} |"
                )
            lines.append("")
        if surface.upstream_unplanned_steps:
            unplanned = ", ".join(str(i) for i in surface.upstream_unplanned_steps)
            lines.extend(
                [
                    (
                        f"Selected but never planned by upstream: {unplanned} "
                        "(the bridge reports these as `NOT_RUN` failures)."
                    ),
                    "",
                ]
            )
    if surface.upstream_bridge_error:
        lines.extend([f"Bridge-level error: {surface.upstream_bridge_error}", ""])
    if surface.upstream_failures:
        lines.extend(["## Upstream Step Failures", ""])
        for failure in surface.upstream_failures:
            lines.append(f"- Step {failure.step_index} `{failure.script}`: {failure.reason}")
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
                "be green while selected optional upstream pipeline steps fail. Steps "
                "outside the bridge selection are not part of the all-step gate, even "
                "when upstream ran them as prerequisites. Manuscript and docs should "
                "state that boundary explicitly."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _step_universe(surface: AuditSurface) -> list[int]:
    indices = {step.step_index for step in surface.upstream_steps}
    indices.update(surface.upstream_steps_skipped)
    indices.update(step.step_index for step in surface.upstream_auto_included)
    if not indices:
        indices = {f.step_index for f in surface.upstream_failures}
    return sorted(indices)


_CELL_COLORS = {
    "pass": ("#2f9e6e", "#0f2a1f"),
    "fail": ("#d84c4c", "#fff"),
    "auto_pass": ("#9fd3b8", "#0f2a1f"),
    "auto_fail": ("#f0a8a8", "#4a1010"),
    "unselected": ("#c9d1cb", "#405047"),
}


def render_svg(surface: AuditSurface) -> str:
    """Render a compact SVG visualization of audit lanes and upstream steps."""
    universe = _step_universe(surface)
    total = max(len(universe), 1)
    width = 1040
    margin = 40
    step_gap = 4
    cell_w = (width - (2 * margin) - ((total - 1) * step_gap)) / total
    kind_by_index = {
        step.step_index: "pass" if step.success else "fail" for step in surface.upstream_steps
    }
    for failure in surface.upstream_failures:
        kind_by_index[failure.step_index] = "fail"
    for step in surface.upstream_auto_included:
        kind_by_index.setdefault(step.step_index, "auto_pass" if step.success else "auto_fail")
    rects: list[str] = []
    for position, step_index in enumerate(universe):
        x = margin + position * (cell_w + step_gap)
        color, label_color = _CELL_COLORS[kind_by_index.get(step_index, "unselected")]
        rects.append(
            f'<rect x="{x:.1f}" y="126" width="{cell_w:.1f}" height="44" rx="4" fill="{color}"/>'
        )
        if cell_w >= 22:
            rects.append(
                f'<text x="{x + cell_w / 2:.1f}" y="153" text-anchor="middle" '
                f'font-family="Arial, sans-serif" font-size="12" fill="{label_color}">{step_index}</text>'
            )
    version_fill = "#2f9e6e" if surface.version_claim_pass else "#d84c4c"
    supply_fill = "#2f9e6e" if surface.supply_chain_pass else "#d49a28"
    upstream_fill = "#2f9e6e" if surface.upstream_all_steps_pass else "#d84c4c"
    title = html.escape(f"COGANT GNN upstream audit surface ({_release_label(surface)})")
    label = html.escape(
        f"COGANT GNN upstream audit surface ({_release_label(surface)})", quote=True
    )
    subtitle = html.escape(
        f"Version: {surface.distribution_version or '?'} / engine {surface.engine_version or '?'} "
        f"@ {_short(surface.upstream_commit)}; "
        f"upstream steps {surface.upstream_steps_success}/{surface.upstream_steps_total}"
    )
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="260" viewBox="0 0 1040 260" role="img" aria-label="{label}">',
            '<rect width="1040" height="260" fill="#f8faf7"/>',
            f'<text x="40" y="38" font-family="Arial, sans-serif" font-size="20" font-weight="700" fill="#172018">{title}</text>',
            f'<text x="40" y="64" font-family="Arial, sans-serif" font-size="14" fill="#405047">{subtitle}</text>',
            f'<rect x="40" y="84" width="260" height="28" rx="4" fill="{version_fill}"/>',
            '<text x="52" y="103" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#ffffff">Version and bridge boundary</text>',
            f'<rect x="318" y="84" width="260" height="28" rx="4" fill="{upstream_fill}"/>',
            '<text x="330" y="103" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#ffffff">Selected upstream all-step gate</text>',
            f'<rect x="596" y="84" width="260" height="28" rx="4" fill="{supply_fill}"/>',
            '<text x="608" y="103" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#ffffff">Supply-chain scan</text>',
            '<text x="40" y="119" font-family="Arial, sans-serif" font-size="12" fill="#405047">Upstream step index: green = success, red = selected step failure, pale = run by upstream outside the selection, grey = not run</text>',
            *rects,
            '<line x1="40" x2="1000" y1="192" y2="192" stroke="#ccd6ce" stroke-width="1"/>',
            '<text x="40" y="218" font-family="Arial, sans-serif" font-size="13" fill="#172018">Claim boundary: COGANT-owned method paths can pass while selected upstream steps fail; pale and grey cells sit outside the gate.</text>',
            "</svg>",
        ]
    )


def write_outputs(surface: AuditSurface, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        output_dir / f"{SURFACE_STEM}.json",
        output_dir / f"{SURFACE_STEM}.md",
        output_dir / f"{SURFACE_STEM}.svg",
    ]
    paths[0].write_text(json.dumps(surface.to_dict(), indent=2) + "\n", encoding="utf-8")
    paths[1].write_text(render_markdown(surface), encoding="utf-8")
    paths[2].write_text(render_svg(surface), encoding="utf-8")
    return paths


# ---------------------------------------------------------------------------
# Collecting an audit directory
# ---------------------------------------------------------------------------


def _last_line(text: str) -> str:
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()[:500]
    return ""


def _clean_import(module: str, *, attribute: str | None = None) -> subprocess.CompletedProcess[str]:
    """Import ``module`` in an isolated interpreter (``-I``) from an empty cwd."""
    code = f"import {module}"
    if attribute:
        code += f"; print({module}.{attribute})"
    with tempfile.TemporaryDirectory(prefix="cogant_gnn_probe_") as cwd:
        return subprocess.run(
            [sys.executable, "-I", "-c", code],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )


def _installed_commit() -> tuple[str | None, str | None]:
    """Return ``(commit, url)`` from the upstream distribution's PEP 610 record."""
    import importlib.metadata

    try:
        raw = importlib.metadata.distribution(UPSTREAM_DISTRIBUTION).read_text("direct_url.json")
    except importlib.metadata.PackageNotFoundError:
        return None, None
    try:
        record = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return None, None
    vcs = record.get("vcs_info") if isinstance(record, dict) else None
    commit = vcs.get("commit_id") if isinstance(vcs, dict) else None
    url = record.get("url") if isinstance(record, dict) else None
    return (str(commit) if commit else None), (str(url) if url else None)


def _ls_remote(url: str, tag: str | None) -> dict[str, str]:
    """Probe upstream HEAD and the release tag commit; failures are recorded, not raised."""
    refs = ["HEAD"]
    if tag:
        refs += [f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"]
    try:
        proc = subprocess.run(
            ["git", "ls-remote", url, *refs],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ls_remote_error": str(exc)[:300]}
    if proc.returncode != 0:
        return {
            "ls_remote_error": _last_line(proc.stderr) or f"git ls-remote exited {proc.returncode}"
        }
    found: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2:
            found[parts[1]] = parts[0]
    values: dict[str, str] = {}
    if "HEAD" in found:
        values["origin_HEAD"] = found["HEAD"]
    if tag:
        peeled = found.get(f"refs/tags/{tag}^{{}}") or found.get(f"refs/tags/{tag}")
        if peeled:
            values["release_tag_commit"] = peeled
    return values


def probe_versions(expectation: UpstreamExpectation, *, ls_remote: bool = True) -> dict[str, str]:
    """Probe the running interpreter's upstream install and the import controls."""
    import importlib
    import importlib.metadata

    values: dict[str, str] = {
        "collected_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        "pinned_commit": expectation.pinned_commit or "",
        "locked_version": expectation.locked_version or "",
        "locked_commit": expectation.locked_commit or "",
        "release_tag": expectation.release_tag or "",
    }
    try:
        values["dist"] = importlib.metadata.version(UPSTREAM_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        values["dist"] = ""
    commit, url = _installed_commit()
    values["installed_commit"] = commit or ""
    values["installed_url"] = url or ""
    try:
        engine = getattr(importlib.import_module(UPSTREAM_IMPORT_NAME), "__version__", "")
        values["engine"] = str(engine or "")
    except Exception as exc:  # upstream import can fail on optional native deps
        values["engine"] = ""
        values["engine_error"] = f"{type(exc).__name__}: {exc}"[:300]

    try:
        from cogant.gnn import upstream_bridge

        values["bridge_available"] = str(upstream_bridge.is_upstream_gnn_available())
        values["bridge_upstream_version"] = upstream_bridge.upstream_version() or ""
    except Exception as exc:
        values["bridge_available"] = "False"
        values["bridge_upstream_version"] = ""
        values["bridge_error"] = f"{type(exc).__name__}: {exc}"[:300]

    negative = _clean_import(NEGATIVE_CONTROL_MODULE)
    values["negative_control_import"] = NEGATIVE_CONTROL_MODULE
    values["returncode"] = str(negative.returncode)
    values["stderr_last"] = _last_line(negative.stderr)
    positive = _clean_import(UPSTREAM_IMPORT_NAME, attribute="__version__")
    values["clean_gnn_import_returncode"] = str(positive.returncode)
    values["clean_gnn_import_version"] = (
        _last_line(positive.stdout) if positive.returncode == 0 else ""
    )

    if ls_remote and expectation.repository_url:
        values.update(_ls_remote(expectation.repository_url, expectation.release_tag))
    # One line per key: the probe file is a key=value format.
    return {key: " ".join(str(value).split()) for key, value in values.items()}


def _write_probe(path: Path, values: dict[str, str]) -> None:
    lines = [f"# COGANT upstream GNN version probe ({Path(__file__).name} --collect)"]
    lines += [f"{key}={value}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _translate_example(example: Path, package_dest: Path) -> dict[str, Any]:
    """Translate ``example`` with COGANT into a temp dir; copy its ``gnn_package/``."""
    from cogant.api.pipeline import PipelineConfig, PipelineRunner

    with tempfile.TemporaryDirectory(prefix="cogant_gnn_translate_") as tmp:
        PipelineRunner().run(str(example), PipelineConfig(output_dir=tmp))
        produced = Path(tmp) / "gnn_package"
        if not (produced / "model.gnn.md").is_file():
            raise RuntimeError(
                f"COGANT translation of {example} produced no gnn_package/model.gnn.md"
            )
        if package_dest.exists():
            shutil.rmtree(package_dest)
        shutil.copytree(produced, package_dest)
    return {"example": str(example), "gnn_package": str(package_dest)}


def _single_file_validation(package_dir: Path) -> dict[str, Any]:
    """COGANT package validation plus upstream ``validate_gnn_syntax`` per level."""
    from cogant.gnn.upstream_bridge import run_upstream_validate_gnn
    from cogant.gnn.validator import GNNValidator

    results: list[dict[str, Any]] = []
    cogant_result = GNNValidator().validate_package(str(package_dir), upstream_gnn=False)
    results.append(
        {
            "validator": "cogant GNNValidator",
            "level": "package",
            "detail": f"score {cogant_result.score:.1f}/100",
            "ok": bool(cogant_result.valid),
            "available": True,
            "errors": [str(e) for e in cogant_result.errors],
        }
    )
    markdown = (package_dir / "model.gnn.md").read_text(encoding="utf-8")
    for level in VALIDATION_LEVELS:
        verdict = run_upstream_validate_gnn(markdown, validation_level=level)
        results.append(
            {
                "validator": "upstream validate_gnn_syntax",
                "level": level,
                "ok": bool(verdict.ok) and verdict.available,
                "available": verdict.available,
                "errors": list(verdict.errors)
                or ([verdict.skipped_reason] if verdict.skipped_reason else []),
                "detail": f"upstream {verdict.version}" if verdict.version else "",
            }
        )
    return {"package_dir": str(package_dir), "results": results}


def _site_packages() -> str:
    import sysconfig

    return sysconfig.get_paths()["purelib"]


def _run_pip_audit(destination: Path, log_path: Path) -> dict[str, Any]:
    """Run ``pip-audit --format json`` against this interpreter's site-packages."""
    uvx = shutil.which("uvx")
    pip_audit = shutil.which("pip-audit")
    if uvx:
        base = [uvx, "pip-audit"]
    elif pip_audit:
        base = [pip_audit]
    else:
        return {"ran": False, "reason": "neither uvx nor pip-audit is on PATH"}
    cmd = [*base, "--format", "json", "--progress-spinner", "off", "--path", _site_packages()]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ran": False, "reason": f"pip-audit could not run: {exc}"[:300]}
    log_path.write_text(proc.stderr, encoding="utf-8")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "ran": False,
            "returncode": proc.returncode,
            "reason": _last_line(proc.stderr) or "pip-audit emitted no JSON",
        }
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"ran": True, "returncode": proc.returncode, "command": cmd}


def collect_audit_dir(
    audit_dir: Path,
    *,
    example: Path = DEFAULT_EXAMPLE,
    expectation: UpstreamExpectation | None = None,
    pip_audit: bool = True,
    ls_remote: bool = True,
) -> Path:
    """Build ``audit_dir`` from the running interpreter (see the module docstring).

    Requires an interpreter that imports ``cogant``; the upstream evidence is
    only meaningful when the ``upstream`` extra is installed in it. The
    upstream pipeline runs with the bridge's default step selection and
    ``skip_llm=True``.
    """
    from cogant.gnn.upstream_bridge.pipeline import (
        UpstreamPipelineConfig,
        run_upstream_pipeline,
    )

    expectation = expectation or load_upstream_expectation()
    audit_dir = audit_dir.resolve()
    if audit_dir.exists() and any(audit_dir.iterdir()):
        raise FileExistsError(f"Audit collection requires an empty directory: {audit_dir}")
    audit_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "tool": Path(__file__).name,
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "python": sys.executable,
        "expectation": asdict(expectation),
        "phases": {},
    }
    manifest_path = audit_dir / "collect_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def _phase(name: str, started: float, **info: Any) -> None:
        manifest["phases"][name] = {"duration_s": round(time.perf_counter() - started, 2), **info}

    started = time.perf_counter()
    _write_probe(audit_dir / "version_probe.txt", probe_versions(expectation, ls_remote=ls_remote))
    _phase("version_probe", started)

    started = time.perf_counter()
    package_dir = audit_dir / "gnn_package"
    _phase("translate", started, **_translate_example(example.resolve(), package_dir))

    started = time.perf_counter()
    (audit_dir / "single_file_validation.json").write_text(
        json.dumps(_single_file_validation(package_dir), indent=2) + "\n",
        encoding="utf-8",
    )
    _phase("single_file_validation", started)

    started = time.perf_counter()
    upstream_dir = audit_dir / SUMMARY_DIRNAMES[0]
    result = run_upstream_pipeline(
        UpstreamPipelineConfig(target_dir=package_dir, output_dir=upstream_dir, skip_llm=True)
    )
    summary_path = upstream_dir / PIPELINE_SUMMARY_NAME
    if not summary_path.is_file():
        # The bridge returns early (no summary) when upstream is unavailable.
        upstream_dir.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    _phase(
        "upstream_pipeline",
        started,
        available=result.available,
        executed=list(result.executed),
        skipped=list(result.skipped),
        success_count=result.success_count,
        failure_count=result.failure_count,
        upstream_status=result.upstream_status,
        error=result.error,
    )

    if pip_audit:
        started = time.perf_counter()
        _phase(
            "pip_audit",
            started,
            **_run_pip_audit(audit_dir / "pip_audit_path.json", audit_dir / "pip_audit.log"),
        )

    manifest["finished_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    (audit_dir / "collect_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return audit_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT_DIR)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--collect",
        action="store_true",
        help="Build the audit directory first (requires an interpreter that imports cogant).",
    )
    parser.add_argument(
        "--example",
        type=Path,
        default=DEFAULT_EXAMPLE,
        help="Repository COGANT translates for --collect (default: control-positive calculator).",
    )
    parser.add_argument(
        "--no-pip-audit", action="store_true", help="Skip the pip-audit scan in --collect."
    )
    parser.add_argument(
        "--no-ls-remote",
        action="store_true",
        help="Skip the network probe of upstream HEAD and the release tag in --collect.",
    )
    parser.add_argument(
        "--pyproject", type=Path, help="Pin source (default: cogant/pyproject.toml)."
    )
    parser.add_argument("--lock", type=Path, help="Lock source (default: cogant/uv.lock).")
    parser.add_argument(
        "--strict-version",
        action="store_true",
        help="Exit non-zero when the version/bridge claim fails.",
    )
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
    expectation = load_upstream_expectation(args.pyproject, args.lock)
    if args.collect:
        collect_audit_dir(
            args.audit_dir,
            example=args.example,
            expectation=expectation,
            pip_audit=not args.no_pip_audit,
            ls_remote=not args.no_ls_remote,
        )
    output_dir = args.output_dir or (args.audit_dir / "published_surface")
    surface = build_surface(args.audit_dir, expectation)
    for path in write_outputs(surface, output_dir):
        print(path)
    if args.strict_version and not surface.version_claim_pass:
        return 1
    if args.strict_upstream and not surface.upstream_all_steps_pass:
        return 1
    if args.strict_supply_chain and not surface.supply_chain_pass:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
