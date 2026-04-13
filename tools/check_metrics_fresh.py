#!/usr/bin/env python3
"""Check whether ``cogant/evaluation/METRICS.yaml`` is fresh.

"Fresh" here means two things, both of which must hold:

1. **Coverage drift** — ``testing.coverage_percent`` in METRICS.yaml agrees
   with ``cogant/coverage.json`` to within ``COVERAGE_TOLERANCE`` (±0.1 pp
   by default). This catches the common case of "tests ran again, coverage
   shifted, nobody re-ran ``regenerate_metrics.py``".

2. **Git SHA drift** — ``generator_git_sha`` equals the current
   ``git rev-parse HEAD``. This catches every change that edits code or
   docs after the last metrics refresh.

Anything NOT checked here (ruff, mypy, test counts, roundtrip results) is
deliberately out of scope: this is a *fast* pre-commit / pre-PR guard. The
full refresh, run by ``tools/regenerate_metrics.py`` from CI on every merge,
is still the authoritative source of truth.

Exit codes
----------
* ``0`` — METRICS.yaml is in sync OR a prerequisite (coverage.json,
          git) is missing and cannot be checked.
* ``1`` — detected drift OR the YAML is missing / malformed.

Invocation is directory-independent (paths anchored on ``__file__``); you
may call the script from any cwd.

Usage:
    uv run python tools/check_metrics_fresh.py           # from staging root
    cd cogant && uv run python ../tools/check_metrics_fresh.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
COGANT_DIR = REPO_ROOT / "cogant"
METRICS_PATH = COGANT_DIR / "evaluation" / "METRICS.yaml"
COVERAGE_JSON = COGANT_DIR / "coverage.json"

# Maximum allowed drift between METRICS.yaml and coverage.json (percent).
COVERAGE_TOLERANCE = 0.1

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fail(msg: str) -> None:
    """Print a helpful stale-metrics message to stderr and exit 1."""
    print("METRICS.yaml is STALE:", file=sys.stderr)
    print(f"  {msg}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Fix by regenerating and committing:", file=sys.stderr)
    print("  cd cogant && uv run python ../tools/regenerate_metrics.py", file=sys.stderr)
    print("  git add cogant/evaluation/METRICS.yaml && git commit", file=sys.stderr)
    sys.exit(1)


def _load_metrics() -> dict:
    if not METRICS_PATH.exists():
        _fail(f"{METRICS_PATH} does not exist")
    with METRICS_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        _fail(f"{METRICS_PATH} did not parse to a mapping")
    return data


def _load_coverage_percent() -> float | None:
    if not COVERAGE_JSON.exists():
        # coverage.json is produced by pytest --cov runs; if it's missing,
        # we can't verify drift. Skip this check with a warning (exit 0).
        print(
            f"check_metrics_fresh: {COVERAGE_JSON} not found — skipping coverage drift check",
            file=sys.stderr,
        )
        return None
    try:
        with COVERAGE_JSON.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        _fail(f"could not read {COVERAGE_JSON}: {e}")
    totals = data.get("totals", {})
    percent = totals.get("percent_covered")
    if percent is None:
        _fail(f"{COVERAGE_JSON} missing totals.percent_covered")
    return float(percent)


def _current_git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        print(
            f"check_metrics_fresh: could not run git rev-parse HEAD: {e}",
            file=sys.stderr,
        )
        return None
    if result.returncode != 0:
        print(
            "check_metrics_fresh: git rev-parse HEAD failed — skipping sha check",
            file=sys.stderr,
        )
        return None
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_coverage_percent(metrics: dict) -> None:
    """Compare METRICS.yaml testing.coverage_percent vs coverage.json totals."""
    live_percent = _load_coverage_percent()
    if live_percent is None:
        return  # coverage.json missing; already warned
    testing = metrics.get("testing", {})
    recorded = testing.get("coverage_percent")
    if recorded is None:
        _fail("METRICS.yaml missing testing.coverage_percent")
    drift = abs(float(recorded) - live_percent)
    if drift > COVERAGE_TOLERANCE:
        _fail(
            f"testing.coverage_percent drift: METRICS.yaml={recorded} "
            f"vs coverage.json={live_percent:.2f} (|drift|={drift:.3f} > {COVERAGE_TOLERANCE})"
        )


def check_git_sha(metrics: dict) -> None:
    """Compare METRICS.yaml generator_git_sha vs current HEAD."""
    live_sha = _current_git_sha()
    if live_sha is None:
        return  # git unavailable; already warned
    recorded = metrics.get("generator_git_sha")
    if not recorded:
        _fail("METRICS.yaml missing generator_git_sha")
    if recorded != live_sha:
        _fail(
            f"generator_git_sha drift: METRICS.yaml={recorded} vs HEAD={live_sha}"
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    metrics = _load_metrics()
    check_coverage_percent(metrics)
    check_git_sha(metrics)
    print("check_metrics_fresh: METRICS.yaml is in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
