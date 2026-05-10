#!/usr/bin/env python3
"""Compare per-module Stmts/Cover in manuscript Table 9 to a live ``coverage`` report.

The table in ``manuscript/06_04_tests_mutation_and_benchmarks.md`` ({#tbl:coverage-stmt-modules})
is maintained manually. After ``uv run pytest tests/ --cov=cogant`` in the **package root**
(``.../cogant/cogant/`` by default), run this script to detect drift from ``coverage report``.

Exit codes
----------
* ``0`` — all rows match (or no manuscript table / nothing to compare).
* ``1`` — mismatch, missing ``coverage`` data when ``--strict``, or table parse error.

Path layout (staging): ``projects_in_progress/cogant/{tools,manuscript,cogant/}`` with the
importable package under ``cogant/cogant/py/cogant/``; ``--package-root`` should point to the
directory that contains the inner ``cogant`` test tree and ``pyproject.toml`` used for ``pytest``."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def _default_paths() -> tuple[Path, Path]:
    """tools/ -> staging root; package root = staging/cogant/."""
    tools_dir = Path(__file__).resolve().parent
    staging = tools_dir.parent
    return staging / "manuscript" / "06_04_tests_mutation_and_benchmarks.md", staging / "cogant"


def _parse_table(md_path: Path) -> list[tuple[str, int, int]]:
    text = md_path.read_text(encoding="utf-8")
    rows: list[tuple[str, int, int]] = []
    in_table = False
    row_re = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|\s*(\d+)%\s*\|\s*$")
    for line in text.splitlines():
        if line.strip().startswith("| Module | Stmts | Cover |"):
            in_table = True
            continue
        if in_table and line.strip().startswith(": Table 9"):
            break
        if not in_table:
            continue
        m = row_re.match(line)
        if m:
            mod, stmts, cover = m.group(1), int(m.group(2)), int(m.group(3))
            rows.append((mod, stmts, cover))
    return rows


def _file_to_module(path: str) -> str:
    """``cogant/translate/engine.py`` -> ``cogant.translate.engine``."""
    p = path.strip()
    if not p.endswith(".py"):
        return ""
    return p[:-3].replace("/", ".")


def _parse_coverage_report(stdout: str) -> dict[str, tuple[int, int]]:
    """Return module -> (stmts, cover_percent). Skips non-module header lines."""
    out: dict[str, tuple[int, int]] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("---") or line.startswith("Name "):
            continue
        if line == "TOTAL":
            break
        parts = line.split()
        if len(parts) < 4:
            continue
        path, stmts_s, _miss, cover_s = parts[0], parts[1], parts[2], parts[3]
        if not path.startswith("cogant/"):
            continue
        mod = _file_to_module(path)
        if not mod:
            continue
        try:
            stmts = int(stmts_s)
        except ValueError:
            continue
        cov = int(cover_s.rstrip("%"))
        out[mod] = (stmts, cov)
    return out


def _run_coverage_report(package_root: Path) -> str | None:
    """Run ``uv run coverage report`` in package_root; return stdout or None on failure."""
    try:
        proc = subprocess.run(
            [
                "uv",
                "run",
                "coverage",
                "report",
                "--precision=0",
            ],
            cwd=package_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        if err:
            print(f"check_coverage_table: coverage stderr: {err}", file=sys.stderr)
        return None
    return proc.stdout


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--manuscript",
        type=Path,
        default=None,
        help="Path to 06_04_tests_mutation_and_benchmarks.md (default: beside tools/)",
    )
    p.add_argument(
        "--package-root",
        type=Path,
        default=None,
        help="Directory with pytest/coverage config (default: <staging>/cogant)",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if .coverage is missing or any row mismatches (for CI).",
    )
    args = p.parse_args()
    ms_path, pkg_default = _default_paths()
    manuscript = args.manuscript or ms_path
    package_root = (args.package_root or pkg_default).resolve()

    if not manuscript.is_file():
        print(f"check_coverage_table: manuscript not found: {manuscript}", file=sys.stderr)
        return 1 if args.strict else 0

    table = _parse_table(manuscript)
    if not table:
        print("check_coverage_table: no table rows parsed (expected | `cogant.…` | N | M% |).", file=sys.stderr)
        return 1 if args.strict else 0

    report = _run_coverage_report(package_root)
    if report is None:
        print(
            f"check_coverage_table: could not run `uv run coverage report` in {package_root}. "
            "Run `uv run pytest tests/ --cov=cogant` there first to produce .coverage.",
            file=sys.stderr,
        )
        return 1 if args.strict else 0

    live = _parse_coverage_report(report)
    if not live:
        print("check_coverage_table: parsed zero modules from coverage report output.", file=sys.stderr)
        return 1 if args.strict else 0

    bad: list[str] = []
    for mod, st_tbl, co_tbl in table:
        if mod not in live:
            bad.append(f"  {mod}: not in coverage report (table Stmts={st_tbl} Cover={co_tbl}%)")
            continue
        st_l, co_l = live[mod]
        if st_tbl != st_l or co_tbl != co_l:
            bad.append(
                f"  {mod}: table Stmts={st_tbl} Cover={co_tbl}% vs report Stmts={st_l} Cover={co_l}%"
            )

    if bad:
        print("check_coverage_table: mismatches:\n" + "\n".join(bad), file=sys.stderr)
        return 1

    print(f"check_coverage_table: OK ({len(table)} rows match coverage report in {package_root})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
