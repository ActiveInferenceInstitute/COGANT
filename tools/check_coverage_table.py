#!/usr/bin/env python3
"""Compare generated manuscript tables to their machine-readable sources.

The table in ``manuscript/06_04_tests_mutation_and_benchmarks.md`` ({#tbl:coverage-stmt-modules})
is maintained manually from ``coverage report`` / ``coverage.json``. The fixture
metric tables in ``06_03_performance_and_fixture_metrics.md`` are maintained from
``cogant/evaluation/figures/metrics.json``, and the benchmark table in
``06_04_tests_mutation_and_benchmarks.md`` is maintained from the benchmark JSON
sidecar named in ``METRICS.yaml``. This script checks all of those non-METRICS
tables so a strict gate can catch table drift from committed artifacts.

Exit codes
----------
* ``0`` — all rows match (or no manuscript table / nothing to compare).
* ``1`` — mismatch, missing ``coverage`` data when ``--strict``, or table parse error.

Path layout: ``{tools,manuscript,cogant/}`` at the COGANT project root, or
``projects/cogant/{tools,manuscript,cogant/}`` when vendored into the parent
template. ``--package-root`` should point to the directory that contains the
inner ``cogant`` test tree and ``pyproject.toml`` used for ``pytest``."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


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
        if in_table and "{#tbl:coverage-stmt-modules}" in line:
            break
        if not in_table:
            continue
        m = row_re.match(line)
        if m:
            mod, stmts, cover = m.group(1), int(m.group(2)), int(m.group(3))
            rows.append((mod, stmts, cover))
    return rows


def _split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _strip_markdown(cell: str) -> str:
    return (
        cell.replace("`", "")
        .replace("**", "")
        .replace("\\", "")
        .strip()
    )


def _numeric_cell(cell: str) -> float:
    cleaned = _strip_markdown(cell)
    if cleaned in {"---", "-", ""}:
        return 0.0
    cleaned = cleaned.rstrip("%")
    return float(cleaned)


def _fixture_cell(cell: str) -> str:
    return _strip_markdown(cell)


def _parse_captioned_table(
    md_path: Path,
    header_prefix: str,
    caption_id: str,
) -> list[list[str]]:
    text = md_path.read_text(encoding="utf-8")
    rows: list[list[str]] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(header_prefix):
            in_table = True
            continue
        if in_table and caption_id in stripped:
            break
        if not in_table or not stripped.startswith("|"):
            continue
        cells = _split_markdown_row(stripped)
        if not cells or all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(cells)
    return rows


def _file_to_module(path: str) -> str:
    """``py/cogant/translate/engine.py`` -> ``cogant.translate.engine``."""
    p = path.strip()
    if p.startswith("py/cogant/"):
        p = p[3:]
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
        if not (path.startswith("cogant/") or path.startswith("py/cogant/")):
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


def _load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _load_metrics_yaml(package_root: Path) -> dict[str, Any]:
    metrics_path = package_root / "evaluation" / "METRICS.yaml"
    if not metrics_path.is_file():
        return {}
    try:
        import yaml

        data = yaml.safe_load(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _compare_metric_row(
    findings: list[str],
    *,
    table_name: str,
    fixture: str,
    label: str,
    actual: float,
    expected: float,
    tolerance: float = 0.0,
) -> None:
    if abs(actual - expected) <= tolerance:
        return
    findings.append(
        f"  {table_name}/{fixture}/{label}: table={actual:g} vs artifact={expected:g}"
    )


def _check_metric_tables(manuscript_dir: Path, package_root: Path) -> list[str]:
    md_path = manuscript_dir / "06_03_performance_and_fixture_metrics.md"
    metrics_path = package_root / "evaluation" / "figures" / "metrics.json"
    metrics = _load_json(metrics_path)
    if not md_path.is_file() or not isinstance(metrics, dict):
        return [f"  metrics tables: missing {md_path} or unusable {metrics_path}"]

    findings: list[str] = []

    repo_rows = _parse_captioned_table(
        md_path,
        "| Fixture | Files | LOC | Nodes | Edges | Mappings | State vars |",
        "{#tbl:repo-pipeline-metrics}",
    )
    if not repo_rows:
        findings.append("  repo-pipeline-metrics: no rows parsed")
    repo_fields = [
        ("files", "files", 0.0),
        ("loc", "loc", 0.0),
        ("nodes", "nodes", 0.0),
        ("edges", "edges", 0.0),
        ("mappings", "mappings_total", 0.0),
        ("state_vars", "state_variables", 0.0),
        ("obs", "observations", 0.0),
        ("actions", "actions", 0.0),
        ("transitions", "transitions", 0.0),
        ("gnn_sections", "gnn_sections", 0.0),
        ("gnn_score", "gnn_score", 0.01),
        ("wall_clock_s", "elapsed_s", 0.01),
    ]
    for row in repo_rows:
        fixture = _fixture_cell(row[0])
        source = metrics.get(fixture)
        if not isinstance(source, dict):
            findings.append(f"  repo-pipeline-metrics/{fixture}: fixture missing from {metrics_path}")
            continue
        for index, (label, key, tolerance) in enumerate(repo_fields, start=1):
            _compare_metric_row(
                findings,
                table_name="repo-pipeline-metrics",
                fixture=fixture,
                label=label,
                actual=_numeric_cell(row[index]),
                expected=float(source.get(key, 0)),
                tolerance=tolerance,
            )

    graph_rows = _parse_captioned_table(
        md_path,
        "| Fixture | MODULE | CLASS | METHOD | FUNCTION | CONTAINS |",
        "{#tbl:fixture-graph-metrics}",
    )
    if not graph_rows:
        findings.append("  fixture-graph-metrics: no rows parsed")
    graph_fields = [
        ("MODULE", "nodes_by_kind", "MODULE"),
        ("CLASS", "nodes_by_kind", "CLASS"),
        ("METHOD", "nodes_by_kind", "METHOD"),
        ("FUNCTION", "nodes_by_kind", "FUNCTION"),
        ("CONTAINS", "edges_by_kind", "CONTAINS"),
        ("WRITES", "edges_by_kind", "WRITES"),
        ("READS", "edges_by_kind", "READS"),
        ("CALLS", "edges_by_kind", "CALLS"),
        ("IMPORTS", "edges_by_kind", "IMPORTS"),
        ("INHERITS", "edges_by_kind", "INHERITS"),
    ]
    for row in graph_rows:
        fixture = _fixture_cell(row[0])
        source = metrics.get(fixture)
        if not isinstance(source, dict):
            findings.append(f"  fixture-graph-metrics/{fixture}: fixture missing from {metrics_path}")
            continue
        for index, (label, group, key) in enumerate(graph_fields, start=1):
            bucket = source.get(group)
            expected = float((bucket or {}).get(key, 0)) if isinstance(bucket, dict) else 0.0
            _compare_metric_row(
                findings,
                table_name="fixture-graph-metrics",
                fixture=fixture,
                label=label,
                actual=_numeric_cell(row[index]),
                expected=expected,
            )

    state_rows = _parse_captioned_table(
        md_path,
        "| Fixture | State variables | Observations | Actions |",
        "{#tbl:state-space-compilation}",
    )
    if not state_rows:
        findings.append("  state-space-compilation: no rows parsed")
    state_fields = [
        ("state_variables", "state_variables"),
        ("observations", "observations"),
        ("actions", "actions"),
        ("transitions", "transitions"),
        ("policies", "policies"),
    ]
    for row in state_rows:
        fixture = _fixture_cell(row[0])
        source = metrics.get(fixture)
        if not isinstance(source, dict):
            findings.append(f"  state-space-compilation/{fixture}: fixture missing from {metrics_path}")
            continue
        for index, (label, key) in enumerate(state_fields, start=1):
            _compare_metric_row(
                findings,
                table_name="state-space-compilation",
                fixture=fixture,
                label=label,
                actual=_numeric_cell(row[index]),
                expected=float(source.get(key, 0)),
            )

    output_rows = _parse_captioned_table(
        md_path,
        "| Fixture | `gnn_package/` files | Validation errors |",
        "{#tbl:output-artifacts-per-run}",
    )
    if not output_rows:
        findings.append("  output-artifacts-per-run: no rows parsed")
    output_fields = [
        ("gnn_package_files", "gnn_package_files"),
        ("gnn_errors", "gnn_errors"),
        ("gnn_warnings", "gnn_warnings"),
    ]
    for row in output_rows:
        fixture = _fixture_cell(row[0])
        source = metrics.get(fixture)
        if not isinstance(source, dict):
            findings.append(f"  output-artifacts-per-run/{fixture}: fixture missing from {metrics_path}")
            continue
        for index, (label, key) in enumerate(output_fields, start=1):
            _compare_metric_row(
                findings,
                table_name="output-artifacts-per-run",
                fixture=fixture,
                label=label,
                actual=_numeric_cell(row[index]),
                expected=float(source.get(key, 0)),
            )

    return findings


def _benchmark_sidecar_path(package_root: Path) -> Path:
    metrics = _load_metrics_yaml(package_root)
    suite_file = ((metrics.get("benchmark") or {}).get("benchmark_suite_file") or "").strip()
    if suite_file.endswith(".md"):
        return package_root / "benchmarks" / "results" / suite_file.replace(".md", ".json")
    candidates = sorted((package_root / "benchmarks" / "results").glob("suite_*.json"))
    return candidates[-1] if candidates else package_root / "benchmarks" / "results" / "suite_UNKNOWN.json"


def _check_benchmark_table(md_path: Path, package_root: Path) -> list[str]:
    suite_path = _benchmark_sidecar_path(package_root)
    suite = _load_json(suite_path)
    if not md_path.is_file() or not isinstance(suite, dict):
        return [f"  benchmark-suite-results: missing {md_path} or unusable {suite_path}"]
    fixtures = suite.get("fixtures")
    if not isinstance(fixtures, dict):
        return [f"  benchmark-suite-results: no fixture block in {suite_path}"]
    rows = _parse_captioned_table(
        md_path,
        "| Fixture | Wall-clock median (ms) | Wall-clock p95 (ms) |",
        "{#tbl:benchmark-suite-results}",
    )
    findings: list[str] = []
    if not rows:
        findings.append("  benchmark-suite-results: no rows parsed")
    for row in rows:
        fixture = _fixture_cell(row[0])
        source = fixtures.get(fixture)
        if not isinstance(source, dict):
            findings.append(f"  benchmark-suite-results/{fixture}: fixture missing from {suite_path}")
            continue
        wall = source.get("wall_ms") or {}
        graph = source.get("graph") or {}
        memory = source.get("memory_mb") or {}
        expected_values = [
            ("wall_median_ms", round(float(wall.get("median", 0)))),
            ("wall_p95_ms", round(float(wall.get("p95", 0)))),
            ("nodes", float(graph.get("nodes", 0))),
            ("edges", float(graph.get("edges", 0))),
            ("mappings", float(source.get("mappings_total", 0))),
            ("peak_memory_mb", round(float(memory.get("peak_delta_median", 0)), 1)),
        ]
        for index, (label, expected) in enumerate(expected_values, start=1):
            _compare_metric_row(
                findings,
                table_name="benchmark-suite-results",
                fixture=fixture,
                label=label,
                actual=_numeric_cell(row[index]),
                expected=float(expected),
                tolerance=0.01,
            )
    return findings


def _run_coverage_report(package_root: Path) -> str | None:
    """Run ``coverage report`` in package_root; return stdout or None on failure."""
    try:
        proc = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
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


def _display_covered_int(pc: float) -> int:
    """Integer coverage percent as ``coverage report`` displays it (precision 0).

    Mirrors coverage.py ``Numbers.display_covered``: a value in ``(0, 1)`` shows
    as ``1`` and a value in ``(99, 100)`` shows as ``99`` — coverage never rounds
    up to a misleading ``0%`` or ``100%``. The manuscript table is built from this
    displayed value, so the committed-``coverage.json`` fallback must reproduce it
    rather than naively ``round()``-ing (which turned 99.79% into a false 100%).
    """
    if 0 < pc < 1:
        return 1
    if 99 < pc < 100:
        return 99
    return round(pc)


def _parse_coverage_json(json_path: Path) -> dict[str, tuple[int, int]] | None:
    """Parse a committed ``coverage.json`` file as a fallback when ``.coverage``
    SQLite is unavailable.

    Returns ``module -> (stmts, cover_percent)`` or ``None`` on parse failure.
    This is the durable path: ``coverage.json`` is committed in the repo
    (RedTeam F10 noted that the .coverage SQLite is NOT committed, so
    ``--strict`` checking from a clean checkout requires a JSON fallback).
    """
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    files = data.get("files")
    if not isinstance(files, dict):
        return None
    out: dict[str, tuple[int, int]] = {}
    for path, payload in files.items():
        mod = _file_to_module(path)
        if not mod:
            continue
        summary = (payload or {}).get("summary") or {}
        stmts = summary.get("num_statements")
        percent = summary.get("percent_covered")
        if stmts is None or percent is None:
            continue
        try:
            out[mod] = (int(stmts), _display_covered_int(float(percent)))
        except (TypeError, ValueError):
            continue
    return out or None


def _table_mismatches(
    table: list[tuple[str, int, int]],
    live: dict[str, tuple[int, int]],
) -> list[str]:
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
    return bad


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

    live: dict[str, tuple[int, int]] | None = None
    live_source = "coverage report"
    report = _run_coverage_report(package_root)
    if report is not None:
        live = _parse_coverage_report(report)
        if not live:
            print(
                "check_coverage_table: parsed zero modules from coverage report output.",
                file=sys.stderr,
            )

    json_path = package_root / "coverage.json"
    json_live = _parse_coverage_json(json_path) if json_path.is_file() else None

    # Fallback to committed coverage.json (RedTeam F10 — .coverage SQLite
    # is not committed; coverage.json is). This makes the gate runnable on
    # a clean checkout, not just after a fresh pytest --cov run. It also
    # avoids letting a stale local .coverage file mask the committed
    # canonical artifact when the JSON exactly matches the manuscript table.
    if not live and json_live:
        live = json_live
        live_source = f"coverage.json fallback at {json_path}"
        print(f"check_coverage_table: using committed {live_source}", file=sys.stderr)

    if not live:
        print(
            f"check_coverage_table: could not run `uv run python -m coverage report` in {package_root} "
            f"and no usable coverage.json fallback found. "
            f"Run `uv run pytest tests/ --cov=py/cogant` there first to produce .coverage, "
            f"or commit a populated coverage.json.",
            file=sys.stderr,
        )
        return 1 if args.strict else 0

    bad = _table_mismatches(table, live)
    if bad and json_live and live is not json_live:
        json_bad = _table_mismatches(table, json_live)
        if not json_bad:
            print(
                "check_coverage_table: local coverage report mismatches manuscript; "
                f"using committed coverage.json fallback at {json_path}",
                file=sys.stderr,
            )
            live = json_live
            live_source = f"coverage.json fallback at {json_path}"
            bad = []

    if bad:
        print("check_coverage_table: mismatches:\n" + "\n".join(bad), file=sys.stderr)
        return 1

    generated_findings = _check_metric_tables(manuscript.parent, package_root)
    generated_findings.extend(_check_benchmark_table(manuscript, package_root))
    if generated_findings:
        print(
            "check_coverage_table: generated-table mismatches:\n"
            + "\n".join(generated_findings),
            file=sys.stderr,
        )
        return 1

    print(
        f"check_coverage_table: OK ({len(table)} coverage rows match {live_source}; "
        "metrics.json and benchmark JSON tables match committed artifacts)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
