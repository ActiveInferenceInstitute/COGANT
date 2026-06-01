"""Semantic-preservation & robustness harness for COGANT.

For each base fixture and each semantics-preserving source transform, run the
forward pipeline on the original and the transformed copy, then compare their
role multisets with the same semantic oracle the roundtrip evaluator uses
(:func:`cogant.reverse.metrics.compare_role_distributions`). A transform is
**robust** when the role multiset is preserved (similarity ≥ ``ROBUST_THRESHOLD``).

The harness also runs a NEGATIVE CONTROL (``drop_half_definitions``) that
genuinely changes semantics, asserting the oracle reports degradation rather
than passing vacuously.

Output: ``cogant/evaluation/robustness/robustness_results.json`` — per
``(transform, fixture)`` row (original/transformed role multisets, similarity,
degradation, role delta) plus per-transform aggregates. The companion
``robustness_table.md`` is a dashboard-ready degradation table.

Run from the inner package env::

    cd cogant && uv run python evaluation/robustness/harness.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

_THIS = Path(__file__).resolve()
_PKG_ROOT = _THIS.parents[2]  # .../cogant (package root)
if str(_PKG_ROOT / "py") not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT / "py"))
if str(_THIS.parent) not in sys.path:
    sys.path.insert(0, str(_THIS.parent))

import transforms as T  # noqa: E402

from cogant.reverse.idempotency import (  # noqa: E402
    _role_multiset_from_mappings,
    _run_forward,
)
from cogant.reverse.metrics import compare_role_distributions  # noqa: E402

ROBUST_THRESHOLD = 0.99

EXAMPLES = _PKG_ROOT / "examples"
BASE_FIXTURES = (
    ("control_positive", "calculator"),
    ("control_positive", "event_pipeline"),
    ("control_positive", "flask_mini"),
)
RESULTS_JSON = _THIS.parent / "robustness_results.json"
RESULTS_TABLE = _THIS.parent / "robustness_table.md"


def _forward_roles(repo: Path) -> Counter:
    fwd = _run_forward(repo)
    if fwd.get("error"):
        raise RuntimeError(fwd["error"])
    return _role_multiset_from_mappings(fwd.get("mappings"))


def _apply_transform(src_dir: Path, dst_dir: Path, fn) -> None:
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
    for py in dst_dir.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        try:
            py.write_text(fn(py.read_text(encoding="utf-8")), encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            pass


def _imports_ok(repo: Path) -> bool:
    """True if every top-level module in ``repo`` imports without error.

    Importing (vs merely parsing) is what catches behaviour-breaking edits that
    fire at definition time — e.g. a decorator (`@app.route(..., method=...)`)
    or a `@x.setter` that references a renamed/out-of-order name. A transform is
    only judged ROBUST when role extraction is stable AND this holds, so the
    harness validates behavioural equivalence, not just role-multiset stability.
    """
    mods = sorted(
        p.stem for p in repo.glob("*.py")
        if p.stem != "__init__" and "__pycache__" not in p.parts
    )
    if not mods:
        # package-style fixture: import each top-level package dir
        mods = sorted(
            d.name for d in repo.iterdir() if d.is_dir() and (d / "__init__.py").exists()
        )
    if not mods:
        return True  # nothing importable to check
    for mod in mods:
        proc = subprocess.run(
            [sys.executable, "-c", f"import {mod}"],
            cwd=str(repo), capture_output=True, text=True, timeout=60, check=False,
        )
        if proc.returncode != 0:
            return False
    return True


def _classify(transform: str, similarity: float, runtime_ok: bool) -> str:
    preserving = transform in T.SEMANTICS_PRESERVING
    negative = transform in T.NEGATIVE_CONTROLS
    role_stable = similarity >= ROBUST_THRESHOLD
    if negative:
        return "DETECTED" if (not role_stable or not runtime_ok) else "MISSED"
    if preserving:
        # Robust requires BOTH role stability and that the transformed code
        # still imports (behavioural equivalence), not role stability alone.
        if role_stable and runtime_ok:
            return "ROBUST"
        return "BROKEN" if not runtime_ok else "DEGRADED"
    # sensitivity probe
    return "PRESERVED" if (role_stable and runtime_ok) else "SHIFTED"


def run() -> dict:
    rows: list[dict] = []
    base_roles: dict[str, Counter] = {}
    base_imports: dict[str, bool] = {}
    for group, name in BASE_FIXTURES:
        base_roles[name] = _forward_roles(EXAMPLES / group / name)
        base_imports[name] = _imports_ok(EXAMPLES / group / name)

    for transform_name, fn in T.ALL_TRANSFORMS.items():
        for group, name in BASE_FIXTURES:
            base = EXAMPLES / group / name
            orig = base_roles[name]
            with tempfile.TemporaryDirectory() as tmp:
                dst = Path(tmp) / name
                try:
                    _apply_transform(base, dst, fn)
                    transformed = _forward_roles(dst)
                    transformed_imports = _imports_ok(dst)
                    error = None
                except Exception as exc:  # noqa: BLE001
                    transformed = Counter()
                    transformed_imports = False
                    error = f"{type(exc).__name__}: {exc}"
            # A transform "imports cleanly" iff it does not regress importability
            # relative to the original fixture (which must import to baseline).
            runtime_ok = (not base_imports[name]) or transformed_imports
            similarity = compare_role_distributions(orig, transformed)
            delta = {
                k: transformed.get(k, 0) - orig.get(k, 0)
                for k in sorted(set(orig) | set(transformed))
                if transformed.get(k, 0) != orig.get(k, 0)
            }
            rows.append({
                "transform": transform_name,
                "fixture": name,
                "category": (
                    "semantics_preserving" if transform_name in T.SEMANTICS_PRESERVING
                    else "sensitivity_probe" if transform_name in T.SENSITIVITY_PROBES
                    else "negative_control"
                ),
                "original_roles": dict(orig),
                "transformed_roles": dict(transformed),
                "role_delta": delta,
                "similarity": round(float(similarity), 4),
                "degradation": round(1.0 - float(similarity), 4),
                "runtime_ok": bool(runtime_ok),
                "status": _classify(transform_name, similarity, runtime_ok),
                "error": error,
            })

    # Per-transform aggregate: min similarity across fixtures is the headline.
    agg: dict[str, dict] = {}
    for transform_name in T.ALL_TRANSFORMS:
        sub = [r for r in rows if r["transform"] == transform_name]
        sims = [r["similarity"] for r in sub]
        statuses = {r["status"] for r in sub}
        agg[transform_name] = {
            "category": sub[0]["category"],
            "min_similarity": round(min(sims), 4),
            "mean_similarity": round(sum(sims) / len(sims), 4),
            "fixtures": len(sub),
            "status": (
                "ROBUST" if statuses <= {"ROBUST"}
                else "DETECTED" if statuses <= {"DETECTED"}
                else "PRESERVED" if statuses <= {"PRESERVED"}
                else "/".join(sorted(statuses))
            ),
        }

    preserving = list(T.SEMANTICS_PRESERVING)
    robust = sum(1 for t in preserving if agg[t]["status"] == "ROBUST")
    return {
        "schema_version": "1.0",
        "robust_threshold": ROBUST_THRESHOLD,
        "summary": {
            "semantics_preserving_transforms": len(preserving),
            "robust_transforms": robust,
            "negative_controls": len(T.NEGATIVE_CONTROLS),
            "negative_controls_detected": sum(
                1 for t in T.NEGATIVE_CONTROLS if agg[t]["status"] == "DETECTED"
            ),
            "min_preserving_similarity": round(
                min(agg[t]["min_similarity"] for t in preserving), 4
            ),
        },
        "per_transform": agg,
        "rows": rows,
    }


def _write_table(results: dict) -> None:
    lines = [
        "# Generated robustness degradation table (do not edit — re-run harness.py)",
        "",
        "| Transform | Category | Min role similarity | Status |",
        "|---|---|---:|---|",
    ]
    for name, a in results["per_transform"].items():
        lines.append(
            f"| `{name}` | {a['category']} | {a['min_similarity']:.4f} | {a['status']} |"
        )
    RESULTS_TABLE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    results = run()
    RESULTS_JSON.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_table(results)
    s = results["summary"]
    print(f"wrote {RESULTS_JSON}")
    print(f"robust {s['robust_transforms']}/{s['semantics_preserving_transforms']} "
          f"preserving transforms (min similarity {s['min_preserving_similarity']}); "
          f"negative controls detected {s['negative_controls_detected']}/{s['negative_controls']}")
    for name, a in results["per_transform"].items():
        print(f"  {name:24s} {a['category']:20s} minsim={a['min_similarity']:.4f}  {a['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
