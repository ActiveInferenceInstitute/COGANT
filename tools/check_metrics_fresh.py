#!/usr/bin/env python3
"""Check whether ``cogant/evaluation/METRICS.yaml`` is fresh.

"Fresh" here means three check families:

1. **Coverage drift** — ``testing.coverage_percent`` in METRICS.yaml agrees
   with ``cogant/coverage.json`` to within ``COVERAGE_TOLERANCE`` (±0.1 pp
   by default). This catches the common case of "tests ran again, coverage
   shifted, nobody re-ran ``regenerate_metrics.py``".

2. **Git SHA / worktree drift** — ``generator_git_sha`` is an ancestor of
   HEAD and no *metric-affecting source* (package code, tests, fixtures,
   roundtrip dataset, ``cogant/pyproject.toml``) changed in between. A literal
   ``generator_git_sha == HEAD`` is unsatisfiable on a committed tip — the
   commit that records the sha advances HEAD beyond it — so freshness is judged
   against source changes, not exact-equality. By default the script also
   warns when the worktree is dirty; ``--fail-on-dirty`` turns *metric-affecting*
   uncommitted source into a hard failure for release/CI gates.

3. **Roundtrip-status / score-source laundering** (added 2026-05-19,
   extended 2026-05-21) — the per-target ``roundtrip_status`` distribution
   and native aggregate score fields recorded in METRICS.yaml match what
   ``tools/regenerate_metrics.py`` would produce against the current
   ``roundtrip_results.jsonl`` data file. This catches the keystone failure
   mode where METRICS.yaml inherits a richer prior regen (with
   ``role_preservation_score`` fields) and the data file is subsequently
   stripped to unscored rows — leaving METRICS.yaml asserting
   ``role_preserved_count: N`` or ``mean_role_preservation_score: 1.0``
   while the current regen would tag every row as ``NON_NATIVE`` and leave
   native aggregate score fields null.

Anything NOT checked here (ruff, mypy, test counts, ablation deltas) is
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
    uv run python tools/check_metrics_fresh.py           # from project root
    uv run python tools/check_metrics_fresh.py --fail-on-dirty
    cd cogant && uv run python ../tools/check_metrics_fresh.py
"""

from __future__ import annotations

import argparse
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
    """Print a helpful out-of-sync metrics message to stderr and exit 1."""
    print("METRICS.yaml is OUT OF SYNC:", file=sys.stderr)
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


def _git_dirty_paths() -> list[str] | None:
    """Return porcelain status lines, or ``None`` when git status is unavailable."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        print(
            f"check_metrics_fresh: could not run git status --porcelain: {e}",
            file=sys.stderr,
        )
        return None
    if result.returncode != 0:
        print(
            "check_metrics_fresh: git status --porcelain failed — skipping dirty-worktree check",
            file=sys.stderr,
        )
        return None
    return [line for line in result.stdout.splitlines() if line.strip()]


# Paths whose change invalidates METRICS.yaml (test counts, coverage, mypy/ruff,
# codebase stats, ablation, roundtrip). Everything else — the regenerated
# artifacts themselves (METRICS.yaml, evaluation/figures/*, coverage.json),
# the manuscript, tools/scripts, CI, and root-shell tests/ — does NOT, so a
# commit that touches only those keeps the metrics fresh even though HEAD moved.
_METRICS_SOURCE_PREFIXES = (
    "cogant/py/cogant/",
    "cogant/tests/",
    "cogant/examples/",
    "cogant/evaluation/dataset/",
)
_METRICS_SOURCE_FILES = ("cogant/pyproject.toml",)


def _path_is_metrics_source(path: str) -> bool:
    p = path.strip().strip('"')
    # porcelain rename lines look like ``source -> destination``; judge the destination.
    if " -> " in p:
        p = p.split(" -> ", 1)[1]
    return p.startswith(_METRICS_SOURCE_PREFIXES) or p in _METRICS_SOURCE_FILES


def _git_committed_changes_since(base_sha: str) -> list[str] | None:
    """Files changed between ``base_sha`` and HEAD (committed only).

    Returns ``None`` when ``base_sha`` is not an ancestor of HEAD (shallow
    clone, rewritten history) so the caller can fall back to a strict check.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_sha}..HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line.strip()]


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


