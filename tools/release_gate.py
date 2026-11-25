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
import shlex
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


# Direct script execution must import the same anchored command owner, not the
# compatibility shell's environment or a caller's unrelated run_gate module.
sys.path.insert(0, str(ROOT))
from run_gate import Step, build_release_steps


@dataclass
class GateResult:
    name: str
    status: str
    returncode: int | None
    duration_seconds: float
    command: list[str]
    output_tail: str


def _run_step(name: str, step: Step) -> GateResult:
    started = time.perf_counter()
    environment = os.environ.copy()
    environment.update(step.env)
    try:
        completed = subprocess.run(
            list(step.argv),
            cwd=step.cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=step.timeout,
            check=False,
        )
        output = (completed.stdout + completed.stderr).strip()
        return GateResult(
            name=name,
            status="passed" if completed.returncode == 0 else "failed",
            returncode=completed.returncode,
            duration_seconds=round(time.perf_counter() - started, 3),
            command=list(step.argv),
            output_tail=output[-4_000:],
        )
    except subprocess.TimeoutExpired as exc:
        output = str(exc.output or "")
        return GateResult(
            name=name,
            status="timed_out",
            returncode=None,
            duration_seconds=round(time.perf_counter() - started, 3),
            command=list(step.argv),
            output_tail=output[-4_000:],
        )
    except OSError as exc:
        return GateResult(
            name=name,
            status="unavailable",
            returncode=None,
            duration_seconds=round(time.perf_counter() - started, 3),
            command=list(step.argv),
            output_tail=f"{type(exc).__name__}: {exc}",
        )


def run_gate(
    *, include_tests: bool = True, dry_run: bool = False
) -> tuple[list[GateResult], bool]:
    results: list[GateResult] = []
    if not include_tests:
        results.append(
            GateResult("package-tests", "skipped", None, 0.0, [], "--skip-tests")
        )
    for name, step in build_release_steps(include_tests=include_tests):
        printable = shlex.join(step.argv)
        print(f"[gate] {name}: {printable}")
        if dry_run:
            results.append(
                GateResult(name, "skipped", None, 0.0, list(step.argv), "dry-run")
            )
            continue
        result = _run_step(name, step)
        results.append(result)
        print(f"[gate] {name}: {result.status} ({result.duration_seconds:.1f}s)")
        if result.status != "passed":
            print(result.output_tail, file=sys.stderr)
            # Stop at the first failed required gate. Later checks would be
            # misleading because their inputs may already be invalid.
            break
    if dry_run:
        return results, False
    return results, bool(results) and all(
        result.status == "passed" for result in results
    )


def _write_report(results: list[GateResult], overall_pass: bool) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "root": str(ROOT),
        "overall": (
            "dry_run"
            if all(result.status == "skipped" for result in results)
            else "passed"
            if overall_pass
            else "incomplete"
            if all(result.status in {"passed", "skipped"} for result in results)
            else "failed"
        ),
        "results": [asdict(result) for result in results],
    }
    REPORT_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip the full package test stage"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print commands without executing them"
    )
    args = parser.parse_args(argv)

    results, overall_pass = run_gate(
        include_tests=not args.skip_tests, dry_run=args.dry_run
    )
    _write_report(results, overall_pass)
    verdict = "DRY RUN" if args.dry_run else "PASS" if overall_pass else "FAIL"
    print(f"release_gate: {verdict} ({REPORT_PATH})")
    return 0 if args.dry_run or overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
