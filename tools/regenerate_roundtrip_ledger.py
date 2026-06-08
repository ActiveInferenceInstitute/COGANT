#!/usr/bin/env python3
"""Regenerate the native v0.6 roundtrip ledger ``roundtrip_results.jsonl``.

Runs ``verify_repo_roundtrip`` (forward → reverse → forward) on every
locally-available evaluation fixture (``examples/{zoo,control_positive,
real_world}/``) and writes a **native v0.6** ledger carrying
``roundtrip_status``, ``role_preservation_score``, per-role multiset counts,
graph size, file/LOC, and the scaffolding diagnostic inputs.

Each row is self-classifying for ``tools/regenerate_metrics.py`` /
``tools/check_metrics_fresh.py``: because it carries an explicit
``roundtrip_status``, those tools route it through the native path, so
``METRICS.yaml`` reports native v0.6 counts.

Run from the inner package env so ``cogant`` imports resolve::

    cd cogant && uv run python ../tools/regenerate_roundtrip_ledger.py

JS-only fixtures (no ``*.py`` sources) are skipped — the ledger stays on the
Python front end that the manuscript scopes its roundtrip claims to.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
_REPO_ROOT = _TOOLS.parent
_PKG_ROOT = _REPO_ROOT / "cogant"
if (_PKG_ROOT / "py" / "cogant" / "__init__.py").exists():
    sys.path.insert(0, str(_PKG_ROOT / "py"))
else:  # linked under projects/working/cogant/ — fall back to a sibling layout
    sys.path.insert(0, str(_REPO_ROOT / "py"))

from cogant.reverse.idempotency import (  # noqa: E402
    ROLE_PRESERVATION_THRESHOLD,
    verify_repo_roundtrip,
)

EXAMPLES = _PKG_ROOT / "examples"
GROUPS = (
    ("zoo", EXAMPLES / "zoo"),
    ("control_positive", EXAMPLES / "control_positive"),
    ("real_world", EXAMPLES / "real_world"),
)
LEDGER_PATH = _PKG_ROOT / "evaluation" / "dataset" / "roundtrip_results.jsonl"

# Stable field order for readable, diff-friendly rows.
_FIELD_ORDER = (
    "rank", "group", "repo", "roundtrip_status", "role_preservation_score",
    "structurally_isomorphic", "matrix_score", "structural_score",
    "generated_code_ok",
    "orig_n_hidden", "orig_n_obs", "orig_n_actions",
    "synth_n_hidden", "synth_n_obs", "synth_n_actions",
    "shape_match", "node_count", "edge_count", "file_count", "loc",
    "fixture_group", "elapsed_s", "error",
)


def _count_source(repo: Path) -> tuple[int, int]:
    files = [f for f in repo.rglob("*.py") if "__pycache__" not in f.parts]
    loc = 0
    for f in files:
        try:
            loc += sum(1 for _ in f.open(encoding="utf-8", errors="replace"))
        except OSError:
            pass
    return len(files), loc


def _role_counts(roles: dict[str, int]) -> tuple[int, int, int]:
    roles = roles or {}
    return (
        int(roles.get("HIDDEN_STATE", 0)),
        int(roles.get("OBSERVATION", 0)),
        int(roles.get("ACTION", 0)),
    )


def run_target(group: str, repo: Path) -> dict:
    start = time.perf_counter()
    files, loc = _count_source(repo)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            res = verify_repo_roundtrip(
                repo, output_dir=tmp, role_threshold=ROLE_PRESERVATION_THRESHOLD
            )
        oh, oo, oa = _role_counts(res.original_roles)
        sh, so, sa = _role_counts(res.synthesized_roles)
        summary = res.original_graph_summary or {}
        return {
            "group": group,
            "repo": repo.name,
            "roundtrip_status": str(res.roundtrip_status),
            "role_preservation_score": round(float(res.role_preservation_score), 4),
            "structurally_isomorphic": bool(res.structurally_isomorphic),
            "matrix_score": round(float(res.matrix_score), 4),
            "structural_score": round(float(res.structural_score), 4),
            "generated_code_ok": bool(res.generated_code_ok),
            "orig_n_hidden": oh, "orig_n_obs": oo, "orig_n_actions": oa,
            "synth_n_hidden": sh, "synth_n_obs": so, "synth_n_actions": sa,
            "shape_match": dict(res.shape_match or {}),
            "node_count": int(summary.get("node_count", 0)),
            "edge_count": int(summary.get("edge_count", 0)),
            "file_count": files,
            "loc": loc,
            "fixture_group": group,
            "elapsed_s": round(time.perf_counter() - start, 3),
        }
    except Exception as exc:  # noqa: BLE001 — any failure is a FAILED row, never fatal
        return {
            "group": group,
            "repo": repo.name,
            "roundtrip_status": "FAILED",
            "role_preservation_score": 0.0,
            "structurally_isomorphic": False,
            "matrix_score": 0.0,
            "structural_score": 0.0,
            "generated_code_ok": False,
            "orig_n_hidden": 0, "orig_n_obs": 0, "orig_n_actions": 0,
            "synth_n_hidden": 0, "synth_n_obs": 0, "synth_n_actions": 0,
            "shape_match": {},
            "node_count": 0, "edge_count": 0, "file_count": files, "loc": loc,
            "fixture_group": group,
            "elapsed_s": round(time.perf_counter() - start, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }


def _ordered(row: dict) -> dict:
    out = {k: row[k] for k in _FIELD_ORDER if k in row}
    out.update({k: v for k, v in row.items() if k not in out})
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only", action="append", default=None,
        help="Run only the named fixture(s) (repeatable); default: all.",
    )
    args = parser.parse_args(argv)

    rows: list[dict] = []
    for group, gdir in GROUPS:
        if not gdir.is_dir():
            continue
        for repo in sorted(p for p in gdir.iterdir() if p.is_dir()):
            if args.only and repo.name not in args.only:
                continue
            if not any(
                f for f in repo.rglob("*.py") if "__pycache__" not in f.parts
            ):
                print(f"[skip] {group}/{repo.name} (no Python sources)", flush=True)
                continue
            print(f"[roundtrip] {group}/{repo.name} ...", flush=True)
            rows.append(run_target(group, repo))

    # Rank by role-preservation score (desc), then group/name for stability.
    rows.sort(key=lambda r: (-r.get("role_preservation_score", 0.0), r["group"], r["repo"]))
    for i, row in enumerate(rows, start=1):
        row["rank"] = i

    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(
        "\n".join(json.dumps(_ordered(r)) for r in rows) + "\n", encoding="utf-8"
    )

    dist = Counter(r["roundtrip_status"] for r in rows)
    print(f"\nWrote {len(rows)} native rows -> {LEDGER_PATH}")
    print(f"status distribution: {dict(dist)}")
    rp = sum(dist[s] for s in ("ROLE_PRESERVED", "STRUCTURALLY_ISOMORPHIC"))
    print(f"role_preserved={rp}  strict_isomorphic={dist['STRUCTURALLY_ISOMORPHIC']}  "
          f"drift={dist['DRIFT']}  failed={dist['FAILED']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