def check_git_sha(metrics: dict, *, fail_on_dirty: bool = False) -> None:
    """Verify METRICS.yaml is in sync with *metric-affecting source*.

    ``generator_git_sha`` records HEAD at regeneration time. Because committing
    the regenerated METRICS.yaml necessarily advances HEAD, a literal
    ``generator_git_sha == HEAD`` equality is unsatisfiable on any committed tip
    (a git hash cannot contain its own value). Instead we treat the metrics as
    fresh when ``generator_git_sha`` is an ancestor of HEAD and **no
    metric-affecting source** (see ``_METRICS_SOURCE_PREFIXES``) changed in
    between — i.e. only the regenerated artifacts / manuscript / tooling moved.
    """
    live_sha = _current_git_sha()
    if live_sha is None:
        return  # git unavailable; already warned
    recorded = metrics.get("generator_git_sha")
    if not recorded:
        _fail("METRICS.yaml missing generator_git_sha")
    if recorded != live_sha:
        changed = _git_committed_changes_since(recorded)
        if changed is None:
            _fail(
                f"generator_git_sha {recorded} is not an ancestor of HEAD "
                f"{live_sha}; cannot verify freshness — regenerate METRICS.yaml"
            )
        source_changed = sorted(p for p in changed if _path_is_metrics_source(p))
        if source_changed:
            preview = "\n".join(f"    {p}" for p in source_changed[:20])
            if len(source_changed) > 20:
                preview += f"\n    ... {len(source_changed) - 20} more"
            _fail(
                f"metric-affecting source changed since generator_git_sha "
                f"{recorded[:12]} (HEAD={live_sha[:12]}):\n{preview}"
            )
        # Only regenerated artifacts / docs / tooling changed since regen — fresh.
    dirty_paths = _git_dirty_paths()
    if not dirty_paths:
        return
    preview = "\n".join(f"    {line}" for line in dirty_paths[:20])
    if len(dirty_paths) > 20:
        preview += f"\n    ... {len(dirty_paths) - 20} more"
    message = (
        f"worktree has {len(dirty_paths)} uncommitted path(s); "
        "generator_git_sha only binds committed HEAD, not these edits:\n"
        f"{preview}"
    )
    if fail_on_dirty:
        _fail(message)
    print(f"check_metrics_fresh: WARNING: {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Roundtrip-status laundering check (RedTeam F19, 2026-05-19)
# ---------------------------------------------------------------------------


_JSONL_PATH = COGANT_DIR / "evaluation" / "dataset" / "roundtrip_results.jsonl"
_ROLE_COUNT_KEYS = (
    "orig_n_hidden",
    "orig_n_obs",
    "orig_n_actions",
)


def _classify_row(entry: dict) -> str:
    """Mirror ``tools/regenerate_metrics.py:_status()`` exactly.

    Keep the body of this function lockstep with the regenerator. The
    regression test ``test_check_metrics_fresh_roundtrip_status_guard.py``
    proves the two implementations agree on the shipped fixtures.
    """
    status = entry.get("roundtrip_status")
    if status:
        return str(status)
    if "role_preservation_score" not in entry:
        return "NON_NATIVE"
    tier = str(entry.get("tier") or "").upper()
    if tier == "ISOMORPHIC":
        return "ROLE_PRESERVED"
    if tier in {"APPROXIMATE", "DIVERGENT"}:
        return "DRIFT"
    return "FAILED" if entry.get("error") else "DRIFT"


def _score_source(entry: dict) -> str:
    """Mirror the regenerator's role-score provenance classification."""
    if "role_preservation_score" in entry:
        return "current_native"
    return "empty"


def _aggregate_score_source(rows: list[dict]) -> str:
    sources = {_score_source(row) for row in rows}
    if not rows or sources == {"empty"}:
        return "empty"
    if "current_native" in sources and sources - {"current_native", "empty"}:
        return "mixed"
    return "current_native"


def _source_role_total(row: dict) -> int:
    return sum(int(row.get(key) or 0) for key in _ROLE_COUNT_KEYS)


def _check_control_positive_rows_are_role_bearing(rows: list[dict]) -> list[str]:
    defects: list[str] = []
    for row in rows:
        if row.get("fixture_group") != "control_positive" and row.get("group") != "control_positive":
            continue
        if _classify_row(row) in {"FAILED", "NON_NATIVE"}:
            continue
        if _source_role_total(row) == 0:
            repo = row.get("repo", "<unknown>")
            defects.append(
                f"  control_positive/{repo}: source role count is zero; "
                "this fixture cannot support a role-preservation claim"
            )
    return defects


def check_roundtrip_status_distribution(metrics: dict) -> None:
    """Catch the F1/F19 laundering pattern: METRICS asserts a non-zero
    ``role_preserved_count`` while the current data file would produce zero.

    Implementation: re-classify every row in ``roundtrip_results.jsonl``
    via the same ``_status()`` logic used by the regenerator, recount
    ``role_preserved_count`` / ``strict_isomorphism_count`` /
    ``drift_count`` / ``failed_count``, and assert each matches the
    committed METRICS.yaml value. Mismatch is a freshness defect — the
    data file has changed since the last regen, or the regen logic has
    changed since the last METRICS write.
    """
    if not _JSONL_PATH.exists():
        print(
            f"check_metrics_fresh: {_JSONL_PATH} not found — skipping roundtrip distribution check",
            file=sys.stderr,
        )
        return
    rows: list[dict] = []
    with _JSONL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                _fail(f"{_JSONL_PATH}: invalid JSON line: {e}")
    statuses = [_classify_row(e) for e in rows]
    expected = {
        "total_targets": len(rows),
        "role_preserved_count": sum(
            1 for s in statuses if s in {"STRUCTURALLY_ISOMORPHIC", "ROLE_PRESERVED"}
        ),
        "strict_isomorphism_count": sum(1 for s in statuses if s == "STRUCTURALLY_ISOMORPHIC"),
        "drift_count": sum(1 for s in statuses if s == "DRIFT"),
        "failed_count": sum(1 for s in statuses if s == "FAILED"),
        "non_native_count": sum(1 for s in statuses if s == "NON_NATIVE"),
        "role_preservation_score_source": _aggregate_score_source(rows),
    }
    native_scores = [float(row["role_preservation_score"]) for row in rows if "role_preservation_score" in row]
    expected_score_fields = {
        "mean_role_preservation_score": None,
        "median_role_preservation_score": None,
        "min_role_preservation_score": None,
        "max_role_preservation_score": None,
    }
    if native_scores:
        import statistics

        expected_score_fields = {
            "mean_role_preservation_score": round(statistics.mean(native_scores), 4),
            "median_role_preservation_score": round(statistics.median(native_scores), 4),
            "min_role_preservation_score": min(native_scores),
            "max_role_preservation_score": max(native_scores),
        }
    corpus_defects = _check_control_positive_rows_are_role_bearing(rows)
    roundtrip = (metrics.get("evaluation") or {}).get("roundtrip") or {}
    drifts: list[str] = list(corpus_defects)
    for key, want in expected.items():
        got = roundtrip.get(key)
        if got is None:
            drifts.append(f"  {key}: missing in METRICS.yaml; expected {want}")
            continue
        if isinstance(want, str):
            if str(got) != want:
                drifts.append(f"  {key}: METRICS.yaml={got!r} but live classification produces {want!r}")
            continue
        if int(got) != want:
            drifts.append(f"  {key}: METRICS.yaml={got} but live classification produces {want}")
    for key, want in expected_score_fields.items():
        got = roundtrip.get(key)
        if want is None:
            if got is not None:
                drifts.append(
                    f"  {key}: METRICS.yaml={got} but current native rows are absent, so expected null"
                )
            continue
        if got is None:
            drifts.append(f"  {key}: missing in METRICS.yaml; expected {want}")
            continue
        if abs(float(got) - float(want)) > 0.0001:
            drifts.append(f"  {key}: METRICS.yaml={got} but live native-score stats produce {want}")
    if drifts:
        msg = (
            "roundtrip status distribution mismatch — METRICS.yaml is out of sync "
            "with the current roundtrip_results.jsonl (laundering risk per RedTeam F1/F19):\n"
            + "\n".join(drifts)
        )
        _fail(msg)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fail-on-dirty",
        action="store_true",
        help="Fail when git status reports uncommitted or untracked files.",
    )
    args = parser.parse_args(argv)

    metrics = _load_metrics()
    check_coverage_percent(metrics)
    check_git_sha(metrics, fail_on_dirty=args.fail_on_dirty)
    check_roundtrip_status_distribution(metrics)
    print("check_metrics_fresh: METRICS.yaml is in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
