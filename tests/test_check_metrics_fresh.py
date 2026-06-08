"""Tests for ``tools/check_metrics_fresh.py``, including the
roundtrip-status laundering guard added 2026-05-19 (RedTeam F19).

Three contracts:

1. **Positive control** — the shipped METRICS.yaml passes the gate against
   the shipped data file. If a future regen breaks this, the gate flips red
   and the team is alerted before out-of-sync metric laundering ships.

2. **Negative control** — a synthetic METRICS.yaml that asserts a non-zero
   ``role_preserved_count`` against a NON_NATIVE-only data file MUST fail
   the gate. Without this control, a regression in the classify-and-recount
   logic would let laundered METRICS.yaml through silently — the very
   failure mode this gate was added to catch (see
   ``feedback-shape-tests-dont-bind-truth`` memory).

3. **Dirty-tree control** — the default gate warns on uncommitted work, while
   ``--fail-on-dirty`` turns that warning into a release-gate failure.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "check_metrics_fresh.py"


def _run() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )


def test_freshness_gate_passes_on_current_tree() -> None:
    """The shipped tree must satisfy the non-strict freshness checks."""
    result = _run()
    assert result.returncode == 0, (
        f"check_metrics_fresh failed on current tree:\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "is in sync" in result.stdout


def test_freshness_gate_detects_laundered_roundtrip_count(tmp_path: Path) -> None:
    """A synthetic METRICS.yaml with ``role_preserved_count: 23`` against a
    non-native data file must FAIL the gate.

    This replicates the F1/F19 keystone laundering scenario: an out-of-sync
    METRICS.yaml that asserts a richer count than the current data file
    can support. The fix in ``check_metrics_fresh.py:check_roundtrip_status_distribution``
    re-classifies every row via the same ``_status()`` logic as the
    regenerator and compares the resulting count to the committed value.

    To isolate the test from the live tree, we copy the gate into a
    minimal sandbox with a forged METRICS.yaml and a non-native JSONL.
    """
    sandbox = tmp_path / "sandbox"
    (sandbox / "cogant" / "evaluation" / "dataset").mkdir(parents=True)
    (sandbox / "tools").mkdir()

    # 1. Copy the gate script into the sandbox so its ``REPO_ROOT`` anchor
    #    resolves to the sandbox (the gate uses Path(__file__).parent.parent).
    (sandbox / "tools" / "check_metrics_fresh.py").write_text(GATE.read_text())

    # 2. Write a non-native JSONL with
    #    THREE rows, all v0.5 (no role_preservation_score, no roundtrip_status).
    jsonl = sandbox / "cogant" / "evaluation" / "dataset" / "roundtrip_results.jsonl"
    non_native_rows = [
        {"rank": 1, "group": "zoo", "repo": "fake_a", "tier": "ISOMORPHIC", "epsilon": 1.0},
        {"rank": 2, "group": "zoo", "repo": "fake_b", "tier": "ISOMORPHIC", "epsilon": 1.0},
        {"rank": 3, "group": "rw", "repo": "fake_c", "tier": "APPROXIMATE", "epsilon": 0.6},
    ]
    jsonl.write_text("\n".join(json.dumps(r) for r in non_native_rows) + "\n")

    # 3. Write a LAUNDERED METRICS.yaml that claims all 3 are role-preserved
    #    against this non-native data — the gate must catch this.
    metrics_path = sandbox / "cogant" / "evaluation" / "METRICS.yaml"
    metrics = {
        "schema_version": "1.0",
        "generator_git_sha": "deadbeef" * 5,  # gate will skip git check if /sandbox isn't a repo
        "testing": {"coverage_percent": 95.0},
        "evaluation": {
            "roundtrip": {
                "total_targets": 3,
                "role_preserved_count": 3,  # WRONG — should be 0 (all NON_NATIVE)
                "strict_isomorphism_count": 3,  # WRONG — should be 0
                "drift_count": 0,
                "failed_count": 0,
                "non_native_count": 3,
                "role_preservation_score_source": "epsilon_proxy",
                "mean_role_preservation_score": None,
                "median_role_preservation_score": None,
                "min_role_preservation_score": None,
                "max_role_preservation_score": None,
            },
        },
    }
    metrics_path.write_text(yaml.safe_dump(metrics))

    # 4. Run the gate from the sandbox; the SHA check will skip because
    #    sandbox is not a git repo. Coverage check will skip because
    #    coverage.json is absent. Only the new distribution check should
    #    drive the verdict.
    result = subprocess.run(
        [sys.executable, str(sandbox / "tools" / "check_metrics_fresh.py")],
        capture_output=True,
        text=True,
        cwd=sandbox,
        check=False,
    )
    assert result.returncode == 1, (
        "Laundered METRICS.yaml passed the freshness gate — regression in the "
        f"roundtrip-status distribution check.\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert "role_preserved_count" in combined
    assert "NON_NATIVE" in combined or "laundering" in combined.lower() or "live classification" in combined


def test_freshness_gate_passes_when_metrics_match_non_native_data(tmp_path: Path) -> None:
    """The honest case: METRICS.yaml asserts 0/0/0/0 against non-native data.
    The gate must pass.
    """
    sandbox = tmp_path / "sandbox"
    (sandbox / "cogant" / "evaluation" / "dataset").mkdir(parents=True)
    (sandbox / "tools").mkdir()
    (sandbox / "tools" / "check_metrics_fresh.py").write_text(GATE.read_text())
    jsonl = sandbox / "cogant" / "evaluation" / "dataset" / "roundtrip_results.jsonl"
    non_native_rows = [
        {"rank": 1, "group": "zoo", "repo": "fake_a", "tier": "ISOMORPHIC", "epsilon": 1.0},
        {"rank": 2, "group": "zoo", "repo": "fake_b", "tier": "ISOMORPHIC", "epsilon": 1.0},
    ]
    jsonl.write_text("\n".join(json.dumps(r) for r in non_native_rows) + "\n")
    metrics_path = sandbox / "cogant" / "evaluation" / "METRICS.yaml"
    metrics = {
        "schema_version": "1.0",
        "generator_git_sha": "deadbeef" * 5,
        "testing": {"coverage_percent": 95.0},
        "evaluation": {
            "roundtrip": {
                "total_targets": 2,
                "role_preserved_count": 0,  # Honest: all NON_NATIVE
                "strict_isomorphism_count": 0,
                "drift_count": 0,
                "failed_count": 0,
                "non_native_count": 2,
                "role_preservation_score_source": "epsilon_proxy",
                "mean_role_preservation_score": None,
                "median_role_preservation_score": None,
                "min_role_preservation_score": None,
                "max_role_preservation_score": None,
            },
        },
    }
    metrics_path.write_text(yaml.safe_dump(metrics))
    result = subprocess.run(
        [sys.executable, str(sandbox / "tools" / "check_metrics_fresh.py")],
        capture_output=True,
        text=True,
        cwd=sandbox,
        check=False,
    )
    assert result.returncode == 0, (
        f"Honest non-native METRICS.yaml failed the freshness gate:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_freshness_gate_strict_detects_dirty_worktree(tmp_path: Path) -> None:
    """``generator_git_sha`` only binds committed HEAD, so strict mode must
    fail when the worktree carries uncommitted changes.
    """
    sandbox = tmp_path / "sandbox"
    (sandbox / "cogant" / "evaluation" / "dataset").mkdir(parents=True)
    (sandbox / "tools").mkdir()
    (sandbox / "tools" / "check_metrics_fresh.py").write_text(GATE.read_text())
    jsonl = sandbox / "cogant" / "evaluation" / "dataset" / "roundtrip_results.jsonl"
    jsonl.write_text(json.dumps({"tier": "ISOMORPHIC", "epsilon": 1.0}) + "\n")
    coverage = sandbox / "cogant" / "coverage.json"
    coverage.write_text(json.dumps({"totals": {"percent_covered": 95.0}}))

    subprocess.run(["git", "init"], cwd=sandbox, capture_output=True, text=True, check=True)
    subprocess.run(["git", "add", "."], cwd=sandbox, capture_output=True, text=True, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=COGANT Test",
            "-c",
            "user.email=cogant-test@example.com",
            "commit",
            "-m",
            "seed freshness gate sandbox",
        ],
        cwd=sandbox,
        capture_output=True,
        text=True,
        check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=sandbox,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    metrics_path = sandbox / "cogant" / "evaluation" / "METRICS.yaml"
    metrics = {
        "schema_version": "1.0",
        "generator_git_sha": head,
        "testing": {"coverage_percent": 95.0},
        "evaluation": {
            "roundtrip": {
                "total_targets": 1,
                "role_preserved_count": 0,
                "strict_isomorphism_count": 0,
                "drift_count": 0,
                "failed_count": 0,
                "non_native_count": 1,
                "role_preservation_score_source": "epsilon_proxy",
                "mean_role_preservation_score": None,
                "median_role_preservation_score": None,
                "min_role_preservation_score": None,
                "max_role_preservation_score": None,
            },
        },
    }
    metrics_path.write_text(yaml.safe_dump(metrics))

    default_result = subprocess.run(
        [sys.executable, str(sandbox / "tools" / "check_metrics_fresh.py")],
        capture_output=True,
        text=True,
        cwd=sandbox,
        check=False,
    )
    assert default_result.returncode == 0
    assert "worktree has" in default_result.stderr

    strict_result = subprocess.run(
        [sys.executable, str(sandbox / "tools" / "check_metrics_fresh.py"), "--fail-on-dirty"],
        capture_output=True,
        text=True,
        cwd=sandbox,
        check=False,
    )
    assert strict_result.returncode == 1
    assert "generator_git_sha only binds committed HEAD" in (
        strict_result.stdout + strict_result.stderr
    )


def _git(sandbox: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@e.x", *args],
        cwd=sandbox,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _seed_sandbox(tmp_path: Path) -> Path:
    """A minimal git repo with a metric source file, dataset, coverage, and gate."""
    sandbox = tmp_path / "sandbox"
    (sandbox / "cogant" / "py" / "cogant").mkdir(parents=True)
    (sandbox / "cogant" / "evaluation" / "dataset").mkdir(parents=True)
    (sandbox / "tools").mkdir()
    (sandbox / "manuscript").mkdir()
    (sandbox / "tools" / "check_metrics_fresh.py").write_text(GATE.read_text())
    (sandbox / "cogant" / "py" / "cogant" / "core.py").write_text("X = 1\n")
    (sandbox / "manuscript" / "ch.md").write_text("draft\n")
    (sandbox / "cogant" / "evaluation" / "dataset" / "roundtrip_results.jsonl").write_text(
        json.dumps({"tier": "ISOMORPHIC", "epsilon": 1.0}) + "\n"
    )
    (sandbox / "cogant" / "coverage.json").write_text(json.dumps({"totals": {"percent_covered": 95.0}}))
    _git(sandbox, "init")
    _git(sandbox, "add", ".")
    _git(sandbox, "commit", "-m", "seed source")
    return sandbox


def _write_metrics(sandbox: Path, sha: str) -> None:
    (sandbox / "cogant" / "evaluation" / "METRICS.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "generator_git_sha": sha,
                "testing": {"coverage_percent": 95.0},
                "evaluation": {
                    "roundtrip": {
                        "total_targets": 1,
                        "role_preserved_count": 0,
                        "strict_isomorphism_count": 0,
                        "drift_count": 0,
                        "failed_count": 0,
                        "non_native_count": 1,
                        "role_preservation_score_source": "epsilon_proxy",
                        "mean_role_preservation_score": None,
                        "median_role_preservation_score": None,
                        "min_role_preservation_score": None,
                        "max_role_preservation_score": None,
                    },
                },
            }
        )
    )


def _run_in(sandbox: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(sandbox / "tools" / "check_metrics_fresh.py")],
        capture_output=True,
        text=True,
        cwd=sandbox,
        check=False,
    )


def test_freshness_gate_passes_when_only_artifacts_changed_since_sha(tmp_path: Path) -> None:
    """C1: the committed tip can never satisfy ``generator_git_sha == HEAD``
    (the metrics commit advances HEAD). The gate must instead pass when only
    NON-metric-affecting paths (METRICS.yaml, manuscript, tooling) changed
    since ``generator_git_sha``.
    """
    sandbox = _seed_sandbox(tmp_path)
    base = _git(sandbox, "rev-parse", "HEAD")
    _write_metrics(sandbox, base)  # regenerated against `base`'s source tree
    (sandbox / "manuscript" / "ch.md").write_text("revised prose\n")  # non-source edit
    _git(sandbox, "add", ".")
    _git(sandbox, "commit", "-m", "commit metrics + manuscript (HEAD now != base)")

    result = _run_in(sandbox)
    assert result.returncode == 0, (
        "gate must treat artifact/manuscript-only changes since generator_git_sha "
        f"as fresh.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "is in sync" in result.stdout


def test_freshness_gate_fails_when_source_changed_since_sha(tmp_path: Path) -> None:
    """The dual: if metric-affecting source (package code) changed since
    ``generator_git_sha``, the metrics are out of sync and the gate must fail."""
    sandbox = _seed_sandbox(tmp_path)
    base = _git(sandbox, "rev-parse", "HEAD")
    _write_metrics(sandbox, base)
    (sandbox / "cogant" / "py" / "cogant" / "core.py").write_text("X = 2  # changed\n")
    _git(sandbox, "add", ".")
    _git(sandbox, "commit", "-m", "change package source after metrics")

    result = _run_in(sandbox)
    assert result.returncode == 1, (
        "gate must flag metrics when package source changed since "
        f"generator_git_sha.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "metric-affecting source changed" in (result.stdout + result.stderr)


def test_classify_row_matches_regenerator_logic() -> None:
    """Sanity test: ``_classify_row`` in check_metrics_fresh must produce
    the same status string as ``_status()`` in regenerate_metrics for every
    relevant input shape. If a regen-side change drifts from this gate, the
    two will disagree silently and the gate stops binding truth. Pin a
    table of canonical (input → expected status) cases.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        # Force a fresh import so any in-flight edit to the file is picked up.
        import importlib
        import check_metrics_fresh as cmf

        importlib.reload(cmf)
    finally:
        sys.path.pop(0)

    cases = [
        # Non-native rows (no role_preservation_score field) — NON_NATIVE
        ({"tier": "ISOMORPHIC", "epsilon": 1.0}, "NON_NATIVE"),
        ({"tier": "APPROXIMATE", "epsilon": 0.6}, "NON_NATIVE"),
        # v0.6 rows with explicit roundtrip_status — pass through
        ({"roundtrip_status": "ROLE_PRESERVED", "role_preservation_score": 1.0}, "ROLE_PRESERVED"),
        ({"roundtrip_status": "STRUCTURALLY_ISOMORPHIC", "role_preservation_score": 1.0}, "STRUCTURALLY_ISOMORPHIC"),
        # v0.6 rows without explicit status but with role_preservation_score
        # (derived from tier)
        ({"role_preservation_score": 0.9, "tier": "ISOMORPHIC"}, "ROLE_PRESERVED"),
        ({"role_preservation_score": 0.6, "tier": "APPROXIMATE"}, "DRIFT"),
        ({"role_preservation_score": 0.3, "tier": "DIVERGENT"}, "DRIFT"),
        ({"role_preservation_score": 0.0, "error": "boom"}, "FAILED"),
    ]
    for entry, expected in cases:
        got = cmf._classify_row(entry)
        assert got == expected, f"_classify_row({entry!r}) = {got!r}, expected {expected!r}"


