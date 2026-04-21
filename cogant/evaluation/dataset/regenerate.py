#!/usr/bin/env python3
"""Regenerate COGANT roundtrip evaluation dataset from zoo fixtures.

Runs ``cogant.reverse.idempotency.verify_repo_roundtrip()`` on every zoo
fixture and curated real-world example, and ``cogant roundtrip`` (subprocess)
for the third-party library fixtures in ``evaluation/eval_repos/``.

Outputs ``evaluation/dataset/roundtrip_results.jsonl`` — one JSON object per line,
with fields:

    rank, group, repo, epsilon, tier, orig_n_hidden, orig_n_obs,
    orig_n_actions, synth_n_hidden, synth_n_obs, synth_n_actions, elapsed_s

Usage::

    cd /path/to/cogant   # repository root containing ``py/`` and ``examples/``
    python evaluation/dataset/regenerate.py [--output evaluation/dataset/roundtrip_results.jsonl]

The script is deterministic given a fixed COGANT version.  Re-running it on
the same installation should produce byte-identical ε values modulo
wall-clock elapsed times.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]  # inner COGANT repo root (py/, examples/, …)
ZOO_DIR = REPO_ROOT / "examples" / "zoo"
RWEX_DIR = REPO_ROOT / "examples" / "real_world"
RW_DIR = REPO_ROOT / "evaluation" / "eval_repos"
DEFAULT_OUTPUT = REPO_ROOT / "evaluation" / "dataset" / "roundtrip_results.jsonl"

TIER_THRESHOLDS = {"ISOMORPHIC": 0.8, "APPROXIMATE": 0.5}


def classify(epsilon: float) -> str:
    if epsilon >= TIER_THRESHOLDS["ISOMORPHIC"]:
        return "ISOMORPHIC"
    if epsilon >= TIER_THRESHOLDS["APPROXIMATE"]:
        return "APPROXIMATE"
    return "DIVERGENT"


def _shape_to_ints(shape: list[int] | None, idx: int) -> int:
    """Extract a single dimension from a GNN shape list; return 0 on failure."""
    if shape and len(shape) > idx:
        return int(shape[idx])
    return 0


# ---------------------------------------------------------------------------
# Per-group runners
# ---------------------------------------------------------------------------


def run_zoo_fixture(fixture_path: Path) -> dict[str, Any]:
    """Run roundtrip via cogant Python API on a zoo fixture directory.

    ``verify_repo_roundtrip`` now returns a ``RoundtripResult`` dataclass
    (post-wave-16). Shape fields are derived from the role multisets
    (``original_roles`` / ``synthesized_roles``) rather than a deprecated
    ``state_space_shape`` list.
    """
    try:
        from cogant.reverse.idempotency import verify_repo_roundtrip  # type: ignore[import]
    except ImportError as exc:
        raise SystemExit(
            f"cogant is not installed in this environment: {exc}\n"
            "Run `uv sync` or `pip install -e .` from the cogant project root."
        ) from exc

    t0 = time.perf_counter()
    result = verify_repo_roundtrip(fixture_path)
    elapsed = time.perf_counter() - t0

    orig_roles: dict[str, int] = result.original_roles
    synth_roles: dict[str, int] = result.synthesized_roles

    return {
        "epsilon": float(result.role_match_score),
        "orig_n_hidden": orig_roles.get("HIDDEN_STATE", 0),
        "orig_n_obs": orig_roles.get("OBSERVATION", 0),
        "orig_n_actions": orig_roles.get("ACTION", 0),
        "synth_n_hidden": synth_roles.get("HIDDEN_STATE", 0),
        "synth_n_obs": synth_roles.get("OBSERVATION", 0),
        "synth_n_actions": synth_roles.get("ACTION", 0),
        "elapsed_s": round(elapsed, 3),
    }


def run_subprocess_roundtrip(target_path: Path) -> dict[str, Any]:
    """Run roundtrip via ``cogant roundtrip <path> --json`` subprocess.

    Uses the ``cogant`` console-script entry-point rather than
    ``python -m cogant``, which is not supported post-wave-16. The JSON
    payload now carries ``original_roles`` / ``synthesized_roles`` dicts
    (role-name → count) instead of the former ``original_gnn.state_space_shape``
    list.
    """
    # Locate the cogant console-script inside the venv managed by uv.
    # Prefer the venv binary so we don't rely on a global install.
    venv_cogant = REPO_ROOT / ".venv" / "bin" / "cogant"
    cogant_bin = str(venv_cogant) if venv_cogant.exists() else "cogant"

    t0 = time.perf_counter()
    result = subprocess.run(
        [cogant_bin, "roundtrip", str(target_path), "--json"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=300,
    )
    elapsed = time.perf_counter() - t0

    if result.returncode not in (0, 1):
        # rc=1 means not-isomorphic but the run succeeded; only hard errors matter.
        raise RuntimeError(
            f"cogant roundtrip failed for {target_path.name} "
            f"(rc={result.returncode}):\n{result.stderr[:2000]}"
        )

    # The CLI prints JSON to stdout; stderr carries log lines — strip those.
    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError(
            f"cogant roundtrip produced no JSON output for {target_path.name}."
            f"\nstderr: {result.stderr[:2000]}"
        )
    data = json.loads(stdout)

    orig_roles: dict[str, int] = data.get("original_roles", {})
    synth_roles: dict[str, int] = data.get("synthesized_roles", {})

    return {
        "epsilon": float(data.get("role_match_score", 0.0)),
        "orig_n_hidden": orig_roles.get("HIDDEN_STATE", 0),
        "orig_n_obs": orig_roles.get("OBSERVATION", 0),
        "orig_n_actions": orig_roles.get("ACTION", 0),
        "synth_n_hidden": synth_roles.get("HIDDEN_STATE", 0),
        "synth_n_obs": synth_roles.get("OBSERVATION", 0),
        "synth_n_actions": synth_roles.get("ACTION", 0),
        "elapsed_s": round(elapsed, 3),
    }


# ---------------------------------------------------------------------------
# Target catalogue
# ---------------------------------------------------------------------------

# Each entry: (rank, group, repo_name, path_resolver)
# path_resolver is a callable that returns the Path to evaluate.
TARGETS: list[tuple[int, str, str, str]] = [
    # rank, group, repo, subdir (relative to its group directory)
    (1, "zoo", "01_simple_state", "01_simple_state"),
    (2, "zoo", "02_observer", "02_observer"),
    (3, "zoo", "03_actor", "03_actor"),
    (4, "zoo", "04_pomdp_minimal", "04_pomdp_minimal"),
    (5, "zoo", "05_multi_factor", "05_multi_factor"),
    (6, "zoo", "06_hierarchical", "06_hierarchical"),
    (7, "zoo", "08_preferences", "08_preferences"),
    (8, "zoo", "11_sensor_fusion", "11_sensor_fusion"),
    (9, "rwex", "json_stdlib", "json_stdlib"),
    (10, "rwex", "requests_lib", "requests_lib"),
    (11, "zoo", "12_full_pomdp", "12_full_pomdp"),
    (12, "rw", "dateutil", "dateutil"),
    (13, "rw", "pyyaml", "pyyaml"),
    (14, "rwex", "flask_app", "flask_app"),
    (15, "zoo", "07_event_driven", "07_event_driven"),
    (16, "zoo", "10_constraint", "10_constraint"),
    (17, "zoo", "09_policy", "09_policy"),
    (18, "rw", "tqdm", "tqdm"),
    (19, "rw", "fastapi", "fastapi"),
    (20, "rw", "click", "click"),
    (21, "rw", "httpx", "httpx"),
    (22, "rw", "urllib3", "urllib3"),
    (23, "rw", "requests", "requests"),
]


def resolve_path(group: str, subdir: str) -> Path:
    if group == "zoo":
        return ZOO_DIR / subdir
    if group == "rwex":
        return RWEX_DIR / subdir
    if group == "rw":
        return RW_DIR / subdir
    raise ValueError(f"Unknown group: {group!r}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output .jsonl path (default: %(default)s)",
    )
    parser.add_argument(
        "--group",
        choices=["zoo", "rwex", "rw", "all"],
        default="all",
        help="Which target group to evaluate (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print targets without running evaluation",
    )
    args = parser.parse_args(argv)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for rank, group, repo, subdir in TARGETS:
        if args.group != "all" and group != args.group:
            continue

        target_path = resolve_path(group, subdir)
        if args.dry_run:
            status = "EXISTS" if target_path.exists() else "MISSING"
            print(f"[{rank:2d}] {group:4s}  {repo:<20s}  {target_path}  [{status}]")
            continue

        if not target_path.exists():
            print(
                f"[{rank:2d}] SKIP  {repo}: path not found: {target_path}",
                file=sys.stderr,
            )
            continue

        print(f"[{rank:2d}] {group:4s}  {repo:<20s} ...", end=" ", flush=True)
        try:
            if group in ("zoo", "rwex"):
                metrics = run_zoo_fixture(target_path)
            else:
                metrics = run_subprocess_roundtrip(target_path)

            epsilon = metrics["epsilon"]
            tier = classify(epsilon)
            row = {
                "rank": rank,
                "group": group,
                "repo": repo,
                "epsilon": epsilon,
                "tier": tier,
                **{k: v for k, v in metrics.items() if k != "epsilon"},
            }
            rows.append(row)
            print(f"ε={epsilon:.4f}  {tier}  ({metrics['elapsed_s']:.2f}s)")
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: {exc}", file=sys.stderr)
            continue

    if args.dry_run:
        return

    with output_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(rows)} rows to {output_path}")

    # Distribution summary
    from collections import Counter

    dist = Counter(r["tier"] for r in rows)
    total = len(rows)
    for tier in ("ISOMORPHIC", "APPROXIMATE", "DIVERGENT"):
        n = dist.get(tier, 0)
        print(f"  {tier}: {n}/{total} ({100 * n / total:.0f}%)" if total else f"  {tier}: 0")


if __name__ == "__main__":
    main()
