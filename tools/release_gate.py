#!/usr/bin/env python3
"""Run COGANT's aggregate engineering, evidence, and publication gate.

The gate is intentionally fail-closed.  It does not regenerate source-of-truth
artifacts implicitly: freshness checks prove that metrics and generated
manuscript outputs were regenerated deliberately before release.

Run from the COGANT project root::

    uv run python tools/release_gate.py

Use ``--dry-run`` to inspect the exact commands, or ``--skip-tests`` for a
fast local audit while iterating on generated artifacts.  A skipped check is
recorded as skipped and is never reported as a pass.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INNER = ROOT / "cogant"
REPORT_PATH = ROOT / "output" / "reports" / "release_gate.json"


@dataclass(frozen=True)
class GateStep:
    name: str
    cwd: Path
    command: tuple[str, ...]
    env: tuple[tuple[str, str], ...] = ()
    timeout_seconds: int = 900
    required: bool = True


@dataclass
class GateResult:
    name: str
    status: str
    returncode: int | None
    duration_seconds: float
    command: list[str]
    output_tail: str


def _step(
    name: str,
    command: Sequence[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    timeout_seconds: int = 900,
) -> GateStep:
    return GateStep(
        name=name,
        cwd=cwd,
        command=tuple(command),
        env=tuple(sorted((env or {}).items())),
        timeout_seconds=timeout_seconds,
    )


def build_steps(*, include_tests: bool = True) -> list[GateStep]:
    """Return the canonical gate sequence in dependency order."""

    steps: list[GateStep] = []
    if include_tests:
        steps.append(
            _step(
                "package-tests",
                ("uv", "run", "pytest", "tests/", "-q"),
                cwd=INNER,
                timeout_seconds=1_800,
            )
        )
    steps.extend(
        [
            _step("ruff", ("uv", "run", "ruff", "check", "py/cogant", "tests"), cwd=INNER),
            _step(
                "mypy",
                ("uv", "run", "mypy", "--package", "cogant", "--strict", "--no-warn-unused-configs"),
                cwd=INNER,
                env={"MYPYPATH": "py"},
            ),
            _step("rust-format", ("cargo", "fmt", "--manifest-path", "rust/Cargo.toml", "--all", "--check"), cwd=INNER),
            _step("rust-check", ("cargo", "check", "--manifest-path", "rust/Cargo.toml", "--workspace"), cwd=INNER),
            _step("rust-test", ("cargo", "test", "--manifest-path", "rust/Cargo.toml", "--workspace"), cwd=INNER),
            _step(
                "rust-clippy",
                ("cargo", "clippy", "--manifest-path", "rust/Cargo.toml", "--workspace", "--all-targets", "--", "-D", "warnings"),
                cwd=INNER,
            ),
            _step("wheel-smoke", ("make", "wheel-smoke"), cwd=INNER),
            _step(
                "release-integrity",
                (
                    "uv",
                    "run",
                    "python",
                    "../tools/audit_release_integrity.py",
                    "--require-wheel",
                    "--check-wheel-reproducibility",
                ),
                cwd=INNER,
                timeout_seconds=600,
            ),
            _step(
                "server-security",
                (
                    "uv",
                    "run",
                    "pytest",
                    "tests/integration/test_server.py",
                    "tests/unit/test_server_app_routes_and_metrics.py",
                    "-q",
                    "--no-cov",
                ),
                cwd=INNER,
                timeout_seconds=300,
            ),
            _step(
                "provenance-contract",
                (
                    "uv",
                    "run",
                    "pytest",
                    "tests/unit/test_bundle_stage_outcomes.py",
                    "tests/unit/test_cache_hasher_store_hash_file_repo_get_targeted.py",
                    "-q",
                    "--no-cov",
                ),
                cwd=INNER,
                timeout_seconds=300,
            ),
            _step(
                "parser-graph-contract",
                (
                    "uv",
                    "run",
                    "pytest",
                    "tests/unit/test_parser_capability_matrix.py",
                    "tests/unit/test_api_orchestration_stage_functions.py",
                    "-q",
                    "--no-cov",
                ),
                cwd=INNER,
                timeout_seconds=300,
            ),
            _step("folder-docs", ("uv", "run", "python", "../tools/audit_folder_docs.py"), cwd=INNER),
            _step("stage-list", ("uv", "run", "python", "../tools/audit_stage_list.py"), cwd=INNER),
            _step("roadmap-truth", ("uv", "run", "python", "tools/audit_roadmap_truth.py")),
            _step("manuscript-crossrefs", ("uv", "run", "python", "tools/audit_manuscript_crossrefs.py")),
            _step("manuscript-citations", ("uv", "run", "python", "tools/audit_manuscript_citations.py")),
            _step(
                "manuscript-module-refs",
                ("uv", "run", "python", "../tools/audit_manuscript_module_refs.py", "--strict"),
                cwd=INNER,
            ),
            _step("manuscript-formalisms", ("uv", "run", "python", "tools/audit_manuscript_formalisms.py", "--strict")),
            _step("manuscript-numbers", ("uv", "run", "python", "tools/audit_manuscript_numbers.py")),
            _step("manuscript-links", ("uv", "run", "python", "tools/audit_manuscript_markdown_links.py")),
            _step("manuscript-math", ("uv", "run", "python", "tools/audit_manuscript_math_adjacency.py")),
            _step("manuscript-claim-scope", ("uv", "run", "python", "tools/audit_manuscript_claim_scope.py")),
            _step("robustness-table", ("uv", "run", "python", "tools/audit_robustness_table.py")),
            _step("synthetic-surfaces", ("uv", "run", "python", "tools/audit_synthetic_surfaces.py", "--strict")),
            _step("figure-renderers", ("uv", "run", "python", "../tools/audit_figure_renderers.py"), cwd=INNER),
            _step("publication-readiness", ("uv", "run", "python", "tools/audit_publication_readiness.py", "--strict")),
            _step("metrics-freshness", ("uv", "run", "python", "tools/check_metrics_fresh.py", "--fail-on-dirty")),
        ]
    )
    return steps


def _run_step(step: GateStep) -> GateResult:
    started = time.perf_counter()
    environment = os.environ.copy()
    environment.update(dict(step.env))
    try:
        completed = subprocess.run(
            list(step.command),
            cwd=step.cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=step.timeout_seconds,
            check=False,
        )
        output = (completed.stdout + completed.stderr).strip()
        return GateResult(
            name=step.name,
            status="passed" if completed.returncode == 0 else "failed",
            returncode=completed.returncode,
            duration_seconds=round(time.perf_counter() - started, 3),
            command=list(step.command),
            output_tail=output[-4_000:],
        )
    except subprocess.TimeoutExpired as exc:
        output = str(exc.output or "")
        return GateResult(
            name=step.name,
            status="timed_out",
            returncode=None,
            duration_seconds=round(time.perf_counter() - started, 3),
            command=list(step.command),
            output_tail=output[-4_000:],
        )
    except OSError as exc:
        return GateResult(
            name=step.name,
            status="unavailable",
            returncode=None,
            duration_seconds=round(time.perf_counter() - started, 3),
            command=list(step.command),
            output_tail=f"{type(exc).__name__}: {exc}",
        )


def run_gate(*, include_tests: bool = True, dry_run: bool = False) -> tuple[list[GateResult], bool]:
    results: list[GateResult] = []
    for step in build_steps(include_tests=include_tests):
        printable = " ".join(step.command)
        print(f"[gate] {step.name}: {printable}")
        if dry_run:
            results.append(
                GateResult(step.name, "skipped", None, 0.0, list(step.command), "dry-run")
            )
            continue
        result = _run_step(step)
        results.append(result)
        print(f"[gate] {step.name}: {result.status} ({result.duration_seconds:.1f}s)")
        if result.status != "passed":
            print(result.output_tail, file=sys.stderr)
            # Stop at the first failed required gate. Later checks would be
            # misleading because their inputs may already be invalid.
            break
    if dry_run:
        return results, True
    return results, bool(results) and all(result.status == "passed" for result in results)


def _write_report(results: list[GateResult], overall_pass: bool) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "root": str(ROOT),
        "overall": "dry_run" if all(result.status == "skipped" for result in results) else (
            "passed" if overall_pass else "failed"
        ),
        "results": [asdict(result) for result in results],
    }
    REPORT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true", help="Skip the full package test stage")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them")
    args = parser.parse_args(argv)

    results, overall_pass = run_gate(include_tests=not args.skip_tests, dry_run=args.dry_run)
    _write_report(results, overall_pass)
    print(f"release_gate: {'PASS' if overall_pass else 'FAIL'} ({REPORT_PATH})")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