def test_freshness_gate_detects_epsilon_proxy_scores_mislabeled_as_native(tmp_path: Path) -> None:
    """Epsilon-only rows must not populate native role-score aggregates."""
    sandbox = tmp_path / "sandbox"
    (sandbox / "cogant" / "evaluation" / "dataset").mkdir(parents=True)
    (sandbox / "tools").mkdir()
    (sandbox / "tools" / "check_metrics_fresh.py").write_text(GATE.read_text())
    (sandbox / "cogant" / "evaluation" / "dataset" / "roundtrip_results.jsonl").write_text(
        json.dumps({"rank": 1, "group": "zoo", "repo": "fake", "tier": "ISOMORPHIC", "epsilon": 1.0})
        + "\n"
    )
    metrics = {
        "schema_version": "1.0",
        "generator_git_sha": "deadbeef" * 5,
        "testing": {"coverage_percent": 95.0},
        "evaluation": {
            "roundtrip": {
                "total_targets": 1,
                "role_preserved_count": 0,
                "strict_isomorphism_count": 0,
                "drift_count": 0,
                "failed_count": 0,
                "non_native_count": 1,
                "role_preservation_score_source": "v0.6_native",  # WRONG: no native field exists
                "mean_role_preservation_score": 1.0,  # WRONG: epsilon proxy, not native s_role
                "median_role_preservation_score": 1.0,
                "min_role_preservation_score": 1.0,
                "max_role_preservation_score": 1.0,
            },
        },
    }
    (sandbox / "cogant" / "evaluation" / "METRICS.yaml").write_text(yaml.safe_dump(metrics))

    result = subprocess.run(
        [sys.executable, str(sandbox / "tools" / "check_metrics_fresh.py")],
        capture_output=True,
        text=True,
        cwd=sandbox,
        check=False,
    )
    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "role_preservation_score_source" in combined
    assert "mean_role_preservation_score" in combined
